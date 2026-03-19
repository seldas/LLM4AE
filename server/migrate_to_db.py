import os
import json
import sqlite3
import re
from database_manager import get_db_connection, init_db

# Configuration
HISTORY_DIR = os.path.join(os.path.dirname(__file__), 'history')
META_DIR = os.path.join(HISTORY_DIR, 'Meta')

def migrate():
    # 1. Initialize DB with new schema
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
        
        # Determine source_file from Meta folder
        # Expecting something like "{project_name}_Meta.xlsx"
        source_file = None
        if os.path.exists(META_DIR):
            for mfile in os.listdir(META_DIR):
                if mfile.startswith(project_name) and mfile.endswith('.xlsx'):
                    source_file = mfile
                    break

        cursor.execute('''
            INSERT INTO projects (name, source_file) 
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET source_file = excluded.source_file
        ''', (project_name, source_file))
        
        cursor.execute("SELECT id FROM projects WHERE name = ?", (project_name,))
        project_id = cursor.fetchone()['id']

        # 4. Process JSON Files
        for filename in os.listdir(project_path):
            if not filename.endswith('.json'):
                continue
                
            # Extract case/version from filename (e.g., "12345-1.json")
            case_num, ver_num = None, None
            match = re.match(r'^(.+)-(.+)\.json$', filename)
            if match:
                case_num, ver_num = match.groups()
                
            file_path = os.path.join(project_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                pages_json = json.dumps(data.get('pages', []))
                meta_json = json.dumps(data.get('meta', {}))
                
                cursor.execute('''
                    INSERT INTO documents (project_id, filename, pages, meta, case_number, version_number)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_id, filename) DO UPDATE SET
                        pages = excluded.pages,
                        meta = excluded.meta,
                        case_number = excluded.case_number,
                        version_number = excluded.version_number
                ''', (project_id, filename, pages_json, meta_json, case_num, ver_num))
                
                cursor.execute('SELECT id FROM documents WHERE project_id = ? AND filename = ?', (project_id, filename))
                doc_id = cursor.fetchone()['id']

                # 5. Insert Annotations
                annotations = data.get('annotations', [])
                # Clear existing for this doc before re-migrating
                conn.execute('DELETE FROM annotations WHERE document_id = ?', (doc_id,))
                
                for ann in annotations:
                    note = str(ann.get('note', '')).strip().upper()
                    user_id = admin_id
                    for key, val in user_mapping.items():
                        if key in note:
                            user_id = val
                            break
                    
                    label = ann.get('label', 'UNKNOWN')
                    start = ann.get('textContext', {}).get('start', 0)
                    end = ann.get('textContext', {}).get('end', 0)
                    text_content = ann.get('textContext', {}).get('text', '')
                    relationships = json.dumps(ann.get('relationships', {}))
                    
                    cursor.execute('''
                        INSERT INTO annotations (document_id, user_id, label, start_offset, end_offset, text_content, note, relationships)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (doc_id, user_id, label, start, end, text_content, note, relationships))

            except Exception as e:
                print(f"  Error processing {filename}: {e}")

        conn.commit()

    conn.close()
    print("--- Migration Complete with Meta Info ---")

if __name__ == "__main__":
    migrate()
