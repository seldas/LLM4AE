#!/usr/bin/env python3
"""
run_VAERS_bert.py

True k-fold cross-validation with multiple independent training seeds per fold for BioBERT NER on the VAERS corpus.

Structurally identical to run_FAERS_bert.py; only the dataset path, results path,
label-normalisation table, and eval-category groupings are adapted for VAERS.

Key reliability features (inherited from run_FAERS_bert.py):
  * Clean spaCy training logs: ANSI/terminal control sequences are stripped before
    writing train.log, so the file stays plain UTF-8 text.
  * Stable tqdm output: spaCy stdout is captured and parsed directly instead of
    tailing a colorised log file in a second thread.
  * Multi-GPU safety: one long-lived worker process is pinned to each requested
    GPU and executes its assigned folds sequentially.
  * Correct sentence offsets: uses spaCy Span.start_char/end_char.
  * Consistent label filtering: labels are selected from TRAIN once and reused
    for dev and test.
  * Negative sentences are retained in train/dev/test.
  * Aggregation bug fixed: per-label results carry fold/seed columns.
  * Test inference uses nlp.pipe() and handles empty-alignment edge cases.

Default evaluation: 10-fold CV with 8 folds for training, 1 fold for development, and 1 fold for testing.
The fold partition is fixed across random seeds; seeds affect model training only.

VAERS label taxonomy (SME1 annotations)
----------------------------------------
  SYM        – symptom / adverse event sign
  sDx        – signed/confirmed AE diagnosis
  pDx        – provisional diagnosis (AE)
  DX         – final/confirmed diagnosis (non-AE context)
  MHx        – medical history
  FHx        – family history
  Lab        – laboratory finding / vital
  VAX        – vaccine (causative agent, analogous to Drug in FAERS)
  TEMPO      – temporal expression
  DOSE       – dose / lot number
  STATUS     – patient outcome / status
  TX         – treatment / provider / intervention
  AGE        – patient age
  SEX        – patient sex

Eval categories collapse the fine-grained labels:
  AE         – sym, sdx, pdx
  DX         – dx
  VAX        – vax
  HX         – mhx, fhx
  LAB        – lab
  DOSE       – dose
  STATUS     – status
  TX         – tx
  TEMPORAL   – temporal
  AGE        – age
  SEX        – sex

Examples:
  # Full manuscript run: 10 folds x 5 seeds = 50 training jobs, up to 8 concurrent GPUs
  python scripts/run_VAERS_bert.py --folds 10 --seeds 42 123 456 789 1011 --gpu-ids 0 1 2 3 4 5 6 7

  # Single-GPU smoke test
  python scripts/run_VAERS_bert.py --folds 10 --seeds 42 --gpu-ids 0 --max-steps 1000

Requirements:
  spacy, spacy-transformers, transformers, torch, pandas, openpyxl, tqdm
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
import subprocess
import sys
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import pandas as pd
import spacy
from spacy.tokens import DocBin
from spacy.util import filter_spans
from tqdm import tqdm

# -----------------------------------------------------------------------------
# Project defaults
# -----------------------------------------------------------------------------
BASE = Path("/compute001/lwu/projects/LLM4AE/LLM4AE-dev/publication")
DEFAULT_DATA_DIR = BASE / "Datasets" / "VAERS"
DEFAULT_RESULTS_DIR = BASE / "results" / "bert_runs_VAERS"
DEFAULT_REF_SCORER = BASE / "code/custom_scorer_v5.py"
DEFAULT_TRAIN_PYTHON = sys.executable

_BERT_MODEL_NAME = "dmis-lab/biobert-base-cased-v1.1"
_BERT_MAX_TOKENS = 512

# Any terminal escapes that survive NO_COLOR are removed before log writing.
_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_C0_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Lazy process-local singletons.
_tokenizer = None
_custom_scorer_loaded: Set[str] = set()


# -----------------------------------------------------------------------------
# VAERS label normalisation
# -----------------------------------------------------------------------------
# Maps every raw annotation label seen in SME1 annotations to a canonical
# lowercase string, or to None to explicitly exclude it from training.
RAW_TO_LABEL: Dict[str, Optional[str]] = {
    # ── Primary Diagnosis ───────────────────────────────────────────────────
    "pDx": "pdx",
    "PDX": "pdx",
    "pdx": "pdx",
    "Dx": "pdx",
    # ── Secondary Diagnosis (Second Level) ──────────────────────────────────
    "sDx": "sdx",
    "SDX": "sdx",
    "sdx": "sdx",
    # ── Rule-out Diagnosis ──────────────────────────────────────────────────
    "R/O": "ro",
    "RO": "ro",
    "ro": "ro",
    "r/o": "ro",
    # ── Symptom / Adverse-Event Sign ────────────────────────────────────────
    "SYM": "sym",
    "sym": "sym",
    "SX": "sym",
    "sx": "sym",
    # ── Cause of Death ──────────────────────────────────────────────────────
    "CoD": "cod",
    "COD": "cod",
    "cod": "cod",
    "CAUSE OF DEATH": "cod",
    "cause of death": "cod",
    # ── Laboratory Finding / Diagnostic Instrument ──────────────────────────
    "Lab": "lab",
    "LAB": "lab",
    "lab": "lab",
    # ── Patient Status / Outcome ────────────────────────────────────────────
    "STATUS": "status",
    "Status": "status",
    "status": "status",
    # ── Family History ──────────────────────────────────────────────────────
    "FHx": "fhx",
    "FHX": "fhx",
    "fhx": "fhx",
    "FAMILY HISTORY": "fhx",
    # ── Medical History ─────────────────────────────────────────────────────
    "MHx": "mhx",
    "MHX": "mhx",
    "mhx": "mhx",
    "MEDICAL HISTORY": "mhx",
    # ── Drug Product / Treatment ────────────────────────────────────────────
    "TX": "tx",
    "Tx": "tx",
    "tx": "tx",
    "TREATMENT": "tx",
    "Treatment": "tx",
    "treatment": "tx",
    # ── Vaccine Product ─────────────────────────────────────────────────────
    "VAX": "vax",
    "Vax": "vax",
    "vax": "vax",
    "VACCINE": "vax",
    "Vaccine": "vax",
    "vaccine": "vax",
    # ── Excluded / unsupported legacy metadata tags ─────────────────────────
    "TEMPO": None,
    "Tempo": None,
    "tempo": None,
    "TEMPORAL": None,
    "DOSE": None,
    "Dose": None,
    "dose": None,
    "AGE": None,
    "Age": None,
    "age": None,
    "SEX": None,
    "Sex": None,
    "sex": None,
    "DX": None,
    "dx": None,
}

# Fallback: harmless case/whitespace variations not listed above.
_RAW_TO_LABEL_CASEFOLD = {str(k).strip().casefold(): v for k, v in RAW_TO_LABEL.items()}

# Maps canonical label → broad evaluation category.
EVAL_LABEL_POOL: Dict[str, str] = {
    "pdx": "pDx",
    "sdx": "sDx",
    "ro": "RO",
    "sym": "SYM",
    "cod": "CoD",
    "lab": "Lab",
    "status": "STATUS",
    "fhx": "FHx",
    "mhx": "MHx",
    "tx": "TX",
    "vax": "VAX",
}

_nlp_sent = spacy.blank("en")
_nlp_sent.add_pipe("sentencizer")


# -----------------------------------------------------------------------------
# Console/log helpers
# -----------------------------------------------------------------------------
def clean_terminal_text(text: str) -> str:
    """Remove ANSI terminal escapes, carriage returns and unsafe C0 controls."""
    text = _ANSI_ESCAPE_RE.sub("", text)
    text = text.replace("\r", "")
    return _C0_CONTROL_RE.sub("", text)


def console_print(message: str, *, enabled: bool = True) -> None:
    """Print without corrupting an active tqdm display."""
    if enabled:
        tqdm.write(str(message), file=sys.stdout)


def _tail_text_file(path: Path, n_lines: int = 40) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-n_lines:])


def _progress_enabled(no_progress: bool) -> bool:
    return (not no_progress) and sys.stdout.isatty()


def _load_bert_tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(_BERT_MODEL_NAME)


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = _load_bert_tokenizer()
    return _tokenizer


def _ensure_custom_scorer_loaded(ref_scorer: Path) -> None:
    """Register the custom spaCy scorer once per Python process."""
    key = str(ref_scorer.resolve())
    if key in _custom_scorer_loaded:
        return
    spec = importlib.util.spec_from_file_location(
        f"llm4ae_custom_scorer_{abs(hash(key))}", key
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load custom scorer: {ref_scorer}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _custom_scorer_loaded.add(key)


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------
def _normalize_raw_label(raw_label: object) -> Optional[str]:
    if raw_label is None:
        return None
    raw = str(raw_label).strip()
    if raw in RAW_TO_LABEL:
        return RAW_TO_LABEL[raw]
    return _RAW_TO_LABEL_CASEFOLD.get(raw.casefold())


def load_json_files(data_dir: Path):
    """
    Return (records, stats).

    Each record is (filename, normalised_page_text, SME1_annotations), where
    an annotation is (start, end, canonical_label).  The single-character '↵'
    marker is replaced by '\\n' to preserve character offsets.
    """
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")

    records = []
    stats: Dict[str, int] = defaultdict(int)
    unknown_labels: Dict[str, int] = defaultdict(int)

    files = sorted(data_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON files found in: {data_dir}")

    for fpath in files:
        try:
            with fpath.open(encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as exc:
            raise RuntimeError(f"Failed to read JSON file {fpath}: {exc}") from exc

        pages = doc.get("pages", [])
        if not pages:
            stats["documents_without_pages"] += 1
            page_text = ""
        else:
            page_text = str(pages[0])

        page_text_norm = page_text.replace("↵", "\n")
        sme_anns = []

        for ann in doc.get("annotations", []):
            if ann.get("note") != "SME1":
                continue
            stats["sme1_annotations_seen"] += 1

            raw_label = ann.get("label", "")
            canon = _normalize_raw_label(raw_label)
            if canon is None:
                raw_key = str(raw_label).strip()
                is_known = (
                    raw_key in RAW_TO_LABEL
                    or raw_key.casefold() in _RAW_TO_LABEL_CASEFOLD
                )
                if is_known:
                    stats["explicitly_excluded_labels"] += 1
                else:
                    unknown_labels[raw_key] += 1
                    stats["unknown_or_unmapped_labels"] += 1
                continue

            tc = ann.get("textContext") or {}
            try:
                start = int(tc.get("start"))
                end = int(tc.get("end"))
            except (TypeError, ValueError):
                stats["invalid_offsets"] += 1
                continue

            if start < 0 or start >= end or end > len(page_text):
                stats["invalid_offsets"] += 1
                continue

            sme_anns.append((start, end, canon))
            stats["annotations_kept_after_loading"] += 1

        records.append((fpath.name, page_text_norm, sme_anns))

    stats["documents"] = len(records)
    stats["unknown_label_types"] = len(unknown_labels)
    stats["unknown_labels"] = dict(sorted(unknown_labels.items()))
    return records, dict(stats)


# -----------------------------------------------------------------------------
# Conversion to spaCy format
# -----------------------------------------------------------------------------
def clean_entities(entities, text: str):
    """Strip leading/trailing whitespace from sentence-relative entity spans."""
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


def validate_no_overlap(entities) -> bool:
    ents = sorted(entities, key=lambda x: (x[0], x[1]))
    return all(ents[i][1] <= ents[i + 1][0] for i in range(len(ents) - 1))


def count_labels(records) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for _, _, anns in records:
        for _, _, label in anns:
            counts[label] += 1
    return dict(counts)


def records_to_docbin(
    records,
    *,
    valid_labels: Set[str],
    include_negative_sentences: bool = True,
):
    """
    Convert records to a sentence-level DocBin using a fixed label set.

    valid_labels must be derived from TRAIN once, then reused for dev and test.
    Sentences with no retained entities are kept by default so the model sees
    negative examples and spurious predictions are counted at test time.
    """
    nlp = spacy.blank("en")
    tokenizer = _get_tokenizer()
    db = DocBin(store_user_data=False)
    stats: Dict[str, int] = defaultdict(int)

    for _, text, anns in records:
        doc_sents = _nlp_sent(text)
        crossing_ann_ids: Set[int] = set()

        for sent in doc_sents.sents:
            sent_start = sent.start_char
            sent_end = sent.end_char
            sent_text = text[sent_start:sent_end]
            stats["sentences_seen"] += 1

            if not sent_text.strip():
                stats["blank_sentences_skipped"] += 1
                continue

            n_tokens = len(
                tokenizer(
                    sent_text,
                    add_special_tokens=True,
                    truncation=False,
                )["input_ids"]
            )
            if n_tokens > _BERT_MAX_TOKENS:
                stats["sentences_too_long"] += 1
                continue

            sent_ents = []
            for ann_idx, (start, end, label) in enumerate(anns):
                if label not in valid_labels:
                    continue
                if start >= sent_start and end <= sent_end:
                    sent_ents.append((start - sent_start, end - sent_start, label))
                elif start < sent_end and end > sent_start:
                    crossing_ann_ids.add(ann_idx)

            sent_ents = clean_entities(sent_ents, sent_text)
            if not validate_no_overlap(sent_ents):
                stats["sentences_skipped_overlap"] += 1
                continue

            sent_doc = nlp.make_doc(sent_text)
            spans = []
            alignment_failed = False
            for rel_start, rel_end, label in sent_ents:
                span = sent_doc.char_span(
                    rel_start,
                    rel_end,
                    label=label,
                    alignment_mode="strict",
                )
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

        stats["cross_sentence_entities"] += len(crossing_ann_ids)

    return db, dict(stats)


def format_docbin_stats(name: str, stats: Dict[str, int]) -> str:
    return (
        f"  {name}: sentences={stats.get('sentences_added', 0)}, "
        f"entities={stats.get('entities_added', 0)}, "
        f"negative={stats.get('negative_sentences_added', 0)}, "
        f"too_long={stats.get('sentences_too_long', 0)}, "
        f"overlap_skip={stats.get('sentences_skipped_overlap', 0)}, "
        f"align_skip={stats.get('sentences_skipped_alignment', 0)}, "
        f"cross_sentence_entities={stats.get('cross_sentence_entities', 0)}"
    )


# -----------------------------------------------------------------------------
# Training config
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
batch_size = 32

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
max_batch_items = 4096
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
size = 2000
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


def _parse_spacy_training_row(line: str):
    """Parse spaCy ConsoleLogger rows; return None for non-table lines."""
    parts = line.strip().split()
    if len(parts) < 8:
        return None
    try:
        epoch = int(parts[0])
        step = int(parts[1])
        loss_trans = float(parts[2])
        loss_ner = float(parts[3])
        ents_f = float(parts[4])
        ents_p = float(parts[5])
        ents_r = float(parts[6])
        score = float(parts[7])
    except (TypeError, ValueError):
        return None
    return {
        "epoch": epoch,
        "step": step,
        "loss_trans": loss_trans,
        "loss_ner": loss_ner,
        "ents_f": ents_f,
        "ents_p": ents_p,
        "ents_r": ents_r,
        "score": score,
    }


def run_spacy_train(
    cmd: Sequence[str],
    *,
    log_path: Path,
    max_steps: int,
    fold_idx: int,
    seed: int,
    show_progress: bool,
    console_enabled: bool,
    spacy_console: str,
    progress_callback: Optional[Callable[[dict], None]] = None,
):
    """Run spaCy training, write a clean UTF-8 log, and drive tqdm from parsed rows."""
    log_path.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "NO_COLOR": "1",
            "FORCE_COLOR": "0",
            "TERM": "dumb",
            "PYTHONUNBUFFERED": "1",
        }
    )

    pbar = None
    if show_progress:
        pbar = tqdm(
            total=max_steps,
            desc=f"Fold {fold_idx:02d} seed {seed} train",
            unit="step",
            dynamic_ncols=True,
            leave=True,
            mininterval=0.2,
            file=sys.stdout,
        )

    last_step = 0
    best_f1 = float("-inf")
    last_metrics = None

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

    assert proc.stdout is not None
    with log_path.open("w", encoding="utf-8", newline="\n") as logf:
        for raw_line in proc.stdout:
            clean = clean_terminal_text(raw_line).rstrip("\n")
            logf.write(clean + "\n")
            logf.flush()

            metrics = _parse_spacy_training_row(clean)
            if metrics is not None:
                last_metrics = metrics
                step = max(0, int(metrics["step"]))
                best_f1 = max(best_f1, float(metrics["ents_f"]))
                if pbar is not None and step > last_step:
                    pbar.update(min(step, max_steps) - min(last_step, max_steps))
                    pbar.set_postfix_str(
                        f"F1={metrics['ents_f']:.2f}% best={best_f1:.2f}%"
                    )
                last_step = max(last_step, step)
                if progress_callback is not None:
                    progress_callback(
                        {
                            "type": "train_progress",
                            "fold": fold_idx,
                            "seed": seed,
                            "step": step,
                            "max_steps": max_steps,
                            "best_f1": best_f1,
                            **metrics,
                        }
                    )
                if spacy_console == "all" and console_enabled:
                    console_print(clean)
            elif spacy_console == "all" and console_enabled and clean.strip():
                console_print(clean)

    returncode = proc.wait()

    if pbar is not None:
        prefix = f"Fold {fold_idx:02d} seed {seed}"
        if returncode == 0:
            if last_step >= max_steps:
                pbar.set_description_str(prefix + " train done")
            else:
                pbar.set_description_str(prefix + " train stopped")
        else:
            pbar.set_description_str(prefix + " train FAILED")
        pbar.close()

    if progress_callback is not None:
        progress_callback(
            {
                "type": "train_end",
                "fold": fold_idx,
                "seed": seed,
                "returncode": returncode,
                "last_step": last_step,
                "max_steps": max_steps,
                "best_f1": None if best_f1 == float("-inf") else best_f1,
            }
        )

    return returncode, last_step, last_metrics


# -----------------------------------------------------------------------------
# ADE-style entity alignment and metrics
# -----------------------------------------------------------------------------
def _overlap(a0, a1, b0, b1):
    return (
        (a0 == b0)
        or (a1 == b1)
        or (a0 < b0 < a1)
        or (a0 < b1 < a1)
        or (b0 < a0 < b1)
    )


def align_entities(text, gold_ents, pred_ents):
    rows = []
    gold_sorted = sorted(gold_ents, key=lambda x: (x[0], x[1], x[2]))
    pred_sorted = sorted(pred_ents, key=lambda x: (x[0], x[1], x[2]))
    pred_flag = [False] * len(pred_sorted)

    for g0, g1, glab in gold_sorted:
        exact_j = None
        partial_j = None
        best_ov = 0

        for j, (p0, p1, plab) in enumerate(pred_sorted):
            if pred_flag[j]:
                continue
            if p0 == g0 and p1 == g1 and plab == glab:
                exact_j = j
                break
            if plab == glab and _overlap(g0, g1, p0, p1):
                ov = max(0, min(g1, p1) - max(g0, p0))
                if ov > best_ov:
                    best_ov = ov
                    partial_j = j

        if exact_j is not None:
            p0, p1, plab = pred_sorted[exact_j]
            pred_flag[exact_j] = True
            rows.append(
                dict(
                    match_type="M",
                    label_gold=glab,
                    gold_start=g0,
                    gold_end=g1,
                    gold_text=text[g0:g1],
                    label_pred=plab,
                    pred_start=p0,
                    pred_end=p1,
                    pred_text=text[p0:p1],
                )
            )
        elif partial_j is not None:
            p0, p1, plab = pred_sorted[partial_j]
            pred_flag[partial_j] = True
            rows.append(
                dict(
                    match_type="C",
                    label_gold=glab,
                    gold_start=g0,
                    gold_end=g1,
                    gold_text=text[g0:g1],
                    label_pred=plab,
                    pred_start=p0,
                    pred_end=p1,
                    pred_text=text[p0:p1],
                )
            )
        else:
            rows.append(
                dict(
                    match_type="N",
                    label_gold=glab,
                    gold_start=g0,
                    gold_end=g1,
                    gold_text=text[g0:g1],
                    label_pred=None,
                    pred_start=None,
                    pred_end=None,
                    pred_text=None,
                )
            )

    for j, (p0, p1, plab) in enumerate(pred_sorted):
        if pred_flag[j]:
            continue
        rows.append(
            dict(
                match_type="S",
                label_gold=None,
                gold_start=None,
                gold_end=None,
                gold_text=None,
                label_pred=plab,
                pred_start=p0,
                pred_end=p1,
                pred_text=text[p0:p1],
            )
        )

    return rows


_RAW_COLUMNS = [
    "fold",
    "seed",
    "sent_id",
    "sentence",
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
    "fold",
    "seed",
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


def _weighted_prf(M, C, S, N):
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


def compute_metrics(df: pd.DataFrame, *, fold_idx: int, seed: int):
    if df.empty:
        overall = dict(
            fold=fold_idx,
            seed=seed,
            M=0,
            C=0,
            S=0,
            N=0,
            precision=0.0,
            recall=0.0,
            f1=0.0,
        )
        return overall, pd.DataFrame(columns=_PER_LABEL_COLUMNS)

    cnt = df["match_type"].value_counts().to_dict()
    M = int(cnt.get("M", 0))
    C = int(cnt.get("C", 0))
    S = int(cnt.get("S", 0))
    N = int(cnt.get("N", 0))
    p, r, f1 = _weighted_prf(M, C, S, N)
    overall = dict(
        fold=fold_idx,
        seed=seed,
        M=M,
        C=C,
        S=S,
        N=N,
        precision=p,
        recall=r,
        f1=f1,
    )

    all_labels = set(
        df.loc[df["match_type"].isin(["M", "C", "N"]), "label_gold"].dropna()
    )
    all_labels.update(df.loc[df["match_type"] == "S", "label_pred"].dropna())

    rows = []
    for label in sorted(all_labels):
        M_l = int(((df["match_type"] == "M") & (df["label_gold"] == label)).sum())
        C_l = int(((df["match_type"] == "C") & (df["label_gold"] == label)).sum())
        N_l = int(((df["match_type"] == "N") & (df["label_gold"] == label)).sum())
        S_l = int(((df["match_type"] == "S") & (df["label_pred"] == label)).sum())
        p_l, r_l, f_l = _weighted_prf(M_l, C_l, S_l, N_l)
        rows.append(
            dict(
                fold=fold_idx,
                seed=seed,
                label=label,
                eval_category=EVAL_LABEL_POOL.get(label, label.upper()),
                M=M_l,
                C=C_l,
                S=S_l,
                N=N_l,
                precision=p_l,
                recall=r_l,
                f1=f_l,
            )
        )

    return overall, pd.DataFrame(rows, columns=_PER_LABEL_COLUMNS)


# -----------------------------------------------------------------------------
# Fold execution
# -----------------------------------------------------------------------------
def make_cv_folds(records, n_folds: int, cv_seed: int):
    """
    Create one deterministic, disjoint document-level k-fold partition.

    IMPORTANT: this partition is created once and reused for every training seed.
    Therefore variation across --seeds reflects stochastic model training rather
    than a changing train/test split.
    """
    if n_folds < 3:
        raise ValueError("True train/dev/test k-fold CV requires --folds >= 3")
    if len(records) < n_folds:
        raise ValueError(
            f"Cannot create {n_folds} folds from only {len(records)} documents"
        )

    shuffled = list(records)
    random.Random(cv_seed).shuffle(shuffled)

    # Round-robin allocation after one shuffle keeps fold sizes within one document.
    folds = [[] for _ in range(n_folds)]
    for i, record in enumerate(shuffled):
        folds[i % n_folds].append(record)
    return folds


def get_cv_split(cv_folds, fold_idx: int, dev_fold_offset: int = 1):
    """
    Return train/dev/test records for one outer fold.

    test = fold_idx
    dev  = (fold_idx + dev_fold_offset) % K
    train = all remaining folds

    With K=10 and dev_fold_offset=1, this is exactly 80/10/10. Across the
    complete 10-fold cycle every document is used exactly once for test and once
    for development.
    """
    n_folds = len(cv_folds)
    test_fold_idx = fold_idx
    dev_fold_idx = (fold_idx + dev_fold_offset) % n_folds
    if dev_fold_idx == test_fold_idx:
        raise ValueError("Development fold cannot equal the test fold")

    train_recs = []
    for i, fold_records in enumerate(cv_folds):
        if i not in (test_fold_idx, dev_fold_idx):
            train_recs.extend(fold_records)

    dev_recs = list(cv_folds[dev_fold_idx])
    test_recs = list(cv_folds[test_fold_idx])
    return train_recs, dev_recs, test_recs, dev_fold_idx


def _emit_event(callback, event_type: str, **payload):
    if callback is not None:
        callback({"type": event_type, **payload})


def run_fold(
    *,
    fold_idx: int,
    cv_folds,
    seed: int,
    gpu_id: int,
    max_steps: int,
    work_dir: Path,
    ref_scorer: Path,
    train_python: str,
    dev_fold_offset: int,
    min_label_count: int,
    include_negative_sentences: bool,
    eval_batch_size: int,
    eval_on_gpu: bool,
    show_progress: bool,
    console_enabled: bool,
    spacy_console: str,
    progress_callback: Optional[Callable[[dict], None]] = None,
):
    _emit_event(
        progress_callback,
        "fold_start",
        fold=fold_idx,
        seed=seed,
        gpu_id=gpu_id,
        max_steps=max_steps,
    )

    if console_enabled:
        console_print("")
        console_print("=" * 78)
        console_print(f"FOLD {fold_idx:02d} | seed={seed} | GPU={gpu_id}")
        console_print("=" * 78)

    # Seed-specific run directory prevents collisions when multiple seeds from
    # the same fold execute concurrently on different GPUs.
    run_dir = work_dir / f"fold_{fold_idx:02d}" / f"seed_{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)

    train_recs, dev_recs, test_recs, dev_fold_idx = get_cv_split(
        cv_folds, fold_idx, dev_fold_offset
    )
    if console_enabled:
        console_print(
            f"  CV split: train={len(train_recs)}, dev={len(dev_recs)} "
            f"(fold {dev_fold_idx:02d}), test={len(test_recs)} "
            f"(fold {fold_idx:02d})"
        )

    # Persist the exact document split for reproducibility.
    split_manifest = {
        "fold": fold_idx,
        "seed": seed,
        "dev_fold": dev_fold_idx,
        "test_fold": fold_idx,
        "train_documents": [r[0] for r in train_recs],
        "dev_documents": [r[0] for r in dev_recs],
        "test_documents": [r[0] for r in test_recs],
    }
    (run_dir / "split_manifest.json").write_text(
        json.dumps(split_manifest, indent=2), encoding="utf-8"
    )

    # Derive the model label set from TRAIN only and reuse it everywhere.
    train_label_counts = count_labels(train_recs)
    valid_labels = {
        label
        for label, count in train_label_counts.items()
        if count >= min_label_count
    }
    if not valid_labels:
        raise RuntimeError(
            f"No labels meet min_label_count={min_label_count} in fold {fold_idx}."
        )

    excluded_counts = {
        k: v for k, v in train_label_counts.items() if k not in valid_labels
    }
    if console_enabled:
        console_print(f"  Training labels ({len(valid_labels)}): {sorted(valid_labels)}")
        if excluded_counts:
            console_print(
                f"  Excluded rare train labels: {dict(sorted(excluded_counts.items()))}"
            )

    _emit_event(
        progress_callback,
        "stage",
        fold=fold_idx,
        seed=seed,
        gpu_id=gpu_id,
        stage="docbin",
    )

    train_db, train_stats = records_to_docbin(
        train_recs,
        valid_labels=valid_labels,
        include_negative_sentences=include_negative_sentences,
    )
    dev_db, dev_stats = records_to_docbin(
        dev_recs,
        valid_labels=valid_labels,
        include_negative_sentences=include_negative_sentences,
    )
    test_db, test_stats = records_to_docbin(
        test_recs,
        valid_labels=valid_labels,
        include_negative_sentences=include_negative_sentences,
    )

    if console_enabled:
        console_print(format_docbin_stats("train", train_stats))
        console_print(format_docbin_stats("dev  ", dev_stats))
        console_print(format_docbin_stats("test ", test_stats))

    if train_stats.get("sentences_added", 0) == 0:
        raise RuntimeError(f"Fold {fold_idx}, seed {seed}: training DocBin is empty")
    if dev_stats.get("sentences_added", 0) == 0:
        raise RuntimeError(f"Fold {fold_idx}, seed {seed}: dev DocBin is empty")
    if test_stats.get("sentences_added", 0) == 0:
        raise RuntimeError(f"Fold {fold_idx}, seed {seed}: test DocBin is empty")

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
    )
    cfg_path = run_dir / "train.cfg"
    cfg_path.write_text(cfg_text, encoding="utf-8")

    model_dir = run_dir / "model"
    log_path = run_dir / "train.log"
    cmd = [
        train_python,
        "-m",
        "spacy",
        "train",
        str(cfg_path),
        "--output",
        str(model_dir),
        "--gpu-id",
        str(gpu_id),
        "--code",
        str(ref_scorer),
    ]

    if console_enabled:
        console_print(f"  Training log: {log_path}")
        console_print(f"  Command: {' '.join(cmd)}")

    _emit_event(
        progress_callback,
        "stage",
        fold=fold_idx,
        seed=seed,
        gpu_id=gpu_id,
        stage="train",
    )

    returncode, last_step, last_metrics = run_spacy_train(
        cmd,
        log_path=log_path,
        max_steps=max_steps,
        fold_idx=fold_idx,
        seed=seed,
        show_progress=show_progress,
        console_enabled=console_enabled,
        spacy_console=spacy_console,
        progress_callback=progress_callback,
    )

    if returncode != 0:
        tail = _tail_text_file(log_path, 40)
        message = (
            f"Fold {fold_idx}, seed {seed}: spaCy training exited with code "
            f"{returncode}. See {log_path}."
        )
        if console_enabled:
            console_print(f"  ERROR: {message}")
            if tail:
                console_print("  Last clean log lines:\n" + tail)
        raise RuntimeError(message)

    if console_enabled:
        if last_step < max_steps:
            console_print(
                f"  Training completed at step {last_step}/{max_steps} "
                "(spaCy early stopping/patience may have triggered)."
            )
        else:
            console_print(f"  Training completed at step {last_step}/{max_steps}.")
        if last_metrics:
            console_print(
                f"  Last dev row: ENTS_F={last_metrics['ents_f']:.2f}% "
                f"P={last_metrics['ents_p']:.2f}% R={last_metrics['ents_r']:.2f}% "
                f"SCORE={last_metrics['score']:.4f}"
            )

    best_model_path = model_dir / "model-best"
    if not best_model_path.exists():
        raise FileNotFoundError(f"model-best not found: {best_model_path}")

    _emit_event(
        progress_callback,
        "stage",
        fold=fold_idx,
        seed=seed,
        gpu_id=gpu_id,
        stage="eval",
    )

    _ensure_custom_scorer_loaded(ref_scorer)

    if eval_on_gpu:
        try:
            spacy.require_gpu(gpu_id)
            if console_enabled:
                console_print(f"  Test inference device: GPU {gpu_id}")
        except Exception as exc:
            if console_enabled:
                console_print(
                    f"  WARNING: could not place evaluation on GPU {gpu_id}; "
                    f"falling back to CPU ({exc})"
                )
            spacy.require_cpu()
    else:
        spacy.require_cpu()
        if console_enabled:
            console_print("  Test inference device: CPU")

    nlp_eval = spacy.load(str(best_model_path))
    nlp_blank = spacy.blank("en")
    test_gold_docs = list(DocBin().from_disk(test_path).get_docs(nlp_blank.vocab))

    all_rows = []
    text_iter = (doc.text for doc in test_gold_docs)
    pred_iter = nlp_eval.pipe(text_iter, batch_size=eval_batch_size)

    eval_iter = zip(test_gold_docs, pred_iter)
    if show_progress:
        eval_iter = tqdm(
            eval_iter,
            total=len(test_gold_docs),
            desc=f"Fold {fold_idx:02d} seed {seed} eval",
            unit="sent",
            dynamic_ncols=True,
            leave=False,
            file=sys.stdout,
        )

    for sent_id, (gold_doc, pred_doc) in enumerate(eval_iter):
        text = gold_doc.text
        gold_ents = [(e.start_char, e.end_char, e.label_) for e in gold_doc.ents]
        pred_ents = [(e.start_char, e.end_char, e.label_) for e in pred_doc.ents]
        rows = align_entities(text, gold_ents, pred_ents)
        for row in rows:
            row["fold"] = fold_idx
            row["seed"] = seed
            row["sent_id"] = sent_id
            row["sentence"] = text
        all_rows.extend(rows)

    raw_df = pd.DataFrame(all_rows, columns=_RAW_COLUMNS)
    overall, per_label_df = compute_metrics(raw_df, fold_idx=fold_idx, seed=seed)

    if console_enabled:
        console_print(
            f"  Test overall: P={overall['precision']:.4f} "
            f"R={overall['recall']:.4f} F1={overall['f1']:.4f} "
            f"(M={overall['M']}, C={overall['C']}, S={overall['S']}, N={overall['N']})"
        )

    # Release evaluation model before the next job on this worker/GPU.
    del nlp_eval
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass

    _emit_event(
        progress_callback,
        "fold_done",
        fold=fold_idx,
        seed=seed,
        gpu_id=gpu_id,
        overall=overall,
    )
    return raw_df, overall, per_label_df


# -----------------------------------------------------------------------------
# Output and aggregation
# -----------------------------------------------------------------------------
def save_fold(
    results_dir: Path,
    fold_idx: int,
    seed: int,
    raw_df: pd.DataFrame,
    overall: dict,
    per_label_df: pd.DataFrame,
    *,
    console_enabled: bool = True,
):
    results_dir.mkdir(parents=True, exist_ok=True)
    stem = f"fold_{fold_idx:02d}_seed_{seed}"
    raw_xlsx = results_dir / f"{stem}_raw.xlsx"
    perf_xlsx = results_dir / f"{stem}_metrics.xlsx"

    with pd.ExcelWriter(raw_xlsx, engine="openpyxl") as writer:
        raw_df.to_excel(writer, sheet_name="Raw_Results", index=False)
    with pd.ExcelWriter(perf_xlsx, engine="openpyxl") as writer:
        pd.DataFrame([overall]).to_excel(writer, sheet_name="Overall", index=False)
        per_label_df.to_excel(writer, sheet_name="Per_Label", index=False)

    if console_enabled:
        console_print(f"  Saved: {raw_xlsx.name} | {perf_xlsx.name}")


def _add_prf_from_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Add weighted precision/recall/F1 to a dataframe containing M/C/S/N."""
    if df.empty:
        return df
    prf = df.apply(
        lambda row: pd.Series(
            _weighted_prf(row.M, row.C, row.S, row.N),
            index=["precision", "recall", "f1"],
        ),
        axis=1,
    )
    out = df.copy()
    out[["precision", "recall", "f1"]] = prf
    return out


def build_overall_summary(
    results_dir: Path,
    all_overall: List[dict],
    all_per_label_dfs: List[pd.DataFrame],
    *,
    expected_folds: int,
):
    """
    Aggregate 10-fold x N-seed results in a manuscript-friendly way.

    The key headline table is Per_Seed_Pooled: for each seed, M/C/S/N are pooled
    across all test folds first, then micro P/R/F1 are computed. Mean +/- SD
    across those seed-level pooled metrics isolates training-seed variability
    while every document contributes exactly once to test for each seed.
    """
    if not all_overall:
        raise RuntimeError("No successful fold/seed runs are available for aggregation")

    overall_df = (
        pd.DataFrame(all_overall)
        .sort_values(["seed", "fold"])
        .reset_index(drop=True)
    )

    per_seed_counts = (
        overall_df.groupby("seed", as_index=False)
        .agg(
            folds_completed=("fold", "nunique"),
            M=("M", "sum"),
            C=("C", "sum"),
            S=("S", "sum"),
            N=("N", "sum"),
        )
    )
    per_seed_pooled = _add_prf_from_counts(per_seed_counts)
    per_seed_pooled["complete"] = per_seed_pooled["folds_completed"] == expected_folds

    complete_seed_df = per_seed_pooled[per_seed_pooled["complete"]].copy()
    seed_source = complete_seed_df if not complete_seed_df.empty else per_seed_pooled
    overall_seed_summary = pd.DataFrame(
        [
            {
                "expected_folds_per_seed": expected_folds,
                "seeds_complete": int(per_seed_pooled["complete"].sum()),
                "seeds_total": int(len(per_seed_pooled)),
                "precision_mean": seed_source["precision"].mean(),
                "precision_std": seed_source["precision"].std(ddof=1)
                if len(seed_source) > 1
                else 0.0,
                "recall_mean": seed_source["recall"].mean(),
                "recall_std": seed_source["recall"].std(ddof=1)
                if len(seed_source) > 1
                else 0.0,
                "f1_mean": seed_source["f1"].mean(),
                "f1_std": seed_source["f1"].std(ddof=1)
                if len(seed_source) > 1
                else 0.0,
            }
        ]
    ).round(4)

    nonempty_label_frames = [df for df in all_per_label_dfs if not df.empty]
    if nonempty_label_frames:
        combined_per_label = pd.concat(nonempty_label_frames, ignore_index=True)

        label_per_seed_counts = (
            combined_per_label.groupby(
                ["seed", "label", "eval_category"], as_index=False
            )
            .agg(
                folds_completed=("fold", "nunique"),
                M=("M", "sum"),
                C=("C", "sum"),
                S=("S", "sum"),
                N=("N", "sum"),
            )
        )
        label_per_seed = _add_prf_from_counts(label_per_seed_counts)
        # A label need not occur in every test fold. Seed completeness is therefore
        # determined from the overall fold/seed runs, not from label-specific fold
        # presence. folds_completed remains informational for each label.
        complete_seed_values = set(
            per_seed_pooled.loc[per_seed_pooled["complete"], "seed"].tolist()
        )
        label_per_seed["complete_seed"] = label_per_seed["seed"].isin(
            complete_seed_values
        )

        label_summary_source = label_per_seed[
            label_per_seed["complete_seed"]
        ].copy()
        if label_summary_source.empty:
            label_summary_source = label_per_seed
        label_summary = (
            label_summary_source.groupby(["label", "eval_category"], as_index=False)
            .agg(
                seeds_present=("seed", "nunique"),
                precision_mean=("precision", "mean"),
                precision_std=("precision", "std"),
                recall_mean=("recall", "mean"),
                recall_std=("recall", "std"),
                f1_mean=("f1", "mean"),
                f1_std=("f1", "std"),
            )
            .round(4)
        )

        category_per_run = (
            combined_per_label.groupby(
                ["seed", "fold", "eval_category"], as_index=False
            )
            .agg(M=("M", "sum"), C=("C", "sum"), S=("S", "sum"), N=("N", "sum"))
        )
        category_per_run = _add_prf_from_counts(category_per_run)

        category_per_seed_counts = (
            category_per_run.groupby(["seed", "eval_category"], as_index=False)
            .agg(
                folds_completed=("fold", "nunique"),
                M=("M", "sum"),
                C=("C", "sum"),
                S=("S", "sum"),
                N=("N", "sum"),
            )
        )
        category_per_seed = _add_prf_from_counts(category_per_seed_counts)
        category_per_seed["complete_seed"] = category_per_seed["seed"].isin(
            complete_seed_values
        )

        category_summary_source = category_per_seed[
            category_per_seed["complete_seed"]
        ].copy()
        if category_summary_source.empty:
            category_summary_source = category_per_seed
        category_summary = (
            category_summary_source.groupby("eval_category", as_index=False)
            .agg(
                seeds_present=("seed", "nunique"),
                precision_mean=("precision", "mean"),
                precision_std=("precision", "std"),
                recall_mean=("recall", "mean"),
                recall_std=("recall", "std"),
                f1_mean=("f1", "mean"),
                f1_std=("f1", "std"),
            )
            .round(4)
        )
    else:
        combined_per_label = pd.DataFrame(columns=_PER_LABEL_COLUMNS)
        label_per_seed = pd.DataFrame()
        label_summary = pd.DataFrame()
        category_per_run = pd.DataFrame()
        category_per_seed = pd.DataFrame()
        category_summary = pd.DataFrame()

    for df in (label_summary, category_summary):
        if not df.empty:
            std_cols = [c for c in df.columns if c.endswith("_std")]
            df[std_cols] = df[std_cols].fillna(0.0)

    summary_xlsx = results_dir / "overall_summary.xlsx"
    with pd.ExcelWriter(summary_xlsx, engine="openpyxl") as writer:
        overall_df.to_excel(writer, sheet_name="Per_Run_Overall", index=False)
        per_seed_pooled.to_excel(writer, sheet_name="Per_Seed_Pooled", index=False)
        overall_seed_summary.to_excel(writer, sheet_name="Overall_Seed_Summary", index=False)
        label_per_seed.to_excel(writer, sheet_name="Per_Label_Per_Seed", index=False)
        label_summary.to_excel(writer, sheet_name="Per_Label_Summary", index=False)
        category_per_run.to_excel(writer, sheet_name="Category_Per_Run", index=False)
        category_per_seed.to_excel(writer, sheet_name="Category_Per_Seed", index=False)
        category_summary.to_excel(writer, sheet_name="Category_Summary", index=False)

    return (
        summary_xlsx,
        overall_df,
        per_seed_pooled,
        overall_seed_summary,
        label_summary,
        category_summary,
    )


# -----------------------------------------------------------------------------
# Multi-GPU orchestration
# -----------------------------------------------------------------------------
def _gpu_worker_loop(
    gpu_id: int,
    fold_kwargs_list: List[dict],
    results_dir: str,
    event_queue,
    result_queue,
):
    """One worker process owns one GPU and runs its assigned fold/seed jobs sequentially."""

    def callback(event: dict):
        event_queue.put(event)

    for kwargs in fold_kwargs_list:
        fold_idx = kwargs["fold_idx"]
        seed = kwargs["seed"]
        try:
            raw_df, overall, per_label_df = run_fold(
                **kwargs,
                show_progress=False,
                console_enabled=False,
                progress_callback=callback,
            )
            save_fold(
                Path(results_dir),
                fold_idx,
                seed,
                raw_df,
                overall,
                per_label_df,
                console_enabled=False,
            )
            result_queue.put(
                {
                    "type": "result",
                    "fold": fold_idx,
                    "seed": seed,
                    "gpu_id": gpu_id,
                    "overall": overall,
                    "per_label": per_label_df,
                }
            )
        except Exception:
            tb = traceback.format_exc()
            event_queue.put(
                {
                    "type": "fold_failed",
                    "fold": fold_idx,
                    "seed": seed,
                    "gpu_id": gpu_id,
                    "traceback": tb,
                }
            )
            result_queue.put(
                {
                    "type": "result",
                    "fold": fold_idx,
                    "seed": seed,
                    "gpu_id": gpu_id,
                    "overall": None,
                    "per_label": None,
                    "error": tb,
                }
            )

    event_queue.put({"type": "worker_done", "gpu_id": gpu_id})


def run_multi_gpu(
    fold_kwargs_list: List[dict],
    gpu_ids: List[int],
    results_dir: Path,
    max_steps: int,
    no_progress: bool,
):
    """
    Run up to one training process per GPU concurrently.

    Jobs are assigned round-robin before workers start. Each GPU has exactly one
    long-lived worker, so two BioBERT jobs are never launched simultaneously on
    the same GPU by this script.
    """
    ctx = mp.get_context("spawn")
    event_queue = ctx.Queue()
    result_queue = ctx.Queue()

    assignments = {gpu_id: [] for gpu_id in gpu_ids}
    for kwargs in fold_kwargs_list:
        assignments[kwargs["gpu_id"]].append(kwargs)

    active_gpu_ids = [gpu for gpu in gpu_ids if assignments[gpu]]
    processes = []
    for gpu_id in active_gpu_ids:
        proc = ctx.Process(
            target=_gpu_worker_loop,
            args=(
                gpu_id,
                assignments[gpu_id],
                str(results_dir),
                event_queue,
                result_queue,
            ),
            name=f"llm4ae-gpu-{gpu_id}",
        )
        proc.start()
        processes.append(proc)

    use_bars = _progress_enabled(no_progress)
    job_bar = tqdm(
        total=len(fold_kwargs_list),
        desc="All fold/seed jobs",
        unit="job",
        position=0,
        dynamic_ncols=True,
        disable=not use_bars,
        file=sys.stdout,
    )
    gpu_bars = {}
    gpu_last_step = {}
    for pos, gpu_id in enumerate(active_gpu_ids, start=1):
        gpu_bars[gpu_id] = tqdm(
            total=max_steps,
            desc=f"GPU {gpu_id}: waiting",
            unit="step",
            position=pos,
            dynamic_ncols=True,
            leave=True,
            disable=not use_bars,
            file=sys.stdout,
        )
        gpu_last_step[gpu_id] = 0

    completed_results = {}
    n_received = 0

    def handle_event(event):
        event_type = event.get("type")
        gpu_id = event.get("gpu_id")
        fold_idx = event.get("fold")
        seed = event.get("seed")
        bar = gpu_bars.get(gpu_id)
        run_label = (
            f"F{int(fold_idx):02d} S{seed}"
            if fold_idx is not None and seed is not None
            else "waiting"
        )

        if event_type == "fold_start" and bar is not None:
            bar.reset(total=max_steps)
            gpu_last_step[gpu_id] = 0
            bar.set_description_str(f"GPU {gpu_id} | {run_label}")
            bar.set_postfix_str("starting")
        elif event_type == "train_progress" and bar is not None:
            step = int(event.get("step", 0))
            previous = gpu_last_step.get(gpu_id, 0)
            if step > previous:
                bar.update(min(step, max_steps) - min(previous, max_steps))
                gpu_last_step[gpu_id] = step
            best_f1 = event.get("best_f1")
            current_f1 = event.get("ents_f")
            if best_f1 is not None and current_f1 is not None:
                bar.set_postfix_str(f"F1={current_f1:.2f}% best={best_f1:.2f}%")
        elif event_type == "stage" and bar is not None:
            stage = event.get("stage", "")
            bar.set_description_str(f"GPU {gpu_id} | {run_label} {stage}")
        elif event_type == "train_end" and bar is not None:
            last_step = event.get("last_step", 0)
            rc = event.get("returncode", 0)
            state = "train done" if rc == 0 else "TRAIN FAILED"
            bar.set_postfix_str(f"{state} @ {last_step}/{max_steps}")
        elif event_type == "fold_done" and bar is not None:
            overall = event.get("overall") or {}
            bar.set_description_str(f"GPU {gpu_id} | {run_label} done")
            bar.set_postfix_str(f"test F1={overall.get('f1', 0.0):.4f}")
        elif event_type == "fold_failed":
            console_print(f"Fold {fold_idx:02d}, seed {seed} on GPU {gpu_id} FAILED")
            tb = event.get("traceback", "")
            if tb:
                console_print(tb)

    while n_received < len(fold_kwargs_list):
        while True:
            try:
                handle_event(event_queue.get_nowait())
            except queue.Empty:
                break

        try:
            result = result_queue.get(timeout=0.25)
        except queue.Empty:
            if all(not proc.is_alive() for proc in processes):
                while True:
                    try:
                        handle_event(event_queue.get_nowait())
                    except queue.Empty:
                        break
                if n_received < len(fold_kwargs_list):
                    break
            continue

        n_received += 1
        fold_idx = result["fold"]
        seed = result["seed"]
        key = (fold_idx, seed)
        if result.get("overall") is not None:
            completed_results[key] = (result["overall"], result["per_label"])
            overall = result["overall"]
            job_bar.update(1)
            console_print(
                f"Completed fold {fold_idx:02d}, seed {seed} on GPU {result['gpu_id']}: "
                f"P={overall['precision']:.4f} R={overall['recall']:.4f} "
                f"F1={overall['f1']:.4f}"
            )
        else:
            job_bar.update(1)
            console_print(f"Skipping failed fold {fold_idx:02d}, seed {seed}.")

    for proc in processes:
        proc.join()

    job_bar.close()
    for bar in gpu_bars.values():
        bar.close()

    if n_received < len(fold_kwargs_list):
        expected = {(x["fold_idx"], x["seed"]) for x in fold_kwargs_list}
        missing = sorted(expected - set(completed_results))
        console_print(
            "WARNING: one or more GPU workers exited before reporting every job. "
            f"Inspect per-run logs. Missing/failed jobs may include: {missing}"
        )

    return completed_results


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "BioBERT NER true k-fold cross-validation on VAERS with multiple "
            "independent training seeds per fold and one worker per GPU."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Recommended manuscript run:\n"
            "  python scripts/run_VAERS_bert.py --folds 10 "
            "--seeds 42 123 456 789 1011 --gpu-ids 0 1 2 3 4 5 6 7\n\n"
            "For 10 folds, each run uses 8 train folds + 1 dev fold + 1 test fold. "
            "The document partition is fixed across seeds."
        ),
    )
    parser.add_argument(
        "--folds",
        type=int,
        default=10,
        help="Number of disjoint CV folds. Default: 10 (80/10/10 train/dev/test per run).",
    )
    parser.add_argument(
        "--cv-seed",
        type=int,
        default=42,
        help=(
            "Seed used ONCE to create the document-level fold partition. "
            "This is separate from model training seeds. Default: 42."
        ),
    )
    parser.add_argument(
        "--dev-fold-offset",
        type=int,
        default=1,
        help=(
            "Development fold is (test_fold + offset) mod K. Default: 1. "
            "With K=10 this yields 80/10/10."
        ),
    )
    parser.add_argument(
        "--gpu-ids",
        type=int,
        nargs="+",
        default=[0],
        help=(
            "GPU IDs. One long-lived worker is created per GPU. Example for the "
            "full node: --gpu-ids 0 1 2 3 4 5 6 7"
        ),
    )
    parser.add_argument("--max-steps", type=int, default=20000)
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[42, 123, 456, 789, 1011],
        help=(
            "Independent model-training seeds applied to EVERY fold. "
            "Default: 42 123 456 789 1011."
        ),
    )
    parser.add_argument(
        "--min-label-count",
        type=int,
        default=5,
        help="Minimum count in TRAIN for a label to be modelled (default 5).",
    )
    parser.add_argument(
        "--positive-only",
        action="store_true",
        help=(
            "Compatibility mode: omit sentences with no retained gold entity. "
            "Not recommended because it biases NER false-positive evaluation."
        ),
    )
    parser.add_argument("--eval-batch-size", type=int, default=32)
    parser.add_argument(
        "--eval-on-cpu",
        action="store_true",
        help="Evaluate model-best on CPU instead of the run's GPU.",
    )
    parser.add_argument(
        "--spacy-console",
        choices=("progress", "all"),
        default="progress",
        help=(
            "progress: show only clean tqdm/status output (default); "
            "all: also echo every cleaned spaCy training line."
        ),
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable tqdm bars. Bars are also auto-disabled when stdout is not a TTY.",
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--ref-scorer", type=Path, default=DEFAULT_REF_SCORER)
    parser.add_argument(
        "--train-python",
        type=str,
        default=DEFAULT_TRAIN_PYTHON,
        help="Python executable used for `python -m spacy train`.",
    )
    return parser.parse_args()


def validate_args(args):
    if args.folds < 3:
        raise ValueError("--folds must be >= 3 for train/dev/test k-fold CV")
    if args.max_steps < 1:
        raise ValueError("--max-steps must be >= 1")
    if args.min_label_count < 1:
        raise ValueError("--min-label-count must be >= 1")
    if args.eval_batch_size < 1:
        raise ValueError("--eval-batch-size must be >= 1")
    if not args.gpu_ids:
        raise ValueError("At least one --gpu-ids value is required")
    if len(set(args.gpu_ids)) != len(args.gpu_ids):
        raise ValueError("--gpu-ids contains duplicates; each GPU ID must appear once")
    if any(gpu_id < 0 for gpu_id in args.gpu_ids):
        raise ValueError("--gpu-ids values must be >= 0")
    if not args.seeds:
        raise ValueError("At least one --seeds value is required")
    if len(set(args.seeds)) != len(args.seeds):
        raise ValueError("--seeds contains duplicates")
    if args.dev_fold_offset % args.folds == 0:
        raise ValueError("--dev-fold-offset must not select the same fold as test")

    if not Path(args.train_python).exists():
        raise FileNotFoundError(f"--train-python does not exist: {args.train_python}")
    if not args.ref_scorer.exists():
        raise FileNotFoundError(f"Custom scorer not found: {args.ref_scorer}")


def write_experiment_manifest(args, cv_folds, seeds):
    manifest = {
        "model": _BERT_MODEL_NAME,
        "folds": args.folds,
        "cv_seed": args.cv_seed,
        "training_seeds": list(seeds),
        "dev_fold_offset": args.dev_fold_offset,
        "gpu_ids": list(args.gpu_ids),
        "max_steps": args.max_steps,
        "train_fraction": (args.folds - 2) / args.folds,
        "dev_fraction": 1 / args.folds,
        "test_fraction": 1 / args.folds,
        "fold_documents": {
            str(i): [record[0] for record in fold_records]
            for i, fold_records in enumerate(cv_folds)
        },
    }
    path = args.results_dir / "experiment_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def main():
    args = parse_args()
    validate_args(args)

    args.results_dir.mkdir(parents=True, exist_ok=True)
    work_dir = args.results_dir / "workdir"
    work_dir.mkdir(parents=True, exist_ok=True)

    seeds = list(args.seeds)

    console_print(f"Loading JSON files from {args.data_dir}")
    records, load_stats = load_json_files(args.data_dir)
    console_print(
        f"Loaded {len(records)} documents; retained "
        f"{load_stats.get('annotations_kept_after_loading', 0)} SME1 annotations."
    )
    if load_stats.get("unknown_or_unmapped_labels", 0):
        console_print(
            f"WARNING: skipped {load_stats['unknown_or_unmapped_labels']} annotations "
            f"with unmapped labels: {load_stats.get('unknown_labels', {})}"
        )

    cv_folds = make_cv_folds(records, args.folds, args.cv_seed)
    fold_sizes = [len(x) for x in cv_folds]
    manifest_path = write_experiment_manifest(args, cv_folds, seeds)

    gpu_ids = list(args.gpu_ids)
    n_jobs = args.folds * len(seeds)
    n_workers = min(len(gpu_ids), n_jobs)
    console_print(
        f"True {args.folds}-fold CV x {len(seeds)} seeds = {n_jobs} training jobs"
    )
    console_print(
        f"Fold sizes={fold_sizes} | cv_seed={args.cv_seed} | "
        f"dev_fold_offset={args.dev_fold_offset}"
    )
    console_print(
        f"GPUs={gpu_ids} | active GPU workers={n_workers} | max_steps={args.max_steps}"
    )
    console_print(
        f"Per run fractions: train={(args.folds - 2) / args.folds:.0%}, "
        f"dev={1 / args.folds:.0%}, test={1 / args.folds:.0%}"
    )
    console_print(f"Training seeds: {seeds}")
    console_print(f"Train python: {args.train_python}")
    console_print(f"Results dir: {args.results_dir}")
    console_print(f"Experiment manifest: {manifest_path}")

    # Build one job for every (fold, seed) combination. The same cv_folds object
    # is reused for all seeds, so the held-out documents never change with seed.
    fold_kwargs_list = []
    task_idx = 0
    for fold_idx in range(args.folds):
        for seed in seeds:
            gpu_id = gpu_ids[task_idx % len(gpu_ids)]
            fold_kwargs_list.append(
                dict(
                    fold_idx=fold_idx,
                    cv_folds=cv_folds,
                    seed=seed,
                    gpu_id=gpu_id,
                    max_steps=args.max_steps,
                    work_dir=work_dir,
                    ref_scorer=args.ref_scorer,
                    train_python=args.train_python,
                    dev_fold_offset=args.dev_fold_offset,
                    min_label_count=args.min_label_count,
                    include_negative_sentences=not args.positive_only,
                    eval_batch_size=args.eval_batch_size,
                    eval_on_gpu=not args.eval_on_cpu,
                    spacy_console=args.spacy_console,
                )
            )
            task_idx += 1

    all_overall: List[dict] = []
    all_per_label_dfs: List[pd.DataFrame] = []

    if len(gpu_ids) == 1:
        # Sequential mode: clean local tqdm bars and immediate detailed messages.
        for kwargs in fold_kwargs_list:
            fold_idx = kwargs["fold_idx"]
            seed = kwargs["seed"]
            try:
                raw_df, overall, per_label_df = run_fold(
                    **kwargs,
                    show_progress=_progress_enabled(args.no_progress),
                    console_enabled=True,
                    progress_callback=None,
                )
                save_fold(
                    args.results_dir,
                    fold_idx,
                    seed,
                    raw_df,
                    overall,
                    per_label_df,
                    console_enabled=True,
                )
                all_overall.append(overall)
                all_per_label_dfs.append(per_label_df)
            except Exception:
                console_print(
                    f"Fold {fold_idx:02d}, seed {seed} FAILED:\n{traceback.format_exc()}"
                )
    else:
        # Multi-GPU mode: one worker owns each GPU and runs its queue sequentially.
        completed = run_multi_gpu(
            fold_kwargs_list,
            gpu_ids,
            args.results_dir,
            args.max_steps,
            args.no_progress,
        )
        for key in sorted(completed, key=lambda x: (x[1], x[0])):
            overall, per_label_df = completed[key]
            all_overall.append(overall)
            all_per_label_dfs.append(per_label_df)

    if not all_overall:
        raise SystemExit(
            "No fold/seed jobs completed successfully. Inspect "
            "workdir/fold_*/seed_*/train.log"
        )

    (
        summary_xlsx,
        overall_df,
        per_seed_pooled,
        overall_seed_summary,
        label_summary,
        category_summary,
    ) = build_overall_summary(
        args.results_dir,
        all_overall,
        all_per_label_dfs,
        expected_folds=args.folds,
    )

    console_print("")
    console_print(f"Saved overall summary: {summary_xlsx}")
    console_print("=== POOLED OUT-OF-FOLD MICRO METRICS BY TRAINING SEED ===")
    for _, row in per_seed_pooled.sort_values("seed").iterrows():
        state = "complete" if bool(row["complete"]) else "INCOMPLETE"
        console_print(
            f"Seed {int(row['seed']):>6}: P={row['precision']:.4f} "
            f"R={row['recall']:.4f} F1={row['f1']:.4f} "
            f"folds={int(row['folds_completed'])}/{args.folds} [{state}]"
        )

    headline = overall_seed_summary.iloc[0]
    console_print("=== MEAN +/- SD ACROSS COMPLETE TRAINING SEEDS ===")
    console_print(
        f"Precision: {headline['precision_mean']:.4f} +/- {headline['precision_std']:.4f}"
    )
    console_print(
        f"Recall   : {headline['recall_mean']:.4f} +/- {headline['recall_std']:.4f}"
    )
    console_print(
        f"F1       : {headline['f1_mean']:.4f} +/- {headline['f1_std']:.4f}"
    )
    console_print(
        f"Complete seeds: {int(headline['seeds_complete'])}/{int(headline['seeds_total'])}"
    )

    if not label_summary.empty:
        console_print("Per-label pooled-across-folds mean F1 across seeds:")
        for _, row in label_summary.sort_values("f1_mean", ascending=False).iterrows():
            console_print(
                f"  {row['label']:<22} [{row['eval_category']:<10}] "
                f"F1={row['f1_mean']:.3f}+/-{row['f1_std']:.3f} "
                f"P={row['precision_mean']:.3f} R={row['recall_mean']:.3f} "
                f"seeds={int(row['seeds_present'])}"
            )

    if not category_summary.empty:
        console_print("Collapsed category pooled-across-folds mean F1 across seeds:")
        for _, row in category_summary.sort_values("f1_mean", ascending=False).iterrows():
            console_print(
                f"  {row['eval_category']:<12} "
                f"F1={row['f1_mean']:.3f}+/-{row['f1_std']:.3f} "
                f"P={row['precision_mean']:.3f} R={row['recall_mean']:.3f} "
                f"seeds={int(row['seeds_present'])}"
            )


if __name__ == "__main__":
    main()
