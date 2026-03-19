from flask import jsonify, request, Blueprint
from flask_cors import cross_origin
import pandas as pd
import os
import json
import traceback
from text_processing import generate_demographic_content, generate_outcomes_content, generate_products_content

project_blueprint = Blueprint('project', __name__)

def find_header_row(excel_path, sheet_name, engine='openpyxl'):
    """
    Search for the row containing 'Case Number' and 'Version Number'.
    Returns the row index (to be used as 'header' in pd.read_excel).
    """
    df_preview = pd.read_excel(excel_path, sheet_name=sheet_name, header=None, nrows=20, engine=engine)
    for idx, row in df_preview.iterrows():
        row_values = [str(val).strip() for val in row.values]
        if "Case Number" in row_values and "Version Number" in row_values:
            return idx
    return 0  # Fallback to first row

# Endpoint to create a project from an Excel file
@project_blueprint.route('/api/create-project-from-excel', methods=['POST'])
@cross_origin()
def create_project_from_excel():
    if 'file' not in request.files or 'projectName' not in request.form:
        return jsonify({'error': 'Missing file or project name'}), 400

    uploaded_file = request.files['file']
    project_name = request.form['projectName'].strip()
    file_mode = 'not specified'

    if not project_name:
        return jsonify({'error': 'Empty project name'}), 400

    try:
        # Save the Excel to Meta/
        meta_path = os.path.join('history', 'Meta')
        os.makedirs(meta_path, exist_ok=True)
        excel_save_path = os.path.join(meta_path, f'{project_name}_Meta.xlsx')
        uploaded_file.save(excel_save_path)
        
        excel_file = pd.ExcelFile(excel_save_path, engine='openpyxl')
        sheet_names = excel_file.sheet_names
            
        if "Case Detail" in sheet_names:
            file_mode = 'RxLogix'
            header_idx = find_header_row(excel_save_path, "Case Detail")
            df = pd.read_excel(excel_save_path, sheet_name="Case Detail", header=header_idx, engine='openpyxl')
            if not df.empty:
                first_cell_last_row = str(df.iloc[-1, 0]).strip().lower()
            if 'meddra version' in first_cell_last_row:
                df = df.iloc[:-1]  # Drop the last row
        elif 'Case Details' in sheet_names:
            file_mode = 'InfoVIP'
            header_idx = find_header_row(excel_save_path, "Case Details")
            df = pd.read_excel(excel_save_path, sheet_name="Case Details", header=header_idx, engine='openpyxl')
            df = df.rename(columns={
                "Attachments Info/Link":"Attachments Info-Link",
                "FAERS Case #": "Case Number",
                "Version Number": "Version Number",
                "Latest FDA Received date": "Latest FDA Received Date",
                "Manufacturer Control #":"MCN or CTU",
                "Medical History/Medical History Comments":"Medical History and Comments",
                "ALL Suspect Product Names":"ALL Suspect Products",
                "Country Derived": "Country Derived",
                "Patient Id": "Patient ID",
                "Age in Years": "Age in Years",
                "DOB": "DOB",
                "Sex": "Sex",
                "Weight (kg)": "Weight In kg",
                "Health Professional": "Health Professional"
            })
        else: 
            detail_sheets = [s for s in sheet_names if "detail" in s.lower()]
            if not detail_sheets:
                return jsonify({'error': 'No sheet named "Case Detail" or similar found.'}), 400
            df = excel_file.parse(sheet_name=detail_sheets[0])
        #update the table with new columns
        df = df.fillna('')
        df.to_excel(excel_save_path, index=None, engine='openpyxl')

        # Ensure project folder exists
        project_path = os.path.join('history', project_name)
        os.makedirs(project_path, exist_ok=True)

        # Loop over each row in the sheet
        for idx, row in df.iterrows():
            # === Basic Content ===
            text = str(row.get("Narrative", "")).strip()
            
            # Safely get Case Number and Version Number as strings
            raw_case = row.get("Case Number", "0")
            try:
                # If it's a number (float/int), convert to int then str to avoid .0
                case_number = str(int(float(raw_case))) if raw_case != "" else "0"
            except (ValueError, TypeError):
                case_number = str(raw_case).strip() or "0"

            raw_version = row.get("Version Number", "1")
            try:
                version_number = str(int(float(raw_version))) if raw_version != "" else "1"
            except (ValueError, TypeError):
                version_number = str(raw_version).strip() or "1"

            file_name = str(row.get("annotate_filename", "")).strip()
            if not file_name:
                file_name = f"{case_number}-{version_number}.json"
            elif not file_name.endswith(".json"):
                file_name += ".json"

            # generating meta data 
            demographic_html = generate_demographic_content(row, mode=file_mode)
            outcomes_html = generate_outcomes_content(row, mode=file_mode)
            products_html = generate_products_content(row, columns=df.columns, mode=file_mode)

            # === Save JSON ===
            file_path = os.path.join(project_path, file_name)
            
            # Smart logic: if file exists, preserve annotations
            existing_annotations = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        old_data = json.load(f)
                        existing_annotations = old_data.get("annotations", [])
                except Exception as e:
                    print(f"Warning: Failed to load existing file {file_name} for merging: {e}")

            json_data = {
                "pages": [text],
                "annotations": existing_annotations,
                "meta": {
                    "demographic": demographic_html,
                    "outcomes": outcomes_html,
                    "products": products_html
                }
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

        return jsonify({'message': f'Project {project_name} created with {len(df)} files.'}), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to create project: {str(e)}'}), 500

@project_blueprint.route('/api/delete-project', methods=['POST'])
@cross_origin()
def delete_project():
    data = request.get_json()
    project_name = data.get("projectName")
    if not project_name:
        return jsonify({'error': 'No project name provided'}), 400

    try:
        meta_path = os.path.join('history', 'Meta', f'{project_name}_Meta.xlsx')
        project_path = os.path.join('history', project_name)

        if os.path.exists(meta_path):
            os.remove(meta_path)

        if os.path.exists(project_path):
            import shutil
            shutil.rmtree(project_path)

        return jsonify({'message': f'Project {project_name} deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
