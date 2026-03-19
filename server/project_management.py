from flask import jsonify, request, Blueprint
from flask_cors import cross_origin
import pandas as pd
import os
import json
from text_processing import generate_demographic_content, generate_outcomes_content, generate_products_content

project_blueprint = Blueprint('project', __name__)

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
        # Try to load the "Case Detail" sheet first
        
        excel_file = pd.ExcelFile(excel_save_path)
        sheet_names = excel_file.sheet_names
            
        if "Case Detail" in sheet_names:
            file_mode = 'RxLogix'
            df = pd.read_excel(excel_save_path, sheet_name="Case Detail", skiprows=2, engine='openpyxl')
            if not df.empty:
                first_cell_last_row = str(df.iloc[-1, 0]).strip().lower()
            if 'meddra version' in first_cell_last_row:
                df = df.iloc[:-1]  # Drop the last row
        elif 'Case Details' in sheet_names:
            file_mode = 'InfoVIP'
            df = pd.read_excel(excel_save_path, sheet_name="Case Details", engine='openpyxl')
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
        df.to_excel(excel_save_path,index=None)

        # Ensure project folder exists
        project_path = os.path.join('history', project_name)
        os.makedirs(project_path, exist_ok=True)

        # Loop over each row in the sheet
        for idx, row in df.iterrows():
            # === Basic Content ===
            text = str(row.get("Narrative", "")).strip()
            case_number = str(int(row.get("Case Number", "0"))).strip()
            version_number = str(int(row.get("Version Number", "Tmp"))).strip()

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
            json_data = {
                "pages": [text],
                "annotations": [],
                "meta": {
                    "demographic": demographic_html,
                    "outcomes": outcomes_html,
                    "products": products_html
                }
            }

            file_path = os.path.join(project_path, file_name)
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
