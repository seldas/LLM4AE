import os
import json
import sqlite3
from database_manager import get_db_connection, init_db

# Configuration
HISTORY_DIR = os.path.join(os.path.dirname(__file__), 'history')

def migrate():
    # 1. Initialize DB if not exists
    init_db()
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # 2. Build User/Role Cache for mapping
    # We map 'SME1', 'SME2', 'LLM' (migration_keys) to actual user_ids
    cursor.execute('SELECT id, username, migration_key FROM users')
    user_rows = cursor.fetchall()
    
    # Map both username and migration_key to the same user_id
    user_mapping = {}
    for u in user_rows:
        user_mapping[u['username'].upper()] = u['id']
        if u['migration_key']:
            user_mapping[u['migration_key'].upper()] = u['id']
            
    # Default fallback user (Admin) for unknown notes
    cursor.execute("SELECT id FROM users WHERE username = 'Admin'")
    admin_id = cursor.fetchone()['id']

    # 3. Process Projects
    if not os.path.exists(HISTORY_DIR):
        print(f"Error: History directory {HISTORY_DIR} not found.")
        return

    # Ensure "Playground" project exists
    cursor.execute("INSERT OR IGNORE INTO projects (name, description) VALUES (?, ?)", 
                   ('Playground', 'Ad-hoc manual annotations'))
    conn.commit()

    for project_name in os.listdir(HISTORY_DIR):
        project_path = os.path.join(HISTORY_DIR, project_name)
        
        # Skip 'Meta' folder and non-directories
        if not os.path.isdir(project_path) or project_name == 'Meta':
            continue

        print(f"--- Migrating Project: {project_name} ---")
        
        # Create or Get Project ID
        cursor.execute("INSERT OR IGNORE INTO projects (name) VALUES (?)", (project_name,))
        cursor.execute("SELECT id FROM projects WHERE name = ?", (project_name,))
        project_id = cursor.fetchone()['id']

        # 4. Process JSON Files in Project
        for filename in os.listdir(project_path):
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join(project_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                pages_json = json.dumps(data.get('pages', []))
                meta_json = json.dumps(data.get('meta', {}))
                
                # Insert Document
                cursor.execute('''
                    INSERT OR IGNORE INTO documents (project_id, filename, pages, meta)
                    VALUES (?, ?, ?, ?)
                ''', (project_id, filename, pages_json, meta_json))
                
                cursor.execute('SELECT id FROM documents WHERE project_id = ? AND filename = ?', 
                               (project_id, filename))
                doc_id = cursor.fetchone()['id']

                # 5. Insert Annotations
                annotations = data.get('annotations', [])
                for ann in annotations:
                    # Determine User ID from 'note' or fallback
                    note = str(ann.get('note', '')).strip().upper()
                    
                    # Search mapping (e.g., 'SME1' -> MJ.L's ID)
                    user_id = admin_id
                    for key, val in user_mapping.items():
                        if key in note: # Partial match (e.g. 'SME1 (auto)')
                            user_id = val
                            break
                    
                    # Extract fields
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
    print("--- Migration Complete ---")

if __name__ == "__main__":
    migrate()
