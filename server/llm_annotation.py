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
    "SDRUG", "CDRUG", "ODRUG", "DOSE", "TREATMENT", "AE", "MAE", "BSYM", "RO", "DX", "COD",
    "LAB", "FHX", "MHx", "IND", "STATUS", "AGE", "SEX", "DATE", "TIME", "DURATION",
    "RELATIVE", "LATENCY", "TEMPORAL"
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
    import logging
    logging.info(f"Calling AI Provider: {AI_PROVIDER}")
    return ai_client.call(message=message, system_prompt=prompt, temperature=0.0, max_tokens=max_output_tokens)

def _extract_json_object(s: str) -> dict | None:
    s = (s or "").strip()
    import logging
    try: 
        obj = json.loads(s)
        logging.info("Successfully parsed LLM JSON response")
        return obj
    except: pass
    
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m: 
        logging.warning(f"Could not find JSON object in LLM response: {s[:200]}...")
        return None
    try: 
        obj = json.loads(m.group(0))
        logging.info("Extracted JSON from LLM response via regex")
        return obj
    except: 
        logging.error(f"Failed to parse extracted JSON block: {m.group(0)[:200]}...")
        return None

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
    import logging
    raw = call_llm(query, prompt_ner)
    obj = _extract_json_object(raw)
    if not obj or "spans" not in obj: 
        logging.warning("LLM response missing 'spans' key")
        return "", []
    
    validated = []
    for sp in obj.get("spans", []):
        try:
            label = str(sp.get("label", "")).upper()
            start = int(sp.get("start", -1))
            end = int(sp.get("end", -1))
            text = sp.get("text", "")
            
            if label in _ALLOWED_LABELS and 0 <= start < end <= len(query):
                # Extra validation: does text match narrative at those offsets?
                actual_text = query[start:end]
                if actual_text.lower() == text.lower():
                    validated.append({"label": label, "start": start, "end": end, "text": actual_text})
                else:
                    logging.debug(f"Span text mismatch: expected '{text}', found '{actual_text}'")
        except Exception as e: 
            logging.debug(f"Error validating span: {e}")
            continue
    logging.info(f"Validated {len(validated)} spans from LLM")
    return obj.get("annotated_text", ""), _dedupe_and_resolve_overlaps(validated)

def run_llm_annotation(doc_id):
    """
    Main annotation pipeline.
    """
    import logging
    logging.info(f"Starting LLM Annotation for doc_id={doc_id}")
    
    conn = get_db_connection()
    doc = conn.execute('SELECT pages, meta FROM cases WHERE id = ?', (doc_id,)).fetchone()
    if not doc: 
        conn.close()
        return False, "Doc not found"
        
    pages = json.loads(doc['pages'])
    meta = json.loads(doc['meta']) if doc['meta'] else {}
    narrative = pages[0]
    
    # Determine AI user
    ai_user_id = get_user_by_note('LLM') or get_user_by_note('Llama4') or 6
    ai_note = "Llama4"
    conn.close()

    chunks = _split_text_by_token_budget(narrative, MAX_INPUT_TOKENS)
    llm_annotations = []
    current_offset = 0

    for chunk in chunks:
        _, spans = mode_AE_annotation(chunk)
        for sp in spans:
            llm_annotations.append({
                "label": sp["label"],
                "user_id": ai_user_id,
                "note": ai_note,
                "start": sp["start"] + current_offset,
                "end": sp["end"] + current_offset,
                "text": sp["text"]
            })
        current_offset += len(chunk)
    
    if doc_id:
        conn = get_db_connection()
        # Save annotations to DB
        logging.info(f"Saving {len(llm_annotations)} annotations to database")
        for ann in llm_annotations:
            conn.execute('''
                INSERT INTO annotations (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships, adjudication)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (doc_id, ann['user_id'], ann['label'], ann['start'], ann['end'], ann['text'], ann['note'], '{}', None))
        
        meta["llm_processed"] = "Done"
        meta["llm_provider"] = AI_PROVIDER
        conn.execute('UPDATE cases SET meta = ?, llm_status = "Done" WHERE id = ?', (json.dumps(meta), doc_id))
        conn.commit()
        conn.close()
        logging.info(f"LLM Annotation task finished for doc_id={doc_id}")
