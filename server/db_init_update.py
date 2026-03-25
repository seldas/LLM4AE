import sqlite3
import os
import json
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'llm4ae.db')

def get_db_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def add_column_if_missing(cursor, table_name, column_name, column_definition):
    """Adds a column to a table if it doesn't already exist."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row['name'] for row in cursor.fetchall()]
    if column_name not in columns:
        print(f"Adding column '{column_name}' to table '{table_name}'...")
        cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {column_definition}')

def init_update_db():
    """Initializes the database and updates schema to latest version."""
    print(f"Initializing/Updating database at: {DATABASE_PATH}")
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Create Tables (Standard CREATE TABLE IF NOT EXISTS)
    cursor.execute('CREATE TABLE IF NOT EXISTS roles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            role_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_number TEXT NOT NULL,
            version_number TEXT NOT NULL,
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            start_offset INTEGER NOT NULL,
            end_offset INTEGER NOT NULL,
            text_content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 2. Add Missing Columns (for existing environments)
    
    # Users table updates
    add_column_if_missing(cursor, 'users', 'password', 'TEXT')
    add_column_if_missing(cursor, 'users', 'full_name', 'TEXT')
    add_column_if_missing(cursor, 'users', 'migration_key', 'TEXT')

    # Projects table updates
    add_column_if_missing(cursor, 'projects', 'description', 'TEXT')
    add_column_if_missing(cursor, 'projects', 'source_file', 'TEXT')
    add_column_if_missing(cursor, 'projects', 'source_file_blob', 'BLOB')

    # Cases table updates (adding all possible columns from database_manager.py)
    case_columns = [
        ('mcn_or_ctu', 'TEXT'),
        ('report_type', 'TEXT'),
        ('form_type', 'TEXT'),
        ('initial_fda_received_date', 'TEXT'),
        ('latest_fda_received_date', 'TEXT'),
        ('completeness_score', 'TEXT'),
        ('patient_id', 'TEXT'),
        ('age_in_years', 'TEXT'),
        ('dob', 'TEXT'),
        ('sex', 'TEXT'),
        ('weight_in_kg', 'TEXT'),
        ('race', 'TEXT'),
        ('medical_history_and_comments', 'TEXT'),
        ('sender_mfr_organization', 'TEXT'),
        ('reporter_organization', 'TEXT'),
        ('country_derived', 'TEXT'),
        ('reporter_qualifications', 'TEXT'),
        ('health_professional', 'TEXT'),
        ('report_source', 'TEXT'),
        ('narrative', 'TEXT'),
        ('seriousness', 'TEXT'),
        ('all_outcomes', 'TEXT'),
        ('all_suspect_products', 'TEXT'),
        ('all_suspect_pais', 'TEXT'),
        ('all_concomitant_products', 'TEXT'),
        ('all_llts', 'TEXT'),
        ('all_pts', 'TEXT'),
        ('all_hlts', 'TEXT'),
        ('all_hlgts', 'TEXT'),
        ('all_socs', 'TEXT'),
        ('annotate_filename', 'TEXT'),
        ('pages', 'TEXT'),
        ('meta', 'TEXT'),
        ('full_data', 'TEXT')
    ]
    for col_name, col_def in case_columns:
        add_column_if_missing(cursor, 'cases', col_name, col_def)

    # Annotations table updates
    add_column_if_missing(cursor, 'annotations', 'note', 'TEXT')
    add_column_if_missing(cursor, 'annotations', 'relationships', 'TEXT')

    # 3. Create Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_project_cases_project ON project_cases(project_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_project_cases_case ON project_cases(case_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_annotations_case ON annotations(case_id)')

    # 4. Ensure Default Roles
    roles = [('Admin',), ('Annotator',), ('Adjudicator',), ('AI',)]
    cursor.executemany('INSERT OR IGNORE INTO roles (name) VALUES (?)', roles)
    
    cursor.execute('SELECT id, name FROM roles')
    rmap = {n: i for i, n in cursor.fetchall()}

    # 5. Ensure Default Admin User
    # Special check for admin user as requested
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    admin_user = cursor.fetchone()
    if not admin_user:
        print("Creating default admin user...")
        cursor.execute('''
            INSERT INTO users (username, password, full_name, role_id) 
            VALUES (?, ?, ?, ?)
        ''', ('admin', '1986414', 'System Administrator', rmap['Admin']))
    else:
        # If admin exists but password is NULL or empty, update it
        cursor.execute("SELECT password FROM users WHERE username = 'admin'")
        row = cursor.fetchone()
        if row and not row['password']:
            print("Updating admin user password...")
            cursor.execute("UPDATE users SET password = ? WHERE username = 'admin'", ('1986414',))

    # 6. Ensure other default users (optional but good for consistency with database_manager.py)
    other_users = [
        ('MJ.L', 'password123', 'MJ.L', rmap['Annotator'], 'SME1'),
        ('K.L', 'password123', 'K.L', rmap['Annotator'], 'SME2'),
        ('L.W', 'password123', 'L.W', rmap['Adjudicator'], None),
        ('O.D', 'password123', 'O.D', rmap['Adjudicator'], None),
        ('Llama4', None, 'Meta Llama 4', rmap['AI'], 'LLM'),
        ('BioBERT', None, 'BioBERT Foundation', rmap['AI'], 'BERT'),
        ('Elsa', None, 'Elsa AI Agent', rmap['AI'], None),
        ('guest', 'guest', 'Guest User', rmap['Annotator'], 'GUEST')
    ]
    for username, password, full_name, role_id, migration_key in other_users:
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (username, password, full_name, role_id, migration_key) 
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password, full_name, role_id, migration_key))

    conn.commit()
    conn.close()
    print("Database initialization/update completed successfully.")

if __name__ == "__main__":
    init_update_db()
