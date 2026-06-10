import fitz, re
from docx import Document
from charset_normalizer import from_path
import json
import pandas as pd

def sectionize_texts(text):
    pattern = re.compile(r'(?=\b(\d+\.\d+ [A-Z][a-z]+(?: [A-Z][a-z]+)*|\d+ [A-Z\s]+)\b)')

    # Split the text using the pattern, capturing the matched section headers
    html_content = pattern.sub(lambda match: f"<h3>{match.group(1)}</h3>", text)

    return html_content

def clean_text(text):
    # Remove non-printable characters
    return ''.join(c for c in text if c.isprintable())
    
def extract_text_from_pdf(file_path):
    pages = ''
    with fitz.open(file_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf.load_page(page_num)
            text_data = ''

            # Extract text blocks
            blocks = page.get_text("blocks")  # Returns a list of tuples with block details

            for block in blocks:
                x0, y0, x1, y1, text, bn, block_type = block

                # Only process text blocks (skip images or other non-text blocks)
                if block_type == 0:  # 0 means text block in PyMuPDF
                    # text = re.sub(r'(?<=\b(\.)\b)\n', ' ', text).strip()
                    # text_data += '<p>'+clean_text(text)+'</p>'
                    text_data += '<p>'+text+'</p>'    
                    
            pages += text_data
    return [pages,]
    
def extract_text_from_docx(file_path, max_paragraphs_per_page=10):
    pages = ''
    doc = Document(file_path)
    text = ''
    paragraph_count = 0

    for para in doc.paragraphs:
        formatted_text=para.text.strip()
        if not formatted_text:
            continue
        # Add the paragraph to the text with a newline
        # text += '<p>'+clean_text(formatted_text)+'</p>' 
        text += '<p>'+formatted_text+'</p>' 
        paragraph_count += 1

        # Check if we have reached the max paragraphs per "page"
        if paragraph_count >= max_paragraphs_per_page:
            pages += text
            text = ''
            paragraph_count = 0

    # Add any remaining text as the last page
    if text:
        pages += text

    return [pages,]

def generate_demographic_content(row, mode='RxLogix'):
    demographic_keys = [
            "Attachments Info-Link", "Age in Years", "Sex",
            "Weight In kg", "Medical History and Comments", "Reporter Qualifications", "Health Professional", "All Lab Tests",
            "Confirmatory Test Comments", "Seriousness", "All Outcomes"
    ]

    entries = []
    for key in demographic_keys:
        val = row.get(key, "")
        if pd.isna(val):
            continue
        value = str(val).strip() if isinstance(val, str) else str(val)
        if not value:
            continue

        if key in ["Medical History and Comments", "Medical History/Medical History Comments"]:
            items = [item.strip(' ;)') for item in value.split(';') if item.strip()]
            if not items:
                continue
            entries.append({
                "label": key,
                "type": "list",
                "items": items
            })
        else:
            entries.append({
                "label": key,
                "type": "text",
                "value": value
            })

    return entries
    
def generate_outcomes_content(row, mode='RxLogix'):
    if mode == 'InfoVIP':
        categories = ['All LLTs', 'All PTs', 'All HLTs', 'All HLGTs', 'All SOCs']
        include_start_date = False

        def parse_list(text):
            items = []
            for item in str(text).split(':'):
                value = item.strip()
                if not value:
                    continue
                items.append({"rank": None, "text": value})
            return items
    else:
        categories = ['All SOCs', 'All HLGTs', 'All HLTs', 'All PTs', 'All LLTs']
        include_start_date = True

        def parse_list(text):
            items = []
            for item in str(text).split(';'):
                value = item.strip()
                if not value:
                    continue
                match = re.match(r'^(\d+)\)\s*(.*)$', value)
                if match:
                    items.append({"rank": int(match.group(1)), "text": match.group(2).strip()})
                else:
                    items.append({"rank": None, "text": value})
            return items

    parsed_data = {category: parse_list(row.get(category, '')) for category in categories}
    max_items = max((len(parsed_data[category]) for category in categories), default=0)

    def fetch_value(category_list, index, rank=None):
        if rank:
            for entry in category_list:
                if entry.get("rank") == rank:
                    return entry.get("text", "")
        if index < len(category_list):
            return category_list[index].get("text", "")
        return ""

    rows = []
    for idx in range(max_items):
        term_id = idx + 1
        term_rank = term_id if mode != 'InfoVIP' else None
        soc = fetch_value(parsed_data['All SOCs'], idx, term_rank)
        hlgt = fetch_value(parsed_data['All HLGTs'], idx, term_rank)
        hlt = fetch_value(parsed_data['All HLTs'], idx, term_rank)
        pt = fetch_value(parsed_data['All PTs'], idx, term_rank)
        llt = fetch_value(parsed_data['All LLTs'], idx, term_rank)

        term_val = ''
        date = ''
        if mode != 'InfoVIP':
            term_raw = row.get(f"PT Term Event {term_id}", "")
            term_val = term_raw.strip() if isinstance(term_raw, str) else str(term_raw or "")
            date_val = row.get(f"Start Date Event {term_id}", "")
            date = date_val.strip() if isinstance(date_val, str) else str(date_val or "")

        if any([soc, hlgt, hlt, pt, llt, term_val]):
            rows.append({
                "term_id": term_id,
                "soc": soc,
                "hlgt": hlgt,
                "hlt": hlt,
                "pt": pt,
                "llt": llt,
                "term_label": pt or term_val,
                "term_event": term_val,
                "start_date": date,
            })

    categories_summary = {
        category: [
            {"rank": entry.get("rank"), "text": entry.get("text", "")}
            for entry in parsed_data[category]
            if entry.get("text")
        ]
        for category in categories
        if parsed_data[category]
    }

    return {
        "mode": mode,
        "rows": rows,
        "categories": categories_summary
    }


def generate_products_content(row, columns, mode='RxLogix'):
    if mode == 'RxLogix':
        product_keys = [
            "Product Name", "Product Active Ingredient", "Reported Verbatim", "Compounded Product", "Combination Product",
            "Role", "Reason for Use", "Strength", "Strength (Unit)", "Dose (Amount)", "Dose (Unit)",
            "Dosage Text", "Dosage Form", "Route", "Frequency", "Dechallenge", "Rechallenge",
            "Start Date", "Stop Date", "Therapy Duration (Days)", "Therapy Duration (Verbatim)", "Time To Onset (Days)", "Manufacturer",
            "Application Type", "Application #", "NDC #", "LOT #"
        ]
    else:  # InfoVIP export mode
        product_keys = [
            "Product Name", "Prod Active Ingred", "Reported Verbatim", "Compounded Product", "Combination Product",
            "Role", "Reason for Use", "Strength", "Strength Unit", "Dose Amount", "Dose Unit",
            "Dosage Text", "Dosage Form", "Route", "Frequency", "Dechallenge", "Rechallenge",
            "Start Date", "Stop Date", "Therapy Duration", "Time To Onset", "Manufacturer",
            "Application Type", "Application Number", "NDC Number", "Lot Number"
        ]

    product_prefixes = set()
    for col in columns:
        col_str = str(col)
        if col_str.startswith("Product ") and "Product Name" in col_str:
            prefix = col_str.split("Product Name")[0].strip()
            product_prefixes.add(prefix)

    grouped_products = {"Suspect": [], "Concomitant": [], "Other": []}
    sorted_prefixes = sorted(product_prefixes, key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 0)

    for prefix in sorted_prefixes:
        product_data = {str(col)[len(prefix):].strip(): row[col] for col in columns if str(col).startswith(prefix)}
        role = str(product_data.get("Role", "")).strip().lower()
        if role == "suspect":
            grouped_products["Suspect"].append(product_data)
        elif role == "concomitant":
            grouped_products["Concomitant"].append(product_data)
        else:
            grouped_products["Other"].append(product_data)

    def normalize_value(value):
        if pd.isna(value):
            return ""
        return str(value).strip()

    def to_fields(product_data):
        fields = []
        for key in product_keys:
            value = normalize_value(product_data.get(key, ""))
            if not value:
                continue
            fields.append({"label": key, "value": value})
        return fields

    def determine_display_name(product_data):
        for candidate in ["Product Name", "Prod Active Ingred", "Product Active Ingredient"]:
            val = normalize_value(product_data.get(candidate, ""))
            if val:
                return val
        return "(Unnamed Product)"

    groups = []
    for category, items in grouped_products.items():
        group_items = []
        for product_data in items:
            fields = to_fields(product_data)
            if not fields:
                continue
            group_items.append({
                "display_name": determine_display_name(product_data),
                "fields": fields,
            })
        if group_items:
            groups.append({
                "role": category,
                "count": len(group_items),
                "items": group_items
            })

    return {
        "mode": mode,
        "groups": groups
    }

def load_json_with_charset_normalizer(file_path):
    """
    Load a JSON file using charset-normalizer to auto-detect encoding.
    Returns parsed JSON content.
    """
    # Auto-detect and decode content
    result = from_path(file_path)
    decoded = result.best()
    
    if decoded is None:
        raise ValueError(f"Unable to detect encoding for file: {file_path}")

    return json.loads(str(decoded))


