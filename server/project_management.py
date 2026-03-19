from flask import jsonify, request, Blueprint
from flask_cors import cross_origin
import pandas as pd
import os
import json
import traceback
import io
from text_processing import generate_demographic_content, generate_outcomes_content, generate_products_content
from database_manager import create_project, upsert_case, link_case_to_project, get_db_connection, get_project_by_name

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
    # Case-insensitive lookup
    row_keys = {str(k).strip().lower(): k for k in row.index}
    possible_cols = COL_MAP.get(internal_key, [])
    for c in possible_cols:
        c_lower = c.lower()
        if c_lower in row_keys:
            val = row[row_keys[c_lower]]
            return str(val).strip() if pd.notna(val) else ""
    return ""

def find_header_row(file_bytes, sheet_name, engine='openpyxl'):
    df_preview = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=None, nrows=20, engine=engine)
    for idx, row in df_preview.iterrows():
        vals = [str(v).strip().lower() for v in row.values]
        if "case number" in vals or "faers case #" in vals: return idx
    return 0

@project_blueprint.route('/api/projects', methods=['GET'])
@cross_origin()
def list_projects():
    try:
        conn = get_db_connection()
        rows = conn.execute('SELECT name, source_file FROM projects ORDER BY name ASC').fetchall()
        conn.close()
        projects = [row['name'] for row in rows]
        return jsonify(projects), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_blueprint.route('/api/show_project/<project_name>', methods=['GET'])
@cross_origin()
def show_project(project_name):
    try:
        project = get_project_by_name(project_name)
        if not project: return jsonify({'error': 'Project not found'}), 404

        conn = get_db_connection()
        query = '''
            SELECT 
                c.case_number as "Case Number", c.version_number as "Version Number", 
                c.mcn_or_ctu as "MCN or CTU", c.report_type as "Report Type", c.form_type as "Form Type",
                c.initial_fda_received_date as "Initial FDA Received Date", 
                c.latest_fda_received_date as "Latest FDA Received Date", 
                c.completeness_score as "Completeness Score",
                c.patient_id as "Patient ID", c.age_in_years as "Age in Years", c.dob as "DOB", 
                c.sex as "Sex", c.weight_in_kg as "Weight In kg", c.race as "Race",
                c.medical_history_and_comments as "Medical History and Comments", 
                c.sender_mfr_organization as "Sender Mfr Organization", 
                c.reporter_organization as "Reporter Organization",
                c.country_derived as "Country Derived", 
                c.reporter_qualifications as "Reporter Qualifications", 
                c.health_professional as "Health Professional",
                c.report_source as "Report Source", c.narrative as "Narrative", 
                c.seriousness as "Seriousness", c.all_outcomes as "All Outcomes",
                c.all_suspect_products as "All Suspect Products", 
                c.all_suspect_pais as "All Suspect PAIs", 
                c.all_concomitant_products as "All Concomitant Products",
                c.all_llts as "All LLTs", c.all_pts as "All PTs", 
                c.all_hlts as "All HLTs", c.all_hlgts as "All HLGTs", 
                c.all_socs as "All SOCs",
                c.annotate_filename, c.meta
            FROM cases c
            JOIN project_cases pc ON c.id = pc.case_id
            WHERE pc.project_id = ?
        '''
        rows = conn.execute(query, (project['id'],)).fetchall()
        conn.close()

        records = [dict(r) for r in rows]
        for r in records:
            r['counts'] = {'LLM': 0, 'SME1': 0, 'SME2': 0} # Placeholders
            r['meta'] = json.loads(r['meta']) if r['meta'] else {}

        return jsonify({'projectName': project_name, 'records': records}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        target_sheet = "Case Detail" if "Case Detail" in xl.sheet_names else ("Case Details" if "Case Details" in xl.sheet_names else xl.sheet_names[0])
        h_idx = find_header_row(file_bytes, target_sheet)
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=target_sheet, header=h_idx, engine='openpyxl')
        
        file_mode = 'InfoVIP' if any('FAERS Case #' in str(c) for c in df.columns) else 'RxLogix'
        df.columns = [str(c).strip() for c in df.columns]
        if file_mode == 'InfoVIP':
            df = df.rename(columns={"FAERS Case #": "Case Number"})

        df = df.fillna('')
        project_id = create_project(project_name, source_file=uploaded_file.filename, source_blob=file_bytes)

        for _, row in df.iterrows():
            raw_case = str(row.get("Case Number", "0"))
            try: case_num = str(int(float(raw_case))) if raw_case else "0"
            except: case_num = raw_case or "0"

            raw_ver = str(row.get("Version Number", "1"))
            try: ver_num = str(int(float(raw_ver))) if raw_ver else "1"
            except: ver_num = raw_ver or "1"

            attrs = {k: get_mapped_value(row, k) for k in COL_MAP.keys()}
            if not attrs['annotate_filename']: attrs['annotate_filename'] = f"{case_num}-{ver_num}.json"

            attrs['pages'] = json.dumps([attrs['narrative']])
            attrs['meta'] = json.dumps({
                "demographic": generate_demographic_content(row, mode=file_mode),
                "outcomes": generate_outcomes_content(row, mode=file_mode),
                "products": generate_products_content(row, columns=df.columns, mode=file_mode)
            })
            attrs['full_data'] = json.dumps(row.to_dict())

            case_id = upsert_case(case_num, ver_num, attrs)
            link_case_to_project(project_id, case_id)

        return jsonify({'message': 'Import complete'}), 200
    except Exception as e:
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
