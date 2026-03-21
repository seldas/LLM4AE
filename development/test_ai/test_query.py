import sqlite3
import os
import json

db_path = os.path.join('server', 'database', 'llm4ae.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

project_name = 'FAERS_R1'
res = conn.execute('SELECT * FROM projects WHERE name = ?', (project_name,)).fetchone()
project_id = res['id']

query = '''
    SELECT 
        c.id, c.case_number,
        COUNT(CASE WHEN u.username IN ('Llama4', 'BioBERT') OR u.migration_key = 'LLM' THEN a.id END) as count_llm,
        COUNT(CASE WHEN u.username = 'MJ.L' OR u.migration_key = 'SME1' THEN a.id END) as count_sme1,
        COUNT(CASE WHEN u.username = 'K.L' OR u.migration_key = 'SME2' THEN a.id END) as count_sme2,
        COUNT(CASE WHEN u.username NOT IN ('Llama4', 'BioBERT', 'MJ.L', 'K.L') AND u.migration_key NOT IN ('LLM', 'SME1', 'SME2') THEN a.id END) as count_other
    FROM cases c
    JOIN project_cases pc ON c.id = pc.case_id
    LEFT JOIN annotations a ON c.id = a.case_id
    LEFT JOIN users u ON a.user_id = u.id
    WHERE pc.project_id = ?
    GROUP BY c.id
    LIMIT 5
'''
rows = conn.execute(query, (project_id,)).fetchall()
for r in rows:
    print(dict(r))

conn.close()
