"""
LLM-based Named Entity Recognition Annotation for LLM4AE
Synchronized with publication/scripts/ (run_FAERS_llama4.py, annotation_prompts.py)

Supports:
- Tagged XML extraction (P2_TAG / P2_TAG_VAERS) with fuzzy SequenceMatcher boundary alignment
- Structured JSON extraction (P1_JSON / P1_JSON_VAERS)
- Multi-provider AIClient (Anthropic Claude, OpenAI / vLLM / Ollama, Google Gemini, FDA Elsa)
- FAERS (17 categories) and VAERS (14 categories) schemas
- Database persistence and case metadata tracking
"""

import json
import logging
import os
import re
import time
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Sequence, Tuple

from ai_client import AIClient
from database_manager import get_db_connection, get_user_by_note
from llm_prompts import (
    ANNOTATION_GUIDE,
    ANNOTATION_GUIDE_VAERS,
    FAERS_TAGS,
    P1_JSON,
    P1_JSON_VAERS,
    P2_TAG,
    P2_TAG_VAERS,
    RAW_TO_LABEL,
    TAG_TO_LABEL,
    VAERS_TAGS,
    prompt_ner_html,
    prompt_ner_json,
)

logger = logging.getLogger(__name__)

# Configuration
AI_PROVIDER = os.getenv('AI_PROVIDER', 'vllm')
MAX_INPUT_TOKENS = 80000
DEFAULT_MAX_OUTPUT_TOKENS = 28000

# Regular expressions for tag parsing and sanitization
_ALLOWED_TAG_NAMES = "|".join(sorted(TAG_TO_LABEL.keys(), key=len, reverse=True))
_TAG_RE = re.compile(
    rf"<\s*(?P<close>/?)\s*(?P<tag>{_ALLOWED_TAG_NAMES})\s*>",
    flags=re.IGNORECASE,
)

_FENCE_START_RE = re.compile(r"^\s*```(?:xml|html|text|json)?\s*\n?", re.IGNORECASE)
_FENCE_END_RE = re.compile(r"\n?\s*```\s*$")
_KNOWN_PREAMBLE_RE = re.compile(
    r"^\s*The annotated text is shown as below:\s*(?:\r?\n)?",
    flags=re.IGNORECASE,
)

_RAW_TO_LABEL_CASEFOLD = {k.casefold(): v for k, v in RAW_TO_LABEL.items()}


def normalize_label(raw: str) -> Optional[str]:
    """Map any raw category name or tag into canonical schema label."""
    if not raw:
        return None
    raw_str = str(raw).strip()
    # Check exact match first
    if raw_str in RAW_TO_LABEL:
        return RAW_TO_LABEL[raw_str]
    if raw_str.upper() in TAG_TO_LABEL:
        return TAG_TO_LABEL[raw_str.upper()]
    return _RAW_TO_LABEL_CASEFOLD.get(raw_str.casefold(), raw_str)


def sanitize_model_output(output: str) -> str:
    """Remove common LLM wrappers (markdown code fences, introductory preambles)."""
    text = (output or "").replace("\ufeff", "").strip()
    text = _FENCE_START_RE.sub("", text, count=1)
    text = _FENCE_END_RE.sub("", text, count=1)
    text = _KNOWN_PREAMBLE_RE.sub("", text, count=1)
    return text.strip()


def parse_tagged_output(tagged_text: str) -> Tuple[str, List[dict], List[str]]:
    """
    Remove allowed XML tags and return spans in tag-stripped-output coordinates.
    Tolerates tag casing/spacing variations and gracefully handles unclosed/nested tags.
    """
    clean_parts: List[str] = []
    clean_len = 0
    spans: List[dict] = []
    warnings: List[str] = []
    stack: List[Tuple[str, str, int]] = []  # (tag_name, canonical_label, clean_start)

    cursor = 0
    for match in _TAG_RE.finditer(tagged_text):
        segment = tagged_text[cursor:match.start()]
        clean_parts.append(segment)
        clean_len += len(segment)

        tag_name = match.group("tag").upper()
        label = TAG_TO_LABEL.get(tag_name, tag_name)
        is_close = bool(match.group("close"))

        if not is_close:
            if stack:
                warnings.append(f"nested tag <{tag_name}> inside <{stack[-1][0]}>")
            stack.append((tag_name, label, clean_len))
        else:
            if not stack:
                warnings.append(f"closing tag </{tag_name}> without opening tag")
            else:
                matching_idx = None
                for idx in range(len(stack) - 1, -1, -1):
                    if stack[idx][0] == tag_name:
                        matching_idx = idx
                        break
                if matching_idx is None:
                    warnings.append(f"closing tag </{tag_name}> has no matching opener")
                else:
                    if matching_idx != len(stack) - 1:
                        warnings.append(f"misnested closing tag </{tag_name}>")
                    open_tag, open_label, start = stack.pop(matching_idx)
                    if clean_len > start:
                        spans.append({
                            "tag": open_tag,
                            "label": open_label,
                            "clean_start": start,
                            "clean_end": clean_len,
                        })
                    else:
                        warnings.append(f"empty tag <{tag_name}></{tag_name}>")

        cursor = match.end()

    tail = tagged_text[cursor:]
    clean_parts.append(tail)
    clean_len += len(tail)

    if stack:
        warnings.extend(f"unclosed tag <{tag}>" for tag, _, _ in stack)

    clean_text = "".join(clean_parts)
    spans.sort(key=lambda row: (row["clean_start"], row["clean_end"], row["label"]))
    return clean_text, spans, warnings


def build_boundary_map(clean_text: str, original_text: str) -> Tuple[List[int], float, List[Tuple[str, int, int, int, int]]]:
    """
    Map every character boundary in clean_text to a boundary in original_text using SequenceMatcher.
    """
    matcher = SequenceMatcher(None, clean_text, original_text, autojunk=False)
    opcodes = matcher.get_opcodes()
    boundary: List[Optional[int]] = [None] * (len(clean_text) + 1)

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for k in range(i2 - i1 + 1):
                boundary[i1 + k] = j1 + k
        elif tag == "insert":
            boundary[i1] = j2
        elif tag == "delete":
            n = i2 - i1
            for k in range(n + 1):
                boundary[i1 + k] = j1
        else:  # replace
            n = i2 - i1
            m = j2 - j1
            if n == 0:
                boundary[i1] = j2
            else:
                for k in range(n + 1):
                    boundary[i1 + k] = j1 + round(m * k / n)

    last = 0
    for idx in range(len(boundary)):
        if boundary[idx] is None:
            boundary[idx] = last
        last = max(last, int(boundary[idx]))
        boundary[idx] = min(last, len(original_text))

    for idx in range(len(boundary) - 2, -1, -1):
        boundary[idx] = min(int(boundary[idx]), int(boundary[idx + 1]))

    return [int(x) for x in boundary], matcher.ratio(), opcodes


def _nearest_exact_occurrence(needle: str, haystack: str, expected_start: int, window: int = 800) -> Optional[int]:
    if not needle:
        return None
    lo = max(0, expected_start - window)
    hi = min(len(haystack), expected_start + window + len(needle))
    local = haystack[lo:hi]
    starts = []
    pos = local.find(needle)
    while pos >= 0:
        starts.append(lo + pos)
        pos = local.find(needle, pos + 1)
    if not starts:
        return None
    return min(starts, key=lambda value: abs(value - expected_start))


def clean_span(start: int, end: int, text: str) -> Tuple[int, int]:
    """Strip leading/trailing whitespace from entity boundary offsets."""
    start = max(0, min(int(start), len(text)))
    end = max(0, min(int(end), len(text)))
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def map_predicted_spans_to_original(
    clean_text: str,
    spans: Sequence[dict],
    original_text: str,
) -> Tuple[List[dict], dict]:
    """Map tag spans from LLM output coordinates back to original narrative offsets."""
    boundary, ratio, _ = build_boundary_map(clean_text, original_text)
    mapped: List[dict] = []
    dropped = 0
    exact_refined = 0

    for span in spans:
        c0 = int(span["clean_start"])
        c1 = int(span["clean_end"])
        label = normalize_label(str(span["label"])) or str(span["label"])
        pred_surface = clean_text[c0:c1]

        o0 = boundary[max(0, min(c0, len(clean_text)))]
        o1 = boundary[max(0, min(c1, len(clean_text)))]
        if o1 < o0:
            o0, o1 = o1, o0

        found = _nearest_exact_occurrence(pred_surface, original_text, o0)
        if found is not None:
            o0 = found
            o1 = found + len(pred_surface)
            exact_refined += 1

        o0, o1 = clean_span(o0, o1, original_text)
        if o0 >= o1:
            dropped += 1
            continue

        mapped_text = original_text[o0:o1]
        mapped.append({
            "label": label,
            "start": o0,
            "end": o1,
            "text": mapped_text,
        })

    meta = {
        "alignment_ratio": ratio,
        "n_spans": len(spans),
        "n_mapped": len(mapped),
        "n_dropped": dropped,
        "n_exact_refined": exact_refined,
    }
    return mapped, meta


def _dedupe_and_resolve_overlaps(spans: List[dict]) -> List[dict]:
    """Sort spans and remove exact duplicates and strict overlaps (favor longer spans)."""
    # Sort primarily by start offset, then longest length first
    sorted_spans = sorted(spans, key=lambda x: (x["start"], -(x["end"] - x["start"])))
    out: List[dict] = []
    seen = set()
    last_end = -1

    for sp in sorted_spans:
        key = (sp["start"], sp["end"], sp["label"])
        if key in seen:
            continue
        if sp["start"] < last_end:
            # Overlapping span; skip to enforce non-overlapping invariant
            continue
        seen.add(key)
        out.append(sp)
        last_end = sp["end"]

    return out


def _extract_json_spans(raw_output: str, original_text: str) -> List[dict]:
    """Parse JSON format model output and validate offsets against original text."""
    raw = sanitize_model_output(raw_output)
    obj = None
    try:
        obj = json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(0))
            except Exception:
                pass

    if not obj or not isinstance(obj, dict):
        return []

    spans: List[dict] = []
    
    # Handle top-level "spans" list
    if "spans" in obj and isinstance(obj["spans"], list):
        for item in obj["spans"]:
            if not isinstance(item, dict):
                continue
            raw_label = item.get("label") or item.get("category")
            label = normalize_label(raw_label)
            start = item.get("start")
            end = item.get("end")
            text = item.get("text", "")
            if label and start is not None and end is not None:
                try:
                    s, e = int(start), int(end)
                    if 0 <= s < e <= len(original_text):
                        extracted_text = original_text[s:e]
                        if text and text != extracted_text:
                            # Try nearest exact match if offset drifted slightly
                            found = _nearest_exact_occurrence(text, original_text, s)
                            if found is not None:
                                s = found
                                e = found + len(text)
                                extracted_text = original_text[s:e]
                        s, e = clean_span(s, e, original_text)
                        if s < e:
                            spans.append({"label": label, "start": s, "end": e, "text": original_text[s:e]})
                except Exception:
                    continue

    # Handle per-category key structure (e.g. {"ae": [...], "sdrug": [...]})
    for cat_key, items in obj.items():
        if cat_key in ("spans", "annotated_text", "meta"):
            continue
        if isinstance(items, list):
            label = normalize_label(cat_key) or cat_key
            for item in items:
                if not isinstance(item, dict):
                    continue
                start = item.get("start")
                end = item.get("end")
                text = item.get("text", "")
                if start is not None and end is not None:
                    try:
                        s, e = int(start), int(end)
                        if 0 <= s < e <= len(original_text):
                            extracted_text = original_text[s:e]
                            if text and text != extracted_text:
                                found = _nearest_exact_occurrence(text, original_text, s)
                                if found is not None:
                                    s = found
                                    e = found + len(text)
                                    extracted_text = original_text[s:e]
                            s, e = clean_span(s, e, original_text)
                            if s < e:
                                spans.append({"label": label, "start": s, "end": e, "text": original_text[s:e]})
                    except Exception:
                        continue

    return _dedupe_and_resolve_overlaps(spans)


def get_ai_client(provider: Optional[str] = None) -> AIClient:
    prov = provider or os.getenv('AI_PROVIDER', 'vllm')
    return AIClient(provider=prov)


def call_llm(message: str, prompt: str = 'Help answer the following requests.', 
             provider: Optional[str] = None, max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
             temperature: float = 0.0, **kwargs) -> str:
    client = get_ai_client(provider=provider)
    return client.call(message=message, system_prompt=prompt, temperature=temperature, max_tokens=max_output_tokens, **kwargs)


def mode_AE_annotation(query: str, mode: str = "tag", schema: str = "faers", provider: Optional[str] = None, **kwargs) -> Tuple[str, List[dict]]:
    """
    Annotate narrative text using LLM.
    
    Args:
        query (str): Clinical narrative text.
        mode (str): "tag" (default, In-Text XML Tagging P2_TAG) or "json" (Structured JSON P1_JSON).
        schema (str): "faers" (default, 17 categories) or "vaers" (14 categories).
        provider (str): Optional AI provider override.
        **kwargs: Additional parameters passed to call_llm.
        
    Returns:
        Tuple[str, List[dict]]: (raw_output, list of validated span dicts)
    """
    is_vaers = str(schema).lower() == "vaers"
    
    if mode.lower() == "json":
        system_prompt = P1_JSON_VAERS if is_vaers else P1_JSON
        user_message = f"### Narrative\n\n{query}\n\n### CRITICAL OUTPUT REQUIREMENTS\nReturn ONLY valid JSON."
        raw = call_llm(message=user_message, prompt=system_prompt, provider=provider, **kwargs)
        spans = _extract_json_spans(raw, query)
        return raw, spans
    else:
        # Default: In-Text XML Tagging (P2_TAG) - Primary manuscript paradigm
        system_prompt = P2_TAG_VAERS if is_vaers else P2_TAG
        user_message = f"### Narrative\n\n{query}\n\n### CRITICAL OUTPUT REQUIREMENTS\nReturn ONLY the fully annotated narrative."
        raw = call_llm(message=user_message, prompt=system_prompt, provider=provider, **kwargs)
        sanitized = sanitize_model_output(raw)
        clean_text, parsed_spans, warnings = parse_tagged_output(sanitized)
        mapped_spans, meta = map_predicted_spans_to_original(clean_text, parsed_spans, query)
        deduped_spans = _dedupe_and_resolve_overlaps(mapped_spans)
        return raw, deduped_spans


def run_llm_annotation(doc_id: Optional[int] = None, file_path: Optional[str] = None,
                       mode: str = "tag", schema: str = "faers",
                       provider: Optional[str] = None, model: Optional[str] = None,
                       note: Optional[str] = None) -> Tuple[bool, str]:
    """
    Main annotation execution pipeline for LLM4AE.
    Fetches case narrative, executes model inference, aligns offsets, and persists annotations to DB.
    """
    try:
        active_provider = provider or os.getenv('AI_PROVIDER', 'vllm')
        active_note = note or os.getenv('LLM_MODEL_NOTE', 'Llama4')

        if doc_id:
            conn = get_db_connection()
            doc = conn.execute('SELECT pages, meta FROM cases WHERE id = ?', (doc_id,)).fetchone()
            if not doc:
                conn.close()
                return False, f"Document id {doc_id} not found"
            
            pages = json.loads(doc['pages']) if doc['pages'] else [""]
            narrative = pages[0] if pages else ""
            meta = json.loads(doc['meta']) if doc['meta'] else {}
            
            # Resolve AI user ID
            ai_user_id = get_user_by_note(active_note) or get_user_by_note('LLM') or get_user_by_note('Llama4')
            if not ai_user_id:
                # Fallback to any user with role 'AI'
                ai_user_row = conn.execute("SELECT id FROM users WHERE role_id = (SELECT id FROM roles WHERE name = 'AI') LIMIT 1").fetchone()
                ai_user_id = ai_user_row['id'] if ai_user_row else 2
            
            conn.close()
        elif file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            narrative = data['pages'][0]
            meta = data.get('meta', {})
            ai_user_id = None
        else:
            return False, "Either doc_id or file_path must be provided"

        if not narrative or not narrative.strip():
            return False, "Empty narrative text"

        # Execute LLM annotation
        raw_output, spans = mode_AE_annotation(
            query=narrative,
            mode=mode,
            schema=schema,
            provider=active_provider
        )

        llm_annotations = []
        for sp in spans:
            llm_annotations.append({
                "label": sp["label"],
                "user_id": ai_user_id,
                "note": active_note,
                "start": sp["start"],
                "end": sp["end"],
                "text": sp["text"]
            })

        if doc_id:
            conn = get_db_connection()
            with conn:
                # Delete existing AI annotations for this case
                conn.execute('DELETE FROM annotations WHERE case_id = ? AND user_id = ?', (doc_id, ai_user_id))
                
                # Insert newly predicted spans
                for ann in llm_annotations:
                    conn.execute('''
                        INSERT INTO annotations 
                        (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships, adjudication)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (doc_id, ann['user_id'], ann['label'], ann['start'], ann['end'], ann['text'], ann['note'], '{}', None))
                
                # Update case metadata
                meta["llm_processed"] = "Done"
                meta["llm_provider"] = active_provider
                meta["llm_mode"] = mode
                meta["llm_schema"] = schema
                meta["llm_count"] = len(llm_annotations)
                conn.execute('UPDATE cases SET meta = ? WHERE id = ?', (json.dumps(meta), doc_id))
            
            conn.close()

        return True, f"Annotation complete. Produced {len(llm_annotations)} annotations."

    except Exception as e:
        logger.error(f"Error in run_llm_annotation: {e}", exc_info=True)
        if doc_id:
            try:
                conn = get_db_connection()
                doc = conn.execute('SELECT meta FROM cases WHERE id = ?', (doc_id,)).fetchone()
                if doc:
                    meta = json.loads(doc['meta']) if doc['meta'] else {}
                    meta["llm_processed"] = f"Error: {str(e)}"
                    conn.execute('UPDATE cases SET meta = ? WHERE id = ?', (json.dumps(meta), doc_id))
                    conn.commit()
                conn.close()
            except Exception:
                pass
        return False, str(e)

