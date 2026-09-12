#!/usr/bin/env python3
"""
run_FAERS_sonnet.py

One-pass Claude Sonnet annotation/evaluation for the FAERS D1 corpus using the project's
P2_TAG prompt from scripts/annotation_prompts.py.

Design goals
------------
* NO training and NO train/dev split: every FAERS document is evaluated once.
* The LLM sees ONLY the narrative text from JSON["pages"][0]. SME annotations
  are deliberately loaded only AFTER an LLM prediction has been produced (or
  recovered from the incremental prediction cache), so they cannot leak into
  the prompt.
* The prompt is imported verbatim from scripts/annotation_prompts.py and only
  P2_TAG is used.
* The LLM is instructed to insert XML-style tags without changing the source.
  Because Sonnet output may still contain small text changes, predicted spans are
  mapped back to the original page text with difflib.SequenceMatcher.
* Evaluation uses the same ADE-style M/C/S/N alignment and weighted P/R/F1
  logic as the BioBERT script template.
* Results are written under results/sonnet_runs_FAERS by default.
* Incremental JSONL caching makes long API runs resumable without re-calling
  successfully completed documents.

Expected .env entries
---------------------
ELSA_API_NAME=...
ELSA_API_KEY=...
ELSA_MODEL_ID=...
ELSA_MODEL_NAME=CLAUDE_46_SONNET

Default project layout
----------------------
/compute001/lwu/projects/LLM4AE/LLM4AE-dev/publication/
    .env
    Datasets/FAERS_D1_clean/*.json
    scripts/annotation_prompts.py
    results/sonnet_runs_FAERS/

Examples
--------
python scripts/run_FAERS_sonnet.py
python scripts/run_FAERS_sonnet.py --limit 10
python scripts/run_FAERS_sonnet.py --no-resume
python scripts/run_FAERS_sonnet.py --timeout 600 --max-output-tokens 32768

Requirements
------------
pandas, openpyxl, requests, tqdm
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import logging
import os
import re
import sys
import time
import traceback
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd
import requests
from tqdm import tqdm


# =============================================================================
# Project defaults
# =============================================================================

BASE = Path("/compute001/lwu/projects/LLM4AE/LLM4AE-dev/publication")
DEFAULT_DATA_DIR = BASE / "Datasets" / "FAERS_D1_clean"
DEFAULT_RESULTS_DIR = BASE / "results" / "sonnet_runs_FAERS"
DEFAULT_PROMPT_FILE = BASE / "scripts" / "annotation_prompts.py"
DEFAULT_ENV_FILE = BASE / ".env"

# Canonical evaluation labels. These match the BioBERT evaluation naming where
# possible while extending it to the current 17-category schema.
RAW_TO_LABEL = {
    # Adverse events
    "ae": "ae",
    "AE": "ae",
    "mae": "mae",
    "mAE": "mae",
    "MAE": "mae",
    # Drugs
    "sDrug": "sdrug",
    "SDRUG": "sdrug",
    "sdrug": "sdrug",
    "cDrug": "cdrug",
    "CDRUG": "cdrug",
    "cdrug": "cdrug",
    # Historical datasets often used generic Drug/DRUG for the current oDrug
    # concept. Map those labels to odrug for the current 17-category schema.
    "oDrug": "odrug",
    "ODRUG": "odrug",
    "odrug": "odrug",
    "Drug": "odrug",
    "DRUG": "odrug",
    # Dose / indication / treatment
    "Dose": "dose",
    "DOSE": "dose",
    "dose": "dose",
    "IND": "indication",
    "INDICATION": "indication",
    "indication": "indication",
    "Treatment": "treatment",
    "TREATMENT": "treatment",
    "treatment": "treatment",
    # Diagnostics / laboratory
    "Dx": "diagnostic",
    "DX": "diagnostic",
    "DIAGNOSTIC": "diagnostic",
    "diagnostic": "diagnostic",
    "Lab": "lab",
    "LAB": "lab",
    "lab": "lab",
    # Patient status
    "Status": "status",
    "STATUS": "status",
    "status": "status",
    # Rule-out / cause of death
    "R/O": "ro",
    "RO": "ro",
    "r/o": "ro",
    "ro": "ro",
    "CoD": "cod",
    "COD": "cod",
    "CAUSE OF DEATH": "cod",
    "cod": "cod",
    # History
    "MHx": "mhx",
    "MHX": "mhx",
    "MEDICAL HISTORY": "mhx",
    "mhx": "mhx",
    "FHx": "fhx",
    "FHX": "fhx",
    "FAMILY HISTORY": "fhx",
    "fhx": "fhx",
    # Demographics
    "Age": "age",
    "AGE": "age",
    "age": "age",
    "Sex": "sex",
    "SEX": "sex",
    "sex": "sex",
    # Explicitly excluded from the CURRENT 17-category prompt/evaluation.
    "bSYM": None,
    "BSYM": None,
    "BASELINE SYMPTOM": None,
    "TEMPO": None,
    "tempo": None,
    "TEMPORAL": None,
    "Date": None,
    "DATE": None,
    "Time": None,
    "TIME": None,
    "Duration": None,
    "DURATION": None,
    "Relative": None,
    "RELATIVE": None,
    "Latency": None,
    "LATENCY": None,
}

_RAW_TO_LABEL_CASEFOLD = {
    str(key).strip().casefold(): value for key, value in RAW_TO_LABEL.items()
}

TAG_TO_LABEL = {
    "SDRUG": "sdrug",
    "CDRUG": "cdrug",
    "ODRUG": "odrug",
    "DOSE": "dose",
    "IND": "indication",
    "TREATMENT": "treatment",
    "AE": "ae",
    "MAE": "mae",
    "DX": "diagnostic",
    "LAB": "lab",
    "STATUS": "status",
    "RO": "ro",
    "COD": "cod",
    "MHX": "mhx",
    "FHX": "fhx",
    "AGE": "age",
    "SEX": "sex",
}

EVAL_LABEL_POOL = {
    "ae": "AE",
    "mae": "AE",
    "sdrug": "DRUG",
    "cdrug": "DRUG",
    "odrug": "DRUG",
    "mhx": "HX",
    "fhx": "HX",
    "diagnostic": "DX",
    "treatment": "DX",
    "lab": "LAB",
    "dose": "DOSE",
    "status": "STATUS",
    "ro": "RO",
    "cod": "COD",
    "age": "AGE",
    "sex": "SEX",
    "indication": "INDICATION",
}

ALL_LABELS = tuple(TAG_TO_LABEL.values())

# Recognize only the 17 allowed XML-like tags. Other angle-bracket text remains
# untouched and therefore participates in SequenceMatcher alignment.
_ALLOWED_TAG_NAMES = "|".join(sorted(TAG_TO_LABEL, key=len, reverse=True))
_TAG_RE = re.compile(
    rf"<\s*(?P<close>/?)\s*(?P<tag>{_ALLOWED_TAG_NAMES})\s*>",
    flags=re.IGNORECASE,
)

# Minimal cleanup for common model wrappers that violate P2_TAG's output rule.
_FENCE_START_RE = re.compile(r"^\s*```(?:xml|html|text)?\s*\n?", re.IGNORECASE)
_FENCE_END_RE = re.compile(r"\n?\s*```\s*$")
_KNOWN_PREAMBLE_RE = re.compile(
    r"^\s*The annotated text is shown as below:\s*(?:\r?\n)?",
    flags=re.IGNORECASE,
)

_RAW_COLUMNS = [
    "document",
    "match_type",
    "label_gold",
    "gold_start",
    "gold_end",
    "gold_text",
    "label_pred",
    "pred_start",
    "pred_end",
    "pred_text",
]

_PER_LABEL_COLUMNS = [
    "label",
    "eval_category",
    "M",
    "C",
    "S",
    "N",
    "precision",
    "recall",
    "f1",
]


# =============================================================================
# Logging / console helpers
# =============================================================================

def console_print(message: str) -> None:
    """Print without damaging an active tqdm display."""
    tqdm.write(str(message), file=sys.stdout)


def setup_logger(log_path: Path) -> logging.Logger:
    """Plain UTF-8 file logger; no ANSI, emojis, or terminal control codes."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("llm4ae_sonnet")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


# =============================================================================
# Configuration and prompt loading
# =============================================================================

def load_env_file(path: Path) -> None:
    """
    Load simple KEY=VALUE entries from .env without requiring python-dotenv.

    Existing process environment variables take precedence over file values.
    """
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


def load_p2_tag(prompt_file: Path) -> str:
    """Import exactly P2_TAG from scripts/annotation_prompts.py."""
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    spec = importlib.util.spec_from_file_location("llm4ae_annotation_prompts", prompt_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not import prompt module: {prompt_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "P2_TAG"):
        raise AttributeError(f"{prompt_file} does not define P2_TAG")
    prompt = getattr(module, "P2_TAG")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("P2_TAG must be a non-empty string")
    if "{text}" not in prompt:
        raise ValueError("P2_TAG must contain a {text} placeholder")
    return prompt


def prompt_sha256(prompt_template: str) -> str:
    return hashlib.sha256(prompt_template.encode("utf-8")).hexdigest()


# =============================================================================
# Data loading -- strict separation of inference text and SME ground truth
# =============================================================================

def load_page_records(data_dir: Path, limit: Optional[int] = None) -> List[dict]:
    """
    Load ONLY filename/path and pages[0] for LLM inference.

    This function intentionally never reads doc["annotations"]. Ground-truth SME
    annotations are loaded later, after a prediction exists, by load_gold().
    """
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")

    files = sorted(data_dir.glob("*.json"))
    if limit is not None:
        files = files[:limit]
    if not files:
        raise FileNotFoundError(f"No JSON files found in: {data_dir}")

    records = []
    for fpath in files:
        with fpath.open(encoding="utf-8") as handle:
            doc = json.load(handle)
        pages = doc.get("pages", [])
        page_text = str(pages[0]) if pages else ""
        records.append(
            {
                "document": fpath.name,
                "path": fpath,
                "text": page_text,
            }
        )
    return records


def normalize_raw_label(raw_label: object) -> Optional[str]:
    if raw_label is None:
        return None
    raw = str(raw_label).strip()
    if raw in RAW_TO_LABEL:
        return RAW_TO_LABEL[raw]
    return _RAW_TO_LABEL_CASEFOLD.get(raw.casefold())


def clean_span(start: int, end: int, text: str) -> Tuple[int, int]:
    """Match BioBERT preprocessing by stripping whitespace at entity edges."""
    start = max(0, min(int(start), len(text)))
    end = max(0, min(int(end), len(text)))
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def load_gold(fpath: Path, page_text: str) -> Tuple[List[Tuple[int, int, str]], dict]:
    """
    Load SME1 ground truth AFTER inference.

    Only the current 17 categories are retained. bSYM and temporal categories are
    intentionally excluded because they are not present in the current P2_TAG.
    """
    with fpath.open(encoding="utf-8") as handle:
        doc = json.load(handle)

    stats = defaultdict(int)
    unknown = defaultdict(int)
    gold = []

    for ann in doc.get("annotations", []):
        if ann.get("note") != "SME1":
            continue
        stats["sme1_seen"] += 1

        raw_label = ann.get("label", "")
        label = normalize_raw_label(raw_label)
        if label is None:
            raw = str(raw_label).strip()
            known = raw in RAW_TO_LABEL or raw.casefold() in _RAW_TO_LABEL_CASEFOLD
            if known:
                stats["excluded"] += 1
            else:
                stats["unknown"] += 1
                unknown[raw] += 1
            continue

        tc = ann.get("textContext") or {}
        try:
            start = int(tc.get("start"))
            end = int(tc.get("end"))
        except (TypeError, ValueError):
            stats["invalid_offset"] += 1
            continue

        if start < 0 or start >= end or end > len(page_text):
            stats["invalid_offset"] += 1
            continue

        start, end = clean_span(start, end, page_text)
        if start >= end:
            stats["empty_after_clean"] += 1
            continue

        gold.append((start, end, label))
        stats["kept"] += 1

    stats["unknown_labels"] = dict(sorted(unknown.items()))
    return gold, dict(stats)


# =============================================================================
# LLM API
# =============================================================================

class ElsaClient:
    """Minimal Elsa/Pixel client matching the project AI service contract."""

    DEFAULT_ENDPOINT = "https://elsa-dev.preprod.fda.gov/Monolith/api/engine/runPixel"

    def __init__(
        self,
        *,
        api_name: str,
        api_key: str,
        model_id: str,
        model_name: str,
        endpoint: str,
        timeout: float,
        max_output_tokens: int,
        temperature: float,
        retries: int,
        retry_backoff: float,
        verify_ssl: bool,
    ):
        if not api_name:
            raise ValueError("ELSA_API_NAME is empty")
        if not api_key:
            raise ValueError("ELSA_API_KEY is empty")
        if not model_id:
            raise ValueError("ELSA_MODEL_ID is empty")
        if not model_name:
            raise ValueError("ELSA_MODEL_NAME is empty")

        self.api_name = api_name
        self.api_key = api_key
        self.model_id = model_id
        self.model_name = model_name
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.retries = retries
        self.retry_backoff = retry_backoff
        self.verify_ssl = verify_ssl
        self.session = requests.Session()

        if not verify_ssl:
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass

    def annotate(self, prompt: str) -> Tuple[str, dict]:
        # Match ai_service.py's Elsa execution path: send the prompt inside an
        # <encode> wrapper to the Pixel LLM engine, authenticated with HTTP Basic.
        command = (
            f'LLM(engine = "{self.model_id}", command = "<encode>{prompt}</encode>", '
            f'paramValues = [{{"max_completion_tokens": {self.max_output_tokens}, '
            f'"temperature": {self.temperature}}}])'
        )
        payload = {"expression": command}

        last_error = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.post(
                    self.endpoint,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data=payload,
                    auth=(self.api_name, self.api_key),
                    verify=self.verify_ssl,
                    timeout=self.timeout,
                )

                # Retry rate limits and server-side failures, as in ai_service.py.
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Elsa Service Error ({response.status_code}): {response.text[:1000]}"
                    )

                data = response.json()
                try:
                    output = data["pixelReturn"][0]["output"]["response"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise RuntimeError(
                        "Elsa returned HTTP 200 but the response schema was unexpected: "
                        f"{response.text[:2000]}"
                    ) from exc

                meta = {
                    "provider": "elsa",
                    "model_id": self.model_id,
                    "model_name": self.model_name,
                    "http_status": response.status_code,
                    # Elsa does not expose token usage in this response path.
                    "usage": {},
                }
                return str(output), meta

            except Exception as exc:
                last_error = exc
                retryable = isinstance(
                    exc,
                    (requests.exceptions.ConnectionError, requests.exceptions.Timeout),
                )
                if isinstance(exc, requests.exceptions.HTTPError):
                    status = exc.response.status_code if exc.response is not None else None
                    retryable = status == 429 or (status is not None and 500 <= status < 600)

                if attempt >= self.retries or not retryable:
                    break
                time.sleep(self.retry_backoff * (2 ** attempt))

        raise RuntimeError(
            f"Elsa request failed after {self.retries + 1} attempt(s): {last_error}"
        )


# =============================================================================
# Tagged-output parsing and SequenceMatcher mapping
# =============================================================================

def sanitize_model_output(output: str) -> str:
    """Remove only common wrappers; preserve the model's narrative content."""
    text = output.replace("\ufeff", "")
    text = _FENCE_START_RE.sub("", text, count=1)
    text = _FENCE_END_RE.sub("", text, count=1)
    text = _KNOWN_PREAMBLE_RE.sub("", text, count=1)
    return text


def parse_tagged_output(tagged_text: str) -> Tuple[str, List[dict], List[str]]:
    """
    Remove allowed tags and return spans in tag-stripped-output coordinates.

    The parser tolerates tag case/spacing variation but records malformed,
    overlapping, or nested tag behavior in warnings. Only properly closed spans
    are emitted.
    """
    clean_parts: List[str] = []
    clean_len = 0
    spans: List[dict] = []
    warnings: List[str] = []
    stack: List[Tuple[str, str, int]] = []  # normalized tag, label, clean_start

    cursor = 0
    for match in _TAG_RE.finditer(tagged_text):
        segment = tagged_text[cursor:match.start()]
        clean_parts.append(segment)
        clean_len += len(segment)

        tag_name = match.group("tag").upper()
        label = TAG_TO_LABEL[tag_name]
        is_close = bool(match.group("close"))

        if not is_close:
            if stack:
                warnings.append(
                    f"nested tag <{tag_name}> encountered inside <{stack[-1][0]}>"
                )
            stack.append((tag_name, label, clean_len))
        else:
            if not stack:
                warnings.append(f"closing tag </{tag_name}> without opening tag")
            else:
                # Prefer the closest matching open tag. If misnested, close the
                # matching tag and record that the model violated the contract.
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
                        spans.append(
                            {
                                "tag": open_tag,
                                "label": open_label,
                                "clean_start": start,
                                "clean_end": clean_len,
                            }
                        )
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
    Map every boundary in clean_text to a boundary in original_text.

    Exact blocks are mapped character-for-character. Insert/delete/replace gaps
    are interpolated monotonically so every predicted tag span has usable source
    coordinates. Exact span text is then refined separately when possible.
    """
    matcher = SequenceMatcher(None, clean_text, original_text, autojunk=False)
    opcodes = matcher.get_opcodes()
    boundary: List[Optional[int]] = [None] * (len(clean_text) + 1)

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for k in range(i2 - i1 + 1):
                boundary[i1 + k] = j1 + k
        elif tag == "insert":
            # Nothing in clean_text corresponds to original[j1:j2]. The clean
            # boundary is best aligned to the end of the inserted source chunk.
            boundary[i1] = j2
        elif tag == "delete":
            # clean_text contains extra material absent from the source.
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

    # Fill any rare unset entries using nearest known boundaries while enforcing
    # monotonicity and valid source range.
    last = 0
    for idx in range(len(boundary)):
        if boundary[idx] is None:
            boundary[idx] = last
        last = max(last, int(boundary[idx]))
        boundary[idx] = min(last, len(original_text))

    for idx in range(len(boundary) - 2, -1, -1):
        boundary[idx] = min(int(boundary[idx]), int(boundary[idx + 1]))

    return [int(x) for x in boundary], matcher.ratio(), opcodes


def _nearest_exact_occurrence(
    needle: str,
    haystack: str,
    expected_start: int,
    *,
    window: int = 800,
) -> Optional[int]:
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


def map_predicted_spans_to_original(
    clean_text: str,
    spans: Sequence[dict],
    original_text: str,
) -> Tuple[List[Tuple[int, int, str]], dict]:
    """Map tag spans from Sonnet output coordinates back to original page offsets."""
    boundary, ratio, opcodes = build_boundary_map(clean_text, original_text)
    mapped: List[Tuple[int, int, str]] = []
    details: List[dict] = []
    dropped = 0
    exact_refined = 0

    for span in spans:
        c0 = int(span["clean_start"])
        c1 = int(span["clean_end"])
        label = str(span["label"])
        pred_surface = clean_text[c0:c1]

        o0 = boundary[max(0, min(c0, len(clean_text)))]
        o1 = boundary[max(0, min(c1, len(clean_text)))]
        if o1 < o0:
            o0, o1 = o1, o0

        # If the LLM preserved the tagged entity text exactly, find the nearest
        # exact occurrence around the SequenceMatcher estimate. This resolves
        # ambiguous replace/delete regions more accurately than interpolation.
        found = _nearest_exact_occurrence(pred_surface, original_text, o0)
        mapping_method = "sequence_matcher"
        if found is not None:
            o0 = found
            o1 = found + len(pred_surface)
            exact_refined += 1
            mapping_method = "sequence_matcher+exact_refine"

        o0, o1 = clean_span(o0, o1, original_text)
        if o0 >= o1:
            dropped += 1
            details.append(
                {
                    **span,
                    "pred_surface": pred_surface,
                    "mapped_start": None,
                    "mapped_end": None,
                    "mapped_text": None,
                    "mapping_method": "dropped_empty",
                }
            )
            continue

        mapped_text = original_text[o0:o1]
        mapped.append((o0, o1, label))
        details.append(
            {
                **span,
                "pred_surface": pred_surface,
                "mapped_start": o0,
                "mapped_end": o1,
                "mapped_text": mapped_text,
                "mapping_method": mapping_method,
            }
        )

    # Deduplicate exact duplicate predictions while preserving order.
    deduped = []
    seen = set()
    for item in sorted(mapped, key=lambda x: (x[0], x[1], x[2])):
        if item not in seen:
            deduped.append(item)
            seen.add(item)

    stats = {
        "sequence_matcher_ratio": ratio,
        "n_parsed_spans": len(spans),
        "n_mapped_spans": len(deduped),
        "n_dropped_spans": dropped,
        "n_exact_refined": exact_refined,
        "n_opcodes": len(opcodes),
        "mapped_span_details": details,
    }
    return deduped, stats


# =============================================================================
# ADE-style entity alignment and metrics (same logic as BioBERT template)
# =============================================================================

def _overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return (
        (a0 == b0)
        or (a1 == b1)
        or (a0 < b0 < a1)
        or (a0 < b1 < a1)
        or (b0 < a0 < b1)
    )


def align_entities(text: str, gold_ents, pred_ents) -> List[dict]:
    rows = []
    gold_sorted = sorted(gold_ents, key=lambda x: (x[0], x[1], x[2]))
    pred_sorted = sorted(pred_ents, key=lambda x: (x[0], x[1], x[2]))
    pred_flag = [False] * len(pred_sorted)

    for g0, g1, glab in gold_sorted:
        exact_j = None
        partial_j = None
        best_overlap = 0

        for j, (p0, p1, plab) in enumerate(pred_sorted):
            if pred_flag[j]:
                continue
            if p0 == g0 and p1 == g1 and plab == glab:
                exact_j = j
                break
            if plab == glab and _overlap(g0, g1, p0, p1):
                overlap = max(0, min(g1, p1) - max(g0, p0))
                if overlap > best_overlap:
                    best_overlap = overlap
                    partial_j = j

        if exact_j is not None:
            p0, p1, plab = pred_sorted[exact_j]
            pred_flag[exact_j] = True
            rows.append(
                {
                    "match_type": "M",
                    "label_gold": glab,
                    "gold_start": g0,
                    "gold_end": g1,
                    "gold_text": text[g0:g1],
                    "label_pred": plab,
                    "pred_start": p0,
                    "pred_end": p1,
                    "pred_text": text[p0:p1],
                }
            )
        elif partial_j is not None:
            p0, p1, plab = pred_sorted[partial_j]
            pred_flag[partial_j] = True
            rows.append(
                {
                    "match_type": "C",
                    "label_gold": glab,
                    "gold_start": g0,
                    "gold_end": g1,
                    "gold_text": text[g0:g1],
                    "label_pred": plab,
                    "pred_start": p0,
                    "pred_end": p1,
                    "pred_text": text[p0:p1],
                }
            )
        else:
            rows.append(
                {
                    "match_type": "N",
                    "label_gold": glab,
                    "gold_start": g0,
                    "gold_end": g1,
                    "gold_text": text[g0:g1],
                    "label_pred": None,
                    "pred_start": None,
                    "pred_end": None,
                    "pred_text": None,
                }
            )

    for j, (p0, p1, plab) in enumerate(pred_sorted):
        if pred_flag[j]:
            continue
        rows.append(
            {
                "match_type": "S",
                "label_gold": None,
                "gold_start": None,
                "gold_end": None,
                "gold_text": None,
                "label_pred": plab,
                "pred_start": p0,
                "pred_end": p1,
                "pred_text": text[p0:p1],
            }
        )

    return rows


def weighted_prf(M: int, C: int, S: int, N: int) -> Tuple[float, float, float]:
    """Preserve the BioBERT script's ADE-style weighting exactly."""
    matched_credit = M + 0.5 * C
    spurious_weight = 0.25 * S
    p_den = matched_credit + 0.5 * C + spurious_weight
    r_den = matched_credit + 0.5 * C + N
    precision = matched_credit / p_den if p_den > 0 else 0.0
    recall = matched_credit / r_den if r_den > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )
    return round(precision, 4), round(recall, 4), round(f1, 4)


def compute_metrics(df: pd.DataFrame) -> Tuple[dict, pd.DataFrame]:
    if df.empty:
        overall = {
            "M": 0,
            "C": 0,
            "S": 0,
            "N": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }
        return overall, pd.DataFrame(columns=_PER_LABEL_COLUMNS)

    counts = df["match_type"].value_counts().to_dict()
    M = int(counts.get("M", 0))
    C = int(counts.get("C", 0))
    S = int(counts.get("S", 0))
    N = int(counts.get("N", 0))
    p, r, f1 = weighted_prf(M, C, S, N)
    overall = {
        "M": M,
        "C": C,
        "S": S,
        "N": N,
        "precision": p,
        "recall": r,
        "f1": f1,
    }

    labels = set(
        df.loc[df["match_type"].isin(["M", "C", "N"]), "label_gold"].dropna()
    )
    labels.update(df.loc[df["match_type"] == "S", "label_pred"].dropna())

    rows = []
    for label in sorted(labels):
        M_l = int(((df["match_type"] == "M") & (df["label_gold"] == label)).sum())
        C_l = int(((df["match_type"] == "C") & (df["label_gold"] == label)).sum())
        N_l = int(((df["match_type"] == "N") & (df["label_gold"] == label)).sum())
        S_l = int(((df["match_type"] == "S") & (df["label_pred"] == label)).sum())
        p_l, r_l, f_l = weighted_prf(M_l, C_l, S_l, N_l)
        rows.append(
            {
                "label": label,
                "eval_category": EVAL_LABEL_POOL.get(label, label.upper()),
                "M": M_l,
                "C": C_l,
                "S": S_l,
                "N": N_l,
                "precision": p_l,
                "recall": r_l,
                "f1": f_l,
            }
        )

    return overall, pd.DataFrame(rows, columns=_PER_LABEL_COLUMNS)


def build_collapsed_category_summary(per_label_df: pd.DataFrame) -> pd.DataFrame:
    if per_label_df.empty:
        return pd.DataFrame(
            columns=["eval_category", "M", "C", "S", "N", "precision", "recall", "f1"]
        )

    grouped = (
        per_label_df.groupby("eval_category", as_index=False)
        .agg(M=("M", "sum"), C=("C", "sum"), S=("S", "sum"), N=("N", "sum"))
    )
    metrics = grouped.apply(
        lambda row: pd.Series(
            weighted_prf(int(row.M), int(row.C), int(row.S), int(row.N)),
            index=["precision", "recall", "f1"],
        ),
        axis=1,
    )
    grouped[["precision", "recall", "f1"]] = metrics
    return grouped


# =============================================================================
# Incremental prediction cache
# =============================================================================

def load_prediction_cache(path: Path) -> Dict[str, dict]:
    cache: Dict[str, dict] = {}
    if not path.exists():
        return cache
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            document = row.get("document")
            if document and row.get("status") == "ok":
                cache[str(document)] = row
    return cache


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


# =============================================================================
# Main execution
# =============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "One-pass Claude Sonnet FAERS annotation using scripts/annotation_prompts.py:P2_TAG "
            "and SequenceMatcher offset recovery."
        )
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPT_FILE)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--limit", type=int, default=None, help="Run only first N documents")
    parser.add_argument("--timeout", type=float, default=600.0, help="HTTP timeout seconds")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-backoff", type=float, default=2.0)
    parser.add_argument("--max-output-tokens", type=int, default=32768)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help=(
            "Disable TLS certificate verification for the Elsa endpoint. "
            "Use only when required by the FDA internal/preprod environment."
        ),
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore successful rows already present in predictions.jsonl and call Sonnet again.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable tqdm progress bar.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on the first Elsa/API/document error instead of continuing.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be >= 1")
    if args.timeout <= 0:
        raise ValueError("--timeout must be > 0")
    if args.retries < 0:
        raise ValueError("--retries must be >= 0")
    if args.max_output_tokens < 1:
        raise ValueError("--max-output-tokens must be >= 1")


def main() -> None:
    args = parse_args()
    validate_args(args)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    log_path = args.results_dir / "run.log"
    logger = setup_logger(log_path)

    # Load Elsa configuration from .env. The API key is never printed or persisted.
    load_env_file(args.env_file)
    elsa_api_name = os.environ.get("ELSA_API_NAME", "").strip()
    elsa_api_key = os.environ.get("ELSA_API_KEY", "").strip()
    elsa_model_id = os.environ.get("ELSA_MODEL_ID", "").strip()
    elsa_model_name = os.environ.get("ELSA_MODEL_NAME", "").strip()
    elsa_endpoint = os.environ.get(
        "ELSA_API_URL", ElsaClient.DEFAULT_ENDPOINT
    ).strip() or ElsaClient.DEFAULT_ENDPOINT

    required = [
        ("ELSA_API_NAME", elsa_api_name),
        ("ELSA_API_KEY", elsa_api_key),
        ("ELSA_MODEL_ID", elsa_model_id),
        ("ELSA_MODEL_NAME", elsa_model_name),
    ]
    missing = [name for name, value in required if not value]
    if missing:
        raise RuntimeError(
            f"Missing required Elsa configuration: {', '.join(missing)}. "
            f"Expected them in environment or {args.env_file}."
        )

    prompt_template = load_p2_tag(args.prompt_file)
    prompt_hash = prompt_sha256(prompt_template)

    client = ElsaClient(
        api_name=elsa_api_name,
        api_key=elsa_api_key,
        model_id=elsa_model_id,
        model_name=elsa_model_name,
        endpoint=elsa_endpoint,
        timeout=args.timeout,
        max_output_tokens=args.max_output_tokens,
        temperature=args.temperature,
        retries=args.retries,
        retry_backoff=args.retry_backoff,
        verify_ssl=not args.no_verify_ssl,
    )

    records = load_page_records(args.data_dir, limit=args.limit)
    predictions_path = args.results_dir / "predictions.jsonl"
    cache = {} if args.no_resume else load_prediction_cache(predictions_path)

    logger.info("Run started")
    logger.info("Data directory: %s", args.data_dir)
    logger.info("Results directory: %s", args.results_dir)
    logger.info("Prompt file: %s", args.prompt_file)
    logger.info("P2_TAG SHA256: %s", prompt_hash)
    logger.info("Elsa endpoint: %s", elsa_endpoint)
    logger.info("Elsa model ID: %s", elsa_model_id)
    logger.info("Elsa model name: %s", elsa_model_name)
    logger.info("Documents: %d", len(records))
    logger.info("Resume cache: %d successful documents", len(cache))

    console_print(f"Loaded {len(records)} FAERS documents from {args.data_dir}")
    console_print(f"Prompt: {args.prompt_file} :: P2_TAG")
    console_print(f"P2_TAG SHA256: {prompt_hash[:16]}...")
    console_print(f"Sonnet model: {elsa_model_name} ({elsa_model_id})")
    console_print(f"Results: {args.results_dir}")
    if cache:
        console_print(f"Resume: {len(cache)} successful document(s) already cached")

    all_rows: List[dict] = []
    document_summary_rows: List[dict] = []
    total_gold_stats = defaultdict(int)
    sequence_ratios: List[float] = []
    failed_documents: List[dict] = []

    iterator: Iterable[dict] = records
    if not args.no_progress:
        iterator = tqdm(
            records,
            total=len(records),
            desc="Claude Sonnet FAERS",
            unit="doc",
            dynamic_ncols=True,
            file=sys.stdout,
        )

    for record in iterator:
        document = record["document"]
        page_text = record["text"]
        fpath = record["path"]
        started = time.time()

        try:
            cached_row = cache.get(document)
            if cached_row is not None:
                tagged_output = str(cached_row["llm_output"])
                api_meta = cached_row.get("api_meta") or {}
                source = "cache"
            else:
                # Critical leakage boundary: the prompt is constructed ONLY from
                # page_text. We do not call load_gold() until after this response.
                prompt = prompt_template.format(text=page_text)
                tagged_output, api_meta = client.annotate(prompt)
                source = "api"

            sanitized = sanitize_model_output(tagged_output)
            stripped_text, parsed_spans, parse_warnings = parse_tagged_output(sanitized)
            pred_ents, mapping_stats = map_predicted_spans_to_original(
                stripped_text,
                parsed_spans,
                page_text,
            )

            # Only NOW read SME annotations from the source JSON.
            gold_ents, gold_stats = load_gold(fpath, page_text)
            for key, value in gold_stats.items():
                if isinstance(value, int):
                    total_gold_stats[key] += value

            rows = align_entities(page_text, gold_ents, pred_ents)
            for row in rows:
                row["document"] = document
            all_rows.extend(rows)

            ratio = float(mapping_stats["sequence_matcher_ratio"])
            sequence_ratios.append(ratio)
            elapsed = time.time() - started

            counts = defaultdict(int)
            for row in rows:
                counts[row["match_type"]] += 1
            document_summary_rows.append(
                {
                    "document": document,
                    "source": source,
                    "text_chars": len(page_text),
                    "gold_entities": len(gold_ents),
                    "pred_entities": len(pred_ents),
                    "M": counts["M"],
                    "C": counts["C"],
                    "S": counts["S"],
                    "N": counts["N"],
                    "sequence_matcher_ratio": ratio,
                    "parse_warning_count": len(parse_warnings),
                    "elapsed_seconds": round(elapsed, 3),
                    "finish_reason": api_meta.get("finish_reason"),
                }
            )

            if cached_row is None:
                cache_record = {
                    "status": "ok",
                    "document": document,
                    "llm_output": tagged_output,
                    "stripped_output": stripped_text,
                    "predicted_entities": [
                        {"start": s, "end": e, "label": label, "text": page_text[s:e]}
                        for s, e, label in pred_ents
                    ],
                    "mapping": {
                        key: value
                        for key, value in mapping_stats.items()
                        if key != "mapped_span_details"
                    },
                    "mapped_span_details": mapping_stats["mapped_span_details"],
                    "parse_warnings": parse_warnings,
                    "api_meta": api_meta,
                    "prompt_sha256": prompt_hash,
                }
                append_jsonl(predictions_path, cache_record)

            logger.info(
                "%s | source=%s | gold=%d pred=%d | ratio=%.6f | M=%d C=%d S=%d N=%d | warnings=%d | %.2fs",
                document,
                source,
                len(gold_ents),
                len(pred_ents),
                ratio,
                counts["M"],
                counts["C"],
                counts["S"],
                counts["N"],
                len(parse_warnings),
                elapsed,
            )

            # Mapping quality below 0.95 deserves inspection but is still
            # evaluated because exact-refinement may have recovered entity spans.
            if ratio < 0.95:
                logger.warning(
                    "%s | low SequenceMatcher ratio %.6f; inspect predictions.jsonl",
                    document,
                    ratio,
                )

        except Exception as exc:
            elapsed = time.time() - started
            error_row = {
                "status": "error",
                "document": document,
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "elapsed_seconds": round(elapsed, 3),
                "prompt_sha256": prompt_hash,
            }
            failed_documents.append(error_row)
            append_jsonl(predictions_path, error_row)
            logger.error("%s | FAILED | %s", document, traceback.format_exc())
            if args.fail_fast:
                raise

    raw_df = pd.DataFrame(all_rows, columns=_RAW_COLUMNS)
    overall, per_label_df = compute_metrics(raw_df)
    collapsed_df = build_collapsed_category_summary(per_label_df)
    document_summary_df = pd.DataFrame(document_summary_rows)
    failures_df = pd.DataFrame(failed_documents)

    raw_xlsx = args.results_dir / "sonnet_raw.xlsx"
    metrics_xlsx = args.results_dir / "sonnet_metrics.xlsx"

    with pd.ExcelWriter(raw_xlsx, engine="openpyxl") as writer:
        raw_df.to_excel(writer, sheet_name="Raw_Results", index=False)

    with pd.ExcelWriter(metrics_xlsx, engine="openpyxl") as writer:
        pd.DataFrame([overall]).to_excel(writer, sheet_name="Overall", index=False)
        per_label_df.to_excel(writer, sheet_name="Per_Label", index=False)
        collapsed_df.to_excel(writer, sheet_name="Collapsed_Category", index=False)
        document_summary_df.to_excel(writer, sheet_name="Per_Document", index=False)
        failures_df.to_excel(writer, sheet_name="Failures", index=False)

    metadata = {
        "data_dir": str(args.data_dir),
        "results_dir": str(args.results_dir),
        "prompt_file": str(args.prompt_file),
        "prompt_variable": "P2_TAG",
        "prompt_sha256": prompt_hash,
        "provider": "elsa",
        "elsa_endpoint": elsa_endpoint,
        "elsa_model_id": elsa_model_id,
        "elsa_model_name": elsa_model_name,
        # Intentionally never persist ELSA_API_KEY or ELSA_API_NAME.
        "documents_requested": len(records),
        "documents_completed": len(document_summary_rows),
        "documents_failed": len(failed_documents),
        "mean_sequence_matcher_ratio": (
            round(sum(sequence_ratios) / len(sequence_ratios), 6)
            if sequence_ratios
            else None
        ),
        "gold_annotation_stats": dict(total_gold_stats),
        "overall_metrics": overall,
    }
    (args.results_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Run finished")
    logger.info("Completed=%d Failed=%d", len(document_summary_rows), len(failed_documents))
    logger.info("Overall: %s", overall)

    console_print("")
    console_print("=== CLAUDE SONNET FAERS EVALUATION ===")
    console_print(
        f"Documents: completed={len(document_summary_rows)} failed={len(failed_documents)}"
    )
    if sequence_ratios:
        console_print(
            f"Mean SequenceMatcher ratio: {sum(sequence_ratios) / len(sequence_ratios):.4f}"
        )
    console_print(
        f"Overall: P={overall['precision']:.4f} R={overall['recall']:.4f} "
        f"F1={overall['f1']:.4f} "
        f"(M={overall['M']}, C={overall['C']}, S={overall['S']}, N={overall['N']})"
    )
    console_print(f"Raw results: {raw_xlsx}")
    console_print(f"Metrics: {metrics_xlsx}")
    console_print(f"Predictions/cache: {predictions_path}")
    console_print(f"Log: {log_path}")


if __name__ == "__main__":
    main()
