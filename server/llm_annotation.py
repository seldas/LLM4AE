"""
LLM-based Named Entity Recognition Annotation
Uses ai_client.py for flexible AI provider selection
"""

import json
import os
import re
from charset_normalizer import from_path
from llm_prompts import prompt_ner_json, prompt_ner_html
from ai_client import AIClient

# Configuration
AI_PROVIDER = os.getenv('AI_PROVIDER', 'vllm')  # Can be 'vllm', 'gemini', or 'elsa'
MAX_INPUT_TOKENS = 80000
DEFAULT_MAX_OUTPUT_TOKENS = 28000

_ALLOWED_LABELS = {
    "SDrug", "CDrug", "ODrug", "Dose", "Treatment", "AE", "mAE", "bSYM", "RO", "Dx", "CoD",
    "Lab", "FHx", "MHx", "IND", "Status", "Age", "Sex", "Date", "Time", "Duration",
    "Relative", "Latency", "Temporal"
}

# Lazy initialization of AI client
_ai_client = None

def get_ai_client():
    """Get or initialize the AI client (lazy initialization)"""
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient(provider=AI_PROVIDER)
    return _ai_client


def _count_tokens(text: str, model_name: str = "") -> int:
    """
    Best-effort token counting.
    - If tiktoken exists, use it.
    - Else fallback to a conservative char-based estimate (~4 chars/token).
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, (len(text) + 3) // 4)


def _split_text_by_token_budget(text: str, token_budget: int) -> list[str]:
    """
    Split text into chunks that *approximately* fit within token_budget.
    Prefer paragraph boundaries; fallback to hard character cuts if needed.
    """
    if _count_tokens(text) <= token_budget:
        return [text]

    separators = ["\n\n", "\n", ". "]
    chunks = [text]

    for sep in separators:
        new_chunks = []
        for ch in chunks:
            if _count_tokens(ch) <= token_budget:
                new_chunks.append(ch)
                continue

            parts = ch.split(sep)
            buf = ""
            for part in parts:
                candidate = part if not buf else (buf + sep + part)
                if _count_tokens(candidate) <= token_budget:
                    buf = candidate
                else:
                    if buf:
                        new_chunks.append(buf)
                    buf = part
                    if _count_tokens(part) > token_budget:
                        approx_chars = token_budget * 4
                        new_chunks.append(part[:approx_chars])
                        remainder = part[approx_chars:]
                        if remainder:
                            buf = remainder
                        else:
                            buf = ""
            if buf:
                new_chunks.append(buf)

        chunks = new_chunks
        if all(_count_tokens(c) <= token_budget for c in chunks):
            break

    final_chunks = []
    for ch in chunks:
        while _count_tokens(ch) > token_budget:
            approx_chars = token_budget * 4
            final_chunks.append(ch[:approx_chars])
            ch = ch[approx_chars:]
        if ch:
            final_chunks.append(ch)

    return final_chunks


def call_llm(message, prompt='Help answer the following requests.', max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
    """
    Call LLM using the configured AI provider.
    """
    if not message:
        return 'No input!'
    
    ai_client = get_ai_client()
    return ai_client.call(
        message=message,
        system_prompt=prompt,
        temperature=0.0,
        max_tokens=max_output_tokens
    )


def _extract_json_object(s: str) -> dict | None:
    """
    Robustly extract the first JSON object from model output.
    Handles accidental leading/trailing text.
    """
    s = (s or "").strip()
    try:
        return json.loads(s)
    except Exception:
        pass

    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _dedupe_and_resolve_overlaps(spans: list[dict]) -> list[dict]:
    """
    Enforce:
    - stable sort by (start, longer first)
    - drop duplicates
    - drop overlaps (keep earliest non-overlapping after sort)
    """
    spans = sorted(spans, key=lambda x: (x["start"], -(x["end"] - x["start"]), x["label"]))
    out = []
    last_end = -1
    seen = set()
    for sp in spans:
        key = (sp["label"], sp["start"], sp["end"], sp["text"])
        if key in seen:
            continue
        seen.add(key)
        if sp["start"] < last_end:
            continue
        out.append(sp)
        last_end = sp["end"]
    return out


def mode_AE_annotation(query: str, prompt_ner: str = prompt_ner_json):
    """
    Preferred path: prompt returns JSON with:
    {"annotated_text": "...", "spans":[{"label","start","end","text"}, ...]}
    Offsets must reference ORIGINAL query.
    Returns: (annotated_text, validated_spans)
    """
    raw = call_llm(query, prompt_ner)
    obj = _extract_json_object(raw)

    if not obj or "annotated_text" not in obj or "spans" not in obj:
        # Backward-compatible fallback: attempt to strip legacy header and return no spans
        cleaned = re.sub(r'^The annotated text is shown as below:\s*', '', (raw or "").strip(), flags=re.IGNORECASE)
        return cleaned, []

    annotated_text = obj.get("annotated_text", "") or ""
    spans_in = obj.get("spans", []) or []

    validated = []
    for sp in spans_in:
        try:
            label = sp["label"]
            start = int(sp["start"])
            end = int(sp["end"])
            text = sp["text"]
        except Exception:
            continue

        if label not in _ALLOWED_LABELS:
            continue
        if start < 0 or end <= start or end > len(query):
            continue

        substr = query[start:end]
        if substr != text:
            continue

        validated.append({"label": label, "start": start, "end": end, "text": text})

    validated = _dedupe_and_resolve_overlaps(validated)
    return annotated_text, validated


def run_llm_annotation(file_path):
    """
    Main annotation pipeline.
    """
    data = load_json_with_charset_normalizer(file_path)

    try:
        data['pages'] = [x.encode("latin1").decode("utf-8") for x in data['pages']]
    except Exception:
        pass

    narrative = data['pages'][0]

    # Split into chunks up to ~80k tokens each (best effort)
    chunks = _split_text_by_token_budget(narrative, MAX_INPUT_TOKENS)

    # Keep only non-LLM annotations
    raw_annotations = [
        ann for ann in data.get('annotations', [])
        if 'LLM' not in (ann.get('note') or '').upper()
    ]
    for ann in raw_annotations:
        if not ann.get('note'):
            ann['note'] = 'SME1'

    llm_annotations_all = []
    current_offset = 0

    for chunk in chunks:
        _, spans = mode_AE_annotation(chunk)

        for sp in spans:
            llm_annotations_all.append({
                "label": sp["label"],
                "note": "LLM",
                "textContext": {
                    "text": sp["text"],
                    "start": sp["start"] + current_offset,
                    "end": sp["end"] + current_offset,
                },
                "relationships": {
                    "date": {"page": 0, "text": ""},
                    "frequency": {"page": 0, "text": ""},
                    "relatives": {"page": 0, "text": ""},
                    "span": {"page": 0, "text": ""},
                    "time": {"page": 0, "text": ""}
                }
            })

        current_offset += len(chunk)

    merged_data = {
        "pages": [narrative],
        "annotations": raw_annotations + llm_annotations_all,
        "meta": data.get("meta", {}).copy()
    }
    merged_data["meta"]["llm_processed"] = "Done"
    merged_data["meta"]["llm_provider"] = AI_PROVIDER
    merged_data["meta"]["llm_input_token_budget"] = MAX_INPUT_TOKENS
    merged_data["meta"]["llm_chunks"] = len(chunks)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)

    return True, f"LLM annotation saved to: {file_path}"


def load_json_with_charset_normalizer(file_path):
    """
    Load a JSON file using charset-normalizer to auto-detect encoding.
    Returns parsed JSON content.
    """
    result = from_path(file_path)
    decoded = result.best()

    if decoded is None:
        raise ValueError(f"Unable to detect encoding for file: {file_path}")

    return json.loads(str(decoded))
