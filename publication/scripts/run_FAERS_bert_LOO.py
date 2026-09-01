#!/usr/bin/env python3
"""
run_FAERS_bert_LOO.py

High-Throughput Parallel BioBERT Evaluation Suite for FAERS Clinical Concept Extraction,
addressing key methodological requirements for Drug Safety:

Key Methodological Capabilities:
  1. Leave-One-Drug-AE-Pair-Out (LOO) 4-Fold Cross-Validation:
     - Evaluates true out-of-distribution (OOD) generalization across the 4 FAERS case series:
       * Azacitidine – QT prolongation
       * Tramadol – hypoglycemia
       * Baricitinib – hypersensitivity
       * Erenumab – stroke
     - Guarantees cluster integrity (same case / duplicate never crosses train/test).
  2. Multi-Seed Replication:
     - Runs multiple independent random initialization seeds (default: 5 seeds) per fold.
     - Quantifies seed variance (stochastic optimization) vs. fold variance (data sampling).
  3. Disjoint Stratified K-Fold CV Mode (--mode cv):
     - Enables direct quantification of the In-Distribution (CV) vs. Out-of-Distribution (LOO)
       generalization gap.
  4. Multi-Scheme Evaluation & Compliant Terminology:
     - Scheme 3 (Primary): Strict exact-match micro-P/R/F1.
     - Scheme 2 (Secondary Clinical): ADE-Eval back-office weighted micro-P/R/F1.
     - Scheme 1 (Supplementary): Relaxed entity detection micro-P/R/F1.
     - Error accounting: uses M/C/S/N, where overlapping class confusions are C
       (with ``error_subtype=class_confusion``) and S is non-overlapping only.
  5. Multi-GPU True Concurrent Parallel Architecture:
     - Spawns independent concurrent worker processes across all specified GPUs (--gpu-ids 0 1 2 3 4 5 6).
     - Dynamic task queue automatically load-balances folds and seeds across GPUs.
     - Supports --workers-per-gpu (e.g. 2 workers per 32GB GPU for 14 concurrent training runs).
     - Tuned batch sizes (--batch-size 64, --max-batch-items 8192, --eval-batch-size 64) for maximum throughput.
  6. Statistical Uncertainty:
     - Document-level paired bootstrap (1000 resamples) computing 95% Confidence Intervals (CIs).

Usage Examples:
  # Run 4 LOO folds x 5 seeds across 7 GPUs concurrently in parallel:
  python publication/scripts/run_FAERS_bert_LOO.py --mode loo --gpu-ids 0 1 2 3 4 5 6 --seeds 42 123 456 789 1011

  # High-throughput mode with 2 workers per 32GB GPU (14 parallel training runs):
  python publication/scripts/run_FAERS_bert_LOO.py --mode loo --gpu-ids 0 1 2 3 4 5 6 --workers-per-gpu 2

  # Standard 10-fold CV x 5 seeds on 7 GPUs (50 runs total):
  python publication/scripts/run_FAERS_bert_LOO.py --mode cv --folds 10 --gpu-ids 0 1 2 3 4 5 6

  # Single GPU / Quick Debug Run:
  python publication/scripts/run_FAERS_bert_LOO.py --mode loo --max-steps 100 --seeds 42 --gpu-ids 0

  # Re-evaluate already-trained cloud runs; this never calls spaCy training:
  python publication/scripts/run_FAERS_bert_LOO.py --export-existing \
      --existing-work-dir /path/to/bert_runs_FAERS_LOO/workdir
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import multiprocessing as mp
import os
import queue
import random
import re
import sqlite3
import subprocess
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

try:
    import spacy
    from spacy.tokens import DocBin
    from spacy.util import filter_spans
except ImportError:
    spacy = None
    DocBin = None
    filter_spans = None

_nlp_sent = None

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable=None, *args, **kwargs):
        return iterable if iterable is not None else []
    tqdm.write = lambda msg, file=sys.stdout: print(msg, file=file)

# -----------------------------------------------------------------------------
# Configuration & Paths
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "dataset.db"
DEFAULT_DATA_DIR = PROJECT_ROOT / "Datasets" / "FAERS_D1_clean"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results" / "bert_runs_FAERS_LOO"
# Saved models retain this registry reference in config.cfg.  Keep the scorer
# with the repository so ``--export-existing`` can load cloud-trained models.
DEFAULT_REF_SCORER = PROJECT_ROOT / "code" / "custom_scorer_v5.py"
DEFAULT_TRAIN_PYTHON = sys.executable

_BERT_MODEL_NAME = "dmis-lab/biobert-base-cased-v1.1"
_BERT_MAX_TOKENS = 512

# ANSI escape filtering
_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_C0_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Lazy process-local singletons
_tokenizer = None
_custom_scorer_loaded: Set[str] = set()

# -----------------------------------------------------------------------------
# Drug-AE Case Series Definitions for FAERS
# -----------------------------------------------------------------------------
FAERS_CASE_SERIES = [
    "Azacitidine-QT",
    "Tramadol-Hypoglycemia",
    "Baricitinib-Hypersensitivity",
    "Erenumab-Stroke",
]

CASE_SERIES_KEYWORDS = {
    "Azacitidine-QT": {
        "drugs": ["azacitidine", "vidaza", "5-aza", "azacytidine", "aza"],
        "aes": ["qt", "torsade", "ventricular", "cardiac", "arrhythmia", "ecg", "electrocardiogram", "prolongation", "myelodysplastic", "raeb", "leukemia", "aml"],
    },
    "Tramadol-Hypoglycemia": {
        "drugs": ["tramadol", "ultram", "tramacet", "ixprim", "trarmadol", "tremadol", "tramal", "zydol"],
        "aes": ["hypoglyc", "glucose", "glycemia", "sweating", "coma", "blood sugar", "insulin"],
    },
    "Baricitinib-Hypersensitivity": {
        "drugs": ["baricitinib", "olumiant", "barcitinib", "olimiant"],
        "aes": ["hypersensitiv", "allergic", "allergy", "anaphylax", "rash", "urticaria", "hives", "swelling", "angioedema", "face swollen", "lip", "tongue", "erythema", "pruritus", "dermatitis", "rheumatoid", "arthritis"],
    },
    "Erenumab-Stroke": {
        "drugs": ["erenumab", "aimovig"],
        "aes": ["stroke", "cva", "cerebrovascular", "ischemi", "infarct", "transient ischemic", "tia", "migraine", "headache", "hemiplegia"],
    },
}

# -----------------------------------------------------------------------------
# Label normalization & Taxonomy
# -----------------------------------------------------------------------------
RAW_TO_LABEL = {
    "ae": "ae",
    "mae": "mae",
    "mAE": "mae",
    "MAE": "mae",
    "TEMPO": "temporal",
    "tempo": "temporal",
    "sDrug": "sdrug",
    "SDRUG": "sdrug",
    "cDrug": "cdrug",
    "CDRUG": "cdrug",
    "oDrug": "odrug",
    "ODRUG": "odrug",
    "Drug": "drug",
    "DRUG": "drug",
    "Lab": "lab",
    "LAB": "lab",
    "Dose": "dose",
    "DOSE": "dose",
    "bSYM": "bsym",
    "BSYM": "bsym",
    "BASELINE SYMPTOM": "bsym",
    "MHx": "mhx",
    "MHX": "mhx",
    "MEDICAL HISTORY": "mhx",
    "FHx": "fhx",
    "FHX": "fhx",
    "FAMILY HISTORY": "fhx",
    "Status": "status",
    "STATUS": "status",
    "Treatment": "treatment",
    "TREATMENT": "treatment",
    "INDICATION": "indication",
    "DIAGNOSTIC": "diagnostic",
    "Dx": "diagnostic",
    "Age": "age",
    "AGE": "age",
    "Sex": "sex",
    "SEX": "sex",
    # Explicit exclusions
    "R/O": None,
    "RO": None,
    "CAUSE OF DEATH": None,
    "CoD": None,
    "COD": None,
}

_RAW_TO_LABEL_CASEFOLD = {str(k).strip().casefold(): v for k, v in RAW_TO_LABEL.items()}

EVAL_LABEL_POOL = {
    "ae": "AE",
    "mae": "AE",
    "sdrug": "DRUG",
    "cdrug": "DRUG",
    "odrug": "DRUG",
    "drug": "DRUG",
    "mhx": "HX",
    "fhx": "HX",
    "bsym": "DX",
    "diagnostic": "DX",
    "treatment": "DX",
    "lab": "LAB",
    "dose": "DOSE",
    "status": "STATUS",
    "age": "AGE",
    "sex": "SEX",
    "temporal": "TEMPORAL",
    "indication": "INDICATION",
}


def get_nlp_sent():
    global _nlp_sent
    if _nlp_sent is None:
        if spacy is None:
            raise ImportError("spaCy is required for DocBin processing. Please install spacy.")
        _nlp_sent = spacy.blank("en")
        _nlp_sent.add_pipe("sentencizer")
    return _nlp_sent


# -----------------------------------------------------------------------------
# Utility & Logging Functions
# -----------------------------------------------------------------------------
def clean_terminal_text(text: str) -> str:
    """Remove ANSI terminal escapes, carriage returns and unsafe C0 controls."""
    text = _ANSI_ESCAPE_RE.sub("", text)
    text = text.replace("\r", "")
    return _C0_CONTROL_RE.sub("", text)


def console_print(message: str, *, enabled: bool = True) -> None:
    if enabled:
        tqdm.write(str(message), file=sys.stdout)


def _load_bert_tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(_BERT_MODEL_NAME)


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = _load_bert_tokenizer()
    return _tokenizer


def _ensure_custom_scorer_loaded(ref_scorer: Path) -> None:
    """Register custom spaCy scorer once per Python process."""
    if not ref_scorer.exists():
        raise FileNotFoundError(
            "Custom scorer required by the saved spaCy model was not found: "
            f"{ref_scorer}. Pass --ref-scorer /path/to/publication/code/custom_scorer_v5.py"
        )
    key = str(ref_scorer.resolve())
    if key in _custom_scorer_loaded:
        return
    spec = importlib.util.spec_from_file_location(
        f"llm4ae_custom_scorer_{abs(hash(key))}", key
    )
    if spec is not None and spec.loader is not None:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _custom_scorer_loaded.add(key)


# -----------------------------------------------------------------------------
# Data Ingestion & Case Series Stratification
# -----------------------------------------------------------------------------
def _normalize_raw_label(raw_label: object) -> Optional[str]:
    if raw_label is None:
        return None
    raw = str(raw_label).strip()
    if raw in RAW_TO_LABEL:
        return RAW_TO_LABEL[raw]
    return _RAW_TO_LABEL_CASEFOLD.get(raw.casefold())


def classify_case_series(text: str, annotations: List[Tuple[int, int, str]]) -> str:
    """
    Classify a FAERS document into one of the 4 Drug-AE case series using narrative text
    and gold annotations.
    """
    text_lower = text.lower()
    ann_drugs = " ".join([text[s:e].lower() for s, e, l in annotations if l in ("sdrug", "cdrug", "odrug", "drug")])
    ann_aes = " ".join([text[s:e].lower() for s, e, l in annotations if l in ("ae", "mae")])
    combined = f"{text_lower} {ann_drugs} {ann_aes}"

    scores = {}
    for series_name, kw in CASE_SERIES_KEYWORDS.items():
        drug_matches = sum(combined.count(d) for d in kw["drugs"])
        ae_matches = sum(combined.count(a) for a in kw["aes"])
        scores[series_name] = drug_matches * 10 + ae_matches

    best_series = max(scores, key=scores.get)
    return best_series


def load_records_from_db(db_path: Path) -> Tuple[List[dict], Dict[str, Any]]:
    """Load FAERS documents and SME1 gold annotations from SQLite dataset.db."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    docs_rows = cursor.execute(
        "SELECT doc_id, base_id, suffix, page_text FROM documents WHERE dataset='FAERS' ORDER BY doc_id;"
    ).fetchall()

    anns_rows = cursor.execute(
        "SELECT doc_id, label, tc_start, tc_end FROM annotations "
        "WHERE note='SME1' ORDER BY doc_id, tc_start;"
    ).fetchall()
    conn.close()

    anns_by_doc = defaultdict(list)
    stats = defaultdict(int)

    for doc_id, raw_label, start, end in anns_rows:
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
        anns_by_doc[doc_id].append((start_i, end_i, canon))
        stats["annotations_kept"] += 1

    records = []
    series_distribution = Counter()

    for doc_id, base_id, suffix, raw_text in docs_rows:
        text_norm = raw_text.replace("↵", "\n")
        doc_anns = anns_by_doc.get(doc_id, [])

        valid_anns = []
        for s, e, l in doc_anns:
            if e <= len(text_norm):
                valid_anns.append((s, e, l))
            else:
                stats["out_of_bounds_offsets"] += 1

        case_series = classify_case_series(text_norm, valid_anns)
        series_distribution[case_series] += 1

        records.append({
            "doc_id": doc_id,
            "base_id": base_id,
            "suffix": suffix,
            "text": text_norm,
            "annotations": valid_anns,
            "case_series": case_series,
        })

    stats["documents_loaded"] = len(records)
    stats["case_series_distribution"] = dict(series_distribution)
    return records, dict(stats)


def load_records_from_json(data_dir: Path) -> Tuple[List[dict], Dict[str, Any]]:
    """Fallback: Load FAERS records from JSON directory."""
    if not data_dir.exists():
        raise FileNotFoundError(f"JSON data dir not found: {data_dir}")

    records = []
    stats = defaultdict(int)
    files = sorted(data_dir.glob("*.json"))

    for fpath in files:
        with fpath.open(encoding="utf-8") as f:
            doc = json.load(f)
        pages = doc.get("pages", [])
        page_text = str(pages[0]) if pages else ""
        text_norm = page_text.replace("↵", "\n")

        sme_anns = []
        for ann in doc.get("annotations", []):
            if ann.get("note") != "SME1":
                continue
            stats["sme1_annotations_seen"] += 1
            raw_label = ann.get("label", "")
            canon = _normalize_raw_label(raw_label)
            if canon is None:
                stats["excluded_or_unmapped_labels"] += 1
                continue
            tc = ann.get("textContext") or {}
            try:
                start = int(tc.get("start"))
                end = int(tc.get("end"))
            except (TypeError, ValueError):
                continue
            if 0 <= start < end <= len(text_norm):
                sme_anns.append((start, end, canon))
                stats["annotations_kept"] += 1

        case_series = classify_case_series(text_norm, sme_anns)
        records.append({
            "doc_id": fpath.stem,
            "base_id": fpath.stem.split("-")[0] if "-" in fpath.stem else fpath.stem,
            "suffix": 1,
            "text": text_norm,
            "annotations": sme_anns,
            "case_series": case_series,
        })

    stats["documents_loaded"] = len(records)
    return records, dict(stats)


# -----------------------------------------------------------------------------
# DocBin Conversion for spaCy
# -----------------------------------------------------------------------------
def clean_entities(entities: List[Tuple[int, int, str]], text: str):
    cleaned = []
    for start, end, label in entities:
        start = max(0, min(int(start), len(text)))
        end = max(0, min(int(end), len(text)))
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            cleaned.append((start, end, label))
    return cleaned


def validate_no_overlap(entities: List[Tuple[int, int, str]]) -> bool:
    ents = sorted(entities, key=lambda x: (x[0], x[1]))
    return all(ents[i][1] <= ents[i + 1][0] for i in range(len(ents) - 1))


def count_labels(records: List[dict]) -> Dict[str, int]:
    counts = defaultdict(int)
    for rec in records:
        for _, _, label in rec["annotations"]:
            counts[label] += 1
    return dict(counts)


def records_to_docbin(
    records: List[dict],
    *,
    valid_labels: Set[str],
    include_negative_sentences: bool = True,
):
    nlp = spacy.blank("en")
    tokenizer = _get_tokenizer()
    db = DocBin(store_user_data=False)
    stats = defaultdict(int)

    for rec in records:
        text = rec["text"]
        anns = rec["annotations"]
        doc_sents = get_nlp_sent()(text)

        for sent in doc_sents.sents:
            sent_start = sent.start_char
            sent_end = sent.end_char
            sent_text = text[sent_start:sent_end]
            stats["sentences_seen"] += 1

            if not sent_text.strip():
                stats["blank_sentences_skipped"] += 1
                continue

            n_tokens = len(tokenizer(sent_text, add_special_tokens=True, truncation=False)["input_ids"])
            if n_tokens > _BERT_MAX_TOKENS:
                stats["sentences_too_long"] += 1
                continue

            sent_ents = []
            for start, end, label in anns:
                if label not in valid_labels:
                    continue
                if start >= sent_start and end <= sent_end:
                    sent_ents.append((start - sent_start, end - sent_start, label))

            sent_ents = clean_entities(sent_ents, sent_text)
            if not validate_no_overlap(sent_ents):
                stats["sentences_skipped_overlap"] += 1
                continue

            sent_doc = nlp.make_doc(sent_text)
            spans = []
            alignment_failed = False
            for rel_start, rel_end, label in sent_ents:
                span = sent_doc.char_span(rel_start, rel_end, label=label, alignment_mode="strict")
                if span is None:
                    alignment_failed = True
                    stats["entities_unaligned"] += 1
                else:
                    spans.append(span)

            if alignment_failed:
                stats["sentences_skipped_alignment"] += 1
                continue

            spans = filter_spans(spans)
            sent_doc.ents = spans

            if spans or include_negative_sentences:
                db.add(sent_doc)
                stats["sentences_added"] += 1
                stats["entities_added"] += len(spans)
                if not spans:
                    stats["negative_sentences_added"] += 1

    return db, dict(stats)


# -----------------------------------------------------------------------------
# spaCy Training Configuration
# -----------------------------------------------------------------------------
CONFIG_TEMPLATE = """\
[paths]
train = "{train_path}"
dev   = "{dev_path}"
vectors = null
init_tok2vec = null

[system]
gpu_allocator = "pytorch"
seed = {seed}

[nlp]
lang = "en"
pipeline = ["transformer","ner"]
batch_size = {batch_size}

[components]

[components.ner]
factory = "ner"
incorrect_spans_key = null
moves = null
scorer = {{"@scorers":"ade_weighted_ner_scorer.v1"}}
update_with_oracle_cut_size = 100

[components.ner.model]
@architectures = "spacy.TransitionBasedParser.v2"
state_type = "ner"
extra_state_tokens = false
hidden_width = 64
maxout_pieces = 2
use_upper = false
nO = null

[components.ner.model.tok2vec]
@architectures = "spacy-transformers.TransformerListener.v1"
grad_factor = 1.0
pooling = {{"@layers":"reduce_mean.v1"}}
upstream = "*"

[components.transformer]
factory = "transformer"
max_batch_items = {max_batch_items}
set_extra_annotations = {{"@annotation_setters":"spacy-transformers.null_annotation_setter.v1"}}

[components.transformer.model]
@architectures = "spacy-transformers.TransformerModel.v3"
name = "dmis-lab/biobert-base-cased-v1.1"
mixed_precision = false

[components.transformer.model.get_spans]
@span_getters = "spacy-transformers.strided_spans.v1"
window = 512
stride = 96

[components.transformer.model.grad_scaler_config]

[components.transformer.model.tokenizer_config]
use_fast = true

[components.transformer.model.transformer_config]

[corpora]

[corpora.dev]
@readers = "spacy.Corpus.v1"
path = ${{paths.dev}}
max_length = 0
gold_preproc = false
limit = 0
augmenter = null

[corpora.train]
@readers = "spacy.Corpus.v1"
path = ${{paths.train}}
max_length = 0
gold_preproc = false
limit = 0
augmenter = null

[training]
accumulate_gradient = 3
dev_corpus = "corpora.dev"
train_corpus = "corpora.train"
seed = ${{system.seed}}
gpu_allocator = "pytorch"
dropout = 0.1
patience = 1600
max_epochs = 0
max_steps = {max_steps}
eval_frequency = 200
frozen_components = []
annotating_components = []

[training.batcher]
@batchers = "spacy.batch_by_padded.v1"
discard_oversize = true
size = {batch_size_items}
buffer = 256
get_length = null

[training.logger]
@loggers = "spacy.ConsoleLogger.v1"
progress_bar = false

[training.optimizer]
@optimizers = "Adam.v1"
beta1 = 0.9
beta2 = 0.999
L2_is_weight_decay = true
L2 = 0.01
grad_clip = 1.0
use_averages = false
eps = 0.00000001

[training.optimizer.learn_rate]
@schedules = "warmup_linear.v1"
warmup_steps = 250
total_steps = {max_steps}
initial_rate = 0.0001

[training.score_weights]
ents_f = 1.0
ents_p = 0.0
ents_r = 0.0
ents_per_type = null

[initialize]
vectors = ${{paths.vectors}}
init_tok2vec = ${{paths.init_tok2vec}}
vocab_data = null
lookups = null
"""


# -----------------------------------------------------------------------------
# Comprehensive Multi-Scheme Alignment & Evaluation
# -----------------------------------------------------------------------------
def _overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return (a0 == b0) or (a1 == b1) or (a0 < b0 < a1) or (a0 < b1 < a1) or (b0 < a0 < b1)


def align_and_classify_spans(
    text: str,
    gold_ents: List[Tuple[int, int, str]],
    pred_ents: List[Tuple[int, int, str, float]],
) -> List[dict]:
    """
    Align gold and predicted spans into a compliant error taxonomy:
      - 'M': Exact span & exact class match
      - 'C': Inexact boundary match or overlapping class confusion
      - 'S': Spurious prediction with no gold overlap (Non-overlapping FP)
      - 'N': Missed gold entity (False Negative)
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
                # A label confusion is an overlapping partial match, i.e. C,
                # not an S.  Preserve the reason in a separate audit column.
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


def calculate_three_schemes(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Compute performance across the Two-Tier Evaluation Framework:
      - Scheme 3 (Primary Standard NER): Strict exact-match micro-P/R/F1.
      - Scheme 2 (Secondary Clinical Utility): ADE-Eval back-office weighted micro-P/R/F1,
        where Category C unifies boundary inexactness (C_boundary) and category
        misclassification (C_class) with 0.5 partial credit, and Category S is
        strictly reserved for non-overlapping spurious predictions.
      (Note: Former Scheme 1 has been discontinued).
    """
    if df.empty:
        empty = {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        return {"strict_scheme3": empty, "ade_weighted_scheme2": empty}

    counts = df["match_type"].value_counts().to_dict()
    M = int(counts.get("M", 0))
    # ``S_wrong_class`` and ``S_non_overlap`` are accepted for backwards
    # compatibility with pre-correction task CSVs. Newly exported raw results
    # always use only M/C/S/N in ``match_type``.
    class_confusion_mask = (
        (df["match_type"] == "C") & (df["error_subtype"] == "class_confusion")
        if "error_subtype" in df.columns
        else pd.Series(False, index=df.index)
    )
    C_class = int(class_confusion_mask.sum()) + int(counts.get("S_wrong_class", 0))
    C_total = int(counts.get("C", 0)) + int(counts.get("S_wrong_class", 0))
    C_boundary = C_total - C_class
    S_non_overlap = int(counts.get("S", 0)) + int(counts.get("S_non_overlap", 0))
    N = int(counts.get("N", 0))

    # 1. Scheme 3: Strict Exact-Match Standard NER (Primary Benchmark)
    p3_den = M + C_total + S_non_overlap
    r3_den = M + C_total + N
    p3 = M / p3_den if p3_den > 0 else 0.0
    r3 = M / r3_den if r3_den > 0 else 0.0
    f3 = 2 * p3 * r3 / (p3 + r3) if (p3 + r3) > 0 else 0.0

    # 2. Scheme 2: ADE-Eval Clinical Weighted Metric (Secondary Clinical Utility)
    #    C_total (boundary + category mis-class) gets 0.5 credit
    #    S_non_overlap (phantom / spurious FP) penalized with 0.25 denominator weight
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
            "precision": round(p2, 4),
            "recall": round(r2, 4),
            "f1": round(f2, 4),
        },
    }


def paired_bootstrap_ci(
    raw_df: pd.DataFrame,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> Dict[str, Tuple[float, float]]:
    """Compute document-level paired bootstrap 95% Confidence Intervals."""
    if raw_df.empty or "doc_idx" not in raw_df.columns:
        return {}

    docs = raw_df["doc_idx"].unique()
    n_docs = len(docs)
    if n_docs < 5:
        return {}

    doc_groups = {doc_id: group for doc_id, group in raw_df.groupby("doc_idx")}
    rng = np.random.RandomState(seed)

    strict_f1s, ade_f1s = [], []

    for _ in range(n_bootstraps):
        sampled_docs = rng.choice(docs, size=n_docs, replace=True)
        sampled_rows = pd.concat([doc_groups[d] for d in sampled_docs], ignore_index=True)
        metrics = calculate_three_schemes(sampled_rows)
        strict_f1s.append(metrics["strict_scheme3"]["f1"])
        ade_f1s.append(metrics["ade_weighted_scheme2"]["f1"])

    return {
        "strict_f1_95ci": (round(float(np.percentile(strict_f1s, 2.5)), 4), round(float(np.percentile(strict_f1s, 97.5)), 4)),
        "ade_f1_95ci": (round(float(np.percentile(ade_f1s, 2.5)), 4), round(float(np.percentile(ade_f1s, 97.5)), 4)),
    }


# -----------------------------------------------------------------------------
# Training & Single Run Execution
# -----------------------------------------------------------------------------
def run_spacy_train_proc(
    cmd: Sequence[str],
    *,
    log_path: Path,
    max_steps: int,
    fold_name: str,
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({"NO_COLOR": "1", "FORCE_COLOR": "0", "TERM": "dumb", "PYTHONUNBUFFERED": "1"})

    proc = subprocess.Popen(
        list(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
    )

    with log_path.open("w", encoding="utf-8", newline="\n") as logf:
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            clean = clean_terminal_text(raw_line).rstrip("\n")
            logf.write(clean + "\n")
            logf.flush()

    return proc.wait()


def evaluate_model_on_test(
    model_path: Path,
    test_path: Path,
    test_recs: List[dict],
    gpu_id: int,
    eval_batch_size: int = 64,
) -> pd.DataFrame:
    """Evaluate trained spaCy model on held-out test documents."""
    try:
        spacy.require_gpu(gpu_id)
    except Exception:
        spacy.require_cpu()

    nlp = spacy.load(str(model_path))
    nlp_blank = spacy.blank("en")
    test_docs = list(DocBin().from_disk(test_path).get_docs(nlp_blank.vocab))

    all_rows = []
    text_iter = (doc.text for doc in test_docs)
    pred_iter = nlp.pipe(text_iter, batch_size=eval_batch_size)

    for doc_idx, (gold_doc, pred_doc) in enumerate(zip(test_docs, pred_iter)):
        text = gold_doc.text
        gold_ents = [(e.start_char, e.end_char, e.label_) for e in gold_doc.ents]
        pred_ents = [(e.start_char, e.end_char, e.label_, 1.0) for e in pred_doc.ents]

        rows = align_and_classify_spans(text, gold_ents, pred_ents)
        for r in rows:
            r["doc_idx"] = doc_idx
            r["sentence"] = text
        all_rows.extend(rows)

    del nlp
    gc.collect()
    return pd.DataFrame(all_rows)


def summarize_evaluation(
    raw_df: pd.DataFrame,
    *,
    fold_idx: int,
    fold_name: str,
    seed: int,
) -> Tuple[dict, pd.DataFrame]:
    """Calculate overall and per-category metrics for one saved model evaluation."""
    schemes = calculate_three_schemes(raw_df)
    strict = schemes["strict_scheme3"]
    ade = schemes["ade_weighted_scheme2"]

    overall_row = {
        "fold": fold_idx,
        "fold_name": fold_name,
        "seed": seed,
        "test_case_series": fold_name,
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
    for cat in sorted(set(EVAL_LABEL_POOL.values())):
        cat_df = raw_df[
            (raw_df["label_gold"].map(EVAL_LABEL_POOL) == cat) |
            (raw_df["label_pred"].map(EVAL_LABEL_POOL) == cat)
        ]
        cat_schemes = calculate_three_schemes(cat_df)
        cat_strict = cat_schemes["strict_scheme3"]
        cat_ade = cat_schemes["ade_weighted_scheme2"]
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

    return overall_row, pd.DataFrame(cat_rows)


def _saved_run_metadata(run_dir: Path) -> Tuple[str, int]:
    """Read the fold name and seed from the directory created by ``run_single_run``."""
    match = re.fullmatch(r"(.+)_seed_(\d+)", run_dir.name)
    if match is None:
        raise ValueError(
            f"Cannot infer fold name and seed from '{run_dir.name}'. Expected <fold_name>_seed_<seed>."
        )
    return match.group(1), int(match.group(2))


def export_existing_runs(
    *,
    existing_work_dir: Path,
    results_dir: Path,
    gpu_id: int,
    eval_batch_size: int,
    ref_scorer: Path,
) -> None:
    """Create raw.xlsx and metrics.xlsx by evaluating saved model-best/test.spacy pairs.

    This deliberately does not load the source dataset, regenerate splits, or invoke
    ``spacy train``.  It is intended for completed cloud runs whose work directory
    contains ``<fold_name>_seed_<seed>/model/model-best`` and ``test.spacy``.
    """
    if not existing_work_dir.is_dir():
        raise FileNotFoundError(f"Existing work directory not found: {existing_work_dir}")

    run_dirs = sorted(
        run_dir for run_dir in existing_work_dir.iterdir()
        if run_dir.is_dir()
        and (run_dir / "model" / "model-best").is_dir()
        and (run_dir / "test.spacy").is_file()
    )
    if not run_dirs:
        raise FileNotFoundError(
            "No saved runs found. Expected directories containing both "
            "model/model-best and test.spacy under "
            f"{existing_work_dir}"
        )

    _ensure_custom_scorer_loaded(ref_scorer)
    raw_frames: List[pd.DataFrame] = []
    overall_rows: List[dict] = []
    category_frames: List[pd.DataFrame] = []

    for fold_idx, run_dir in enumerate(run_dirs):
        fold_name, seed = _saved_run_metadata(run_dir)
        console_print(f"[EXPORT] {run_dir.name}: evaluating saved model (no training)")
        raw_df = evaluate_model_on_test(
            run_dir / "model" / "model-best",
            run_dir / "test.spacy",
            [],
            gpu_id,
            eval_batch_size,
        )
        raw_df["fold"] = fold_idx
        raw_df["fold_name"] = fold_name
        raw_df["seed"] = seed
        overall_row, category_df = summarize_evaluation(
            raw_df, fold_idx=fold_idx, fold_name=fold_name, seed=seed
        )
        raw_frames.append(raw_df)
        overall_rows.append(overall_row)
        category_frames.append(category_df)

    raw_combined_df = pd.concat(raw_frames, ignore_index=True)
    overall_df = pd.DataFrame(overall_rows).sort_values(["fold_name", "seed"]).reset_index(drop=True)
    category_df = pd.concat(category_frames, ignore_index=True)

    fold_summary = overall_df.groupby(["fold_name", "test_case_series"], as_index=False).agg(
        runs=("seed", "nunique"),
        M=("M", "sum"),
        C_boundary=("C_boundary", "sum"),
        C_class=("C_class", "sum"),
        C_total=("C_total", "sum"),
        S_non_overlap=("S_non_overlap", "sum"),
        N=("N", "sum"),
        strict_F1_mean=("strict_F1", "mean"),
        strict_F1_std=("strict_F1", "std"),
        ade_F1_mean=("ade_F1", "mean"),
        ade_F1_std=("ade_F1", "std"),
    ).round(4)
    fold_summary[["strict_F1_std", "ade_F1_std"]] = fold_summary[["strict_F1_std", "ade_F1_std"]].fillna(0.0)

    category_summary = category_df.groupby("category", as_index=False).agg(
        runs=("seed", "count"),
        M=("M", "sum"),
        C_boundary=("C_boundary", "sum"),
        C_class=("C_class", "sum"),
        C_total=("C_total", "sum"),
        S_non_overlap=("S_non_overlap", "sum"),
        N=("N", "sum"),
        strict_F1_mean=("strict_F1", "mean"),
        strict_F1_std=("strict_F1", "std"),
        ade_F1_mean=("ade_F1", "mean"),
        ade_F1_std=("ade_F1", "std"),
    ).round(4)
    category_summary[["strict_F1_std", "ade_F1_std"]] = category_summary[["strict_F1_std", "ade_F1_std"]].fillna(0.0)

    results_dir.mkdir(parents=True, exist_ok=True)
    raw_xlsx = results_dir / "raw.xlsx"
    metrics_xlsx = results_dir / "metrics.xlsx"
    with pd.ExcelWriter(raw_xlsx, engine="openpyxl") as writer:
        raw_combined_df.to_excel(writer, sheet_name="Raw_Results", index=False)
    with pd.ExcelWriter(metrics_xlsx, engine="openpyxl") as writer:
        overall_df.to_excel(writer, sheet_name="All_Runs", index=False)
        fold_summary.to_excel(writer, sheet_name="Fold_Summary", index=False)
        category_df.to_excel(writer, sheet_name="Per_Category", index=False)
        category_summary.to_excel(writer, sheet_name="Category_Summary", index=False)

    console_print(f"[EXPORT] Saved {raw_xlsx} and {metrics_xlsx} from {len(run_dirs)} existing runs.")


def run_single_run(
    *,
    fold_idx: int,
    fold_name: str,
    seed: int,
    train_recs: List[dict],
    dev_recs: List[dict],
    test_recs: List[dict],
    gpu_id: int,
    max_steps: int,
    work_dir: Path,
    ref_scorer: Path,
    train_python: str,
    batch_size: int = 64,
    max_batch_items: int = 8192,
    min_label_count: int = 5,
    eval_batch_size: int = 64,
    include_negative_sentences: bool = True,
) -> Tuple[pd.DataFrame, dict, pd.DataFrame]:
    run_dir = work_dir / f"{fold_name}_seed_{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)

    train_label_counts = count_labels(train_recs)
    valid_labels = {l for l, c in train_label_counts.items() if c >= min_label_count}

    train_db, _ = records_to_docbin(train_recs, valid_labels=valid_labels, include_negative_sentences=include_negative_sentences)
    dev_db, _ = records_to_docbin(dev_recs, valid_labels=valid_labels, include_negative_sentences=include_negative_sentences)
    test_db, _ = records_to_docbin(test_recs, valid_labels=valid_labels, include_negative_sentences=include_negative_sentences)

    train_path = run_dir / "train.spacy"
    dev_path = run_dir / "dev.spacy"
    test_path = run_dir / "test.spacy"
    train_db.to_disk(train_path)
    dev_db.to_disk(dev_path)
    test_db.to_disk(test_path)

    cfg_text = CONFIG_TEMPLATE.format(
        train_path=str(train_path),
        dev_path=str(dev_path),
        seed=seed,
        max_steps=max_steps,
        batch_size=batch_size,
        max_batch_items=max_batch_items,
        batch_size_items=max_batch_items // 2,
    )
    cfg_path = run_dir / "train.cfg"
    cfg_path.write_text(cfg_text, encoding="utf-8")

    model_dir = run_dir / "model"
    log_path = run_dir / "train.log"
    cmd = [
        train_python, "-m", "spacy", "train",
        str(cfg_path),
        "--output", str(model_dir),
        "--gpu-id", str(gpu_id),
    ]
    if ref_scorer.exists():
        cmd.extend(["--code", str(ref_scorer)])

    returncode = run_spacy_train_proc(cmd, log_path=log_path, max_steps=max_steps, fold_name=fold_name)
    if returncode != 0:
        raise RuntimeError(f"Run {fold_name}_seed_{seed} failed with code {returncode}. Log: {log_path}")

    best_model_path = model_dir / "model-best"
    if not best_model_path.exists():
        raise FileNotFoundError(f"Model not found: {best_model_path}")

    _ensure_custom_scorer_loaded(ref_scorer)
    raw_df = evaluate_model_on_test(best_model_path, test_path, test_recs, gpu_id, eval_batch_size)
    raw_df["fold"] = fold_idx
    raw_df["fold_name"] = fold_name
    raw_df["seed"] = seed

    schemes = calculate_three_schemes(raw_df)
    strict = schemes["strict_scheme3"]
    ade = schemes["ade_weighted_scheme2"]

    overall_row = {
        "fold": fold_idx,
        "fold_name": fold_name,
        "seed": seed,
        "test_case_series": fold_name,
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

    # Per-category evaluation
    cat_rows = []
    for cat in sorted(set(EVAL_LABEL_POOL.values())):
        cat_df = raw_df[
            (raw_df["label_gold"].map(EVAL_LABEL_POOL) == cat) |
            (raw_df["label_pred"].map(EVAL_LABEL_POOL) == cat)
        ]
        cat_schemes = calculate_three_schemes(cat_df)
        cat_rows.append({
            "fold": fold_idx,
            "fold_name": fold_name,
            "seed": seed,
            "category": cat,
            "strict_F1": cat_schemes["strict_scheme3"]["f1"],
            "ade_F1": cat_schemes["ade_weighted_scheme2"]["f1"],
        })

    return raw_df, overall_row, pd.DataFrame(cat_rows)


# -----------------------------------------------------------------------------
# Multi-GPU Parallel Worker Process Loop
# -----------------------------------------------------------------------------
def _gpu_worker_process(
    worker_id: int,
    gpu_id: int,
    task_queue: mp.Queue,
    result_queue: mp.Queue,
    work_dir_str: str,
    ref_scorer_str: str,
    train_python: str,
    max_steps: int,
    batch_size: int,
    max_batch_items: int,
    min_label_count: int,
    eval_batch_size: int,
):
    """
    Dedicated worker process pinned to gpu_id, pulling runs from task_queue.
    All stdout/stderr from child training is isolated to log files.
    """
    work_dir = Path(work_dir_str)
    ref_scorer = Path(ref_scorer_str)

    while True:
        try:
            task = task_queue.get_nowait()
        except queue.Empty:
            break

        if task is None:
            break

        run_id = task["run_id"]
        fold_idx = task["fold_idx"]
        fold_name = task["fold_name"]
        seed = task["seed"]
        train_recs = task["train_recs"]
        dev_recs = task["dev_recs"]
        test_recs = task["test_recs"]

        task_start = time.time()
        result_queue.put({
            "status": "started",
            "run_id": run_id,
            "worker_id": worker_id,
            "gpu_id": gpu_id,
            "fold_name": fold_name,
            "seed": seed,
            "time_str": time.strftime("%H:%M:%S"),
        })

        try:
            raw_df, overall_row, cat_df = run_single_run(
                fold_idx=fold_idx,
                fold_name=fold_name,
                seed=seed,
                train_recs=train_recs,
                dev_recs=dev_recs,
                test_recs=test_recs,
                gpu_id=gpu_id,
                max_steps=max_steps,
                work_dir=work_dir,
                ref_scorer=ref_scorer,
                train_python=train_python,
                batch_size=batch_size,
                max_batch_items=max_batch_items,
                min_label_count=min_label_count,
                eval_batch_size=eval_batch_size,
            )
            duration_s = time.time() - task_start
            result_queue.put({
                "status": "success",
                "run_id": run_id,
                "worker_id": worker_id,
                "gpu_id": gpu_id,
                "fold_idx": fold_idx,
                "fold_name": fold_name,
                "seed": seed,
                "duration_s": duration_s,
                "time_str": time.strftime("%H:%M:%S"),
                "raw_df": raw_df,
                "overall_row": overall_row,
                "cat_df": cat_df,
            })
        except Exception as e:
            tb = traceback.format_exc()
            duration_s = time.time() - task_start
            result_queue.put({
                "status": "error",
                "run_id": run_id,
                "worker_id": worker_id,
                "gpu_id": gpu_id,
                "fold_idx": fold_idx,
                "fold_name": fold_name,
                "seed": seed,
                "duration_s": duration_s,
                "time_str": time.strftime("%H:%M:%S"),
                "error": str(e),
                "traceback": tb,
            })


# -----------------------------------------------------------------------------
# Leave-One-Pair-Out (LOO) & K-Fold Split Generators
# -----------------------------------------------------------------------------
def generate_loo_splits(records: List[dict]) -> List[Tuple[str, List[dict], List[dict], List[dict]]]:
    """Generate 4 Leave-One-Drug-AE-Pair-Out folds."""
    splits = []
    for held_out_series in FAERS_CASE_SERIES:
        test_recs = [r for r in records if r["case_series"] == held_out_series]
        train_pool = [r for r in records if r["case_series"] != held_out_series]

        # Use 85% of remaining for train, 15% for dev early stopping
        rng = random.Random(42)
        shuffled = list(train_pool)
        rng.shuffle(shuffled)
        n_dev = max(1, int(len(shuffled) * 0.15))
        dev_recs = shuffled[:n_dev]
        train_recs = shuffled[n_dev:]

        splits.append((held_out_series, train_recs, dev_recs, test_recs))
    return splits


def generate_cv_splits(records: List[dict], k_folds: int = 10) -> List[Tuple[str, List[dict], List[dict], List[dict]]]:
    """Generate Stratified Disjoint K-Fold CV splits."""
    by_series = defaultdict(list)
    for r in records:
        by_series[r["case_series"]].append(r)

    fold_buckets = [[] for _ in range(k_folds)]
    rng = random.Random(42)

    for series, recs in by_series.items():
        shuffled = list(recs)
        rng.shuffle(shuffled)
        for i, r in enumerate(shuffled):
            fold_buckets[i % k_folds].append(r)

    splits = []
    for k in range(k_folds):
        test_recs = fold_buckets[k]
        train_pool = [r for j in range(k_folds) if j != k for r in fold_buckets[j]]
        rng.shuffle(train_pool)
        n_dev = max(1, int(len(train_pool) * 0.10))
        dev_recs = train_pool[:n_dev]
        train_recs = train_pool[n_dev:]
        splits.append((f"Fold_{k:02d}", train_recs, dev_recs, test_recs))
    return splits


# -----------------------------------------------------------------------------
# Main Execution Pipeline
# -----------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="High-Throughput BioBERT Parallel Leave-One-Pair-Out & Multi-Seed Suite",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode", choices=("loo", "cv"), default="loo",
        help="Evaluation mode: 'loo' (Leave-One-Pair-Out 4-Fold) or 'cv' (Stratified Disjoint K-Fold)."
    )
    parser.add_argument("--folds", type=int, default=10, help="Number of folds for CV mode.")
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[42, 123, 456, 789, 1011],
        help="Random initialization seeds per fold."
    )
    parser.add_argument(
        "--gpu-ids", type=int, nargs="+", default=[0],
        help="List of GPU device IDs to run on simultaneously (e.g. --gpu-ids 0 1 2 3 4 5 6)."
    )
    parser.add_argument(
        "--workers-per-gpu", type=int, default=1,
        help="Concurrent training workers per GPU (e.g. 2 for 32GB GPUs to double parallel runs)."
    )
    parser.add_argument("--batch-size", type=int, default=64, help="spaCy transformer pipeline batch size.")
    parser.add_argument("--max-batch-items", type=int, default=8192, help="Max batch token items (tuned for 32GB GPUs).")
    parser.add_argument("--max-steps", type=int, default=8000, help="Max spaCy training steps.")
    parser.add_argument("--min-label-count", type=int, default=5, help="Min label count in TRAIN.")
    parser.add_argument("--eval-batch-size", type=int, default=64, help="Inference batch size for evaluation.")
    parser.add_argument(
        "--task-index", type=int, default=None,
        help="Run a single specific task index (0-based) for SLURM Array Jobs ($SLURM_ARRAY_TASK_ID)."
    )
    parser.add_argument(
        "--aggregate-only", action="store_true",
        help="Only aggregate existing finished task outputs in results-dir without running training."
    )
    parser.add_argument(
        "--export-existing", action="store_true",
        help=(
            "Re-evaluate saved model/model-best and test.spacy pairs and write raw.xlsx "
            "and metrics.xlsx. This mode never trains or rebuilds data splits."
        ),
    )
    parser.add_argument(
        "--existing-work-dir", type=Path, default=None,
        help=(
            "Directory containing <fold_name>_seed_<seed> run directories for --export-existing. "
            "Defaults to results-dir/workdir."
        ),
    )
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--ref-scorer", type=Path, default=DEFAULT_REF_SCORER)
    parser.add_argument("--train-python", type=str, default=DEFAULT_TRAIN_PYTHON)
    return parser.parse_args()


def main():
    args = parse_args()
    args.results_dir.mkdir(parents=True, exist_ok=True)
    work_dir = args.results_dir / "workdir"
    work_dir.mkdir(parents=True, exist_ok=True)

    console_print("=" * 80)
    console_print(" High-Throughput Parallel BioBERT Evaluation Suite")
    console_print("=" * 80)

    if args.export_existing:
        existing_work_dir = args.existing_work_dir or work_dir
        console_print(
            "[MODE: Export Existing] Re-evaluating saved model/test.spacy pairs; training is disabled."
        )
        export_existing_runs(
            existing_work_dir=existing_work_dir,
            results_dir=args.results_dir,
            gpu_id=args.gpu_ids[0],
            eval_batch_size=args.eval_batch_size,
            ref_scorer=args.ref_scorer,
        )
        return

    # 1. Load data
    if args.db_path.exists():
        console_print(f"Loading authoritative FAERS dataset from SQLite: {args.db_path}")
        records, stats = load_records_from_db(args.db_path)
    else:
        console_print(f"Database not found. Loading from JSON directory: {args.data_dir}")
        records, stats = load_records_from_json(args.data_dir)

    console_print(f"Total FAERS Documents: {len(records)} | Annotations: {stats.get('annotations_kept', 0)}")
    console_print("Case Series Stratification:")
    for series, count in stats.get("case_series_distribution", {}).items():
        console_print(f"  * {series:<32}: {count:4d} reports ({count/len(records):.1%})")

    # 2. Build splits
    if args.mode == "loo":
        splits = generate_loo_splits(records)
        console_print(f"\n[MODE: Leave-One-Drug-AE-Pair-Out (4 Folds, OOD Generalization)]")
    else:
        splits = generate_cv_splits(records, k_folds=args.folds)
        console_print(f"\n[MODE: Stratified Disjoint K-Fold CV ({args.folds} Folds, In-Distribution)]")

    # 3. Create all run tasks
    all_tasks = []
    task_id = 0
    for fold_idx, (fold_name, train_recs, dev_recs, test_recs) in enumerate(splits):
        for seed in args.seeds:
            all_tasks.append({
                "run_id": task_id,
                "fold_idx": fold_idx,
                "fold_name": fold_name,
                "seed": seed,
                "train_recs": train_recs,
                "dev_recs": dev_recs,
                "test_recs": test_recs,
            })
            task_id += 1

    total_runs = len(all_tasks)

    # Branch A: Aggregate Only Mode
    if args.aggregate_only:
        console_print(f"\n[MODE: Aggregate-Only] Scanning {work_dir} for completed task results...")
        all_raw_dfs = []
        all_overall_rows = []
        all_cat_dfs = []
        metrics_files = sorted(work_dir.glob("task_*_metrics.json"))
        for mf in metrics_files:
            with mf.open("r", encoding="utf-8") as f:
                overall_row = json.load(f)
            prefix = mf.name.replace("_metrics.json", "")
            cat_file = work_dir / f"{prefix}_cat.csv"
            raw_file = work_dir / f"{prefix}_raw.csv"
            all_overall_rows.append(overall_row)
            if cat_file.exists():
                all_cat_dfs.append(pd.read_csv(cat_file))
            if raw_file.exists():
                all_raw_dfs.append(pd.read_csv(raw_file))

        console_print(f"Loaded {len(all_overall_rows)}/{total_runs} completed task metrics.")
        if not all_overall_rows:
            console_print("ERROR: No completed task metric files found.")
            return

    # Branch B: Single Task Index Mode (for SLURM Array Jobs)
    elif args.task_index is not None:
        if not (0 <= args.task_index < total_runs):
            raise ValueError(f"--task-index {args.task_index} out of range (0..{total_runs-1})")
        task = all_tasks[args.task_index]
        gpu_id = args.gpu_ids[0]
        console_print(
            f"\n[MODE: SLURM Array Task {args.task_index}/{total_runs-1}] "
            f"Fold [{task['fold_name']}] Seed {task['seed']} on GPU {gpu_id}"
        )
        raw_df, overall_row, cat_df = run_single_run(
            fold_idx=task["fold_idx"],
            fold_name=task["fold_name"],
            seed=task["seed"],
            train_recs=task["train_recs"],
            dev_recs=task["dev_recs"],
            test_recs=task["test_recs"],
            gpu_id=gpu_id,
            max_steps=args.max_steps,
            work_dir=work_dir,
            ref_scorer=args.ref_scorer,
            train_python=args.train_python,
            batch_size=args.batch_size,
            max_batch_items=args.max_batch_items,
            min_label_count=args.min_label_count,
            eval_batch_size=args.eval_batch_size,
        )
        task_prefix = f"task_{args.task_index:03d}_{task['fold_name']}_seed_{task['seed']}"
        with (work_dir / f"{task_prefix}_metrics.json").open("w", encoding="utf-8") as f:
            json.dump(overall_row, f, indent=2)
        cat_df.to_csv(work_dir / f"{task_prefix}_cat.csv", index=False)
        raw_df.to_csv(work_dir / f"{task_prefix}_raw.csv", index=False)

        console_print(
            f"\nTask {args.task_index} COMPLETED: "
            f"Strict F1 = {overall_row['strict_F1']:.4f} | ADE F1 = {overall_row['ade_F1']:.4f}"
        )
        return

    # Branch C: Standard Multi-GPU / Single-Machine Parallel Mode
    else:
        num_gpus = len(args.gpu_ids)
        total_workers = num_gpus * args.workers_per_gpu

        console_print(f"\nTotal Tasks to Execute: {total_runs} runs")
        console_print(f"Allocated GPUs: {args.gpu_ids} ({num_gpus} GPUs)")
        console_print(f"Workers per GPU: {args.workers_per_gpu} -> {total_workers} Concurrent Parallel Processes!")
        console_print(f"Batch Size: {args.batch_size} | Max Batch Items: {args.max_batch_items} | Eval Batch Size: {args.eval_batch_size}")
        console_print(f"Max Steps per Run: {args.max_steps}")

        start_time = time.time()

        all_raw_dfs = []
        all_overall_rows = []
        all_cat_dfs = []

    # 4. Multi-GPU Parallel Execution Pool
    if total_workers > 1 and total_runs > 1:
        ctx = mp.get_context("spawn")
        task_queue = ctx.Queue()
        result_queue = ctx.Queue()

        for t in all_tasks:
            task_queue.put(t)

        processes = []
        for w_idx in range(total_workers):
            gpu_id = args.gpu_ids[w_idx % num_gpus]
            p = ctx.Process(
                target=_gpu_worker_process,
                args=(
                    w_idx,
                    gpu_id,
                    task_queue,
                    result_queue,
                    str(work_dir),
                    str(args.ref_scorer),
                    args.train_python,
                    args.max_steps,
                    args.batch_size,
                    args.max_batch_items,
                    args.min_label_count,
                    args.eval_batch_size,
                ),
                name=f"Worker-{w_idx}-GPU-{gpu_id}",
            )
            p.start()
            processes.append(p)

        pbar = tqdm(total=total_runs, desc="Overall Runs Progress", unit="run", dynamic_ncols=True)
        completed_count = 0

        while completed_count < total_runs:
            try:
                res = result_queue.get(timeout=2.0)

                status = res.get("status")
                if status == "started":
                    t_str = res.get("time_str", "")
                    console_print(
                        f"[{t_str}] [GPU {res['gpu_id']} | Worker {res['worker_id']:02d}] >> START Fold [{res['fold_name']}] Seed {res['seed']}"
                    )

                elif status == "success":
                    completed_count += 1
                    pbar.update(1)
                    all_raw_dfs.append(res["raw_df"])
                    all_overall_rows.append(res["overall_row"])
                    all_cat_dfs.append(res["cat_df"])
                    row = res["overall_row"]
                    dur_min = res.get("duration_s", 0) / 60.0
                    t_str = res.get("time_str", "")
                    console_print(
                        f"[{t_str}] [GPU {res['gpu_id']} | Worker {res['worker_id']:02d}] << DONE  Fold [{row['fold_name']}] Seed {row['seed']} "
                        f"in {dur_min:.1f}m -> Strict F1 = {row['strict_F1']:.4f} | ADE F1 = {row['ade_F1']:.4f} | Det F1 = {row['detection_F1']:.4f} "
                        f"({completed_count}/{total_runs})"
                    )

                elif status == "error":
                    completed_count += 1
                    pbar.update(1)
                    t_str = res.get("time_str", "")
                    console_print(
                        f"[{t_str}] [GPU {res['gpu_id']} | Worker {res['worker_id']:02d}] xx FAILED Run {res['run_id']} ({res['fold_name']} Seed {res['seed']}): {res['error']}"
                    )
                    console_print(res.get("traceback", ""))

            except queue.Empty:
                alive = any(p.is_alive() for p in processes)
                if not alive and completed_count < total_runs:
                    console_print(f"WARNING: All worker processes terminated early ({completed_count}/{total_runs} done).")
                    break

        pbar.close()
        for p in processes:
            p.join(timeout=5)

    else:
        # Sequential single worker fallback
        pbar = tqdm(total=total_runs, desc="BioBERT Runs", unit="run")
        for task in all_tasks:
            gpu_id = args.gpu_ids[0]
            try:
                raw_df, overall_row, cat_df = run_single_run(
                    fold_idx=task["fold_idx"],
                    fold_name=task["fold_name"],
                    seed=task["seed"],
                    train_recs=task["train_recs"],
                    dev_recs=task["dev_recs"],
                    test_recs=task["test_recs"],
                    gpu_id=gpu_id,
                    max_steps=args.max_steps,
                    work_dir=work_dir,
                    ref_scorer=args.ref_scorer,
                    train_python=args.train_python,
                    batch_size=args.batch_size,
                    max_batch_items=args.max_batch_items,
                    min_label_count=args.min_label_count,
                    eval_batch_size=args.eval_batch_size,
                )
                all_raw_dfs.append(raw_df)
                all_overall_rows.append(overall_row)
                all_cat_dfs.append(cat_df)
                console_print(
                    f"  [DONE] Fold [{task['fold_name']}] Seed {task['seed']}: "
                    f"Strict F1 = {overall_row['strict_F1']:.4f} | ADE F1 = {overall_row['ade_F1']:.4f}"
                )
            except Exception as e:
                console_print(f"  [FAILED] Run {task['run_id']}: {e}\n{traceback.format_exc()}")
            pbar.update(1)
        pbar.close()

    elapsed = time.time() - start_time
    console_print(f"\nAll Runs Completed in {elapsed/60:.2f} minutes ({elapsed:.1f} seconds).")

    if not all_overall_rows:
        console_print("ERROR: No runs completed successfully.")
        return

    # 5. Aggregation and Statistical Reporting
    overall_df = pd.DataFrame(all_overall_rows)
    cat_combined_df = pd.concat(all_cat_dfs, ignore_index=True) if all_cat_dfs else pd.DataFrame()
    raw_combined_df = pd.concat(all_raw_dfs, ignore_index=True) if all_raw_dfs else pd.DataFrame()

    fold_summary = overall_df.groupby(["fold", "fold_name", "test_case_series"], as_index=False).agg(
        strict_F1_mean=("strict_F1", "mean"),
        strict_F1_std=("strict_F1", "std"),
        ade_F1_mean=("ade_F1", "mean"),
        ade_F1_std=("ade_F1", "std"),
    ).round(4)

    cat_summary = cat_combined_df.groupby("category", as_index=False).agg(
        strict_F1_mean=("strict_F1", "mean"),
        strict_F1_std=("strict_F1", "std"),
        ade_F1_mean=("ade_F1", "mean"),
        ade_F1_std=("ade_F1", "std"),
    ).round(4) if not cat_combined_df.empty else pd.DataFrame()

    bootstrap_ci = paired_bootstrap_ci(raw_combined_df)

    out_xlsx = args.results_dir / f"{args.mode}_evaluation_summary.xlsx"
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        overall_df.to_excel(writer, sheet_name="All_Runs_Per_Seed", index=False)
        fold_summary.to_excel(writer, sheet_name="Fold_Summary_Across_Seeds", index=False)
        cat_summary.to_excel(writer, sheet_name="Per_Category_Summary", index=False)
        pd.DataFrame([bootstrap_ci]).to_excel(writer, sheet_name="Bootstrap_95CI", index=False)

    console_print("\n" + "=" * 80)
    console_print(" FINAL EXPERIMENT SUMMARY (Two-Tier Evaluation Framework)")
    console_print("=" * 80)
    console_print(f"Summary Saved To: {out_xlsx}")
    console_print(f"\nPrimary Tier   - Strict F1 (Standard CoNLL NER): {overall_df['strict_F1'].mean():.4f} +/- {overall_df['strict_F1'].std():.4f}")
    console_print(f"Secondary Tier - ADE-Eval F1 (Clinical Weighted): {overall_df['ade_F1'].mean():.4f} +/- {overall_df['ade_F1'].std():.4f}")

    if bootstrap_ci:
        console_print(f"Strict F1 95% CI:   {bootstrap_ci.get('strict_f1_95ci')}")
        console_print(f"ADE-Eval F1 95% CI: {bootstrap_ci.get('ade_f1_95ci')}")

    console_print("\nPer-Fold Performance (Seed Mean +/- SD):")
    for _, row in fold_summary.iterrows():
        console_print(
            f"  * {row['test_case_series']:<32}: "
            f"Strict F1 = {row['strict_F1_mean']:.4f} +/- {row['strict_F1_std']:.4f} | "
            f"ADE F1 = {row['ade_F1_mean']:.4f} +/- {row['ade_F1_std']:.4f}"
        )


if __name__ == "__main__":
    main()
