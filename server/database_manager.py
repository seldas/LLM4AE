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
    """Initializes the database schema with common sense roles and predefined users."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Roles table (Fixed set of roles)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # 2. Users table (Admin-managed, fixed roles)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT,
            role_id INTEGER NOT NULL,
            migration_key TEXT, -- e.g., 'SME1', 'SME2' for mapping old data
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. Documents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            pages TEXT NOT NULL, -- JSON array
            meta TEXT,           -- JSON object
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            UNIQUE(project_id, filename)
        )
    ''')

    # 5. Annotations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            start_offset INTEGER NOT NULL,
            end_offset INTEGER NOT NULL,
            text_content TEXT NOT NULL,
            note TEXT,
            relationships TEXT, -- JSON object
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # --- Seeding ---
    
    # 1. Seed Roles
    roles = [('Admin',), ('Annotator',), ('Adjudicator',), ('AI',)]
    cursor.executemany('INSERT OR IGNORE INTO roles (name) VALUES (?)', roles)
    
    cursor.execute('SELECT id, name FROM roles')
    role_map = {name: id for id, name in cursor.fetchall()}

    # 2. Seed Users
    # Structure: (username, full_name, role_id, migration_key)
    users_to_seed = [
        # Admin
        ('Admin', 'System Administrator', role_map['Admin'], None),
        
        # Annotators (with migration aliases)
        ('MJ.L', 'MJ.L', role_map['Annotator'], 'SME1'),
        ('K.L', 'K.L', role_map['Annotator'], 'SME2'),
        
        # Adjudicators
        ('L.W', 'L.W', role_map['Adjudicator'], None),
        ('O.D', 'O.D', role_map['Adjudicator'], None),
        
        # AI Models
        ('Llama4', 'Meta Llama 4', role_map['AI'], 'LLM'),
        ('BioBERT', 'BioBERT Foundation', role_map['AI'], 'BERT'),
        ('Elsa', 'Elsa AI Agent', role_map['AI'], None)
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO users (username, full_name, role_id, migration_key) 
        VALUES (?, ?, ?, ?)
    ''', users_to_seed)

    conn.commit()
    conn.close()
    print(f"Database initialized with updated roles and users at {DATABASE_PATH}")

if __name__ == "__main__":
    init_db()
