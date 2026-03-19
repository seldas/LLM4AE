from flask import jsonify, request, Blueprint
import json
import os
import re
import logging
import pandas as pd
from database_manager import (
    get_db_connection, 
    get_project_by_name, 
    create_project, 
    get_document, 
    upsert_document, 
    get_annotations, 
    save_annotations, 
    get_user_by_note
)

history_blueprint = Blueprint('history', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FOLDER = os.path.join(BASE_DIR, 'history')

# Endpoint to list documents in a project from DB
@history_blueprint.route('/api/history-files/<folder_name>', methods=['GET'])
def list_history_files(folder_name=''):
    try:
        project_name = folder_name or 'Playground'
        project = get_project_by_name(project_name)
        
        if not project:
            return jsonify({'files': [], 'message': f'Project {project_name} not found in DB'}), 200

        conn = get_db_connection()
        query = '''
            SELECT d.id, d.filename, d.meta
            FROM documents d
            WHERE d.project_id = ?
        '''
        docs = conn.execute(query, (project['id'],)).fetchall()
        
        json_files = []
        for doc in docs:
            doc_id = doc['id']
            filename = doc['filename']
            meta = json.loads(doc['meta']) if doc['meta'] else {}
            
            # Count annotations per functional group
            # Mapping database notes/usernames to frontend groups
            counts = {'LLM': 0, 'SME1': 0, 'SME2': 0, 'Other': 0}
            
            annotations = get_annotations(doc_id)
            for ann in annotations:
                note = (ann['note'] or '').upper()
                if 'LLM' in note or 'Llama4' in note.capitalize() or 'BioBERT' in note.capitalize():
                    counts['LLM'] += 1
                elif 'SME2' in note or 'K.L' in note: 
                    counts['SME2'] += 1
                elif 'SME' in note or 'MJ.L' in note:
                    counts['SME1'] += 1
                else:
                    counts['Other'] += 1

            json_files.append({
                'filename': filename,
                'counts': counts,
                'meta': meta
            })

        conn.close()
        return jsonify({'files': json_files})

    except Exception as e:
        logging.error(f"Error listing history files: {e}")
        return jsonify({'error': str(e)}), 500

# Endpoint to load or delete a specific history file from DB
@history_blueprint.route('/api/history/<path:file_path>', methods=['GET', 'POST', 'DELETE'])
def history_file(file_path):
    try:
        if '___' in file_path:
            parts = file_path.split('___')
            project_name = parts[0]
            filename = parts[1]
        else:
            project_name = 'Playground'
            filename = file_path

        if not filename.endswith('.json'):
            filename += '.json'

        project = get_project_by_name(project_name)
        if not project and request.method != 'DELETE':
            project_id = create_project(project_name)
            project = {'id': project_id}

        if request.method in ['GET', 'POST']:
            doc = get_document(project['id'], filename)
            
            if not doc:
                data = request.get_json(silent=True) or {}
                narrative = data.get('narrative', '')
                if narrative:
                    upsert_document(project['id'], filename, [narrative], {})
                    doc = get_document(project['id'], filename)
                else:
                    return jsonify({'error': 'Document not found in database'}), 404

            # Prepare JSON response in existing format
            # pages is stored as JSON string in DB
            pages = json.loads(doc['pages'])
            meta = json.loads(doc['meta']) if doc['meta'] else {}
            
            # Get all annotations
            db_annotations = get_annotations(doc['id'])
            annotations = []
            for ann in db_annotations:
                annotations.append({
                    'label': ann['label'],
                    'textContext': {
                        'start': ann['start_offset'],
                        'end': ann['end_offset'],
                        'text': ann['text_content']
                    },
                    'note': ann['note'],
                    'relationships': json.loads(ann['relationships']) if ann['relationships'] else {}
                })
            
            return jsonify({
                'pages': pages,
                'annotations': annotations,
                'meta': meta
            })

        elif request.method == 'DELETE':
            if not project:
                return jsonify({'error': 'Project not found'}), 404
            
            conn = get_db_connection()
            conn.execute('DELETE FROM documents WHERE project_id = ? AND filename = ?', (project['id'], filename))
            conn.commit()
            conn.close()
            return jsonify({'message': f'{filename} deleted successfully from database.'}), 200

    except Exception as e:
        logging.error(f"Error in history_file: {e}")
        return jsonify({'error': str(e)}), 500

# Endpoint to save content to DB
@history_blueprint.route('/api/save', methods=['POST'])
def save_file():
    data = request.get_json()
    file_name = data.get('fileName', '').strip()
    curr_folder = data.get('curr_folder', 'Playground').strip()
    pages = data.get('pages', [])
    annotations = data.get('annotations', [])
    meta = data.get('meta', {})
    
    if '___' in curr_folder:
        curr_folder = curr_folder.split('___')[0] # Simplify for DB lookup

    if not file_name:
        return jsonify({'error': 'File name is required'}), 400

    if not file_name.endswith('.json'):
        file_name += '.json'

    try:
        project_id = create_project(curr_folder)
        doc_id = upsert_document(project_id, file_name, pages, meta)
        
        # Save annotations grouped by user
        # In a real multi-user app, we'd get the current user from session
        # For now, we'll infer user from the 'note' field in each annotation
        # and fall back to the Admin user (id=1)
        
        # 1. Clear existing annotations for this doc
        conn = get_db_connection()
        conn.execute('DELETE FROM annotations WHERE document_id = ?', (doc_id,))
        
        # 2. Insert new annotations
        for ann in annotations:
            note = ann.get('note', 'Admin')
            user_id = get_user_by_note(note) or 1 # Fallback to Admin
            
            relationships = json.dumps(ann.get('relationships', {}))
            label = ann.get('label', 'UNKNOWN')
            start = ann.get('textContext', {}).get('start', 0)
            end = ann.get('textContext', {}).get('end', 0)
            text_content = ann.get('textContext', {}).get('text', '')
            
            conn.execute('''
                INSERT INTO annotations (document_id, user_id, label, start_offset, end_offset, text_content, note, relationships)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (doc_id, user_id, label, start, end, text_content, note, relationships))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'File saved successfully to database.'})
    except Exception as e:
        logging.error(f"Error saving file: {e}")
        return jsonify({'error': str(e)}), 500

@history_blueprint.route('/api/meta', methods=['GET'])
def get_meta_file():
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({'error': 'Missing file name'}), 400

    meta_path = os.path.join(HISTORY_FOLDER, 'Meta', file_name)
    if not os.path.exists(meta_path):
        return jsonify({'error': 'File not found'}), 404

    try:
        try:
            df = pd.read_excel(meta_path, engine='openpyxl')
        except Exception:
            xl = pd.ExcelFile(meta_path, engine='openpyxl')
            detail_sheets = [s for s in xl.sheet_names if "detail" in s.lower()]
            if not detail_sheets:
                df = xl.parse(sheet_name=0)
            else:
                df = xl.parse(sheet_name=detail_sheets[0], skiprows=2)
        
        df = df.fillna('')
        records = df.to_dict(orient="records")
        return jsonify({'records': records})

    except Exception as e:
        logging.error(f"Error reading meta file {file_name}: {e}")
        return jsonify({'error': f'Failed to read Excel file: {str(e)}'}), 500
