"""
LLM-based Named Entity Recognition Annotation
Uses ai_client.py for flexible AI provider selection
"""

import json
import os
import re
import logging
from llm_prompts import prompt_ner_json, prompt_ner_html, prompt_ner_simple_json
from ai_client import AIClient
from database_manager import get_db_connection, get_annotations, get_user_by_note

# Configuration
MAX_INPUT_TOKENS = 80000
DEFAULT_MAX_OUTPUT_TOKENS = 28000

_ALLOWED_LABELS = {
    "SDRUG", "CDRUG", "ODRUG", "DOSE", "TREATMENT", "AE", "MAE", "BSYM", "RO", "DX", "COD",
    "LAB", "FHX", "MHX", "IND", "STATUS", "AGE", "SEX", "DATE", "TIME", "DURATION",
    "RELATIVE", "LATENCY", "TEMPORAL"
}

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
    approx_chars = token_budget * 4
    return [text[i:i+approx_chars] for i in range(0, len(text), approx_chars)]

def call_llm(message, provider='vllm', prompt='Help answer the following requests.', max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
    logging.info(f"Calling AI Provider: {provider}")
    ai_client = AIClient(provider=provider)
    return ai_client.call(message=message, system_prompt=prompt, temperature=0.0, max_tokens=max_output_tokens)

def _repair_truncated_json(s: str) -> str:
    s = s.strip()
    last_brace = s.rfind('}')
    last_bracket = s.rfind(']')
    if last_brace == -1 and last_bracket == -1: return s
    cut_point = max(last_brace, last_bracket) + 1
    repaired = s[:cut_point]
    open_braces = repaired.count('{') - repaired.count('}')
    open_brackets = repaired.count('[') - repaired.count(']')
    repaired += '}' * open_braces
    repaired += ']' * open_brackets
    return repaired

def _extract_json_object(s: str) -> dict | None:
    s = (s or "").strip()
    try: return json.loads(s, strict=False)
    except: pass
    
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", s, flags=re.DOTALL)
    if m:
        block = m.group(1)
        try: return json.loads(block, strict=False)
        except:
            repaired = _repair_truncated_json(block)
            try: return json.loads(repaired, strict=False)
            except: pass

    # Regex search for first {
    first_brace = s.find('{')
    if first_brace != -1:
        block = s[first_brace:]
        try: return json.loads(block, strict=False)
        except:
            repaired = _repair_truncated_json(block)
            try: return json.loads(repaired, strict=False)
            except: pass
    return None

def _extract_field_via_regex(s: str, field_name: str) -> str | None:
    pattern = rf'"{field_name}"\s*:\s*"(.*?)(?<!\\)"'
    match = re.search(pattern, s, re.DOTALL)
    if match:
        val = match.group(1)
        return val.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
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

def _extract_spans_from_tagged_text(tagged_text: str, original_text: str) -> list[dict]:
    """
    Priority 1: Mapping tagged text to original narrative.
    """
    if not tagged_text or not original_text: return []
    spans = []
    pattern = re.compile(r"<([A-Za-z]+)>(.*?)</\1>", flags=re.DOTALL)
    current_pos = 0
    for match in pattern.finditer(tagged_text):
        label = match.group(1).upper()
        content = match.group(2)
        if label not in _ALLOWED_LABELS: continue
        
        # Sequential search in original to maintain instance mapping
        start_idx = original_text.find(content, current_pos)
        if start_idx == -1:
            start_idx = original_text.find(content, max(0, current_pos - 100)) # Fuzzy lookback
        
        if start_idx != -1:
            end_idx = start_idx + len(content)
            spans.append({"label": label, "start": start_idx, "end": end_idx, "text": content})
            current_pos = end_idx
    return spans

def _get_all_occurrences(text: str, original_text: str, label: str) -> list[dict]:
    """
    Priority 3: Global match for missing offsets.
    """
    if not text: return []
    matches = []
    try:
        pattern = re.compile(re.escape(text), flags=re.IGNORECASE)
        for m in pattern.finditer(original_text):
            matches.append({
                "label": label,
                "start": m.start(),
                "end": m.end(),
                "text": original_text[m.start():m.end()]
            })
    except: pass
    return matches

def mode_AE_annotation(query: str, provider='vllm', prompt_ner: str = prompt_ner_json):
    strategy = os.getenv("LLM_STRATEGY", "span").lower()
    raw = call_llm(query, provider, prompt_ner_simple_json if strategy == "json" else prompt_ner)
    logging.info(f"DEBUG: Full LLM Response from {provider}:\n{raw}")
    
    obj = _extract_json_object(raw)
    
    annotated_text = ""
    spans_from_json = []
    
    if obj:
        annotated_text = obj.get("annotated_text", "")
        spans_from_json = obj.get("spans") or obj.get("entities") or []
    else:
        # If JSON failed, try regex for annotated_text as it's the highest accuracy source
        annotated_text = _extract_field_via_regex(raw, "annotated_text")

    final_spans = []

    # 1. Try TAGGED TEXT mapping (Highest Priority)
    if annotated_text:
        logging.info("Step 1: Attempting tag-based extraction from annotated_text")
        final_spans = _extract_spans_from_tagged_text(annotated_text, query)

    # 2. Try STRUCTURED SPANS (Fallback)
    if not final_spans and spans_from_json:
        logging.info("Step 2: Attempting fallback to structured spans/entities list")
        for entry in spans_from_json:
            label = str(entry.get("label", "")).upper()
            text = str(entry.get("text", ""))
            start = entry.get("start")
            end = entry.get("end")
            
            if not text or label not in _ALLOWED_LABELS: continue
            
            # If start/end provided, validate them
            if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(query):
                if query[start:end].lower() == text.lower():
                    final_spans.append({"label": label, "start": start, "end": end, "text": query[start:end]})
                    continue
            
            # If offsets missing or invalid, search globally (Priority 3)
            final_spans.extend(_get_all_occurrences(text, query, label))

    # 3. Final Ditch: Raw response parsing if nothing else worked
    if not final_spans and "<" in raw and "</" in raw:
        logging.info("Step 3: Attempting direct tag parsing from raw string")
        final_spans = _extract_spans_from_tagged_text(raw, query)

    logging.info(f"Extraction complete. Total unique spans found: {len(final_spans)}")
    return annotated_text, _dedupe_and_resolve_overlaps(final_spans)

def run_llm_annotation(doc_id, provider='vllm'):
    """
    Main annotation pipeline.
    """
    logging.info(f"Starting LLM Annotation for doc_id={doc_id} using provider={provider}")
    conn = get_db_connection()
    doc = conn.execute('SELECT id, pages, meta FROM cases WHERE id = ?', (doc_id,)).fetchone()
    if not doc: 
        conn.close()
        return False, "Doc not found"
    pages = json.loads(doc['pages'])
    meta = json.loads(doc['meta']) if doc['meta'] else {}
    narrative = pages[0]
    ai_user_id = get_user_by_note('LLM') or get_user_by_note('Llama4') or 6
    ai_note = f"LLM ({provider})"
    conn.close()

    chunks = _split_text_by_token_budget(narrative, MAX_INPUT_TOKENS)
    llm_annotations = []
    current_offset = 0

    for chunk in chunks:
        _, spans = mode_AE_annotation(chunk, provider=provider)
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
        logging.info(f"Saving {len(llm_annotations)} annotations to database for doc_id={doc_id}")
        conn.execute('DELETE FROM annotations WHERE case_id = ? AND user_id = ?', (doc_id, ai_user_id))
        for ann in llm_annotations:
            conn.execute('''
                INSERT INTO annotations (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships, adjudication)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (doc_id, ann['user_id'], ann['label'], ann['start'], ann['end'], ann['text'], ann['note'], '{}', None))
        
        meta["llm_processed"] = "Done"
        meta["llm_provider"] = provider
        meta["llm_strategy"] = os.getenv("LLM_STRATEGY", "span")
        conn.execute('UPDATE cases SET meta = ?, llm_status = "Done" WHERE id = ?', (json.dumps(meta), doc_id))
        conn.commit()
        conn.close()
        logging.info(f"LLM Annotation task finished for doc_id={doc_id}")
