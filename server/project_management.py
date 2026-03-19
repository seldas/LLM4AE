from flask import jsonify, request, Blueprint
from flask_cors import cross_origin
import pandas as pd
import os
import json
import traceback
from text_processing import generate_demographic_content, generate_outcomes_content, generate_products_content
from database_manager import create_project, upsert_case, link_case_to_project, get_db_connection

project_blueprint = Blueprint('project', __name__)

def find_header_row(excel_path, sheet_name, engine='openpyxl'):
    df_preview = pd.read_excel(excel_path, sheet_name=sheet_name, header=None, nrows=20, engine=engine)
    for idx, row in df_preview.iterrows():
        vals = [str(v).strip() for v in row.values]
        if "Case Number" in vals and "Version Number" in vals: return idx
    return 0

@project_blueprint.route('/api/create-project-from-excel', methods=['POST'])
@cross_origin()
def create_project_from_excel():
    if 'file' not in request.files or 'projectName' not in request.form:
        return jsonify({'error': 'Missing file or project name'}), 400

    uploaded_file = request.files['file']
    project_name = request.form['projectName'].strip()
    if not project_name: return jsonify({'error': 'Empty project name'}), 400

    try:
        # Save Excel audit trail
        meta_path = os.path.join('history', 'Meta')
        os.makedirs(meta_path, exist_ok=True)
        excel_save_path = os.path.join(meta_path, f'{project_name}_Meta.xlsx')
        uploaded_file.save(excel_save_path)
        
        xl = pd.ExcelFile(excel_save_path, engine='openpyxl')
        sheet_names = xl.sheet_names
        file_mode = 'RxLogix'
        
        if "Case Detail" in sheet_names:
            h_idx = find_header_row(excel_save_path, "Case Detail")
            df = pd.read_excel(excel_save_path, sheet_name="Case Detail", header=h_idx, engine='openpyxl')
        elif "Case Details" in sheet_names:
            file_mode = 'InfoVIP'
            h_idx = find_header_row(excel_save_path, "Case Details")
            df = pd.read_excel(excel_save_path, sheet_name="Case Details", header=h_idx, engine='openpyxl')
            df = df.rename(columns={"FAERS Case #": "Case Number", "Version Number": "Version Number"}) # Minimal rename for core ID
        else:
            detail_sheets = [s for s in sheet_names if "detail" in s.lower()]
            if not detail_sheets: return jsonify({'error': 'No suitable sheet found.'}), 400
            df = xl.parse(sheet_name=detail_sheets[0])

        df = df.fillna('')
        project_id = create_project(project_name, source_file=f'{project_name}_Meta.xlsx')

        for idx, row in df.iterrows():
            narrative = str(row.get("Narrative", "")).strip()
            
            # Identify Unique Case
            raw_case = row.get("Case Number", "0")
            try: case_num = str(int(float(raw_case))) if raw_case != "" else "0"
            except: case_num = str(raw_case).strip() or "0"

            raw_ver = row.get("Version Number", "1")
            try: ver_num = str(int(float(raw_ver))) if raw_ver != "" else "1"
            except: ver_num = str(raw_ver).strip() or "1"

            filename = f"{case_num}-{ver_num}.json"
            
            # Meta HTML (Legacy UI compatibility)
            meta_html = {
                "demographic": generate_demographic_content(row, mode=file_mode),
                "outcomes": generate_outcomes_content(row, mode=file_mode),
                "products": generate_products_content(row, columns=df.columns, mode=file_mode)
            }

            # Full row data as JSON
            full_data = row.to_dict()

            # 1. Upsert Case (Updates if exists)
            case_id = upsert_case(case_num, ver_num, [narrative], meta_html, full_data, filename=filename)
            
            # 2. Link to Project
            link_case_to_project(project_id, case_id)

        return jsonify({'message': f'Project {project_name} processed. {len(df)} cases linked.'}), 200

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@project_blueprint.route('/api/delete-project', methods=['POST'])
@cross_origin()
def delete_project():
    data = request.get_json()
    name = data.get("projectName")
    if not name: return jsonify({'error': 'No name'}), 400
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM projects WHERE name = ?', (name,))
        conn.commit()
        conn.close()
        return jsonify({'message': f'Project {name} deleted'}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500
