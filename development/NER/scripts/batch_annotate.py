import sqlite3
import json
import argparse
import sys
from pathlib import Path

# Add project root to path so we can import server modules if needed
project_root = Path(__file__).resolve().parents[3]
sys.path.append(str(project_root / "server"))

from ner_client import get_ner_client

# --- Configuration ---
DB_PATH = project_root / 'server' / 'database' / 'llm4ae.db'

def batch_annotate(force=False, limit=None):
    # 1. Connect to DB
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 2. Identify BioBERT user
    cursor.execute("SELECT id FROM users WHERE migration_key = 'BERT'")
    user_row = cursor.fetchone()
    if not user_row:
        print("Error: BioBERT user (migration_key='BERT') not found in database.")
        conn.close()
        return
    bert_user_id = user_row['id']
    print(f"BioBERT User ID: {bert_user_id}")

    # 3. Fetch cases
    cursor.execute("SELECT id, pages, meta FROM cases")
    cases = cursor.fetchall()
    print(f"Total cases in database: {len(cases)}")

    client = get_ner_client()
    processed_count = 0
    skipped_count = 0

    for case in cases:
        if limit is not None and processed_count >= limit:
            print(f"Reached limit of {limit} processed cases. Stopping.")
            break

        case_id = case['id']
        meta = json.loads(case['meta']) if case['meta'] else {}
        
        # Check if already processed by BERT
        if not force and meta.get("bert_processed") == "Done":
            skipped_count += 1
            continue

        # Get narrative (assumed to be the first page)
        pages = json.loads(case['pages']) if case['pages'] else [""]
        narrative = pages[0]
        
        if not narrative or not narrative.strip():
            print(f"Case {case_id}: Empty narrative, skipping.")
            continue

        print(f"Processing Case {case_id} ({len(narrative)} chars)...")
        
        try:
            # 4. Annotate
            entities = client.annotate_text(narrative)
            
            # 5. Write to DB
            # Start transaction for this case
            conn.execute("BEGIN TRANSACTION")
            
            # Delete existing BERT annotations for this case
            conn.execute("DELETE FROM annotations WHERE case_id = ? AND user_id = ?", (case_id, bert_user_id))
            
            # Insert new annotations
            for ent in entities:
                conn.execute('''
                    INSERT INTO annotations (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships, adjudication)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (case_id, bert_user_id, ent['label'], ent['start'], ent['end'], ent['text'], 'BERT', '{}', None))
            
            # Update meta
            meta["bert_processed"] = "Done"
            conn.execute("UPDATE cases SET meta = ? WHERE id = ?", (json.dumps(meta), case_id))
            
            conn.commit()
            processed_count += 1
            
        except Exception as e:
            conn.execute("ROLLBACK")
            print(f"Error processing case {case_id}: {e}")

    conn.close()
    print(f"\nBatch processing complete.")
    print(f"Processed: {processed_count}")
    print(f"Skipped:   {skipped_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch annotate ICSR narratives using BioBERT.")
    parser.add_argument("--force", action="store_true", help="Re-annotate cases even if already processed.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of processed records (e.g., 50).")
    args = parser.parse_args()

    batch_annotate(force=args.force, limit=args.limit)
