from flask import Flask, request, jsonify
from flask_cors import cross_origin
import logging
import os
import threading
import json
import re

from history_management import history_blueprint
from project_management import project_blueprint
from text_processing import *  # noqa: F403
from llm_annotation import run_llm_annotation, call_llm  # noqa: F401


# -----------------------------------------------------------------------------
# App + Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.register_blueprint(history_blueprint)
app.register_blueprint(project_blueprint)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FOLDER = os.path.join(BASE_DIR, "history")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def normalize_folder_path(folder: str) -> str:
    """Convert custom delimiter to folder separators and strip whitespace."""
    return re.sub(r"___", "/", (folder or "").strip())


def clean_html(html_text: str) -> str:
    """Strip basic HTML tags while preserving readable text."""
    try:
        from bs4 import BeautifulSoup  # local import to avoid hard dependency at import time

        soup = BeautifulSoup(html_text or "", "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except Exception:
        return html_text or ""


# -----------------------------------------------------------------------------
# API: Upload history
# -----------------------------------------------------------------------------
@app.route("/api/upload-history", methods=["POST"])
@cross_origin()
def upload_history_file():
    curr_folder = request.form.get("curr_folder")
    if not curr_folder:
        return jsonify({"error": "Missing target folder"}), 400

    curr_folder = normalize_folder_path(curr_folder)
    target_folder = os.path.join(HISTORY_FOLDER, curr_folder)

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename.endswith(".json"):
        return jsonify(
            {"error": "Unsupported file format. Only JSON files are allowed."}
        ), 400

    original_filename = uploaded_file.filename
    file_name, file_extension = os.path.splitext(original_filename)

    os.makedirs(target_folder, exist_ok=True)
    file_path = os.path.join(target_folder, original_filename)

    counter = 1
    while os.path.exists(file_path):
        file_path = os.path.join(
            target_folder, f"{file_name}({counter}){file_extension}"
        )
        counter += 1

    try:
        uploaded_file.save(file_path)
        return (
            jsonify(
                {"message": f"File {os.path.basename(file_path)} uploaded successfully."}
            ),
            200,
        )
    except Exception as e:
        logging.error(f"Error while uploading history file: {e}")
        return jsonify({"error": f"Failed to upload file: {str(e)}"}), 500


# -----------------------------------------------------------------------------
# API: Load / create / delete a history file
# -----------------------------------------------------------------------------
@app.route("/api/history/<path:file_path>", methods=["GET", "POST", "DELETE"])
@cross_origin()
def history_file(file_path):
    try:
        parts = file_path.split("___") if "___" in file_path else [file_path]
        json_file_path = os.path.join(HISTORY_FOLDER, *parts)
        logging.debug(f"Accessing file at {json_file_path}")

        if request.method in ["GET", "POST"]:
            if not os.path.exists(json_file_path):
                data = request.get_json(silent=True) or {}
                narrative = (data.get("narrative") or "").strip()

                if narrative:
                    logging.info(
                        "File not found. Creating a new file with provided narrative."
                    )
                    os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
                    with open(json_file_path, "w", encoding="utf-8") as f:
                        json.dump(
                            {"pages": [narrative], "annotations": [], "meta": {}},
                            f,
                            ensure_ascii=False,
                            indent=2,
                        )
                else:
                    return jsonify({"error": "File not found and no narrative provided"}), 404

            with open(json_file_path, "r", encoding="utf-8", errors="ignore") as f:
                json_data = json.load(f)

            # Best-effort decode legacy content
            try:
                json_data["pages"] = [
                    x.encode("latin1").decode("utf-8") for x in json_data.get("pages", [])
                ]
            except Exception:
                pass

            return jsonify(json_data), 200

        if request.method == "DELETE":
            if not os.path.exists(json_file_path):
                return jsonify({"error": "File not found"}), 404

            os.remove(json_file_path)
            return jsonify({"message": f"{parts[-1]} deleted successfully."}), 200

        return jsonify({"error": "Unsupported method"}), 405

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# API: Save (pages/annotations/meta) to history file
# -----------------------------------------------------------------------------
@app.route("/api/save", methods=["POST"])
@cross_origin()
def save_file():
    data = request.get_json(silent=True) or {}

    file_name = (data.get("fileName") or "").strip()
    curr_folder = (data.get("curr_folder") or "").strip()
    pages = data.get("pages") or []
    annotations = data.get("annotations") or []
    meta = data.get("meta") or {}

    if not file_name or not pages:
        return jsonify({"error": "File name and content are required"}), 400

    curr_folder = normalize_folder_path(curr_folder)
    full_path = os.path.join(HISTORY_FOLDER, curr_folder) if curr_folder else HISTORY_FOLDER
    os.makedirs(full_path, exist_ok=True)

    json_file_path = os.path.join(full_path, f"{file_name}.json")

    try:
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(
                {"pages": pages, "annotations": annotations, "meta": meta},
                f,
                ensure_ascii=False,
                indent=2,
            )
        return jsonify({"message": "File saved successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# API: List meta files
# -----------------------------------------------------------------------------
@app.route("/api/meta-files", methods=["GET"])
@cross_origin()
def list_meta_files():
    try:
        meta_folder = os.path.join(HISTORY_FOLDER, "Meta")
        if not os.path.exists(meta_folder):
            return jsonify([]), 200

        meta_files = [f.name for f in os.scandir(meta_folder) if f.name.endswith(".xlsx")]
        return jsonify(meta_files), 200
    except Exception as e:
        logging.error(f"Error listing meta files: {e}")
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# API: Trigger LLM annotation (background)
# -----------------------------------------------------------------------------
@app.route("/api/llm-annotate", methods=["POST"])
@cross_origin()
def trigger_llm_annotation():
    try:
        req = request.get_json(silent=True) or {}
        file_name = (req.get("file") or "").strip()
        folder = (req.get("folder") or "").strip()

        if not file_name or not folder:
            return jsonify({"error": "Missing file or folder name"}), 400

        if not file_name.endswith(".json"):
            file_name += ".json"

        full_path = os.path.join(HISTORY_FOLDER, folder, file_name)
        if not os.path.exists(full_path):
            return jsonify({"error": f"File not found: {full_path}"}), 404

        def background_task():
            # Step 1: Load and remove LLM annotations
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            annotations = data.get("annotations", [])
            cleaned = [a for a in annotations if "LLM" not in (a.get("note") or "")]
            data["annotations"] = cleaned

            # Set meta.llm_processed to 'working'
            data.setdefault("meta", {})
            data["meta"]["llm_processed"] = "working"

            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Step 2: Run fresh LLM annotation
            run_llm_annotation(full_path)

        threading.Thread(target=background_task, daemon=True).start()

        return (
            jsonify({"message": f"LLM annotation started for {file_name}", "file_locked": file_name}),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# Content generators
# -----------------------------------------------------------------------------
def generate_demographic_content(row, mode="RxLogix"):
    demographic_keys = [
        "Attachments Info-Link",
        "Age in Years",
        "Sex",
        "Weight In kg",
        "Medical History and Comments",
        "Reporter Qualifications",
        "Health Professional",
        "All Lab Tests",
        "Confirmatory Test Comments",
        "Seriousness",
        "All Outcomes",
    ]

    demographic_html = "<div class='mb-4 space-y-4 text-sm text-gray-800'>"

    for key in demographic_keys:
        value = str(row.get(key, "")).strip()
        if not value:
            continue

        if key in ["Medical History and Comments", "Medical History/Medical History Comments"]:
            items = [item.strip(" ;)") for item in value.split(";") if item.strip()]
            formatted = f"<p class='text-gray-900 mt-1'>{'; '.join(items)}</p>"
        else:
            formatted = f"<p class='text-gray-900 mt-1'>{value}</p>"

        demographic_html += f"""
            <div>
                <h4>{key}</h4>
                {formatted}
            </div>
        """

    demographic_html += "</div>"
    return demographic_html


def generate_outcomes_content(row, mode="RxLogix"):
    if mode == "InfoVIP":
        categories = ["All LLTs", "All PTs", "All HLTs", "All HLGTs", "All SOCs"]

        def parse_list(text):
            return [item.strip() for item in (text or "").split(":") if item.strip()]

        include_start_date = False
    else:
        categories = ["All SOCs", "All HLGTs", "All HLTs", "All PTs", "All LLTs"]

        def parse_list(text):
            return [
                (int(item.split(")", 1)[0]), item.split(")", 1)[1].strip())
                for item in (text or "").split(";")
                if item.strip()
            ]

        include_start_date = True

    parsed_data = {category: parse_list(row.get(category, "")) for category in categories}
    max_items = max((len(parsed_data[category]) for category in categories), default=0)

    pt_table_html = [
        "<div class='mb-4 overflow-hidden'>",
        "<table class='min-w-full text-sm border border-gray-300 rounded shadow-md'>",
        "<thead class='bg-gray-100 text-left'><tr>",
        "<th class='px-4 py-2 border'>Term ID</th>",
        "<th class='px-4 py-2 border'>MedDRA</th>",
        "<th class='px-4 py-2 border'>PT</th>",
        "<th class='px-4 py-2 border'>LLT</th>",
    ]

    if include_start_date:
        pt_table_html.append("<th class='px-4 py-2 border'>Start Date</th>")

    pt_table_html.append("</tr></thead><tbody>")

    for i in range(max_items):
        term_id = i + 1

        if mode == "InfoVIP":
            soc = parsed_data["All SOCs"][i] if i < len(parsed_data["All SOCs"]) else ""
            hlgt = parsed_data["All HLGTs"][i] if i < len(parsed_data["All HLGTs"]) else ""
            hlt = parsed_data["All HLTs"][i] if i < len(parsed_data["All HLTs"]) else ""
            pt = parsed_data["All PTs"][i] if i < len(parsed_data["All PTs"]) else ""
            llt = parsed_data["All LLTs"][i] if i < len(parsed_data["All LLTs"]) else ""
            term = ""
            date = ""
        else:
            soc = next((item[1] for item in parsed_data["All SOCs"] if item[0] == term_id), "")
            hlgt = next((item[1] for item in parsed_data["All HLGTs"] if item[0] == term_id), "")
            hlt = next((item[1] for item in parsed_data["All HLTs"] if item[0] == term_id), "")
            pt = next((item[1] for item in parsed_data["All PTs"] if item[0] == term_id), "")
            llt = next((item[1] for item in parsed_data["All LLTs"] if item[0] == term_id), "")
            term = (row.get(f"PT Term Event {term_id}") or "").strip()
            date = (row.get(f"Start Date Event {term_id}") or "").strip()

        if any([soc, hlgt, hlt, pt, llt, term]):
            pt_cell = pt or term if mode == "RxLogix" else pt

            row_html = [
                "<tr class='hover:bg-gray-50'>",
                f"<td class='px-4 py-2 border'>{term_id}</td>",
                f"<td class='px-4 py-2 border'>{soc}/{hlgt}/{hlt}</td>",
                f"<td class='px-4 py-2 border'>{pt_cell}</td>",
                f"<td class='px-4 py-2 border'>{llt}</td>",
            ]

            if include_start_date:
                row_html.append(f"<td class='px-4 py-2 border'>{date}</td>")

            row_html.append("</tr>")
            pt_table_html.extend(row_html)

    pt_table_html.append("</tbody></table></div>")
    return "\n".join(pt_table_html)


def generate_products_content(row, columns, mode="RxLogix"):
    if mode == "RxLogix":
        product_keys = [
            "Product Name",
            "Product Active Ingredient",
            "Reported Verbatim",
            "Compounded Product",
            "Combination Product",
            "Role",
            "Reason for Use",
            "Strength",
            "Strength (Unit)",
            "Dose (Amount)",
            "Dose (Unit)",
            "Dosage Text",
            "Dosage Form",
            "Route",
            "Frequency",
            "Dechallenge",
            "Rechallenge",
            "Start Date",
            "Stop Date",
            "Therapy Duration (Days)",
            "Therapy Duration (Verbatim)",
            "Time To Onset (Days)",
            "Manufacturer",
            "Application Type",
            "Application #",
            "NDC #",
            "LOT #",
        ]
    else:
        product_keys = [
            "Product Name",
            "Prod Active Ingred",
            "Reported Verbatim",
            "Compounded Product",
            "Combination Product",
            "Role",
            "Reason for Use",
            "Strength",
            "Strength Unit",
            "Dose Amount",
            "Dose Unit",
            "Dosage Text",
            "Dosage Form",
            "Route",
            "Frequency",
            "Dechallenge",
            "Rechallenge",
            "Start Date",
            "Stop Date",
            "Therapy Duration",
            "Time To Onset",
            "Manufacturer",
            "Application Type",
            "Application Number",
            "NDC Number",
            "Lot Number",
        ]

    # Detect prefixes (Product 1, Product 2, etc.)
    product_prefixes = set()
    for col in columns:
        if col.startswith("Product ") and "Product Name" in col:
            prefix = col.split("Product Name")[0].strip()
            product_prefixes.add(prefix)

    grouped_products = {"Suspect": [], "Concomitant": [], "Other": []}

    def prefix_sort_key(p: str) -> int:
        parts = p.split()
        return int(parts[-1]) if parts and parts[-1].isdigit() else 0

    for prefix in sorted(product_prefixes, key=prefix_sort_key):
        product_data = {col[len(prefix):].strip(): row[col] for col in columns if col.startswith(prefix)}
        role = str(product_data.get("Role", "")).strip().lower()

        if role == "suspect":
            grouped_products["Suspect"].append(product_data)
        elif role == "concomitant":
            grouped_products["Concomitant"].append(product_data)
        else:
            grouped_products["Other"].append(product_data)

    def render_product(product_data):
        rows_html = ""
        for key in product_keys:
            value = str(product_data.get(key, "")).strip()
            if value:
                rows_html += f"""
                    <tr>
                        <td class='pr-4 font-medium text-gray-700'>{key}:</td>
                        <td class='text-gray-900'>{value}</td>
                    </tr>
                """

        name = product_data.get("Product Name", "(Unnamed Product)")
        return f"""
            <div class='mb-4 border border-gray-200 rounded-lg bg-white p-3 shadow-sm'>
                <h4 class='font-semibold text-blue-800 mb-2'>{name}</h4>
                <table class='text-sm table-auto'>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        """

    products_html = ""

    for category, items in grouped_products.items():
        if not items:
            continue

        block = "\n".join(render_product(p) for p in items)
        products_html += f"""
            <details class='mb-4 border rounded-lg bg-white shadow-sm overflow-hidden'>
                <summary class='cursor-pointer select-none px-4 py-2 font-semibold bg-blue-50 text-blue-800 hover:bg-blue-100'>
                    {category} Products ({len(items)})
                </summary>
                <div class='px-4 py-3'>
                    {block}
                </div>
            </details>
        """

    return products_html


# -----------------------------------------------------------------------------
# API: LLM assess scores
# -----------------------------------------------------------------------------
@app.route("/api/llm-assess-scores", methods=["POST"])
@cross_origin()
def llm_assess_scores():
    try:
        data = request.get_json(silent=True) or {}

        narrative = (data.get("narrative") or "").strip()
        demographic_html = (data.get("demographic_html") or "").strip()
        products_html = (data.get("products_html") or "").strip()
        outcomes_html = (data.get("outcomes_html") or "").strip()

        if not narrative:
            return jsonify({"error": "Missing narrative"}), 400

        demographic_text = clean_html(demographic_html)
        products_text = clean_html(products_html)
        outcomes_text = clean_html(outcomes_html)

        icsr_material = f"""[Narratives]
{narrative}

[Demographic Information]
{demographic_text}

[Product Information]
{products_text}

[Outcomes]
{outcomes_text}
"""

        prompt_scores = """
You are a PharmacoVigilance expert. Based ONLY on the provided ICSR case material (narratives and structured data), you must estimate how reasonable each of the following five causality judgments would be if made by a human reviewer:

- Certain
- Probable
- Possible
- Unlikely
- Unassessable

You MUST:
* Consider all five options simultaneously.
* Assign a probability (0–100) to EACH option.
* Ensure the probabilities are integers and sum exactly to 100.
* Indicate which option is overall most consistent with the evidence.

Your response MUST be a single valid JSON object (no markdown, no commentary), exactly in this form:

{
  "scores": {
    "Certain": 0,
    "Probable": 0,
    "Possible": 0,
    "Unlikely": 0,
    "Unassessable": 0
  },
  "recommended_judgment": "Certain | Probable | Possible | Unlikely | Unassessable"
}

Rules:
* All five keys under "scores" MUST be present.
* All score values MUST be integers between 0 and 100.
* The sum of all five scores MUST be exactly 100.
* "recommended_judgment" MUST be set to the single option with the highest score (break ties based on overall clinical plausibility).
"""

        user_message = f"""### ICSR Case Material
{icsr_material}
"""

        # NOTE: this assumes you have an ai_client object defined elsewhere
        raw = ai_client.call(user_message, prompt_scores, temperature=0.0, max_tokens=2000)  # noqa: F821
        raw = (raw or "").strip()

        json_text = raw
        if raw.startswith("```"):
            try:
                first = raw.index("```")
                second = raw.rindex("```")
                inner = raw[first + 3 : second]
                inner = inner.lstrip("json").lstrip()
                json_text = inner
            except Exception:
                json_text = raw

        try:
            parsed = json.loads(json_text)
        except Exception as e:
            logging.error(
                f"Failed to parse LLM assess scores JSON. Error: {e}. Raw: {raw}"
            )
            return (
                jsonify(
                    {
                        "scores": {
                            "Certain": 20,
                            "Probable": 20,
                            "Possible": 20,
                            "Unlikely": 20,
                            "Unassessable": 20,
                        },
                        "recommended_judgment": None,
                    }
                ),
                200,
            )

        return jsonify(parsed), 200

    except Exception as e:
        logging.error(f"Error in /api/llm-assess-scores: {e}")
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# API: LLM assess explanation
# -----------------------------------------------------------------------------
@app.route("/api/llm-assess", methods=["POST"])
@cross_origin()
def llm_assess_explanation():
    try:
        data = request.get_json(silent=True) or {}

        narrative = (data.get("narrative") or "").strip()
        demographic_html = (data.get("demographic_html") or "").strip()
        products_html = (data.get("products_html") or "").strip()
        outcomes_html = (data.get("outcomes_html") or "").strip()
        judgment = (data.get("judgment") or "").strip()

        if not narrative or not judgment:
            return jsonify({"error": "Missing narrative or judgment"}), 400

        demographic_text = clean_html(demographic_html)
        products_text = clean_html(products_html)
        outcomes_text = clean_html(outcomes_html)

        icsr_material = f"""[Narratives]
{narrative}

[Demographic Information]
{demographic_text}

[Product Information]
{products_text}

[Outcomes]
{outcomes_text}
"""

        prompt1 = """
Instruction:

You are a PharmacoVigilance expert. Your task is to analyze an Individual Case Safety Report (ICSR) and a pre-determined causality assessment made by a human reviewer.
Your goal is to "fit" the reviewer's answer by providing a detailed explanation of why they likely arrived at their conclusion (e.g., "Certain", "Probable", "Possible", "Unlikely", or "Unassessable").
You must base your entire analysis only on the provided ICSR materials (column data and narratives). Do not use any external knowledge about the drug or the adverse event.

Inputs:
1) The ICSR case material (narratives and structured data).
2) The Reviewer's final causality judgment: "Certain", "Probable", "Possible", "Unlikely", or "Unassessable".

Process:
First, identify the primary suspected drug and the primary adverse event from the report. Then, evaluate the case against the seven factors listed below.

Factors:
(G1) Time Relationship
(G2) Alternative Explanations
(G3) Response to Withdrawal (Dechallenge)
(G4) Pharmacological/Phenomenological Plausibility
(G5) Response to Re-administration (Rechallenge)
(G6) Need for More Data
(G7) Data Quality

Output:
Return a single valid JSON object:

{
  "header": {
    "suspected_drug": "string",
    "primary_adverse_event": "string",
    "judgment": "Certain | Probable | Possible | Unlikely | Unassessable"
  },
  "summary": "Short paragraph summarizing the key reasons for this judgment.",
  "reasons": [
    {
      "id": "G1",
      "title": "Time Relationship (G1)",
      "finding": "Concise sentence describing the assessment for this factor.",
      "evidence": "Direct quote or summary from the case supporting this finding."
    }
  ],
  "risk_warning": "If there is a major contradiction between the evidence and the judgment, put a concise warning here starting with '[Risk Warning]'. If there is no such contradiction, set this field to null."
}

Rules:
- Reasons must cover G1–G7 with no redundancy.
- If no meaningful discrepancy, risk_warning must be null.
- Output must be strictly valid JSON (no markdown).
"""

        user_message = f"""### ICSR Case Material
{icsr_material}

Reviewer's Final Causality Judgment
{judgment}
"""

        # NOTE: this assumes you have an ai_client object defined elsewhere
        raw = ai_client.call(user_message, prompt1, temperature=0.0, max_tokens=4000)  # noqa: F821
        raw = (raw or "").strip()

        json_text = raw
        if raw.startswith("```"):
            try:
                first = raw.index("```")
                second = raw.rindex("```")
                inner = raw[first + 3 : second]
                inner = inner.lstrip("json").lstrip()
                json_text = inner
            except Exception:
                json_text = raw

        try:
            parsed = json.loads(json_text)
        except Exception as e:
            logging.error(f"Failed to parse LLM assess JSON. Error: {e}. Raw: {raw}")
            return (
                jsonify(
                    {
                        "header": {
                            "suspected_drug": "",
                            "primary_adverse_event": "",
                            "judgment": judgment,
                        },
                        "summary": raw,
                        "reasons": [],
                        "risk_warning": None,
                    }
                ),
                200,
            )

        return jsonify(parsed), 200

    except Exception as e:
        logging.error(f"Error in /api/llm-assess: {e}")
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# API: Save assessment
# -----------------------------------------------------------------------------
@app.route("/api/save-assessment", methods=["POST"])
@cross_origin()
def save_assessment():
    try:
        data = request.get_json(silent=True) or {}

        file_name = (data.get("file") or "").strip()
        folder = (data.get("folder") or "").strip()
        assessment = data.get("assessment") or {}

        if not file_name or not folder:
            return jsonify({"error": "Missing file or folder name"}), 400

        if not file_name.endswith(".json"):
            file_name += ".json"

        full_path = os.path.join(HISTORY_FOLDER, folder, file_name)
        if not os.path.exists(full_path):
            return jsonify({"error": f"File not found: {full_path}"}), 404

        with open(full_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        if "meta" not in json_data or not isinstance(json_data["meta"], dict):
            json_data["meta"] = {}

        json_data["meta"]["assessment"] = assessment

        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        return jsonify({"message": "Assessment saved successfully."}), 200

    except Exception as e:
        logging.error(f"Error in /api/save-assessment: {e}")
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
