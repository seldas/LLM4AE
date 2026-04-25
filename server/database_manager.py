import sqlite3
import os
import json
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'llm4ae.db')

def get_db_connection():
    # Added timeout to prevent "database is locked" errors
    conn = sqlite3.connect(DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS roles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT,
            full_name TEXT,
            role_id INTEGER NOT NULL,
            migration_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            source_file TEXT,
            source_file_blob BLOB, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_number TEXT NOT NULL,
            version_number TEXT NOT NULL,
            mcn_or_ctu TEXT,
            report_type TEXT,
            form_type TEXT,
            initial_fda_received_date TEXT,
            latest_fda_received_date TEXT,
            completeness_score TEXT,
            patient_id TEXT,
            age_in_years TEXT,
            dob TEXT,
            sex TEXT,
            weight_in_kg TEXT,
            race TEXT,
            medical_history_and_comments TEXT,
            sender_mfr_organization TEXT,
            reporter_organization TEXT,
            country_derived TEXT,
            reporter_qualifications TEXT,
            health_professional TEXT,
            report_source TEXT,
            narrative TEXT,
            seriousness TEXT,
            all_outcomes TEXT,
            all_suspect_products TEXT,
            all_suspect_pais TEXT,
            all_concomitant_products TEXT,
            all_llts TEXT,
            all_pts TEXT,
            all_hlts TEXT,
            all_hlgts TEXT,
            all_socs TEXT,
            annotate_filename TEXT,
            pages TEXT, 
            meta TEXT,  
            full_data TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(case_number, version_number)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_cases (
            project_id INTEGER NOT NULL,
            case_id INTEGER NOT NULL,
            PRIMARY KEY (project_id, case_id),
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_project_cases_project ON project_cases(project_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_project_cases_case ON project_cases(case_id)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            start_offset INTEGER NOT NULL,
            end_offset INTEGER NOT NULL,
            text_content TEXT NOT NULL,
            note TEXT,
            relationships TEXT,
            adjudication TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_annotations_case ON annotations(case_id)')

    roles = [('Admin',), ('Annotator',), ('Adjudicator',), ('AI',)]
    cursor.executemany('INSERT OR IGNORE INTO roles (name) VALUES (?)', roles)
    
    cursor.execute('SELECT id, name FROM roles')
    rmap = {n: i for i, n in cursor.fetchall()}
    
    users = [
        ('admin', '1986414', 'System Administrator', rmap['Admin'], None),
        ('MJ.L', 'password123', 'MJ.L', rmap['Annotator'], 'SME1'),
        ('K.L', 'password123', 'K.L', rmap['Annotator'], 'SME2'),
        ('L.W', 'password123', 'L.W', rmap['Adjudicator'], None),
        ('O.D', 'password123', 'O.D', rmap['Adjudicator'], None),
        ('Llama4', None, 'Meta Llama 4', rmap['AI'], 'LLM'),
        ('BioBERT', None, 'BioBERT Foundation', rmap['AI'], 'BERT'),
        ('Elsa', None, 'Elsa AI Agent', rmap['AI'], None),
        ('guest', 'guest', 'Guest User', rmap['Annotator'], 'GUEST')
    ]
    cursor.executemany('INSERT OR IGNORE INTO users (username, password, full_name, role_id, migration_key) VALUES (?, ?, ?, ?, ?)', users)
    
    conn.commit()
    conn.close()

# --- Helper Functions ---

def create_project(name, description=None, source_file=None, source_blob=None):
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO projects (name, description, source_file, source_file_blob) VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET 
                source_file = COALESCE(excluded.source_file, projects.source_file),
                source_file_blob = COALESCE(excluded.source_file_blob, projects.source_file_blob)
        ''', (name, description, source_file, source_blob))
        conn.commit()
        res = conn.execute('SELECT id FROM projects WHERE name = ?', (name,)).fetchone()
        return res['id']
    finally: conn.close()

def upsert_case(case_num, ver_num, attributes):
    conn = get_db_connection()
    try:
        existing = conn.execute('SELECT * FROM cases WHERE case_number = ? AND version_number = ?', (case_num, ver_num)).fetchone()
        if existing:
            updates, params = [], []
            for col, val in attributes.items():
                if col in ['case_number', 'version_number']: continue
                new_val = str(val).strip() if val is not None else ""
                if col == 'meta':
                    final_val = new_val
                else:
                    final_val = new_val if new_val else (existing[col] or "")
                updates.append(f"{col} = ?")
                params.append(final_val)
            params.extend([case_num, ver_num])
            conn.execute(f'UPDATE cases SET {", ".join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE case_number = ? AND version_number = ?', params)
            case_id = existing['id']
        else:
            cols = ['case_number', 'version_number'] + [k for k in attributes.keys() if k not in ['case_number', 'version_number']]
            placeholders = ', '.join(['?'] * len(cols))
            vals = [case_num, ver_num] + [str(attributes[k]).strip() if attributes[k] is not None else "" for k in cols[2:]]
            cursor = conn.execute(f'INSERT INTO cases ({", ".join(cols)}) VALUES ({placeholders})', vals)
            case_id = cursor.lastrowid
        conn.commit()
        return case_id
    finally: conn.close()

def link_case_to_project(project_id, case_id):
    conn = get_db_connection()
    try:
        conn.execute('INSERT OR IGNORE INTO project_cases (project_id, case_id) VALUES (?, ?)', (project_id, case_id))
        conn.commit()
    finally: conn.close()

def get_project_by_name(name):
    conn = get_db_connection()
    try:
        res = conn.execute('SELECT * FROM projects WHERE name = ?', (name,)).fetchone()
        return res
    finally: conn.close()

def get_case(case_id=None, project_id=None, filename=None):
    conn = get_db_connection()
    try:
        if case_id:
            return conn.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
        
        # Try exact match first
        res = conn.execute('''
            SELECT c.* FROM cases c
            JOIN project_cases pc ON c.id = pc.case_id
            WHERE pc.project_id = ? AND c.annotate_filename = ?
        ''', (project_id, filename)).fetchone()
        
        if not res and filename and filename.lower().endswith('.json'):
            # Try without .json suffix
            no_json = filename[:-5]
            res = conn.execute('''
                SELECT c.* FROM cases c
                JOIN project_cases pc ON c.id = pc.case_id
                WHERE pc.project_id = ? AND c.annotate_filename = ?
            ''', (project_id, no_json)).fetchone()
            
        if not res and filename and not filename.lower().endswith('.json'):
            # Try with .json suffix
            with_json = filename + ".json"
            res = conn.execute('''
                SELECT c.* FROM cases c
                JOIN project_cases pc ON c.id = pc.case_id
                WHERE pc.project_id = ? AND c.annotate_filename = ?
            ''', (project_id, with_json)).fetchone()
            
        return res
    finally: conn.close()

def get_annotations(case_id, limit=None, offset=None):
    conn = get_db_connection()
    try:
        # Join with adjudications table to get structured data
        query = '''
            SELECT 
                a.*, 
                u.username, 
                r.name as role_name,
                adj.status as adj_status,
                adj.reason as adj_reason,
                adj.updated_at as adj_updated_at,
                adjudicator.full_name as adj_user_name
            FROM annotations a 
            JOIN users u ON a.user_id = u.id 
            JOIN roles r ON u.role_id = r.id 
            LEFT JOIN adjudications adj ON a.id = adj.annotation_id
            LEFT JOIN users adjudicator ON adj.user_id = adjudicator.id
            WHERE a.case_id = ?
            ORDER BY a.start_offset ASC
        '''
        params = [case_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        if offset is not None:
            query += " OFFSET ?"
            params.append(offset)
            
        return conn.execute(query, params).fetchall()
    finally: conn.close()

def get_user_by_note(note):
    conn = get_db_connection()
    try:
        n = str(note).strip().upper()
        res = conn.execute('SELECT id FROM users WHERE UPPER(username) = ? OR UPPER(migration_key) = ?', (n, n)).fetchone()
        return res['id'] if res else None
    finally: conn.close()

def authenticate_user(username, password):
    conn = get_db_connection()
    try:
        res = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        if res:
            return dict(res)
        return None
    finally: conn.close()

if __name__ == "__main__":
    init_db()
