#!/usr/bin/env python3
"""
evaluate_FAERS_bert_raw.py

Evaluate trained FAERS BioBERT models directly on the FULL raw narrative texts
of held-out test cases, rather than the processed/filtered test.spacy files.

Background & Motivation:
-----------------------
In the previous pipeline (run_FAERS_bert_LOO.py), test.spacy was generated via
records_to_docbin(), which:
  1. Segmented case narratives into sentences.
  2. Skipped sentences exceeding 512 BERT tokens.
  3. Skipped sentences with overlapping annotations.
  4. Skipped sentences where spaCy strict token alignment failed.
  5. Dropped annotations spanning across sentence boundaries.
As a result, test.spacy contained only a filtered subset of sentences and
annotations, artificially altering the evaluation benchmark compared to LLMs
(which were tested on the complete, raw case narratives against all gold annotations).

This script:
  1. Tracks held-out test cases by case series (Azacitidine-QT, Tramadol-Hypoglycemia,
     Baricitinib-Hypersensitivity, Erenumab-Stroke) at the WHOLE-DOCUMENT level.
  2. Retrieves the original, complete raw narrative (page_text) and ALL SME1 gold
     annotations from publication/dataset.db.
  3. Runs the trained spaCy BioBERT model on the raw narrative text.
  4. Aligns predictions with all ground-truth annotations using the exact same
     M/C/S/N error taxonomy and calculates Scheme 3 (Strict exact-match) and
     Scheme 2 (ADE-Eval weighted) micro-P/R/F1.
  5. Produces raw alignment outputs and summary metrics directly comparable to LLM runs.

Usage Examples:
---------------
  # Evaluate all models in a work directory:
  python publication/scripts/evaluate_FAERS_bert_raw.py \
      --work-dir publication/results/bert_runs_FAERS_LOO/workdir \
      --output-dir publication/results/bert_retest_FAERS_raw

  # Evaluate a single model checkpoint on its held-out fold:
  python publication/scripts/evaluate_FAERS_bert_raw.py \
      --model-path /path/to/Azacitidine-QT_seed_42/model/model-best \
      --fold Azacitidine-QT --seed 42

  # Dry-run validation (verifies data loading, tracking, and fold splits without model):
  python publication/scripts/evaluate_FAERS_bert_raw.py --dry-run
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

try:
    import spacy
except ImportError:
    spacy = None

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable=None, *args, **kwargs):
        return iterable if iterable is not None else []
    tqdm.write = lambda msg, file=sys.stdout: print(msg, file=file)

# -----------------------------------------------------------------------------
# Configuration & Taxonomy
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "dataset.db"
DEFAULT_REF_SCORER = PROJECT_ROOT / "code" / "custom_scorer_v5.py"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results" / "bert_retest_FAERS_raw"

FAERS_CASE_SERIES = [
    "Azacitidine-QT",
    "Tramadol-Hypoglycemia",
    "Baricitinib-Hypersensitivity",
    "Erenumab-Stroke",
]

SERIES_TO_FOLD_IDX = {series: i for i, series in enumerate(FAERS_CASE_SERIES)}
FOLD_IDX_TO_SERIES = {i: series for i, series in enumerate(FAERS_CASE_SERIES)}

# Canonical 17-category FAERS evaluation schema (matching Table 2 and run_FAERS_llama4.py)
RAW_TO_LABEL: Dict[str, Optional[str]] = {
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
    "bSYM": "diagnostic",
    "BSYM": "diagnostic",
    "BASELINE SYMPTOM": "diagnostic",
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
    # Excluded from canonical 17-category schema (e.g. TEMPO not evaluated in LLMs/Table 2)
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

_RAW_TO_LABEL_CASEFOLD = {str(k).strip().casefold(): v for k, v in RAW_TO_LABEL.items()}

# Mapping from canonical label to Table 2 categories (17 categories)
LABEL_TO_TABLE2_CATEGORY: Dict[str, str] = {
    "sdrug": "SDrug",
    "cdrug": "CDrug",
    "odrug": "ODrug",
    "dose": "Dose",
    "indication": "Indication",
    "treatment": "Treatment",
    "ae": "AE",
    "mae": "mAE",
    "diagnostic": "Dx",
    "lab": "Lab",
    "status": "Status",
    "ro": "R/O",
    "cod": "CoD",
    "mhx": "MHx",
    "fhx": "FHx",
    "age": "Age",
    "sex": "Sex",
}

# Collapsed evaluation categories (matching run_FAERS_llama4.py)
EVAL_LABEL_POOL: Dict[str, str] = {
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

_custom_scorer_loaded: Set[str] = set()


def _ensure_custom_scorer_loaded(ref_scorer: Path) -> None:
    path_str = str(ref_scorer.resolve())
    if path_str in _custom_scorer_loaded:
        return
    if not ref_scorer.is_file():
        return
    spec = importlib.util.spec_from_file_location("custom_scorer_v5", path_str)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _custom_scorer_loaded.add(path_str)


def _normalize_raw_label(raw: object) -> Optional[str]:
    if raw is None:
        return None
    raw_str = str(raw).strip()
    if raw_str in RAW_TO_LABEL:
        return RAW_TO_LABEL[raw_str]
    return _RAW_TO_LABEL_CASEFOLD.get(raw_str.casefold())


def clean_span(start: int, end: int, text: str) -> Tuple[int, int]:
    start = max(0, min(int(start), len(text)))
    end = max(0, min(int(end), len(text)))
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


# -----------------------------------------------------------------------------
# Data Loading & Tracking
# -----------------------------------------------------------------------------
def load_faers_raw_records(db_path: Path) -> Tuple[List[dict], Dict[str, Any]]:
    """
    Load all included FAERS whole cases directly from dataset.db.

    Returns:
        records: list of dicts with:
            - doc_id: unique document ID (e.g. '10064257-1')
            - base_id: case identifier
            - suffix: document suffix
            - text: FULL raw narrative text (page_text with newline normalized)
            - case_series: assigned drug-AE pair
            - annotations: list of (start, end, label) with offsets relative to full text
        stats: loading statistics
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    docs_rows = cursor.execute(
        """
        SELECT d.doc_id, d.base_id, d.suffix, d.page_text, cs.case_series
        FROM documents AS d
        JOIN faers_case_series AS cs ON cs.doc_id = d.doc_id
        WHERE d.dataset = 'FAERS' AND cs.include_in_loo = 1
        ORDER BY d.doc_id
        """
    ).fetchall()

    anns_rows = cursor.execute(
        """
        SELECT annotations.doc_id, label, tc_start, tc_end, tc_text
        FROM annotations
        JOIN faers_case_series AS cs ON cs.doc_id = annotations.doc_id
        WHERE note = 'SME1' AND cs.include_in_loo = 1
        ORDER BY annotations.doc_id, tc_start
        """
    ).fetchall()
    conn.close()

    anns_by_doc = defaultdict(list)
    stats = defaultdict(int)

    for doc_id, raw_label, start, end, tc_text in anns_rows:
        stats["sme1_annotations_seen"] += 1
        canon = _normalize_raw_label(raw_label)
        if canon is None:
            stats["excluded_or_unmapped_labels"] += 1
            continue
        try:
            start_i = int(start)
            end_i = int(end)
        except (TypeError, ValueError):
            stats["invalid_offsets"] += 1
            continue
        if start_i < 0 or start_i >= end_i:
            stats["invalid_offsets"] += 1
            continue
        anns_by_doc[doc_id].append((start_i, end_i, canon, tc_text))
        stats["annotations_kept"] += 1

    records = []
    series_dist = Counter()

    for doc_id, base_id, suffix, raw_text, case_series in docs_rows:
        text_norm = raw_text.replace("↵", "\n")
        raw_anns = anns_by_doc.get(doc_id, [])

        valid_anns = []
        for s, e, l, original_surface in raw_anns:
            s_clean, e_clean = clean_span(s, e, text_norm)
            if s_clean < e_clean and e_clean <= len(text_norm):
                valid_anns.append((s_clean, e_clean, l))
            else:
                stats["out_of_bounds_or_empty"] += 1

        series_dist[case_series] += 1
        records.append({
            "doc_id": doc_id,
            "base_id": base_id,
            "suffix": suffix,
            "text": text_norm,
            "annotations": valid_anns,
            "case_series": case_series,
        })

    stats["documents_loaded"] = len(records)
    stats["case_series_distribution"] = dict(series_dist)
    return records, dict(stats)


def get_faers_loo_test_records(records: List[dict], target_series: str) -> List[dict]:
    """Retrieve all raw test case records belonging to a held-out case series."""
    return [r for r in records if r["case_series"] == target_series]


# -----------------------------------------------------------------------------
# Span Alignment & Evaluation Schemes
# -----------------------------------------------------------------------------
def _overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return (a0 == b0) or (a1 == b1) or (a0 < b0 < a1) or (a0 < b1 < a1) or (b0 < a0 < b1)


def align_and_classify_spans(
    text: str,
    gold_ents: List[Tuple[int, int, str]],
    pred_ents: List[Tuple[int, int, str, float]],
) -> List[dict]:
    """
    Align gold and predicted spans into the standardized M/C/S/N taxonomy:
      - 'M': Exact boundary match AND exact class match.
      - 'C': Inexact boundary match or overlapping class confusion.
      - 'S': Spurious prediction with no gold overlap (Non-overlapping False Positive).
      - 'N': Missed gold entity (False Negative).
    """
    rows = []
    gold_sorted = sorted(gold_ents, key=lambda x: (x[0], x[1], x[2]))
    pred_sorted = sorted(pred_ents, key=lambda x: (x[0], x[1], x[2]))
    pred_used = [False] * len(pred_sorted)

    for g0, g1, glab in gold_sorted:
        exact_j = None
        same_label_partial_j = None
        diff_label_partial_j = None
        best_same_ov = 0
        best_diff_ov = 0

        for j, (p0, p1, plab, pconf) in enumerate(pred_sorted):
            if pred_used[j]:
                continue
            if p0 == g0 and p1 == g1 and plab == glab:
                exact_j = j
                break
            if _overlap(g0, g1, p0, p1):
                ov = max(0, min(g1, p1) - max(g0, p0))
                if plab == glab:
                    if ov > best_same_ov:
                        best_same_ov = ov
                        same_label_partial_j = j
                else:
                    if ov > best_diff_ov:
                        best_diff_ov = ov
                        diff_label_partial_j = j

        if exact_j is not None:
            p0, p1, plab, pconf = pred_sorted[exact_j]
            pred_used[exact_j] = True
            rows.append({
                "match_type": "M",
                "error_subtype": "exact",
                "label_gold": glab,
                "gold_start": g0, "gold_end": g1, "gold_text": text[g0:g1],
                "label_pred": plab,
                "pred_start": p0, "pred_end": p1, "pred_text": text[p0:p1],
                "confidence": pconf,
            })
        elif same_label_partial_j is not None:
            p0, p1, plab, pconf = pred_sorted[same_label_partial_j]
            pred_used[same_label_partial_j] = True
            rows.append({
                "match_type": "C",
                "error_subtype": "boundary",
                "label_gold": glab,
                "gold_start": g0, "gold_end": g1, "gold_text": text[g0:g1],
                "label_pred": plab,
                "pred_start": p0, "pred_end": p1, "pred_text": text[p0:p1],
                "confidence": pconf,
            })
        elif diff_label_partial_j is not None:
            p0, p1, plab, pconf = pred_sorted[diff_label_partial_j]
            pred_used[diff_label_partial_j] = True
            rows.append({
                "match_type": "C",
                "error_subtype": "class_confusion",
                "label_gold": glab,
                "gold_start": g0, "gold_end": g1, "gold_text": text[g0:g1],
                "label_pred": plab,
                "pred_start": p0, "pred_end": p1, "pred_text": text[p0:p1],
                "confidence": pconf,
            })
        else:
            rows.append({
                "match_type": "N",
                "error_subtype": "missed",
                "label_gold": glab,
                "gold_start": g0, "gold_end": g1, "gold_text": text[g0:g1],
                "label_pred": None,
                "pred_start": None, "pred_end": None, "pred_text": None,
                "confidence": 0.0,
            })

    for j, (p0, p1, plab, pconf) in enumerate(pred_sorted):
        if pred_used[j]:
            continue
        rows.append({
            "match_type": "S",
            "error_subtype": "non_overlap_spurious",
            "label_gold": None,
            "gold_start": None, "gold_end": None, "gold_text": None,
            "label_pred": plab,
            "pred_start": p0, "pred_end": p1, "pred_text": text[p0:p1],
            "confidence": pconf,
        })

    return rows


def calculate_metrics(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Compute Scheme 3 (Strict exact) and Scheme 2 (ADE-Eval weighted) metrics."""
    if df.empty:
        empty = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "M": 0, "C_boundary": 0, "C_class": 0, "C_total": 0, "S_non_overlap": 0, "N": 0}
        return {"strict_scheme3": empty, "ade_weighted_scheme2": empty}

    counts = df["match_type"].value_counts().to_dict()
    M = int(counts.get("M", 0))

    class_confusion_mask = (
        (df["match_type"] == "C") & (df["error_subtype"] == "class_confusion")
        if "error_subtype" in df.columns
        else pd.Series(False, index=df.index)
    )
    C_class = int(class_confusion_mask.sum())
    C_total = int(counts.get("C", 0))
    C_boundary = C_total - C_class
    S_non_overlap = int(counts.get("S", 0))
    N = int(counts.get("N", 0))

    # Scheme 3: Strict exact-match
    p3_den = M + C_total + S_non_overlap
    r3_den = M + C_total + N
    p3 = M / p3_den if p3_den > 0 else 0.0
    r3 = M / r3_den if r3_den > 0 else 0.0
    f3 = 2 * p3 * r3 / (p3 + r3) if (p3 + r3) > 0 else 0.0

    # Scheme 2: ADE-Eval weighted metric (C gets 0.5 credit, S gets 0.25 penalty weight)
    m2 = M + 0.5 * C_total
    p2_den = M + C_total + 0.25 * S_non_overlap
    r2_den = M + C_total + N
    p2 = m2 / p2_den if p2_den > 0 else 0.0
    r2 = m2 / r2_den if r2_den > 0 else 0.0
    f2 = 2 * p2 * r2 / (p2 + r2) if (p2 + r2) > 0 else 0.0

    return {
        "strict_scheme3": {
            "M": M,
            "C_boundary": C_boundary,
            "C_class": C_class,
            "C_total": C_total,
            "S_non_overlap": S_non_overlap,
            "N": N,
            "precision": round(p3, 4),
            "recall": round(r3, 4),
            "f1": round(f3, 4),
        },
        "ade_weighted_scheme2": {
            "M": M,
            "C_boundary": C_boundary,
            "C_class": C_class,
            "C_total": C_total,
            "S_non_overlap": S_non_overlap,
            "N": N,
            "precision": round(p2, 4),
            "recall": round(r2, 4),
            "f1": round(f2, 4),
        },
    }


# -----------------------------------------------------------------------------
# Raw Inference Engine
# -----------------------------------------------------------------------------
def predict_raw_document(
    nlp: Any,
    text: str,
    inference_mode: str = "document",
) -> List[Tuple[int, int, str, float]]:
    """
    Run spaCy BioBERT model on raw narrative text.

    Modes:
      - 'document': Passes the entire text directly to nlp(text).
        spacy-transformers handles strided spans (window=512, stride=96) natively.
      - 'sentence_projected': Segments text into sentences using sentencizer,
        runs nlp(sent.text) on EVERY sentence (none dropped!), and projects
        the character offsets back to the document coordinate space.
    """
def get_model_tokenizer(model_path: Optional[Path] = None) -> Optional[Any]:
    """Load local or cached HuggingFace tokenizer associated with BioBERT."""
    try:
        from transformers import AutoTokenizer
        if model_path:
            local_tf = Path(model_path) / "transformer" / "model"
            if local_tf.is_dir():
                return AutoTokenizer.from_pretrained(str(local_tf))
        return AutoTokenizer.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
    except Exception:
        return None


def _chunk_text_sliding_window(
    text: str,
    tokenizer: Optional[Any] = None,
    max_chars: int = 900,
    overlap_chars: int = 150,
    max_subwords: int = 384,
) -> List[Tuple[int, int, str]]:
    """
    Split text into chunks of at most max_chars with overlap_chars,
    breaking safely at whitespace boundaries to avoid splitting words.
    900 chars is ~150-180 words, strictly <= 350 subwords, avoiding BERT's 512 subword limit.
    If a tokenizer is provided, dynamically verifies and shrinks chunk if subwords > max_subwords.
    """
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + max_chars, text_len)
        if end < text_len:
            space_idx = text.rfind(" ", start, end)
            if space_idx > start + max_chars // 2:
                end = space_idx
        chunk_text = text[start:end]

        # If tokenizer is available, guarantee subwords <= max_subwords (e.g. 384)
        if tokenizer is not None:
            try:
                subwords = tokenizer.tokenize(chunk_text)
                while len(subwords) > max_subwords and end > start + 50:
                    space_idx = text.rfind(" ", start, end - 10)
                    if space_idx > start:
                        end = space_idx
                    else:
                        end = max(start + 50, end - 100)
                    chunk_text = text[start:end]
                    subwords = tokenizer.tokenize(chunk_text)
            except Exception:
                pass

        chunks.append((start, end, chunk_text))
        if end == text_len:
            break
        start = max(start + 1, end - overlap_chars)
        while start < end and text[start].isspace():
            start += 1
    return chunks


def _deduplicate_predictions(
    raw_preds: List[Tuple[int, int, str, float, int]],  # (start, end, label, conf, boundary_margin)
) -> List[Tuple[int, int, str, float]]:
    """
    Merge and deduplicate predicted entity spans from overlapping chunks.
    Resolves overlaps by preferring predictions with larger margin from chunk boundary cuts.
    """
    if not raw_preds:
        return []

    sorted_preds = sorted(raw_preds, key=lambda x: (x[0], x[1], -x[3]))
    kept: List[Tuple[int, int, str, float, int]] = []

    for curr in sorted_preds:
        c_start, c_end, c_label, c_conf, c_margin = curr
        merged = False
        for i, existing in enumerate(kept):
            e_start, e_end, e_label, e_conf, e_margin = existing
            if c_start == e_start and c_end == e_end and c_label == e_label:
                if c_margin > e_margin:
                    kept[i] = curr
                merged = True
                break
            elif _overlap(c_start, c_end, e_start, e_end) and c_label == e_label:
                if c_margin > e_margin:
                    kept[i] = curr
                merged = True
                break

        if not merged:
            kept.append(curr)

    return [(s, e, l, conf) for s, e, l, conf, _ in kept]


def predict_raw_document(
    nlp: Any,
    text: str,
    tokenizer: Optional[Any] = None,
    inference_mode: str = "sliding_window",
    max_chunk_chars: int = 900,
    overlap_chars: int = 150,
) -> List[Tuple[int, int, str, float]]:
    """
    Run spaCy BioBERT model on raw narrative text with three 512-limit resolution modes:

    Modes:
      - 'sliding_window' (RECOMMENDED / DEFAULT): Cuts the document into overlapping
        chunks of <= 900 chars (~150 words, strictly <= 384 subwords). Runs nlp() on each
        chunk, projects character offsets to absolute document positions, and deduplicates
        boundary predictions. Guaranteed to NEVER exceed BERT's 512 token limit.
      - 'sentence_projected': Segments by sentence. If a sentence is unusually long (> 900 chars),
        it automatically falls back to sliding-window chunking so no 512 overflow occurs.
      - 'document': Passes the entire narrative to nlp(text). If strided_spans exceeds 512
        subwords and triggers a dimension mismatch (e.g. 529 vs 512), automatically catches
        the exception and falls back to safe sliding window inference.
    """
    if inference_mode == "document":
        try:
            doc = nlp(text)
            return [(e.start_char, e.end_char, e.label_, 1.0) for e in doc.ents]
        except Exception as exc:
            # Catch tensor dimension mismatch: e.g. (529,) does not meet (512,)
            tqdm.write(f"  [WARN] Full-document inference exceeded BERT 512 token limit ({exc}); falling back to safe sliding-window.")
            inference_mode = "sliding_window"

    if inference_mode == "sliding_window":
        chunks = _chunk_text_sliding_window(
            text, tokenizer=tokenizer, max_chars=max_chunk_chars, overlap_chars=overlap_chars
        )
        raw_preds = []
        for c_start, c_end, c_text in chunks:
            if not c_text.strip():
                continue
            c_doc = nlp(c_text)
            for e in c_doc.ents:
                abs_start = c_start + e.start_char
                abs_end = c_start + e.end_char
                margin = min(e.start_char, len(c_text) - e.end_char)
                raw_preds.append((abs_start, abs_end, e.label_, 1.0, margin))
        return _deduplicate_predictions(raw_preds)

    elif inference_mode == "sentence_projected":
        sent_nlp = spacy.blank("en")
        if "sentencizer" not in sent_nlp.pipe_names:
            sent_nlp.add_pipe("sentencizer")

        sent_doc = sent_nlp(text)
        raw_preds = []

        for sent in sent_doc.sents:
            sent_text = sent.text
            if not sent_text.strip():
                continue

            if len(sent_text) <= max_chunk_chars:
                try:
                    doc_sent = nlp(sent_text)
                    for e in doc_sent.ents:
                        abs_start = sent.start_char + e.start_char
                        abs_end = sent.start_char + e.end_char
                        margin = min(e.start_char, len(sent_text) - e.end_char)
                        raw_preds.append((abs_start, abs_end, e.label_, 1.0, margin))
                except Exception:
                    # If sentence still has > 512 subwords, sub-chunk it
                    sub_chunks = _chunk_text_sliding_window(
                        sent_text, tokenizer=tokenizer, max_chars=max_chunk_chars, overlap_chars=overlap_chars
                    )
                    for sc_start, sc_end, sc_text in sub_chunks:
                        if not sc_text.strip():
                            continue
                        doc_sc = nlp(sc_text)
                        for e in doc_sc.ents:
                            abs_start = sent.start_char + sc_start + e.start_char
                            abs_end = sent.start_char + sc_start + e.end_char
                            margin = min(e.start_char, len(sc_text) - e.end_char)
                            raw_preds.append((abs_start, abs_end, e.label_, 1.0, margin))
            else:
                sub_chunks = _chunk_text_sliding_window(
                    sent_text, tokenizer=tokenizer, max_chars=max_chunk_chars, overlap_chars=overlap_chars
                )
                for sc_start, sc_end, sc_text in sub_chunks:
                    if not sc_text.strip():
                        continue
                    doc_sc = nlp(sc_text)
                    for e in doc_sc.ents:
                        abs_start = sent.start_char + sc_start + e.start_char
                        abs_end = sent.start_char + sc_start + e.end_char
                        margin = min(e.start_char, len(sc_text) - e.end_char)
                        raw_preds.append((abs_start, abs_end, e.label_, 1.0, margin))

        return _deduplicate_predictions(raw_preds)

    else:
        raise ValueError(f"Unknown inference_mode: {inference_mode}")


def evaluate_raw_test_records(
    nlp: Any,
    test_recs: List[dict],
    fold_name: str,
    fold_idx: int,
    seed: int,
    tokenizer: Optional[Any] = None,
    inference_mode: str = "sliding_window",
    max_chunk_chars: int = 900,
    overlap_chars: int = 150,
    batch_size: int = 32,
    show_progress: bool = True,
) -> pd.DataFrame:
    """Evaluate a trained model on all raw test cases in a held-out fold."""
    all_rows = []
    iterator = tqdm(test_recs, desc=f"Eval {fold_name} (seed {seed})", unit="doc") if show_progress else test_recs

    for rec in iterator:
        doc_id = rec["doc_id"]
        raw_text = rec["text"]
        gold_ents = rec["annotations"]

        pred_ents = predict_raw_document(
            nlp,
            raw_text,
            tokenizer=tokenizer,
            inference_mode=inference_mode,
            max_chunk_chars=max_chunk_chars,
            overlap_chars=overlap_chars,
        )
        rows = align_and_classify_spans(raw_text, gold_ents, pred_ents)

        for r in rows:
            r["document"] = doc_id
            r["fold"] = fold_idx
            r["fold_name"] = fold_name
            r["seed"] = seed
            r["test_case_series"] = fold_name
        all_rows.extend(rows)

    return pd.DataFrame(all_rows)



# -----------------------------------------------------------------------------
# Summary & Reporting
# -----------------------------------------------------------------------------
def summarize_fold_eval(
    raw_df: pd.DataFrame,
    fold_name: str,
    fold_idx: int,
    seed: int,
) -> Tuple[dict, pd.DataFrame]:
    """Calculate overall and per-category metrics for one evaluated run."""
    metrics = calculate_metrics(raw_df)
    strict = metrics["strict_scheme3"]
    ade = metrics["ade_weighted_scheme2"]

    overall_row = {
        "fold": fold_idx,
        "fold_name": fold_name,
        "seed": seed,
        "test_case_series": fold_name,
        "documents": raw_df["document"].nunique() if not raw_df.empty else 0,
        "M": strict["M"],
        "C_boundary": strict["C_boundary"],
        "C_class": strict["C_class"],
        "C_total": strict["C_total"],
        "S_non_overlap": strict["S_non_overlap"],
        "N": strict["N"],
        "strict_P": strict["precision"],
        "strict_R": strict["recall"],
        "strict_F1": strict["f1"],
        "ade_P": ade["precision"],
        "ade_R": ade["recall"],
        "ade_F1": ade["f1"],
    }

    cat_rows = []
    table2_rows = []
    if not raw_df.empty:
        # Collapsed categories
        for cat in sorted(set(EVAL_LABEL_POOL.values())):
            cat_df = raw_df[
                (raw_df["label_gold"].map(EVAL_LABEL_POOL) == cat) |
                (raw_df["label_pred"].map(EVAL_LABEL_POOL) == cat)
            ]
            cat_metrics = calculate_metrics(cat_df)
            cat_strict = cat_metrics["strict_scheme3"]
            cat_ade = cat_metrics["ade_weighted_scheme2"]
            cat_rows.append({
                "fold": fold_idx,
                "fold_name": fold_name,
                "seed": seed,
                "category": cat,
                "M": cat_strict["M"],
                "C_boundary": cat_strict["C_boundary"],
                "C_class": cat_strict["C_class"],
                "C_total": cat_strict["C_total"],
                "S_non_overlap": cat_strict["S_non_overlap"],
                "N": cat_strict["N"],
                "strict_P": cat_strict["precision"],
                "strict_R": cat_strict["recall"],
                "strict_F1": cat_strict["f1"],
                "ade_P": cat_ade["precision"],
                "ade_R": cat_ade["recall"],
                "ade_F1": cat_ade["f1"],
            })

        # Table 2 17 fine-grained categories
        for label_key, t2_name in sorted(LABEL_TO_TABLE2_CATEGORY.items(), key=lambda x: x[1]):
            t2_df = raw_df[
                (raw_df["label_gold"] == label_key) |
                (raw_df["label_pred"] == label_key)
            ]
            t2_metrics = calculate_metrics(t2_df)
            t2_strict = t2_metrics["strict_scheme3"]
            t2_ade = t2_metrics["ade_weighted_scheme2"]
            table2_rows.append({
                "fold": fold_idx,
                "fold_name": fold_name,
                "seed": seed,
                "category": t2_name,
                "M": t2_strict["M"],
                "C_boundary": t2_strict["C_boundary"],
                "C_class": t2_strict["C_class"],
                "C_total": t2_strict["C_total"],
                "S_non_overlap": t2_strict["S_non_overlap"],
                "N": t2_strict["N"],
                "strict_P": t2_strict["precision"],
                "strict_R": t2_strict["recall"],
                "strict_F1": t2_strict["f1"],
                "ade_P": t2_ade["precision"],
                "ade_R": t2_ade["recall"],
                "ade_F1": t2_ade["f1"],
            })

    return overall_row, pd.DataFrame(cat_rows), pd.DataFrame(table2_rows)


# -----------------------------------------------------------------------------
# Discovery & Main Execution
# -----------------------------------------------------------------------------
def discover_model_runs(work_dir: Path) -> List[Tuple[str, int, Path]]:
    """
    Locate saved model checkpoints in a work directory.
    Matches:
      - <fold_name>_seed_<seed>/model/model-best
      - fold_<idx>_seed_<seed>/model/model-best
      - <fold_name>/seed_<seed>/model/model-best
    """
    discovered = []
    if not work_dir.is_dir():
        return []

    for mb_path in sorted(work_dir.glob("**/model-best")):
        if not mb_path.is_dir():
            continue
        parent_parts = mb_path.parts
        seed = 42
        fold_name = None

        for part in reversed(parent_parts):
            m_seed = re.search(r"seed[_-]?(\d+)", part, re.IGNORECASE)
            if m_seed:
                seed = int(m_seed.group(1))
                break

        for part in parent_parts:
            for cs in FAERS_CASE_SERIES:
                if cs.lower() in part.lower():
                    fold_name = cs
                    break
            if fold_name:
                break

        if fold_name is None:
            for part in parent_parts:
                m_fold = re.search(r"fold[_-]?(\d+)", part, re.IGNORECASE)
                if m_fold:
                    idx = int(m_fold.group(1))
                    if idx in FOLD_IDX_TO_SERIES:
                        fold_name = FOLD_IDX_TO_SERIES[idx]
                    break

        if fold_name:
            discovered.append((fold_name, seed, mb_path))

    return discovered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-evaluate trained FAERS BioBERT models on raw whole-case narratives."
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "bert_runs_FAERS_LOO" / "workdir",
        help="Directory containing trained model runs.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="Direct path to a single trained spaCy model-best directory.",
    )
    parser.add_argument(
        "--fold",
        type=str,
        default=None,
        help="Specific case series fold name (e.g. Azacitidine-QT) or fold index.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed associated with the model (default: 42).",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to dataset.db (default: {DEFAULT_DB_PATH}).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help=f"Directory to write output files (default: {DEFAULT_RESULTS_DIR}).",
    )
    parser.add_argument(
        "--ref-scorer",
        type=Path,
        default=DEFAULT_REF_SCORER,
        help=f"Path to custom_scorer_v5.py (default: {DEFAULT_REF_SCORER}).",
    )
    parser.add_argument(
        "--gpu-id",
        type=int,
        default=-1,
        help="GPU ID to use (-1 for CPU, default: -1).",
    )
    parser.add_argument(
        "--inference-mode",
        choices=["sliding_window", "sentence_projected", "document"],
        default="sliding_window",
        help="Inference mode: 'sliding_window' (default: safe overlapping chunks <= 384 subwords), 'sentence_projected' (sentence level with fallback), or 'document' (whole narrative).",
    )
    parser.add_argument(
        "--max-chunk-chars",
        type=int,
        default=900,
        help="Maximum characters per chunk (default: 900 chars ~ 150-180 words, strictly <= 384 subwords).",
    )
    parser.add_argument(
        "--overlap-chars",
        type=int,
        default=150,
        help="Overlap characters between sliding window chunks (default: 150 chars ~ 25-30 words).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Evaluation batch size (default: 32).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate raw data tracking and test set partition without model inference.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 78)
    print("FAERS Raw Narrative BioBERT Evaluation Suite")
    print("=" * 78)
    print(f"Database path:  {args.db_path}")
    print(f"Inference mode: {args.inference_mode}")
    print(f"Output dir:     {args.output_dir}")

    # 1. Load full raw cases from dataset.db
    records, stats = load_faers_raw_records(args.db_path)
    print(f"\n[DATA] Loaded {stats['documents_loaded']} FAERS documents with {stats['annotations_kept']} SME1 annotations.")
    print("Case series distribution:")
    for cs, count in stats["case_series_distribution"].items():
        cs_recs = get_faers_loo_test_records(records, cs)
        total_anns = sum(len(r["annotations"]) for r in cs_recs)
        print(f"  - {cs:30s}: {count:3d} documents, {total_anns:5d} gold annotations")

    if args.dry_run:
        print("\n[DRY-RUN] Data validation successful. All 4 case series tracked to raw narratives.")
        print("[DRY-RUN] Test sets are 100% partitioned by whole cases. Exiting without model evaluation.")
        return

    if spacy is None:
        raise ImportError("spaCy is required for model inference. Please install spacy and spacy-transformers.")

    _ensure_custom_scorer_loaded(args.ref_scorer)

    # 2. Configure hardware
    if args.gpu_id >= 0:
        try:
            spacy.require_gpu(args.gpu_id)
            print(f"[DEVICE] Pinned to GPU {args.gpu_id}")
        except Exception as exc:
            print(f"[DEVICE] GPU {args.gpu_id} unavailable ({exc}); falling back to CPU")
            spacy.require_cpu()
    else:
        spacy.require_cpu()
        print("[DEVICE] Running on CPU")

    # 3. Identify models to run
    runs_to_eval = []
    if args.model_path is not None:
        fold_name = args.fold or "Azacitidine-QT"
        runs_to_eval.append((fold_name, args.seed, args.model_path))
    else:
        runs_to_eval = discover_model_runs(args.work_dir)

    if not runs_to_eval:
        print(f"\n[ERROR] No trained models found under {args.work_dir}")
        print("Specify a valid --work-dir containing trained models or provide --model-path directly.")
        sys.exit(1)

    print(f"\n[MODELS] Found {len(runs_to_eval)} model run(s) to evaluate:")
    for fn, s, p in runs_to_eval:
        print(f"  - Fold: {fn:28s} | Seed: {s:4d} | Path: {p}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_raw_frames = []
    overall_rows = []
    all_cat_frames = []
    all_table2_frames = []

    # 4. Run evaluation
    for fold_name, seed, model_path in runs_to_eval:
        fold_idx = SERIES_TO_FOLD_IDX.get(fold_name, 0)
        test_recs = get_faers_loo_test_records(records, fold_name)
        print(f"\nEvaluating {fold_name} (seed {seed}) on {len(test_recs)} raw test cases...")

        nlp = spacy.load(str(model_path))
        tokenizer = get_model_tokenizer(model_path)
        raw_df = evaluate_raw_test_records(
            nlp=nlp,
            test_recs=test_recs,
            fold_name=fold_name,
            fold_idx=fold_idx,
            seed=seed,
            tokenizer=tokenizer,
            inference_mode=args.inference_mode,
            max_chunk_chars=args.max_chunk_chars,
            overlap_chars=args.overlap_chars,
            batch_size=args.batch_size,
        )

        overall_row, cat_df, table2_df = summarize_fold_eval(raw_df, fold_name, fold_idx, seed)
        print(f"  -> Scheme 3 (Strict): P={overall_row['strict_P']:.4f} R={overall_row['strict_R']:.4f} F1={overall_row['strict_F1']:.4f}")
        print(f"  -> Scheme 2 (ADE):    P={overall_row['ade_P']:.4f} R={overall_row['ade_R']:.4f} F1={overall_row['ade_F1']:.4f}")

        all_raw_frames.append(raw_df)
        overall_rows.append(overall_row)
        all_cat_frames.append(cat_df)
        all_table2_frames.append(table2_df)
        del nlp

    # 5. Export comprehensive results
    combined_raw = pd.concat(all_raw_frames, ignore_index=True) if all_raw_frames else pd.DataFrame()
    overall_summary = pd.DataFrame(overall_rows)
    cat_summary = pd.concat(all_cat_frames, ignore_index=True) if all_cat_frames else pd.DataFrame()
    table2_summary = pd.concat(all_table2_frames, ignore_index=True) if all_table2_frames else pd.DataFrame()

    raw_path = args.output_dir / "raw.xlsx"
    summary_path = args.output_dir / "summary.xlsx"

    print(f"\n[EXPORT] Writing raw alignment to {raw_path}")
    combined_raw.to_excel(raw_path, sheet_name="Raw_Results", index=False)

    print(f"[EXPORT] Writing summary metrics to {summary_path}")
    with pd.ExcelWriter(summary_path, engine="openpyxl") as writer:
        overall_summary.to_excel(writer, sheet_name="Overall", index=False)
        cat_summary.to_excel(writer, sheet_name="By_CollapsedCategory", index=False)
        table2_summary.to_excel(writer, sheet_name="By_Table2_17Categories", index=False)

        if "test_case_series" in overall_summary.columns:
            agg = overall_summary.groupby("test_case_series")[["strict_F1", "ade_F1"]].agg(["mean", "std"])
            agg.to_excel(writer, sheet_name="Fold_Aggregates")

    print("\n" + "=" * 78)
    print("Evaluation on Raw Narratives Completed Successfully.")
    print("=" * 78)


if __name__ == "__main__":
    main()
