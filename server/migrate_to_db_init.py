import os
import json
import sqlite3
import re
from database_manager import init_db, get_db_connection

# Configuration
HISTORY_DIR = os.path.join(os.path.dirname(__file__), 'history')
META_DIR = os.path.join(HISTORY_DIR, 'Meta')

def migrate():
    # 1. Initialize schema
    init_db()
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # 2. User mapping cache
    cursor.execute('SELECT id, username, migration_key FROM users')
    user_mapping = {}
    for u in cursor.fetchall():
        user_mapping[u['username'].upper()] = u['id']
        if u['migration_key']:
            user_mapping[u['migration_key'].upper()] = u['id']
            
    cursor.execute("SELECT id FROM users WHERE username = 'Admin'")
    admin_id = cursor.fetchone()['id']

    if not os.path.exists(HISTORY_DIR):
        print(f"Error: History directory {HISTORY_DIR} not found.")
        return

    # 3. Process Projects
    for project_name in os.listdir(HISTORY_DIR):
        project_path = os.path.join(HISTORY_DIR, project_name)
        if not os.path.isdir(project_path) or project_name == 'Meta':
            continue

        print(f"--- Migrating Project: {project_name} ---")
        
        # Determine source_file and blob
        source_file, source_blob = None, None
        if os.path.exists(META_DIR):
            for mfile in os.listdir(META_DIR):
                if mfile.startswith(project_name) and mfile.endswith('.xlsx'):
                    source_file = mfile
                    with open(os.path.join(META_DIR, mfile), 'rb') as fb:
                        source_blob = fb.read()
                    break

        # Create project manually to avoid nested connection
        cursor.execute('''
            INSERT INTO projects (name, source_file, source_file_blob) VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET source_file_blob = excluded.source_file_blob
        ''', (project_name, source_file, source_blob))
        cursor.execute('SELECT id FROM projects WHERE name = ?', (project_name,))
        project_id = cursor.fetchone()['id']

        # 4. Process JSON Files
        for filename in os.listdir(project_path):
            if not filename.endswith('.json'): continue
                
            case_num, ver_num = "0", "1"
            match = re.match(r'^(.+)-(.+)\.json$', filename)
            if match: case_num, ver_num = match.groups()
                
            file_path = os.path.join(project_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                pages = json.dumps(data.get('pages', []))
                meta = json.dumps(data.get('meta', {}))
                
                # Check for existing case to implement smart merge manually
                cursor.execute('SELECT * FROM cases WHERE case_number = ? AND version_number = ?', (case_num, ver_num))
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute('''
                        UPDATE cases SET pages = ?, meta = ?, annotate_filename = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', (pages, meta, filename, existing['id']))
                    case_id = existing['id']
                else:
                    cursor.execute('''
                        INSERT INTO cases (case_number, version_number, pages, meta, annotate_filename)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (case_num, ver_num, pages, meta, filename))
                    case_id = cursor.lastrowid

                # Link project and case
                cursor.execute('INSERT OR IGNORE INTO project_cases (project_id, case_id) VALUES (?, ?)', (project_id, case_id))

                # Annotations
                cursor.execute('DELETE FROM annotations WHERE case_id = ?', (case_id,))
                for ann in data.get('annotations', []):
                    note = str(ann.get('note', '')).strip().upper()
                    user_id = admin_id
                    for key, val in user_mapping.items():
                        if key in note:
                            user_id = val
                            break
                    
                    cursor.execute('''
                        INSERT INTO annotations (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (case_id, user_id, ann.get('label', 'UNKNOWN'), ann.get('textContext', {}).get('start', 0), ann.get('textContext', {}).get('end', 0), ann.get('textContext', {}).get('text', ''), ann.get('note', ''), json.dumps(ann.get('relationships', {}))))

            except Exception as e:
                print(f"  Error processing {filename}: {e}")

        # Commit after each project to keep transactions manageable
        conn.commit()

    conn.close()
    print("--- Migration Complete ---")

if __name__ == "__main__":
    migrate()
