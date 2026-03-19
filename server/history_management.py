from flask import jsonify, request, Blueprint
import json
import os
import re
import logging
import pandas as pd
import io
from database_manager import (
    get_db_connection, 
    get_project_by_name, 
    create_project, 
    get_case, 
    upsert_case, 
    get_annotations, 
    get_user_by_note
)

history_blueprint = Blueprint('history', __name__)

@history_blueprint.route('/api/history-files/<folder_name>', methods=['GET'])
def list_history_files(folder_name=''):
    try:
        project_name = folder_name or 'Playground'
        project = get_project_by_name(project_name)
        if not project: return jsonify({'files': []}), 200

        conn = get_db_connection()
        docs = conn.execute('SELECT id, annotate_filename, meta FROM cases c JOIN project_cases pc ON c.id = pc.case_id WHERE pc.project_id = ?', (project['id'],)).fetchall()
        
        json_files = []
        for doc in docs:
            counts = {'LLM': 0, 'SME1': 0, 'SME2': 0, 'Other': 0}
            anns = get_annotations(doc['id'])
            for ann in anns:
                note = (ann['note'] or '').upper()
                if 'LLM' in note or 'Llama' in note.capitalize() or 'BERT' in note.capitalize(): counts['LLM'] += 1
                elif 'SME2' in note or 'K.L' in note: counts['SME2'] += 1
                elif 'SME' in note or 'MJ.L' in note: counts['SME1'] += 1
                else: counts['Other'] += 1

            json_files.append({
                'filename': doc['annotate_filename'],
                'counts': counts,
                'meta': json.loads(doc['meta']) if doc['meta'] else {}
            })
        conn.close()
        return jsonify({'files': json_files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@history_blueprint.route('/api/history/<path:file_path>', methods=['GET', 'POST', 'DELETE'])
def history_file(file_path):
    try:
        if '___' in file_path:
            parts = file_path.split('___')
            project_name, filename = parts[0], parts[1]
        else:
            project_name, filename = 'Playground', file_path

        # filename here refers to annotate_filename
        project = get_project_by_name(project_name)

        if request.method in ['GET', 'POST']:
            doc = get_case(project_id=project['id'] if project else None, filename=filename)
            if not doc:
                data = request.get_json(silent=True) or {}
                narrative = data.get('narrative', '')
                if narrative:
                    pid = project['id'] if project else create_project(project_name)
                    cid = upsert_case("0", "1", {
                        'narrative': narrative, 
                        'pages': json.dumps([narrative]), 
                        'annotate_filename': filename
                    })
                    from database_manager import link_case_to_project
                    link_case_to_project(pid, cid)
                    doc = get_case(case_id=cid)
                else: return jsonify({'error': 'Not found'}), 404

            return jsonify({
                'pages': json.loads(doc['pages']),
                'annotations': [{
                    'label': a['label'],
                    'textContext': {'start': a['start_offset'], 'end': a['end_offset'], 'text': a['text_content']},
                    'note': a['note'],
                    'relationships': json.loads(a['relationships']) if a['relationships'] else {}
                } for a in get_annotations(doc['id'])],
                'meta': json.loads(doc['meta']) if doc['meta'] else {}
            })

        elif request.method == 'DELETE':
            if not project: return jsonify({'error': 'No project'}), 404
            conn = get_db_connection()
            conn.execute('DELETE FROM project_cases WHERE project_id = ? AND case_id = (SELECT id FROM cases WHERE annotate_filename = ?)', (project['id'], filename))
            conn.commit()
            conn.close()
            return jsonify({'message': 'Deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@history_blueprint.route('/api/save', methods=['POST'])
def save_file():
    data = request.get_json()
    fname = data.get('fileName', '').strip()
    folder = data.get('curr_folder', 'Playground').strip()
    if '___' in folder: folder = folder.split('___')[0]

    try:
        project_id = create_project(folder)
        # Check if already exists to get its case/ver
        existing = get_case(project_id=project_id, filename=fname)
        c_num, v_num = (existing['case_number'], existing['version_number']) if existing else ("0", "1")

        case_id = upsert_case(c_num, v_num, {
            'narrative': data.get('pages', [""])[0],
            'pages': json.dumps(data.get('pages', [])),
            'meta': json.dumps(data.get('meta', {})),
            'annotate_filename': fname
        })
        from database_manager import link_case_to_project
        link_case_to_project(project_id, case_id)
        
        conn = get_db_connection()
        conn.execute('DELETE FROM annotations WHERE case_id = ?', (case_id,))
        for ann in data.get('annotations', []):
            uid = get_user_by_note(ann.get('note', 'Admin')) or 1
            conn.execute('''
                INSERT INTO annotations (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (case_id, uid, ann['label'], ann['textContext']['start'], ann['textContext']['end'], ann['textContext']['text'], ann['note'], json.dumps(ann.get('relationships', {}))))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Saved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@history_blueprint.route('/api/meta', methods=['GET'])
def get_meta_file():
    fname = request.args.get('file')
    if not fname: return jsonify({'error': 'Missing file'}), 400
    try:
        conn = get_db_connection()
        row = conn.execute('SELECT source_file_blob FROM projects WHERE source_file = ?', (fname,)).fetchone()
        conn.close()
        if row and row['source_file_blob']:
            xl = pd.ExcelFile(io.BytesIO(row['source_file_blob']), engine='openpyxl')
            target = "Case Detail" if "Case Detail" in xl.sheet_names else ("Case Details" if "Case Details" in xl.sheet_names else xl.sheet_names[0])
            df = xl.parse(sheet_name=target).fillna('')
            return jsonify({'records': df.to_dict(orient="records")})
        return jsonify({'error': 'Not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
