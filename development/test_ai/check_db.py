import sqlite3
import os

db_path = os.path.join('server', 'database', 'llm4ae.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

print('--- PROJECTS ---')
projects = conn.execute('SELECT * FROM projects').fetchall()
for p in projects:
    cases_count = conn.execute('SELECT COUNT(*) FROM project_cases WHERE project_id = ?', (p['id'],)).fetchone()[0]
    print(f"Project: {p['name']}, ID: {p['id']}, Cases: {cases_count}")

print('\n--- RECENT CASES ---')
cases = conn.execute('SELECT id, case_number, version_number FROM cases LIMIT 5').fetchall()
for c in cases:
    ann_count = conn.execute('SELECT COUNT(*) FROM annotations WHERE case_id = ?', (c['id'],)).fetchone()[0]
    print(f"Case ID: {c['id']}, Num: {c['case_number']}, Ann: {ann_count}")

conn.close()
