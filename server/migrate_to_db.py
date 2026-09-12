import os
import json
import sqlite3
import re
import io
import pandas as pd
from database_manager import init_db, get_db_connection

# Re-use the mapping from project_management
COL_MAP = {
    "mcn_or_ctu": ["MCN or CTU", "Manufacturer Control #"],
    "report_type": ["Report Type"],
    "form_type": ["Form Type"],
    "initial_fda_received_date": ["Initial FDA Received Date"],
    "latest_fda_received_date": ["Latest FDA Received Date", "Latest FDA Received date"],
    "completeness_score": ["Completeness Score"],
    "patient_id": ["Patient ID", "Patient Id"],
    "age_in_years": ["Age in Years"],
    "dob": ["DOB"],
    "sex": ["Sex"],
    "weight_in_kg": ["Weight In kg", "Weight (kg)"],
    "race": ["Race"],
    "medical_history_and_comments": ["Medical History and Comments", "Medical History/Medical History Comments"],
    "sender_mfr_organization": ["Sender Mfr Organization"],
    "reporter_organization": ["Reporter Organization"],
    "country_derived": ["Country Derived"],
    "reporter_qualifications": ["Reporter Qualifications"],
    "health_professional": ["Health Professional"],
    "report_source": ["Report Source"],
    "narrative": ["Narrative"],
    "seriousness": ["Seriousness"],
    "all_outcomes": ["All Outcomes"],
    "all_suspect_products": ["ALL Suspect Products", "All Suspect Product Names"],
    "all_suspect_pais": ["All Suspect PAIs", "ALL Suspect PAIs"],
    "all_concomitant_products": ["All Concomitant Products"],
    "all_llts": ["All LLTs"],
    "all_pts": ["All PTs"],
    "all_hlts": ["All HLTs"],
    "all_hlgts": ["All HLGTs"],
    "all_socs": ["All SOCs"],
    "annotate_filename": ["annotate_filename"]
}

def get_mapped_val(row, internal_key):
    row_keys = {str(k).strip().lower(): k for k in row.index}
    possible_cols = COL_MAP.get(internal_key, [])
    for c in possible_cols:
        c_lower = c.lower()
        if c_lower in row_keys:
            val = row[row_keys[c_lower]]
            return str(val).strip() if pd.notna(val) else ""
    return ""

def migrate():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Map existing projects
    cursor.execute("SELECT id, name, source_file_blob FROM projects")
    projects = cursor.fetchall()

    for proj in projects:
        p_id, p_name, p_blob = proj['id'], proj['name'], proj['source_file_blob']
        if not p_blob:
            print(f"Skipping {p_name}: No Excel BLOB found.")
            continue

        print(f"--- Deep Migrating Meta for Project: {p_name} ---")
        try:
            xl = pd.ExcelFile(io.BytesIO(p_blob), engine='openpyxl')
            target = "Case Detail" if "Case Detail" in xl.sheet_names else ("Case Details" if "Case Details" in xl.sheet_names else xl.sheet_names[0])
            df = pd.read_excel(io.BytesIO(p_blob), sheet_name=target, engine='openpyxl').fillna('')
            df.columns = [str(c).strip() for c in df.columns]
            
            # Map Case #
            case_col = "Case Number"
            if "FAERS Case #" in df.columns: df = df.rename(columns={"FAERS Case #": "Case Number"})

            for _, row in df.iterrows():
                raw_case = str(row.get("Case Number", "0"))
                try: case_num = str(int(float(raw_case))) if raw_case else "0"
                except: case_num = raw_case or "0"

                raw_ver = str(row.get("Version Number", "1"))
                try: ver_num = str(int(float(raw_ver))) if raw_ver else "1"
                except: ver_num = raw_ver or "1"

                # Extract attributes
                attrs = {k: get_mapped_val(row, k) for k in COL_MAP.keys()}
                
                # Check for existing case in DB
                cursor.execute("SELECT id FROM cases WHERE case_number = ? AND version_number = ?", (case_num, ver_num))
                existing = cursor.fetchone()

                if existing:
                    # Update all metadata columns
                    updates = []
                    params = []
                    for k, v in attrs.items():
                        if v: # Only update if Excel has data
                            updates.append(f"{k} = ?")
                            params.append(v)
                    
                    if updates:
                        params.append(existing['id'])
                        cursor.execute(f"UPDATE cases SET {', '.join(updates)} WHERE id = ?", params)
                else:
                    # Rare case: link missing case if narratives exist in history folder
                    # (This script assumes projects are already mostly migrated)
                    pass

            conn.commit()
            print(f"Successfully backfilled metadata for {p_name}")
        except Exception as e:
            print(f"Error migrating {p_name}: {e}")

    conn.close()

if __name__ == "__main__":
    migrate()
