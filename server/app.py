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
from database_manager import get_db_connection, get_project_by_name, get_case, upsert_case, get_annotations, get_user_by_note, authenticate_user
from ai_client import call_ai as ai_call

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
# Auth
# -----------------------------------------------------------------------------
@app.route("/api/login", methods=["POST"])
@cross_origin()
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    
    user = authenticate_user(username, password)
    if user:
        # For simple implementation, return user info. 
        # In real app, use JWT or sessions.
        return jsonify({
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "migration_key": user["migration_key"]
        }), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def normalize_folder_path(folder: str) -> str:
    """Convert custom delimiter to folder separators and strip whitespace."""
    return re.sub(r"___", "/", (folder or "").strip())

def clean_html(html_text: str) -> str:
    """Strip basic HTML tags while preserving readable text."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text or "", "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except Exception:
        return html_text or ""

# -----------------------------------------------------------------------------
# User Management (Admin only recommended)
# -----------------------------------------------------------------------------
@app.route("/api/users", methods=["GET"])
@cross_origin()
def list_users():
    conn = get_db_connection()
    users = conn.execute('''
        SELECT u.id, u.username, u.full_name, u.role_id, u.migration_key, r.name as role_name 
        FROM users u 
        JOIN roles r ON u.role_id = r.id
    ''').fetchall()
    conn.close()
    return jsonify([dict(u) for u in users]), 200

@app.route("/api/users", methods=["POST"])
@cross_origin()
def create_user():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    full_name = data.get("full_name")
    role_id = data.get("role_id")
    migration_key = data.get("migration_key")
    
    if not username or not password or not role_id:
        return jsonify({"error": "Missing required fields"}), 400
        
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO users (username, password, full_name, role_id, migration_key) 
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password, full_name, role_id, migration_key))
        conn.commit()
        return jsonify({"message": "User created"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/users/<int:user_id>", methods=["PUT"])
@cross_origin()
def update_user(user_id):
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    full_name = data.get("full_name")
    role_id = data.get("role_id")
    migration_key = data.get("migration_key")
    
    conn = get_db_connection()
    try:
        if password:
            conn.execute('''
                UPDATE users SET username = ?, password = ?, full_name = ?, role_id = ?, migration_key = ?
                WHERE id = ?
            ''', (username, password, full_name, role_id, migration_key, user_id))
        else:
            conn.execute('''
                UPDATE users SET username = ?, full_name = ?, role_id = ?, migration_key = ?
                WHERE id = ?
            ''', (username, full_name, role_id, migration_key, user_id))
        conn.commit()
        return jsonify({"message": "User updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/users/<int:user_id>", methods=["DELETE"])
@cross_origin()
def delete_user(user_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        return jsonify({"message": "User deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/roles", methods=["GET"])
@cross_origin()
def list_roles():
    conn = get_db_connection()
    roles = conn.execute('SELECT * FROM roles').fetchall()
    conn.close()
    return jsonify([dict(r) for r in roles]), 200

@app.route("/api/adjudicate", methods=["POST"])
@cross_origin()
def adjudicate():
    data = request.get_json()
    annotation_id = data.get("annotation_id")
    status = data.get("status") # approved, denied, modified
    reason = data.get("reason", "")
    adjudicator_id = data.get("user_id")
    
    if not annotation_id or not status:
        return jsonify({"error": "Missing required fields"}), 400
        
    conn = get_db_connection()
    try:
        import json
        from datetime import datetime
        adjudication_data = json.dumps({
            "status": status,
            "reason": reason,
            "adjudicator_id": adjudicator_id,
            "timestamp": datetime.now().isoformat()
        })
        conn.execute('UPDATE annotations SET adjudication = ? WHERE id = ?', (adjudication_data, annotation_id))
        conn.commit()
        return jsonify({"message": "Adjudication saved"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

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

        project = get_project_by_name(folder)
        if not project:
            return jsonify({"error": f"Project not found: {folder}"}), 404

        doc = get_case(project_id=project['id'], filename=file_name)
        if not doc:
            return jsonify({"error": f"Document not found: {file_name}"}), 404

        def background_task(doc_id):
            conn = get_db_connection()
            cursor = conn.execute('SELECT id FROM users WHERE role_id = (SELECT id FROM roles WHERE name = "AI")')
            ai_user_ids = [row['id'] for row in cursor.fetchall()]
            
            if ai_user_ids:
                placeholders = ', '.join(['?'] * len(ai_user_ids))
                conn.execute(f'DELETE FROM annotations WHERE case_id = ? AND user_id IN ({placeholders})', 
                             [doc_id] + ai_user_ids)

            doc_data = conn.execute('SELECT meta FROM cases WHERE id = ?', (doc_id,)).fetchone()
            meta = json.loads(doc_data['meta']) if doc_data['meta'] else {}
            meta["llm_processed"] = "working"
            conn.execute('UPDATE cases SET meta = ? WHERE id = ?', (json.dumps(meta), doc_id))
            conn.commit()
            conn.close()

            run_llm_annotation(doc_id=doc_id) 

        threading.Thread(target=background_task, args=(doc['id'],), daemon=True).start()
        return jsonify({"message": f"LLM annotation started", "file_locked": file_name}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# API: Save assessment to DB
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

        project = get_project_by_name(folder)
        doc = get_case(project_id=project['id'], filename=file_name)
        if not doc:
            return jsonify({"error": "Document not found"}), 404

        meta = json.loads(doc['meta']) if doc['meta'] else {}
        meta["assessment"] = assessment

        conn = get_db_connection()
        conn.execute('UPDATE cases SET meta = ? WHERE id = ?', (json.dumps(meta), doc['id']))
        conn.commit()
        conn.close()

        return jsonify({"message": "Assessment saved to database."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

        icsr_material = f"[Narratives]\n{narrative}\n\n[Demographic Information]\n{demographic_text}\n\n[Product Information]\n{products_text}\n\n[Outcomes]\n{outcomes_text}"

        prompt_scores = """
You are a PharmacoVigilance expert. Based ONLY on the provided ICSR case material (narratives and structured data), you must estimate how reasonable each of the following five causality judgments would be if made by a human reviewer:
- Certain, Probable, Possible, Unlikely, Unassessable.
Assign a probability (0–100) to EACH option summing to 100.
Return a single valid JSON object: {"scores": {"Certain": 0, ...}, "recommended_judgment": "..."}
"""
        raw = ai_call(f"### ICSR Case Material\n{icsr_material}", prompt_scores, temperature=0.0, max_tokens=2000)
        raw = (raw or "").strip()
        
        # Simple extraction for robustness
        if "```" in raw:
            raw = raw.split("```")[1].strip()
            if raw.startswith("json"): raw = raw[4:].strip()

        return jsonify(json.loads(raw)), 200
    except Exception as e:
        logging.error(f"Error in scores: {e}")
        return jsonify({"scores": {"Certain": 20, "Probable": 20, "Possible": 20, "Unlikely": 20, "Unassessable": 20}, "recommended_judgment": None}), 200

# -----------------------------------------------------------------------------
# API: LLM assess explanation
# -----------------------------------------------------------------------------
@app.route("/api/llm-assess", methods=["POST"])
@cross_origin()
def llm_assess_explanation():
    try:
        data = request.get_json(silent=True) or {}
        narrative = (data.get("narrative") or "").strip()
        judgment = (data.get("judgment") or "").strip()
        demographic_text = clean_html(data.get("demographic_html"))
        products_text = clean_html(data.get("products_html"))
        outcomes_text = clean_html(data.get("outcomes_html"))

        if not narrative or not judgment:
            return jsonify({"error": "Missing narrative or judgment"}), 400

        icsr_material = f"[Narratives]\n{narrative}\n\n[Demographic Info]\n{demographic_text}\n\n[Product Info]\n{products_text}\n\n[Outcomes]\n{outcomes_text}"
        
        prompt = "You are a PharmacoVigilance expert. Analyze the ICSR and fit the judgment: " + judgment + ". Factors G1-G7. Return JSON."
        raw = ai_call(f"### ICSR Case Material\n{icsr_material}\n\nJudgment: {judgment}", prompt, temperature=0.0, max_tokens=4000)
        
        if "```" in raw:
            raw = raw.split("```")[1].strip()
            if raw.startswith("json"): raw = raw[4:].strip()
            
        return jsonify(json.loads(raw)), 200
    except Exception as e:
        return jsonify({"header": {"judgment": judgment}, "summary": str(e), "reasons": []}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8862, debug=True)
