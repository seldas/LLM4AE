from flask import jsonify, request, Blueprint
import json
import os
import re
import logging
import pandas as pd
import io
from database_manager import (
    get_db_connection, 
    get_case, 
    upsert_case, 
    get_annotations, 
    get_user_by_note
)

history_blueprint = Blueprint('history', __name__)


@history_blueprint.route('/api/history-files/<folder_name>', methods=['GET'])
def list_history_files(folder_name=''):
    try:
        conn = get_db_connection()
        query = '''
            SELECT 
                c.id, 
                c.annotate_filename, 
                c.meta,
                COUNT(CASE WHEN u.username IN ('Llama4', 'BioBERT') OR u.migration_key = 'LLM' THEN a.id END) as count_llm,
                COUNT(CASE WHEN u.username = 'MJ.L' OR u.migration_key = 'SME1' THEN a.id END) as count_sme1,
                COUNT(CASE WHEN u.username = 'K.L' OR u.migration_key = 'SME2' THEN a.id END) as count_sme2,
                COUNT(CASE WHEN u.username NOT IN ('Llama4', 'BioBERT', 'MJ.L', 'K.L') AND u.migration_key NOT IN ('LLM', 'SME1', 'SME2') THEN a.id END) as count_other
            FROM cases c
            LEFT JOIN annotations a ON c.id = a.case_id
            LEFT JOIN users u ON a.user_id = u.id
            GROUP BY c.id
        '''
        rows = conn.execute(query).fetchall()

        json_files = []
        for row in rows:
            json_files.append({
                'id': row['id'],
                'filename': row['annotate_filename'],
                'counts': {
                    'LLM': row['count_llm'],
                    'SME1': row['count_sme1'],
                    'SME2': row['count_sme2'],
                    'Other': row['count_other']
                },
                'meta': json.loads(row['meta']) if row['meta'] else {}
            })
        conn.close()
        return jsonify({'files': json_files})
    except Exception as e:
        logging.error(f"List error: {e}")
        return jsonify({'error': str(e)}), 500


def extract_case_identifiers(filename: str):
    normalized = filename
    if normalized.lower().endswith('.json'):
        normalized = normalized[:-5]
    match = re.match(r'^(.+)-(.+)$', normalized)
    if match:
        return match.group(1), match.group(2)
    return "0", "1"


def save_annotations_to_db(project_name: str, project, filename: str, data: dict):
    pages = data.get('pages', []) or []
    annotations = data.get('annotations', []) or []
    meta = data.get('meta', {}) or {}
    case_number, version_number = extract_case_identifiers(filename)

    case_id = upsert_case(case_number, version_number, {
        'narrative': pages[0] if pages else '',
        'pages': json.dumps(pages),
        'meta': json.dumps(meta),
        'annotate_filename': filename
    })

    conn = get_db_connection()
    conn.execute('DELETE FROM annotations WHERE case_id = ?', (case_id,))

    insertion_rows = []
    for ann in annotations:
        context = ann.get('textContext', {})
        start = context.get('start', 0)
        end = context.get('end', 0)
        text = context.get('text', '')
        note = ann.get('note', '')
        user_id = get_user_by_note(note) or 1
        relationships = json.dumps(ann.get('relationships', {}))
        adjudication = ann.get('adjudication')
        insertion_rows.append((
            case_id,
            user_id,
            ann.get('label', 'UNKNOWN'),
            start,
            end,
            text,
            note,
            relationships,
            adjudication
        ))

    if insertion_rows:
        conn.executemany('''
            INSERT INTO annotations (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships, adjudication)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', insertion_rows)

    conn.commit()
    conn.close()
    return jsonify({'message': 'Saved to database', 'case_id': case_id}), 200


@history_blueprint.route('/api/history/<path:file_path>', methods=['GET', 'POST', 'DELETE'])
def history_file(file_path):
    try:
        is_id = False
        if file_path.isdigit():
            is_id = True
            case_id = int(file_path)
        elif '___' in file_path:
            parts = file_path.split('___')
            filename = parts[1]
        else:
            filename = file_path

        if request.method == 'DELETE':
            if is_id:
                doc = get_case(case_id=case_id)
            else:
                doc = get_case(filename=filename)

            if not doc:
                return jsonify({'error': 'Not found'}), 404

            conn = get_db_connection()
            conn.execute('DELETE FROM cases WHERE id = ?', (doc['id'],))
            conn.commit()
            conn.close()
            return jsonify({'message': 'Deleted'})

        if request.method == 'POST':
            data = request.get_json(silent=True) or {}

            if data.get('pages') is not None:
                if is_id:
                    doc = get_case(case_id=case_id)
                    filename = doc['annotate_filename'] if doc else f"case-{case_id}.json"
                return save_annotations_to_db('', None, filename, data)

            if is_id:
                doc = get_case(case_id=case_id)
            else:
                doc = get_case(filename=filename)

            if not doc:
                narrative = data.get('narrative', '')
                if narrative:
                    cid = upsert_case("0", "1", {
                        'narrative': narrative, 
                        'pages': json.dumps([narrative]), 
                        'annotate_filename': filename if not is_id else f"case-{case_id}.json"
                      })
                    doc = get_case(case_id=cid)
                else:
                    return jsonify({'error': 'Not found'}), 404

            return jsonify({
                'pages': json.loads(doc['pages']),
                'annotations': [{
                    'id': a['id'],
                    'label': a['label'],
                    'textContext': {'start': a['start_offset'], 'end': a['end_offset'], 'text': a['text_content']},
                    'note': a['note'],
                    'relationships': json.loads(a['relationships']) if a['relationships'] else {},
                    'adjudication': a['adjudication']
                } for a in get_annotations(doc['id'])],
                'meta': json.loads(doc['meta']) if doc['meta'] else {}
            })

        if request.method == 'GET':
            if is_id:
                doc = get_case(case_id=case_id)
            else:
                doc = get_case(filename=filename)
            
            if not doc:
                return jsonify({'error': 'Not found'}), 404

            return jsonify({
                'pages': json.loads(doc['pages']),
                'annotations': [{
                    'id': a['id'],
                    'label': a['label'],
                    'textContext': {'start': a['start_offset'], 'end': a['end_offset'], 'text': a['text_content']},
                    'note': a['note'],
                    'relationships': json.loads(a['relationships']) if a['relationships'] else {},
                    'adjudication': a['adjudication']
                } for a in get_annotations(doc['id'])],
                'meta': json.loads(doc['meta']) if doc['meta'] else {}
            })

        return jsonify({'error': 'Unsupported method'}), 405
    except Exception as e:
        logging.error(f"History endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

@history_blueprint.route('/api/save', methods=['POST'])
def save_file():
    data = request.get_json()
    fname = data.get('fileName', '').strip()

    try:
        existing = get_case(filename=fname)
        c_num, v_num = (existing['case_number'], existing['version_number']) if existing else ("0", "1")

        case_id = upsert_case(c_num, v_num, {
            'narrative': data.get('pages', [""])[0],
            'pages': json.dumps(data.get('pages', [])),
            'meta': json.dumps(data.get('meta', {})),
            'annotate_filename': fname
        })
        
        conn = get_db_connection()
        conn.execute('DELETE FROM annotations WHERE case_id = ?', (case_id,))
        for ann in data.get('annotations', []):
            uid = get_user_by_note(ann.get('note', 'Admin')) or 1
            conn.execute('''
                INSERT INTO annotations (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships, adjudication)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (case_id, uid, ann['label'], ann['textContext']['start'], ann['textContext']['end'], ann['textContext']['text'], ann['note'], json.dumps(ann.get('relationships', {}))), ann.get('adjudication'))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Saved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@history_blueprint.route('/api/meta', methods=['GET'])
def get_meta_file():
    return jsonify({'error': 'Metadata upload not supported in API mode'}), 404
