"""
LLM-based Named Entity Recognition Annotation
Uses ai_client.py for flexible AI provider selection
"""

import json
import os
import re
from llm_prompts import prompt_ner_json, prompt_ner_html
from ai_client import AIClient
from database_manager import get_db_connection, get_annotations, get_user_by_note

# Configuration
AI_PROVIDER = os.getenv('AI_PROVIDER', 'vllm') 
MAX_INPUT_TOKENS = 80000
DEFAULT_MAX_OUTPUT_TOKENS = 28000

_ALLOWED_LABELS = {
    "SDrug", "CDrug", "ODrug", "Dose", "Treatment", "AE", "mAE", "bSYM", "RO", "Dx", "CoD",
    "Lab", "FHx", "MHx", "IND", "Status", "Age", "Sex", "Date", "Time", "Duration",
    "Relative", "Latency", "Temporal"
}

_ai_client = None

def get_ai_client():
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient(provider=AI_PROVIDER)
    return _ai_client

def _count_tokens(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, (len(text) + 3) // 4)

def _split_text_by_token_budget(text: str, token_budget: int) -> list[str]:
    if _count_tokens(text) <= token_budget:
        return [text]
    # Simple split for now
    approx_chars = token_budget * 4
    return [text[i:i+approx_chars] for i in range(0, len(text), approx_chars)]

def call_llm(message, prompt='Help answer the following requests.', max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
    ai_client = get_ai_client()
    return ai_client.call(message=message, system_prompt=prompt, temperature=0.0, max_tokens=max_output_tokens)

def _extract_json_object(s: str) -> dict | None:
    s = (s or "").strip()
    try: return json.loads(s)
    except: pass
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m: return None
    try: return json.loads(m.group(0))
    except: return None

def _dedupe_and_resolve_overlaps(spans: list[dict]) -> list[dict]:
    spans = sorted(spans, key=lambda x: (x["start"], -(x["end"] - x["start"])))
    out = []
    last_end = -1
    for sp in spans:
        if sp["start"] < last_end: continue
        out.append(sp)
        last_end = sp["end"]
    return out

def mode_AE_annotation(query: str, prompt_ner: str = prompt_ner_json):
    raw = call_llm(query, prompt_ner)
    obj = _extract_json_object(raw)
    if not obj or "spans" not in obj: return "", []
    
    validated = []
    for sp in obj.get("spans", []):
        try:
            label, start, end, text = sp["label"], int(sp["start"]), int(sp["end"]), sp["text"]
            if label in _ALLOWED_LABELS and 0 <= start < end <= len(query) and query[start:end] == text:
                validated.append({"label": label, "start": start, "end": end, "text": text})
        except: continue
    return obj.get("annotated_text", ""), _dedupe_and_resolve_overlaps(validated)

def run_llm_annotation(file_path=None, doc_id=None):
    """
    Main annotation pipeline. Supports both legacy file path and new doc_id.
    """
    if doc_id:
        conn = get_db_connection()
        doc = conn.execute('SELECT pages, meta FROM cases WHERE id = ?', (doc_id,)).fetchone()
        if not doc: return False, "Doc not found"
        pages = json.loads(doc['pages'])
        meta = json.loads(doc['meta']) if doc['meta'] else {}
        narrative = pages[0]
        
        # Determine AI user (Llama4)
        ai_user_id = get_user_by_note('Llama4') or 6 # Fallback
    else:
        # Legacy file path logic (if still needed)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        narrative = data['pages'][0]
        meta = data.get('meta', {})

    chunks = _split_text_by_token_budget(narrative, MAX_INPUT_TOKENS)
    llm_annotations = []
    current_offset = 0

    for chunk in chunks:
        _, spans = mode_AE_annotation(chunk)
        for sp in spans:
            llm_annotations.append({
                "label": sp["label"],
                "user_id": ai_user_id if doc_id else None,
                "note": "Llama4",
                "start": sp["start"] + current_offset,
                "end": sp["end"] + current_offset,
                "text": sp["text"]
            })
        current_offset += len(chunk)

    if doc_id:
        conn = get_db_connection()
        # Save annotations to DB
        for ann in llm_annotations:
            conn.execute('''
                INSERT INTO annotations (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships, adjudication)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (doc_id, ann['user_id'], ann['label'], ann['start'], ann['end'], ann['text'], ann['note'], '{}', None))
        
        meta["llm_processed"] = "Done"
        meta["llm_provider"] = AI_PROVIDER
        conn.execute('UPDATE cases SET meta = ? WHERE id = ?', (json.dumps(meta), doc_id))
        conn.commit()
        conn.close()
    else:
        # Update file logic... (omitted for brevity as we are moving to DB)
        pass

    return True, "Annotation complete"
