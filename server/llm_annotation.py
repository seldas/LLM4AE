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
    # Simple split for now
    approx_chars = token_budget * 4
    return [text[i:i+approx_chars] for i in range(0, len(text), approx_chars)]

def call_llm(message, provider='vllm', prompt='Help answer the following requests.', max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
    logging.info(f"Calling AI Provider: {provider}")
    ai_client = AIClient(provider=provider)
    return ai_client.call(message=message, system_prompt=prompt, temperature=0.0, max_tokens=max_output_tokens)

def _extract_field_via_regex(s: str, field_name: str) -> str | None:
    """
    Attempt to extract a specific field value from a string that looks like JSON,
    even if the JSON itself is malformed.
    """
    pattern = rf'"{field_name}"\s*:\s*"(.*?)(?<!\\)"'
    match = re.search(pattern, s, re.DOTALL)
    if match:
        val = match.group(1)
        # Unescape common JSON escapes
        val = val.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
        return val
    return None

def _extract_json_object(s: str) -> dict | None:
    s = (s or "").strip()
    
    # 1. Try direct parse with strict=False (allows literal newlines in strings)
    try: 
        return json.loads(s, strict=False)
    except: pass
    
    # 2. Try extracting from markdown blocks
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", s, flags=re.DOTALL)
    if m:
        block = m.group(1)
        try:
            return json.loads(block, strict=False)
        except: pass

    # 3. Try finding the first { and last }
    m = re.search(r"(\{.*\})", s, flags=re.DOTALL)
    if m:
        block = m.group(1)
        try:
            return json.loads(block, strict=False)
        except:
            # Try to fix common trailing comma issue before closing brace
            try:
                fixed = re.sub(r",\s*([\]\}])", r"\1", block)
                return json.loads(fixed, strict=False)
            except: pass
            
    logging.error(f"Failed to extract valid JSON from LLM response (first 500 chars): {s[:500]}...")
    return None

def _dedupe_and_resolve_overlaps(spans: list[dict]) -> list[dict]:
    # Sort by start (asc) then length (desc)
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
    Backup method: If 'spans' key is missing but LLM provided 'annotated_text',
    we can reconstruct the spans by parsing the XML tags and mapping them back to original text.
    """
    if not tagged_text or not original_text:
        return []

    spans = []
    # Match <TAG>content</TAG>
    pattern = re.compile(r"<([A-Za-z]+)>(.*?)</\1>", flags=re.DOTALL)
    
    current_pos_in_original = 0
    matches = list(pattern.finditer(tagged_text))
    
    for match in matches:
        label = match.group(1).upper()
        content = match.group(2)
        
        # Find the content in the original text, starting from where we left off
        start_idx = original_text.find(content, current_pos_in_original)
        
        if start_idx == -1:
            # Try searching near the previous position if find fails
            start_idx = original_text.find(content, max(0, current_pos_in_original - 50))

        if start_idx != -1:
            end_idx = start_idx + len(content)
            if label in _ALLOWED_LABELS:
                spans.append({
                    "label": label,
                    "start": start_idx,
                    "end": end_idx,
                    "text": content
                })
            current_pos_in_original = end_idx
            
    return spans

def mode_AE_annotation_json_strategy(query: str, provider='vllm'):
    """
    Alternative strategy: LLM returns only a list of entities.
    We then match ALL occurrences of these entities in the text.
    """
    raw = call_llm(query, provider, prompt_ner_simple_json)
    logging.info(f"DEBUG: Full LLM Response (JSON Strategy) from {provider}:\n{raw}")
    
    obj = _extract_json_object(raw)
    if not obj or "entities" not in obj:
        logging.error("Failed to extract 'entities' from LLM response in JSON strategy")
        return "", []
    
    entities = obj.get("entities", [])
    spans = []
    
    for ent in entities:
        label = str(ent.get("label", "")).upper()
        text = str(ent.get("text", ""))
        
        if not text or label not in _ALLOWED_LABELS:
            continue
            
        # Find ALL occurrences of this text in the query narrative
        # We use regex with word boundaries for better accuracy
        try:
            # Escape text for regex
            pattern = re.compile(re.escape(text), flags=re.IGNORECASE)
            for match in pattern.finditer(query):
                spans.append({
                    "label": label,
                    "start": match.start(),
                    "end": match.end(),
                    "text": query[match.start():match.end()]
                })
        except Exception as e:
            logging.debug(f"Error matching entity '{text}': {e}")
            
    # Deduplicate and resolve overlaps (e.g. "blood" and "blood test")
    return "", _dedupe_and_resolve_overlaps(spans)


def mode_AE_annotation(query: str, provider='vllm', prompt_ner: str = prompt_ner_json):
    strategy = os.getenv("LLM_STRATEGY", "span").lower()
    
    if strategy == "json":
        return mode_AE_annotation_json_strategy(query, provider)
    
    # Default 'span' strategy
    raw = call_llm(query, provider, prompt_ner)
    logging.info(f"DEBUG: Full LLM Response from {provider}:\n{raw}")
    
    obj = _extract_json_object(raw)
    
    annotated_text = ""
    spans = []
    
    if obj:
        annotated_text = obj.get("annotated_text", "")
        spans = obj.get("spans", [])
    else:
        logging.warning("JSON parsing failed, attempting regex extraction of 'annotated_text'")
        patterns = [
            r'"annotated_text"\s*:\s*"(.*?)(?<!\\)"',
            r'"annotated_text"\s*:\s*\'(.*?)(?<!\\)\'',
            r'annotated_text\s*:\s*"(.*?)(?<!\\)"'
        ]
        for p in patterns:
            match = re.search(p, raw, re.DOTALL)
            if match:
                annotated_text = match.group(1)
                annotated_text = annotated_text.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
                logging.info(f"Successfully recovered annotated_text via regex")
                break
    
    if annotated_text and (not spans):
        logging.info("Recovering spans from annotated_text via tag parsing")
        spans = _extract_spans_from_tagged_text(annotated_text, query)
    
    if not annotated_text and not spans:
        if "<" in raw and "</" in raw:
            logging.info("Attempting direct tag parsing from raw response")
            spans = _extract_spans_from_tagged_text(raw, query)
            if spans: annotated_text = raw
        
        if not spans: return "", []

    validated = []
    for sp in spans:
        try:
            label = str(sp.get("label", "")).upper()
            start = int(sp.get("start", -1))
            end = int(sp.get("end", -1))
            text = sp.get("text", "")
            
            if label in _ALLOWED_LABELS and 0 <= start < end <= len(query):
                actual_text = query[start:end]
                if actual_text.lower() == text.lower():
                    validated.append({"label": label, "start": start, "end": end, "text": actual_text})
                else:
                    found_idx = query.find(text, max(0, start-100))
                    if found_idx == -1: found_idx = query.find(text)
                    if found_idx != -1:
                        validated.append({"label": label, "start": found_idx, "end": found_idx + len(text), "text": text})
        except: continue
            
    return annotated_text, _dedupe_and_resolve_overlaps(validated)

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
