import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'llm4ae.db')

def update_db():
    print(f"Checking database at {DATABASE_PATH}...")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # 1. Enable WAL Mode for better concurrency (fixes "Database is locked")
    print("Enabling WAL mode...")
    conn.execute('PRAGMA journal_mode=WAL')

    # 2. Ensure all tables exist
    print("Ensuring tables exist...")
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
            narrative TEXT,
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

    # 3. Add missing columns safely
    print("Checking for missing columns...")
    columns_to_add = {
        'cases': [('full_data', 'TEXT')],
        'annotations': [('adjudication', 'TEXT'), ('relationships', 'TEXT')]
    }

    for table, cols in columns_to_add.items():
        cursor.execute(f"PRAGMA table_info({table})")
        existing_cols = [row[1] for row in cursor.fetchall()]
        for col_name, col_type in cols:
            if col_name not in existing_cols:
                print(f"Adding column {col_name} to table {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()
    print("Database sync complete.")

if __name__ == "__main__":
    update_db()
