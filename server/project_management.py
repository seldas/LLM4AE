from flask import jsonify, request, Blueprint
from flask_cors import cross_origin
import pandas as pd
import os
import json
import traceback
import io
from text_processing import generate_demographic_content, generate_outcomes_content, generate_products_content
from database_manager import create_project, upsert_case, link_case_to_project, get_db_connection

project_blueprint = Blueprint('project', __name__)

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

def get_mapped_value(row, internal_key):
    possible_cols = COL_MAP.get(internal_key, [])
    for c in possible_cols:
        if c in row: return row[c]
    return ""

def find_header_row(file_bytes, sheet_name, engine='openpyxl'):
    df_preview = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=None, nrows=20, engine=engine)
    for idx, row in df_preview.iterrows():
        vals = [str(v).strip() for v in row.values]
        if "Case Number" in vals or "FAERS Case #" in vals: return idx
    return 0

@project_blueprint.route('/api/create-project-from-excel', methods=['POST'])
@cross_origin()
def create_project_from_excel():
    if 'file' not in request.files or 'projectName' not in request.form:
        return jsonify({'error': 'Missing file or project name'}), 400

    uploaded_file = request.files['file']
    project_name = request.form['projectName'].strip()
    file_bytes = uploaded_file.read()
    
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes), engine='openpyxl')
        sheet_names = xl.sheet_names
        target_sheet = "Case Detail" if "Case Detail" in sheet_names else ("Case Details" if "Case Details" in sheet_names else sheet_names[0])

        h_idx = find_header_row(file_bytes, target_sheet)
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=target_sheet, header=h_idx, engine='openpyxl')
        
        file_mode = 'InfoVIP' if 'FAERS Case #' in df.columns else 'RxLogix'
        if file_mode == 'InfoVIP': df = df.rename(columns={"FAERS Case #": "Case Number"})

        df = df.fillna('')
        project_id = create_project(project_name, source_file=uploaded_file.filename, source_blob=file_bytes)

        for _, row in df.iterrows():
            raw_case = row.get("Case Number", "0")
            try: case_num = str(int(float(raw_case))) if raw_case != "" else "0"
            except: case_num = str(raw_case).strip() or "0"

            raw_ver = row.get("Version Number", "1")
            try: ver_num = str(int(float(raw_ver))) if raw_ver != "" else "1"
            except: ver_num = str(raw_ver).strip() or "1"

            attrs = {k: get_mapped_value(row, k) for k in COL_MAP.keys()}
            attrs['pages'] = json.dumps([attrs['narrative']])
            attrs['filename'] = f"{case_num}-{ver_num}.json"
            attrs['meta'] = json.dumps({
                "demographic": generate_demographic_content(row, mode=file_mode),
                "outcomes": generate_outcomes_content(row, mode=file_mode),
                "products": generate_products_content(row, columns=df.columns, mode=file_mode)
            })
            attrs['full_data'] = json.dumps(row.to_dict())

            case_id = upsert_case(case_num, ver_num, attrs)
            link_case_to_project(project_id, case_id)

        return jsonify({'message': f'Project {project_name} imported to database.'}), 200

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@project_blueprint.route('/api/delete-project', methods=['POST'])
@cross_origin()
def delete_project():
    data = request.get_json()
    name = data.get("projectName")
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM projects WHERE name = ?', (name,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Deleted'})
    except: return jsonify({'error': 'Fail'}), 500
