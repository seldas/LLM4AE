import sqlite3
import os
import json
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'llm4ae.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema with many-to-many project-case relationships."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Roles table
    cursor.execute('CREATE TABLE IF NOT EXISTS roles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)')

    # 2. Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT,
            role_id INTEGER NOT NULL,
            migration_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles (id)
        )
    ''')

    # 3. Projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            source_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. Cases table (Formerly documents)
    # UNIQUE on case_number + version_number ensures deduplication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_number TEXT NOT NULL,
            version_number TEXT NOT NULL,
            filename TEXT,       -- Display name (e.g. 12345-1.json)
            pages TEXT NOT NULL, -- JSON array of narratives
            meta TEXT,           -- JSON object (HTML snippets)
            full_data TEXT,      -- JSON object (ALL original Excel columns)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(case_number, version_number)
        )
    ''')

    # 5. Project-Case Link table (Many-to-Many)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_cases (
            project_id INTEGER NOT NULL,
            case_id INTEGER NOT NULL,
            PRIMARY KEY (project_id, case_id),
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        )
    ''')

    # 6. Annotations table
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Seeding
    roles = [('Admin',), ('Annotator',), ('Adjudicator',), ('AI',)]
    cursor.executemany('INSERT OR IGNORE INTO roles (name) VALUES (?)', roles)
    cursor.execute('SELECT id, name FROM roles')
    role_map = {name: id for id, name in cursor.fetchall()}

    users_to_seed = [
        ('Admin', 'System Administrator', role_map['Admin'], None),
        ('MJ.L', 'MJ.L', role_map['Annotator'], 'SME1'),
        ('K.L', 'K.L', role_map['Annotator'], 'SME2'),
        ('L.W', 'L.W', role_map['Adjudicator'], None),
        ('O.D', 'O.D', role_map['Adjudicator'], None),
        ('Llama4', 'Meta Llama 4', role_map['AI'], 'LLM'),
        ('BioBERT', 'BioBERT Foundation', role_map['AI'], 'BERT'),
        ('Elsa', 'Elsa AI Agent', role_map['AI'], None)
    ]
    cursor.executemany('INSERT OR IGNORE INTO users (username, full_name, role_id, migration_key) VALUES (?, ?, ?, ?)', users_to_seed)

    conn.commit()
    conn.close()

# --- Helper Functions ---

def create_project(name, description=None, source_file=None):
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO projects (name, description, source_file) VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET source_file = COALESCE(excluded.source_file, projects.source_file)
        ''', (name, description, source_file))
        conn.commit()
        return conn.execute('SELECT id FROM projects WHERE name = ?', (name,)).fetchone()['id']
    finally: conn.close()

def upsert_case(case_num, ver_num, pages, meta, full_data, filename=None):
    conn = get_db_connection()
    try:
        # 1. Insert or Update Case
        conn.execute('''
            INSERT INTO cases (case_number, version_number, filename, pages, meta, full_data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(case_number, version_number) DO UPDATE SET
                pages = excluded.pages,
                meta = excluded.meta,
                full_data = excluded.full_data,
                updated_at = CURRENT_TIMESTAMP
        ''', (case_num, ver_num, filename, json.dumps(pages), json.dumps(meta), json.dumps(full_data)))
        
        case_id = conn.execute('SELECT id FROM cases WHERE case_number = ? AND version_number = ?', (case_num, ver_num)).fetchone()['id']
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
    res = conn.execute('SELECT * FROM projects WHERE name = ?', (name,)).fetchone()
    conn.close()
    return res

def get_case(case_id=None, project_id=None, filename=None):
    conn = get_db_connection()
    if case_id:
        res = conn.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
    else:
        # Find by filename within a specific project
        res = conn.execute('''
            SELECT c.* FROM cases c
            JOIN project_cases pc ON c.id = pc.case_id
            WHERE pc.project_id = ? AND c.filename = ?
        ''', (project_id, filename)).fetchone()
    conn.close()
    return res

def get_annotations(case_id):
    conn = get_db_connection()
    query = 'SELECT a.*, u.username, r.name as role_name FROM annotations a JOIN users u ON a.user_id = u.id JOIN roles r ON u.role_id = r.id WHERE a.case_id = ?'
    rows = conn.execute(query, (case_id,)).fetchall()
    conn.close()
    return rows

def get_user_by_note(note):
    conn = get_db_connection()
    n = str(note).strip().upper()
    user = conn.execute('SELECT id FROM users WHERE UPPER(username) = ? OR UPPER(migration_key) = ?', (n, n)).fetchone()
    conn.close()
    return user['id'] if user else None

if __name__ == "__main__":
    init_db()
