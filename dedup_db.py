import sqlite3
import os
import logging

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'server', 'database', 'llm4ae.db')

def dedup_annotations():
    logging.basicConfig(level=logging.INFO)
    if not os.path.exists(DATABASE_PATH):
        logging.error(f"Database not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    logging.info("Starting deduplication of annotations...")

    # Find duplicates based on case_id, user_id, label, start_offset, end_offset
    # Keep the one with the largest (latest) id
    try:
        cursor.execute('''
            DELETE FROM annotations
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM annotations
                GROUP BY case_id, user_id, label, start_offset, end_offset
            )
        ''')
        deleted_count = cursor.rowcount
        conn.commit()
        logging.info(f"Deduplication complete. Removed {deleted_count} duplicate annotations.")
    except Exception as e:
        logging.error(f"Error during deduplication: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    dedup_annotations()
