from flask import Flask, request, jsonify, redirect
from flask_cors import cross_origin
# ... (inside app.py)

import logging
import os
import threading
import json
import re

from history_management import history_blueprint
from project_management import project_blueprint
from text_processing import *  # noqa: F403
from llm_annotation import run_llm_annotation, call_llm  # noqa: F401
from database_manager import get_db_connection, get_project_by_name, get_case, upsert_case, get_annotations, get_user_by_note, authenticate_user, create_project, link_case_to_project
from llm_prompts import annotation_guideline
from ai_client import call_ai as ai_call

# -----------------------------------------------------------------------------
# App + Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

if __name__ != '__main__':
    # If running via gunicorn, bridge the loggers
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    # Ensure root logging also goes to gunicorn handlers
    logging.getLogger().handlers = gunicorn_logger.handlers
    logging.getLogger().setLevel(gunicorn_logger.level)

app.register_blueprint(history_blueprint)
app.register_blueprint(project_blueprint)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FOLDER = os.path.join(BASE_DIR, "history")

# -----------------------------------------------------------------------------
# Admin Dashboard / Stats
# -----------------------------------------------------------------------------
@app.route("/api/admin/stats", methods=["GET"])
@cross_origin()
def get_admin_stats():
    conn = get_db_connection()
    try:
        # Total counts
        project_count = conn.execute('SELECT COUNT(*) FROM projects').fetchone()[0]
        case_count = conn.execute('SELECT COUNT(*) FROM cases').fetchone()[0]
        user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        
        # BERT Processed Cases
        bert_cases = 0
        all_cases = conn.execute('SELECT meta FROM cases').fetchall()
        for c in all_cases:
            if c['meta']:
                meta = json.loads(c['meta'])
                if meta.get("bert_processed") == "Done":
                    bert_cases += 1
        
        # Annotations per type and source
        label_stats = conn.execute('''
            SELECT 
                a.label, 
                u.username,
                r.name as role_name,
                COUNT(*) as count 
            FROM annotations a
            JOIN users u ON a.user_id = u.id
            JOIN roles r ON u.role_id = r.id
            GROUP BY a.label, u.username, r.name
        ''').fetchall()
        
        label_distribution = {}
        for row in label_stats:
            label = row['label']
            count = row['count']
            username = row['username']
            role_name = row['role_name']
            
            if role_name == 'AI':
                if 'BERT' in username.upper():
                    source = 'BERT'
                else:
                    source = 'LLM'
            else:
                source = 'Human'
                
            if label not in label_distribution:
                label_distribution[label] = {'Human': 0, 'LLM': 0, 'BERT': 0, 'Total': 0}
            
            label_distribution[label][source] += count
            label_distribution[label]['Total'] += count
        
        # Annotations per user (Top 10)
        user_stats = conn.execute('''
            SELECT u.username, COUNT(a.id) as count 
            FROM users u
            JOIN annotations a ON u.id = a.user_id
            GROUP BY u.id
            ORDER BY count DESC
            LIMIT 10
        ''').fetchall()
        user_distribution = {row['username']: row['count'] for row in user_stats}
        
        return jsonify({
            "project_count": project_count,
            "case_count": case_count,
            "bert_processed_count": bert_cases,
            "user_count": user_count,
            "label_distribution": label_distribution,
            "user_distribution": user_distribution
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route("/api/admin/bert-annotate", methods=["POST"])
@cross_origin()
def trigger_batch_bert_annotation():
    # Only admin should trigger this
    # (Simple check for demo, real app would use token/session)
    
    def run_batch_bert():
        try:
            logging.info("Starting background batch BERT annotation")
            # We use a simplified single-process version for the server
            # to avoid complex multiprocessing/CUDA issues in Flask
            
            # Import NERClient here to avoid issues if not needed
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).resolve().parent.parent / "development" / "NER" / "scripts"))
            from ner_client import get_ner_client
            
            client = get_ner_client()
            conn = get_db_connection()
            
            # Get BERT user ID
            bert_user = conn.execute("SELECT id FROM users WHERE migration_key = 'BERT'").fetchone()
            if not bert_user:
                logging.error("BERT user not found")
                return
            bert_user_id = bert_user['id']
            
            # Get cases to process (narrative not empty and not processed)
            cases_to_process = conn.execute("SELECT id, pages, meta FROM cases").fetchall()
            
            for c in cases_to_process:
                meta = json.loads(c['meta']) if c['meta'] else {}
                if meta.get("bert_processed") == "Done":
                    continue
                
                pages = json.loads(c['pages']) if c['pages'] else [""]
                narrative = pages[0] if pages else ""
                if not narrative or not narrative.strip():
                    continue
                
                try:
                    entities = client.annotate_text(narrative)
                    
                    # Save results
                    with conn:
                        conn.execute("DELETE FROM annotations WHERE case_id = ? AND user_id = ?", (c['id'], bert_user_id))
                        for ent in entities:
                            conn.execute("""
                                INSERT INTO annotations 
                                (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (c['id'], bert_user_id, ent['label'], ent['start'], ent['end'], ent['text'], "BERT", "{}"))
                        
                        meta["bert_processed"] = "Done"
                        conn.execute("UPDATE cases SET meta = ? WHERE id = ?", (json.dumps(meta), c['id']))
                except Exception as ex:
                    logging.error(f"Error processing case {c['id']}: {ex}")
            
            conn.close()
            logging.info("Background batch BERT annotation finished")
            
        except Exception as e:
            logging.error(f"Batch BERT error: {e}")

    threading.Thread(target=run_batch_bert, daemon=True).start()
    return jsonify({"message": "Batch BERT annotation started in background"}), 200

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

def log_action(conn, action, entity_type, entity_id, user_id=None, case_id=None, old_value=None, new_value=None):
    """Helper to log actions to history_log table."""
    try:
        conn.execute('''
            INSERT INTO history_log (action, entity_type, entity_id, user_id, case_id, old_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (action, entity_type, entity_id, user_id, case_id, 
              json.dumps(old_value) if old_value else None, 
              json.dumps(new_value) if new_value else None))
    except Exception as e:
        logging.error(f"Error logging action: {e}")

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
        from datetime import datetime
        
        # Get existing for logging
        old_adj = conn.execute('SELECT * FROM adjudications WHERE annotation_id = ?', (annotation_id,)).fetchone()
        case_row = conn.execute('SELECT case_id FROM annotations WHERE id = ?', (annotation_id,)).fetchone()
        case_id = case_row['case_id'] if case_row else None

        # Upsert into adjudications table
        conn.execute('''
            INSERT INTO adjudications (annotation_id, user_id, status, reason, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(annotation_id) DO UPDATE SET
                user_id = excluded.user_id,
                status = excluded.status,
                reason = excluded.reason,
                updated_at = excluded.updated_at
        ''', (annotation_id, adjudicator_id, status, reason, datetime.now().isoformat()))
        
        log_action(conn, 'adjudicate', 'annotation', annotation_id, 
                   user_id=adjudicator_id, case_id=case_id,
                   old_value=dict(old_adj) if old_adj else None,
                   new_value={"status": status, "reason": reason})

        # Legacy: Still update the JSON field in annotations for backward compatibility during transition
        import json
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
        app.logger.error(f"Adjudication error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# API: Trigger LLM annotation (background)
# -----------------------------------------------------------------------------
def parse_annotation_guidelines():
    guidelines = []
    lines = [line.strip() for line in annotation_guideline.splitlines()]
    for line in lines:
        if not line.startswith('|'):
            continue
        columns = [col.strip() for col in line.strip('|').split('|')]
        if len(columns) < 4 or columns[0].lower().startswith('clinical concept'):
            continue
        label = columns[0]
        description = columns[1]
        rule = columns[2]
        if all(ch in '- ' for ch in label):
            continue
        guidelines.append({'label': label, 'description': description, 'rule': rule})
    return guidelines

@app.route("/api/annotation-guidelines", methods=["GET"])
@cross_origin()
def get_annotation_guidelines():
    try:
        return jsonify(parse_annotation_guidelines()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/llm-annotate", methods=["POST"])
@cross_origin()
def trigger_llm_annotation():
    app.logger.debug("Received request for LLM annotation")
    try:
        req = request.get_json(silent=True) or {}
        app.logger.debug(f"Request JSON: {req}")
        
        # Support both 'id' (modern) and 'file' (legacy/integrated)
        case_id = req.get("id") or req.get("file")
        folder = (req.get("folder") or "").strip()

        if case_id:
            if str(case_id).isdigit():
                doc = get_case(case_id=int(case_id))
            else:
                # Fallback to filename lookup if it's not a digit
                project = get_project_by_name(folder)
                if not project:
                    return jsonify({"error": f"Project not found: {folder}"}), 404
                doc = get_case(project_id=project['id'], filename=case_id)
            
            # Find the filename for logging
            file_name = doc['case_number'] + "-" + doc['version_number'] if doc else "unknown"
        else:
            return jsonify({"error": "Missing case identifier (id or file/folder)"}), 400

        if not doc:
            return jsonify({"error": f"Document not found: {case_id or file_name}"}), 404

        def background_task(doc_id):
            conn = get_db_connection()
            cursor = conn.execute('SELECT id FROM users WHERE role_id = (SELECT id FROM roles WHERE name = "AI")')
            ai_user_ids = [row['id'] for row in cursor.fetchall()]
            
            if ai_user_ids:
                placeholders = ', '.join(['?'] * len(ai_user_ids))
                conn.execute(f'DELETE FROM annotations WHERE case_id = ? AND user_id IN ({placeholders})', 
                             [doc_id] + ai_user_ids)

            # Set status to working in new column
            conn.execute('UPDATE cases SET llm_status = "working" WHERE id = ?', (doc_id,))
            conn.commit()
            conn.close()

            run_llm_annotation(doc_id=doc_id)
            
            # Update status to Done after completion
            conn = get_db_connection()
            conn.execute('UPDATE cases SET llm_status = "Done" WHERE id = ?', (doc_id,))
            conn.commit()
            conn.close()

        threading.Thread(target=background_task, args=(doc['id'],), daemon=True).start()
        return jsonify({"message": f"LLM annotation started", "file_locked": file_name}), 200

    except Exception as e:
        app.logger.error(f"Error in LLM annotation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/bert-annotate", methods=["POST"])
@cross_origin()
def trigger_bert_annotation():
    try:
        req = request.get_json(silent=True) or {}
        case_id = req.get("id")
        file_name = (req.get("file") or "").strip()
        folder = (req.get("folder") or "").strip()

        if case_id:
            doc = get_case(case_id=case_id)
            file_name = doc['case_number'] + "-" + doc['version_number'] if doc else "unknown"
        elif file_name and folder:
            project = get_project_by_name(folder)
            if not project:
                return jsonify({"error": f"Project not found: {folder}"}), 404
            doc = get_case(project_id=project['id'], filename=file_name)
        else:
            return jsonify({"error": "Missing case identifier (id or file/folder)"}), 400

        if not doc:
            return jsonify({"error": f"Document not found: {case_id or file_name}"}), 404

        def background_task(doc_id):
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).resolve().parent.parent / "development" / "NER" / "scripts"))
            from ner_client import get_ner_client
            
            client = get_ner_client()
            conn = get_db_connection()
            
            bert_user = conn.execute("SELECT id FROM users WHERE migration_key = 'BERT'").fetchone()
            if not bert_user:
                logging.error("BERT user not found")
                return
            bert_user_id = bert_user['id']

            # Set status to working in new column
            conn.execute('UPDATE cases SET bert_status = "working" WHERE id = ?', (doc_id,))
            conn.commit()

            pages = json.loads(doc['pages']) if doc['pages'] else [""]
            narrative = pages[0] if pages else ""
            
            if narrative and narrative.strip():
                try:
                    entities = client.annotate_text(narrative)
                    with conn:
                        conn.execute("DELETE FROM annotations WHERE case_id = ? AND user_id = ?", (doc_id, bert_user_id))
                        for ent in entities:
                            conn.execute("""
                                INSERT INTO annotations 
                                (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (doc_id, bert_user_id, ent['label'], ent['start'], ent['end'], ent['text'], "BERT", "{}"))
                        
                        # Set status to Done in new column
                        conn.execute("UPDATE cases SET bert_status = 'Done' WHERE id = ?", (doc_id,))
                except Exception as ex:
                    logging.error(f"Error processing case {doc_id}: {ex}")
            
            conn.close()

        threading.Thread(target=background_task, args=(doc['id'],), daemon=True).start()
        return jsonify({"message": f"BERT annotation started", "file_locked": file_name}), 200

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
        case_id = data.get("id")
        file_name = (data.get("file") or "").strip()
        folder = (data.get("folder") or "").strip()
        assessment = data.get("assessment") or {}

        if case_id:
            doc = get_case(case_id=case_id)
        elif file_name and folder:
            project = get_project_by_name(folder)
            if not project:
                return jsonify({"error": "Project not found"}), 404
            doc = get_case(project_id=project['id'], filename=file_name)
        else:
            return jsonify({"error": "Missing identifier (id or file/folder)"}), 400

        if not doc:
            return jsonify({"error": "Document not found"}), 404

        meta = json.loads(doc['meta']) if doc['meta'] else {}
        meta["assessment"] = assessment

        conn = get_db_connection()
        conn.execute('UPDATE cases SET meta = ? WHERE id = ?', (json.dumps(meta), doc['id']))
        conn.commit()
        conn.close()

        return jsonify({"message": "Assessment saved"})
    except Exception as e:
        logging.error(f"Save assessment error: {e}")
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

# -----------------------------------------------------------------------------
# ICSR Integration (AskMyFAERS)
# -----------------------------------------------------------------------------
@app.route("/api/annotate_icsr_intake/", methods=["POST"])
@cross_origin()
def annotate_icsr_intake():
    # Try getting from form (traditional POST) or JSON body
    case_data_raw = request.form.get("case_data")
    if case_data_raw:
        try:
            case_data = json.loads(case_data_raw)
        except Exception:
            return "Invalid JSON in case_data form field", 400
    else:
        case_data = request.get_json(silent=True)
    
    if not case_data:
        return "Missing case_data (should be a JSON object or form field)", 400
    
    try:
        # Use case_report_id if available, fallback to other IDs
        case_num = str(case_data.get("case_report_id") or case_data.get("safety_report_id") or case_data.get("case_id") or case_data.get("id") or "unknown")
        ver_num = str(case_data.get("version") or "1")
        narrative = case_data.get("narrative", "")
        
        meta = {
            "source": "AskMyFAERS",
            "original_id": case_data.get("id"),
            "safety_report_id": case_data.get("safety_report_id"),
            "case_report_id": case_data.get("case_report_id"),
            "is_icsr": True
        }
        
        attrs = {
            "narrative": narrative,
            "pages": json.dumps([narrative]),
            "meta": json.dumps(meta),
            "full_data": json.dumps(case_data)
        }
        
        # 1. Determine project name with prefix
        raw_project_name = case_data.get("project_name") or "Integration"
        project_name = f"AskMyFAERS_{raw_project_name}"
        
        # 2. Ensure project exists
        project_id = create_project(project_name, description="Integrated ICSR Cases")
        
        # 3. Upsert Case (Will keep same ID if case_num/ver_num match)
        case_id = upsert_case(case_num, ver_num, attrs)
        
        # 4. Link to Project
        link_case_to_project(project_id, case_id)
        
        frontend_url = os.environ.get("FRONTEND_URL", "https://ncshpc400.fda.gov")
        base_path = os.environ.get("FRONTEND_BASE_PATH", "/annotator")
        # Redirect to /annotate instead of /annotate_icsr
        return redirect(f"{frontend_url}{base_path}/annotate?id={case_id}&project={project_name}")
    except Exception as e:
        logging.error(f"Error in ICSR intake: {e}")
        return f"Intake Error: {str(e)}", 500

@app.route("/api/case/<int:case_id>", methods=["GET"])
@cross_origin()
def get_case_by_id(case_id):
    try:
        case = get_case(case_id=case_id)        
        if not case:
            return jsonify({"error": "Case not found"}), 404
        
        final_case = dict(case)
        
        # Get count of annotations
        conn = get_db_connection()
        count_res = conn.execute("SELECT COUNT(*) as count FROM annotations WHERE case_id = ?", (case_id,)).fetchone()
        total_in_db = count_res['count']
        final_case['total_annotations'] = total_in_db
        logging.info(f"Case {case_id}: total annotations in DB = {total_in_db}")
        conn.close()

        # Load first chunk of structured annotations (e.g., first 500)
        limit = request.args.get('limit', default=500, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        annotations = get_annotations(case_id, limit=limit, offset=offset)
        logging.info(f"Case {case_id}: get_annotations returned {len(annotations)} formatted rows")
        
        # Map DB structure to Frontend interface structure
        formatted_annotations = []
        for a in annotations:
            ann_dict = dict(a)
            # Create nested textContext
            ann_dict['textContext'] = {
                'text': ann_dict.get('text_content', ''),
                'start': ann_dict.get('start_offset', 0),
                'end': ann_dict.get('end_offset', 0),
                'page': 0 # Default to page 0 if not stored
            }
            # Parse relationships if they exist as JSON string
            if ann_dict.get('relationships'):
                try:
                    ann_dict['relationships'] = json.loads(ann_dict['relationships'])
                except:
                    ann_dict['relationships'] = {}
            else:
                ann_dict['relationships'] = {}

            # Parse adjudication if it exists as JSON string
            if ann_dict.get('adjudication'):
                try:
                    ann_dict['adjudication'] = json.loads(ann_dict['adjudication'])
                except:
                    # If it's not JSON, keep as is or wrap
                    pass
                
            formatted_annotations.append(ann_dict)
            
        final_case['annotations'] = formatted_annotations
        
        return jsonify(final_case), 200
    except Exception as e:
        logging.error(f"Error getting case by ID: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/case/<int:case_id>/annotations", methods=["GET"])
@cross_origin()
def get_case_annotations(case_id):
    try:
        limit = request.args.get('limit', default=500, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        annotations = get_annotations(case_id, limit=limit, offset=offset)
        return jsonify([dict(a) for a in annotations]), 200
    except Exception as e:
        logging.error(f"Error getting annotations: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/export_icsr/<int:case_id>", methods=["GET"])
@cross_origin()
def export_icsr(case_id):
    conn = get_db_connection()
    try:
        case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if not case: return jsonify({"error": "Case not found"}), 404
        
        annotations = conn.execute("""
            SELECT a.*, u.username 
            FROM annotations a 
            JOIN users u ON a.user_id = u.id 
            WHERE a.case_id = ?
        """, (case_id,)).fetchall()
        
        terms = {"drugs": [], "events": [], "time": [], "demographics": []}
        label_map = {
            "DRUG": "drugs", "SDRUG": "drugs", "CDRUG": "drugs",
            "AE": "events", "SYMPTOM": "events", "SIGN": "events",
            "TEMPORAL": "time", "AGE": "demographics", "SEX": "demographics"
        }
        
        for a in annotations:
            target_cat = label_map.get(a['label'].upper())
            if target_cat and a['text_content'] not in terms[target_cat]:
                terms[target_cat].append(a['text_content'])
        
        relationships = []
        for a in annotations:
            if a['relationships']:
                rels = json.loads(a['relationships'])
                for rel_type, target_info in rels.items():
                    if isinstance(target_info, dict) and target_info.get("text"):
                        relationships.append({
                            "source": a['text_content'],
                            "target": target_info['text'],
                            "type": "related_to",
                            "label": rel_type
                        })
        
        # Spec uses "narraives" (typo)
        return jsonify({
            "narraives": case['narrative'],
            "terms": terms,
            "relationships": relationships
        }), 200
    except Exception as e:
        logging.error(f"Export error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# Annotation CRUD (Incremental Updates)
# -----------------------------------------------------------------------------
@app.route("/api/annotations/", methods=["POST"])
@cross_origin()
def create_annotation():
    try:
        data = request.get_json()
        logging.debug(f"Creating annotation with data: {data}")
        case_id = data.get("case_id")
        user_note = data.get("note", "Admin")
        
        if not case_id:
            logging.error("Missing case_id in create_annotation request")
            return jsonify({"error": "Missing case_id"}), 400

        conn = get_db_connection()
        user_id = get_user_by_note(user_note) or 1
        logging.debug(f"Resolved user_id: {user_id} for note: {user_note}")
        
        # Validation: Ensure all target IDs in relationships exist in the same case
        relationships = data.get("relationships", {})
        if isinstance(relationships, dict):
            for rel_type, target_id in relationships.items():
                if isinstance(target_id, int):
                    res = conn.execute("SELECT 1 FROM annotations WHERE id = ? AND case_id = ?", (target_id, case_id)).fetchone()
                    if not res:
                        logging.warning(f"Target annotation {target_id} not found for case {case_id}")
                        return jsonify({"error": f"Target annotation {target_id} for relationship {rel_type} not found in this case"}), 400

        cursor = conn.execute("""
            INSERT INTO annotations (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships, adjudication)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id,
            user_id,
            data.get("label"),
            data.get("start"),
            data.get("end"),
            data.get("text"),
            user_note,
            json.dumps(relationships),
            data.get("adjudication")
        ))
        new_id = cursor.lastrowid
        logging.info(f"Successfully created annotation ID {new_id} in case {case_id}")
        
        log_action(conn, 'create', 'annotation', new_id, user_id=user_id, case_id=case_id, new_value=data)
        
        conn.commit()
        conn.close()
        
        return jsonify({"id": new_id, "message": "Annotation created"}), 201
    except Exception as e:
        logging.error(f"Create annotation error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/api/annotations/<int:ann_id>/", methods=["PATCH", "PUT"])
@cross_origin()
def update_annotation(ann_id):
    try:
        data = request.get_json()
        conn = get_db_connection()
        
        # Get old value for logging
        old_anno = conn.execute('SELECT * FROM annotations WHERE id = ?', (ann_id,)).fetchone()
        if not old_anno:
            return jsonify({"error": "Annotation not found"}), 404
            
        # Build dynamic update
        updates = []
        params = []
        for field in ["label", "note", "relationships", "adjudication"]:
            if field in data:
                updates.append(f"{field} = ?")
                val = data[field]
                if field == "relationships" and isinstance(val, dict):
                    # Validation: Ensure all target IDs in relationships exist in the same case
                    for rel_type, target_id in val.items():
                        if isinstance(target_id, int):
                            res = conn.execute("SELECT 1 FROM annotations WHERE id = ? AND case_id = ?", (target_id, old_anno['case_id'])).fetchone()
                            if not res:
                                return jsonify({"error": f"Target annotation {target_id} for relationship {rel_type} not found in this case"}), 400
                    val = json.dumps(val)
                params.append(val)
        
        if not updates:
            return jsonify({"message": "No changes"}), 200
            
        params.append(ann_id)
        conn.execute(f"UPDATE annotations SET {', '.join(updates)} WHERE id = ?", params)
        
        log_action(conn, 'update', 'annotation', ann_id, 
                   user_id=get_user_by_note(data.get("note", old_anno['note'])), 
                   case_id=old_anno['case_id'],
                   old_value=dict(old_anno), 
                   new_value=data)
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Annotation updated"}), 200
    except Exception as e:
        logging.error(f"Update annotation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/annotations/<int:ann_id>/", methods=["DELETE"])
@cross_origin()
def delete_annotation(ann_id):
    try:
        conn = get_db_connection()
        
        # Get old value for logging
        old_anno = conn.execute('SELECT * FROM annotations WHERE id = ?', (ann_id,)).fetchone()
        if old_anno:
            log_action(conn, 'delete', 'annotation', ann_id, 
                       case_id=old_anno['case_id'],
                       old_value=dict(old_anno))

        conn.execute("DELETE FROM annotations WHERE id = ?", (ann_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Annotation deleted"}), 200
    except Exception as e:
        logging.error(f"Delete annotation error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8862, debug=True)
