from flask import jsonify, request, Blueprint
import json
import os
import re
import logging
import pandas as pd

history_blueprint = Blueprint('history', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FOLDER = os.path.join(BASE_DIR, 'history')
os.makedirs(HISTORY_FOLDER, exist_ok=True)

# Endpoint to list .json files in the history folder and update LLM meta info
@history_blueprint.route('/api/history-files/<folder_name>', methods=['GET'])
def list_history_files(folder_name=''):
    try:
        base_folder = HISTORY_FOLDER
        folder_path = os.path.join(base_folder, 'Playground') if not folder_name else os.path.join(base_folder, folder_name)

        if not os.path.exists(folder_path):
            return jsonify({'files': [], 'error': f'Folder not found: {folder_path}'}), 200

        json_files = []

        for entry in os.scandir(folder_path):
            if entry.is_file() and entry.name.endswith('.json'):
                file_info = {
                    'filename': entry.name,
                    'counts': {'LLM': 0, 'SME1': 0, 'SME2': 0, 'Other': 0}
                }

                try:
                    full_path = entry.path
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    updated = False
                    annotations = data.get('annotations', [])
                    for ann in annotations:
                        note = (ann.get('note') or '').upper()
                        if 'LLM' in note:
                            file_info['counts']['LLM'] += 1
                        elif 'SME2' in note: 
                            file_info['counts']['SME2'] += 1
                        elif 'SME' in note: # SME, if not specified, related to SME1
                            file_info['counts']['SME1'] += 1
                        else:
                            file_info['counts']['Other'] += 1

                    if 'meta' not in data:
                        data['meta'] = {}
                        updated = True
                        
                    file_info['meta'] = data['meta']

                    if updated:
                        with open(full_path, 'w', encoding='utf-8') as fw:
                            json.dump(data, fw, indent=2, ensure_ascii=False)

                except Exception as e:
                    file_info['error'] = str(e)

                json_files.append(file_info)

        return jsonify({'files': json_files})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint to upload a history file
@history_blueprint.route('/api/upload-history', methods=['POST'])
def upload_history_file():
    curr_folder = request.form.get('curr_folder')

    if not curr_folder:
        return jsonify({'error': 'Missing target folder'}), 400

    # Ensure slashes are normalized and secure
    curr_folder = re.sub('___', '/', curr_folder.strip())
    target_folder = os.path.join(HISTORY_FOLDER, curr_folder)

    # Ensure the file exists in the request
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    uploaded_file = request.files['file']

    if not uploaded_file.filename.endswith('.json'):
        return jsonify({'error': 'Unsupported file format. Only JSON files are allowed.'}), 400

    # Extract base filename and prepare target path
    original_filename = uploaded_file.filename
    file_name, file_extension = os.path.splitext(original_filename)

    os.makedirs(target_folder, exist_ok=True)  # Ensure directory exists
    file_path = os.path.join(target_folder, original_filename)

    counter = 1
    while os.path.exists(file_path):
        file_path = os.path.join(target_folder, f"{file_name}({counter}){file_extension}")
        counter += 1

    try:
        uploaded_file.save(file_path)
        return jsonify({'message': f'File {os.path.basename(file_path)} uploaded successfully.'}), 200
    except Exception as e:
        logging.error(f"Error while uploading history file: {e}")
        return jsonify({'error': f'Failed to upload file: {str(e)}'}), 500

# Endpoint to load or delete a specific history file
@history_blueprint.route('/api/history/<path:file_path>', methods=['GET', 'POST', 'DELETE'])
def history_file(file_path):
    try:
        if '___' in file_path:
            parts = file_path.split('___')
        else:
            parts = [file_path]

        json_file_path = os.path.join(HISTORY_FOLDER, *parts)
        print(f"DEBUG: Accessing file at {json_file_path}")

        if request.method in ['GET', 'POST']:
            if not os.path.exists(json_file_path):
                # ✅ Check for narrative in query params
                data = request.get_json()
                narrative = data.get('narrative', '')
                if narrative:
                    print(f"INFO: File not found, creating new with narrative.")
                    os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
                    with open(json_file_path, 'w', encoding='utf-8') as f:
                        json.dump({
                            "pages": [narrative],
                            "annotations": [],
                            "meta": {}
                        }, f, ensure_ascii=False, indent=2)
                else:
                    return jsonify({'error': 'File not found and no narrative provided'}), 404

            with open(json_file_path, "r", encoding="utf-8", errors="ignore") as f:
                json_data = json.load(f)
                try:
                    json_data['pages'] = [x.encode("latin1").decode("utf-8") for x in json_data['pages']]
                except Exception:
                    pass
                return jsonify(json_data)
        elif request.method == 'DELETE':
            if not os.path.exists(json_file_path):
                return jsonify({'error': 'File not found'}), 404
            os.remove(json_file_path)
            return jsonify({'message': f'{parts[-1]} deleted successfully.'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint to save content to a .txt file in the history folder
@history_blueprint.route('/api/save', methods=['POST'])
def save_file():
    data = request.get_json()
    file_name = data.get('fileName', '').strip()
    curr_folder = data.get('curr_folder', HISTORY_FOLDER).strip()
    pages = data.get('pages', [])
    annotations = data.get('annotations', [])
    meta = data.get('meta', {})
    
    if '___' in curr_folder:
        curr_folder = re.sub('___', '/', curr_folder)

    if not file_name or not pages:
        return jsonify({'error': 'File name and content are required'}), 400

    full_path = os.path.join(HISTORY_FOLDER, curr_folder)
    os.makedirs(full_path, exist_ok=True)  # ensure folder exists

    json_file_path = os.path.join(full_path, f"{file_name}.json")

    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump({'pages': pages, 'annotations': annotations, 'meta': meta}, f, ensure_ascii=False, indent=2)
        return jsonify({'message': 'File saved successfully.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint to create a folder
@history_blueprint.route('/api/create-folder', methods=['POST'])
def create_folder():
    data = request.get_json()
    folder_path = data.get('folderPath')

    if not folder_path:
        return jsonify({'error': 'No folder path provided'}), 400

    # Replace custom delimiter with system path separator
    safe_folder_path = folder_path.replace('___', os.sep)

    # Base directory where folders are stored
    base_dir = os.path.join(os.getcwd(), 'data', 'history')
    full_path = os.path.join(base_dir, safe_folder_path)

    try:
        os.makedirs(full_path, exist_ok=True)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@history_blueprint.route('/api/meta', methods=['GET'])
def get_meta_file():
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({'error': 'Missing file name'}), 400

    meta_path = os.path.join(HISTORY_FOLDER, 'Meta', file_name)
    if not os.path.exists(meta_path):
        return jsonify({'error': 'File not found'}), 404

    # Try Case Detail sheet first, then any sheet with "detail"
    try:
        try:
            df = pd.read_excel(meta_path, engine='openpyxl')
        except Exception:
            xl = pd.ExcelFile(meta_path, engine='openpyxl')
            detail_sheets = [s for s in xl.sheet_names if "detail" in s.lower()]
            if not detail_sheets:
                # If no detail sheet, just try the first sheet
                df = xl.parse(sheet_name=0)
            else:
                df = xl.parse(sheet_name=detail_sheets[0], skiprows=2)
        
        df = df.fillna('')
        records = df.to_dict(orient="records")
        return jsonify({'records': records})

    except Exception as e:
        logging.error(f"Error reading meta file {file_name}: {e}")
        return jsonify({'error': f'Failed to read Excel file: {str(e)}'}), 500
