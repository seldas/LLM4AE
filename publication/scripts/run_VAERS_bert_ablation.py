#!/usr/bin/env python3
"""
run_VAERS_bert_ablation.py

Multi-GPU Parallel Ablation Study of Pretrained Transformer Encoders on the VAERS Dataset:
Compares 4 BERT model variants:
  1. BioBERT (dmis-lab/biobert-base-cased-v1.1)
  2. ClinicalBERT (medicalai/ClinicalBERT)
  3. BERT-Base (bert-base-cased)
  4. Bio_ClinicalBERT (emilyalsentzer/Bio_ClinicalBERT)

Evaluation Protocol:
  - 5 independent random train/test splits (seeds: 42, 123, 456, 789, 1011)
  - Split: 80% train, 10% dev (checkpoint selection / early stopping), 10% test (1000 total samples)
  - All models trained with original/default hyperparameters:
      * Learning rate: 1e-4 with linear warmup
      * Optimizer: Adam (beta1=0.9, beta2=0.999, L2 weight decay=0.01)
      * Batch size: 32 (max_batch_items: 4096)
      * Max steps: 8000 (eval_frequency: 200, patience: 1600)
      * Tokenizer max tokens: 512 (with strided sliding window)
  - Multi-GPU Parallel Execution:
      * Up to 8 concurrent GPU worker processes (pinned 1-worker-per-GPU)
      * Multi-bar live tqdm monitoring per GPU
  - Dual-tier Evaluation:
      * Primary Tier: Strict Exact-Match NER (CoNLL exact boundary + exact label)
      * Secondary Tier: Adapted ADE-Eval (Clinical partial credit: M=1.0, C=0.5, S=0.25, N=0.0)

Results saved to:
  `results/bert_replim_VAERS/`

Usage:
  # Multi-GPU run (e.g. 8 GPUs: 4 models x 5 seeds = 20 jobs parallelized)
  python publication/scripts/run_VAERS_bert_ablation.py --gpu-ids 0 1 2 3 4 5 6 7

  # Single-GPU run
  python publication/scripts/run_VAERS_bert_ablation.py --gpu-ids 0

  # Custom models or seeds
  python publication/scripts/run_VAERS_bert_ablation.py --models BioBERT Bio_ClinicalBERT --seeds 42 123 --gpu-ids 0 1
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
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd
import spacy
from spacy.tokens import DocBin
from spacy.util import filter_spans
from tqdm import tqdm


# ==============================================================================
# DEFAULT MODEL CONFIGURATIONS & PATHS
# ==============================================================================

BERT_MODELS = {
    "BioBERT": "dmis-lab/biobert-base-cased-v1.1",
    "ClinicalBERT": "medicalai/ClinicalBERT",
    "BERT": "bert-base-cased",
    "Bio_ClinicalBERT": "emilyalsentzer/Bio_ClinicalBERT",
}

DEFAULT_SEEDS = [42, 123, 456, 789, 1011]
DEFAULT_MAX_STEPS = 8000
_BERT_MAX_TOKENS = 512

# ANSI escape stripper for clean UTF-8 log output
_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_C0_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_nlp_sent = spacy.blank("en")
_nlp_sent.add_pipe("sentencizer")


# ==============================================================================
# VAERS LABEL NORMALIZATION & EVAL CATEGORIES
# ==============================================================================

RAW_TO_LABEL: Dict[str, Optional[str]] = {
    "SYM": "sym", "sym": "sym",
    "sDx": "sdx", "SDX": "sdx", "sdx": "sdx",
    "pDx": "pdx", "PDX": "pdx", "pdx": "pdx",
    "DX": "dx", "dx": "dx", "Dx": "dx",
    "VAX": "vax", "vax": "vax", "Vax": "vax",
    "MHx": "mhx", "MHX": "mhx", "mhx": "mhx", "MEDICAL HISTORY": "mhx",
    "FHx": "fhx", "FHX": "fhx", "fhx": "fhx", "FAMILY HISTORY": "fhx",
    "Lab": "lab", "LAB": "lab", "lab": "lab",
    "TEMPO": "temporal", "tempo": "temporal", "Tempo": "temporal", "TEMPORAL": "temporal",
    "DOSE": "dose", "Dose": "dose", "dose": "dose",
    "STATUS": "status", "Status": "status", "status": "status",
    "TX": "tx", "Tx": "tx", "tx": "tx", "TREATMENT": "tx", "Treatment": "tx", "treatment": "tx",
    "AGE": "age", "Age": "age", "age": "age",
    "SEX": "sex", "Sex": "sex", "sex": "sex",
    "R/O": None, "RO": None, "CAUSE OF DEATH": None, "CoD": None, "COD": None,
}

_RAW_TO_LABEL_CASEFOLD = {str(k).strip().casefold(): v for k, v in RAW_TO_LABEL.items()}

EVAL_LABEL_POOL: Dict[str, str] = {
    "sym": "AE",
    "sdx": "AE",
    "pdx": "AE",
    "dx": "DX",
    "vax": "VAX",
    "mhx": "HX",
    "fhx": "HX",
    "lab": "LAB",
    "dose": "DOSE",
    "status": "STATUS",
    "tx": "TX",
    "temporal": "TEMPORAL",
    "age": "AGE",
    "sex": "SEX",
}


# ==============================================================================
# SPACY TRAINING CONFIG TEMPLATE
# ==============================================================================

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
name = "{hf_model_name}"
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


# ==============================================================================
# UTILITIES & DATA LOADING
# ==============================================================================

def clean_terminal_text(text: str) -> str:
    text = _ANSI_ESCAPE_RE.sub("", text)
    text = text.replace("\r", "")
    return _C0_CONTROL_RE.sub("", text)


def console_print(message: str) -> None:
    tqdm.write(str(message), file=sys.stdout)


def _normalize_raw_label(raw_label: object) -> Optional[str]:
    if raw_label is None:
        return None
    raw = str(raw_label).strip()
    if raw in RAW_TO_LABEL:
        return RAW_TO_LABEL[raw]
    return _RAW_TO_LABEL_CASEFOLD.get(raw.casefold())


def load_vaers_records(data_dir: Path):
    if not data_dir.exists():
        raise FileNotFoundError(f"VAERS data directory not found: {data_dir}")

    files = sorted(data_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON files found in {data_dir}")

    records = []
    for fpath in files:
        with fpath.open("r", encoding="utf-8") as f:
            doc = json.load(f)

        pages = doc.get("pages", [])
        page_text = str(pages[0]) if pages else ""
        page_text_norm = page_text.replace("↵", "\n")

        sme_anns = []
        for ann in doc.get("annotations", []):
            if ann.get("note") != "SME1":
                continue
            raw_label = ann.get("label", "")
            canon = _normalize_raw_label(raw_label)
            if canon is None:
                continue

            tc = ann.get("textContext") or {}
            try:
                start = int(tc.get("start"))
                end = int(tc.get("end"))
            except (TypeError, ValueError):
                continue

            if 0 <= start < end <= len(page_text):
                sme_anns.append((start, end, canon))

        records.append((fpath.name, page_text_norm, sme_anns))

    return records


def clean_entities(entities, text: str):
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


def records_to_docbin(records, valid_labels: Set[str], hf_model_name: str, include_negative: bool = True):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(hf_model_name)
    nlp = spacy.blank("en")
    db = DocBin(store_user_data=False)
    stats = defaultdict(int)

    for _, text, anns in records:
        doc_sents = _nlp_sent(text)
        for sent in doc_sents.sents:
            sent_start, sent_end = sent.start_char, sent.end_char
            sent_text = text[sent_start:sent_end]
            if not sent_text.strip():
                continue

            tokens = tokenizer(sent_text, add_special_tokens=True, truncation=False)["input_ids"]
            if len(tokens) > _BERT_MAX_TOKENS:
                stats["too_long"] += 1
                continue

            sent_ents = [
                (start - sent_start, end - sent_start, label)
                for start, end, label in anns
                if label in valid_labels and start >= sent_start and end <= sent_end
            ]
            sent_ents = clean_entities(sent_ents, sent_text)
            if not validate_no_overlap(sent_ents):
                continue

            sent_doc = nlp.make_doc(sent_text)
            spans = []
            align_fail = False
            for s_start, s_end, label in sent_ents:
                span = sent_doc.char_span(s_start, s_end, label=label, alignment_mode="strict")
                if span is None:
                    align_fail = True
                    break
                spans.append(span)

            if align_fail:
                continue

            spans = filter_spans(spans)
            sent_doc.ents = spans

            if spans or include_negative:
                db.add(sent_doc)
                stats["sentences"] += 1
                stats["entities"] += len(spans)

    return db, dict(stats)


# ==============================================================================
# SCORING & METRICS (Strict Exact-Match & Adapted ADE-Eval)
# ==============================================================================

def _overlap(a0, a1, b0, b1):
    return (a0 == b0) or (a1 == b1) or (a0 < b0 < a1) or (a0 < b1 < a1) or (b0 < a0 < b1)


def align_entities(text: str, gold_ents: list, pred_ents: list):
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
            rows.append(dict(match_type="M", label_gold=glab, gold_start=g0, gold_end=g1, gold_text=text[g0:g1],
                             label_pred=plab, pred_start=p0, pred_end=p1, pred_text=text[p0:p1]))
        elif partial_j is not None:
            p0, p1, plab = pred_sorted[partial_j]
            pred_flag[partial_j] = True
            rows.append(dict(match_type="C", label_gold=glab, gold_start=g0, gold_end=g1, gold_text=text[g0:g1],
                             label_pred=plab, pred_start=p0, pred_end=p1, pred_text=text[p0:p1]))
        else:
            rows.append(dict(match_type="N", label_gold=glab, gold_start=g0, gold_end=g1, gold_text=text[g0:g1],
                             label_pred=None, pred_start=None, pred_end=None, pred_text=None))

    for j, (p0, p1, plab) in enumerate(pred_sorted):
        if not pred_flag[j]:
            rows.append(dict(match_type="S", label_gold=None, gold_start=None, gold_end=None, gold_text=None,
                             label_pred=plab, pred_start=p0, pred_end=p1, pred_text=text[p0:p1]))

    return rows


def compute_metrics(raw_df: pd.DataFrame, model_name: str, seed: int):
    cnt = raw_df["match_type"].value_counts().to_dict()
    M = int(cnt.get("M", 0))
    C = int(cnt.get("C", 0))
    S = int(cnt.get("S", 0))
    N = int(cnt.get("N", 0))

    # Tier 1: Strict Exact-Match (M only)
    strict_p = M / (M + S) if (M + S) > 0 else 0.0
    strict_r = M / (M + N) if (M + N) > 0 else 0.0
    strict_f1 = (2 * strict_p * strict_r / (strict_p + strict_r)) if (strict_p + strict_r) > 0 else 0.0

    # Tier 2: Adapted ADE-Eval (M=1.0, C=0.5, S=0.25, N=0.0)
    matched_credit = M + 0.5 * C
    spurious_weight = 0.25 * S
    ade_p_den = matched_credit + 0.5 * C + spurious_weight
    ade_r_den = matched_credit + 0.5 * C + N
    ade_p = matched_credit / ade_p_den if ade_p_den > 0 else 0.0
    ade_r = matched_credit / ade_r_den if ade_r_den > 0 else 0.0
    ade_f1 = (2 * ade_p * ade_r / (ade_p + ade_r)) if (ade_p + ade_r) > 0 else 0.0

    overall = {
        "model": model_name,
        "seed": seed,
        "M": M, "C": C, "S": S, "N": N,
        "strict_precision": round(strict_p, 4),
        "strict_recall": round(strict_r, 4),
        "strict_f1": round(strict_f1, 4),
        "ade_precision": round(ade_p, 4),
        "ade_recall": round(ade_r, 4),
        "ade_f1": round(ade_f1, 4),
    }

    # Per-Category Evaluation
    all_cats = sorted(set(EVAL_LABEL_POOL.values()))
    cat_rows = []
    
    raw_df["cat_gold"] = raw_df["label_gold"].map(EVAL_LABEL_POOL)
    raw_df["cat_pred"] = raw_df["label_pred"].map(EVAL_LABEL_POOL)

    for cat in all_cats:
        M_c = int(((raw_df["match_type"] == "M") & (raw_df["cat_gold"] == cat)).sum())
        C_c = int(((raw_df["match_type"] == "C") & (raw_df["cat_gold"] == cat)).sum())
        N_c = int(((raw_df["match_type"] == "N") & (raw_df["cat_gold"] == cat)).sum())
        S_c = int(((raw_df["match_type"] == "S") & (raw_df["cat_pred"] == cat)).sum())

        s_p = M_c / (M_c + S_c) if (M_c + S_c) > 0 else 0.0
        s_r = M_c / (M_c + N_c) if (M_c + N_c) > 0 else 0.0
        s_f = (2 * s_p * s_r / (s_p + s_r)) if (s_p + s_r) > 0 else 0.0

        m_cred = M_c + 0.5 * C_c
        a_p_den = m_cred + 0.5 * C_c + 0.25 * S_c
        a_r_den = m_cred + 0.5 * C_c + N_c
        a_p = m_cred / a_p_den if a_p_den > 0 else 0.0
        a_r = m_cred / a_r_den if a_r_den > 0 else 0.0
        a_f = (2 * a_p * a_r / (a_p + a_r)) if (a_p + a_r) > 0 else 0.0

        cat_rows.append({
            "model": model_name,
            "seed": seed,
            "category": cat,
            "M": M_c, "C": C_c, "S": S_c, "N": N_c,
            "strict_precision": round(s_p, 4),
            "strict_recall": round(s_r, 4),
            "strict_f1": round(s_f, 4),
            "ade_precision": round(a_p, 4),
            "ade_recall": round(a_r, 4),
            "ade_f1": round(a_f, 4),
        })

    return overall, pd.DataFrame(cat_rows)


# ==============================================================================
# SINGLE RUN EXECUTION
# ==============================================================================

def run_single_job(
    model_name: str,
    hf_model_name: str,
    seed: int,
    records: list,
    split_ratios: tuple[float, float, float],
    max_steps: int,
    gpu_id: int,
    work_dir: Path,
    ref_scorer_path: Path,
    progress_callback: Optional[Callable[[dict], None]] = None,
):
    run_dir = work_dir / model_name / f"seed_{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)

    if progress_callback:
        progress_callback({"type": "job_start", "model": model_name, "seed": seed, "gpu_id": gpu_id})

    # 1. Deterministic Split for this seed
    shuffled = list(records)
    random.Random(seed).shuffle(shuffled)
    n_total = len(shuffled)
    n_train = int(n_total * split_ratios[0])
    n_dev = int(n_total * split_ratios[1])
    
    train_recs = shuffled[:n_train]
    dev_recs = shuffled[n_train:n_train + n_dev]
    test_recs = shuffled[n_train + n_dev:]

    # Extract valid labels
    label_counts = defaultdict(int)
    for _, _, anns in train_recs:
        for _, _, label in anns:
            label_counts[label] += 1
    valid_labels = {k for k, v in label_counts.items() if v >= 3}

    # Build DocBins
    train_db, _ = records_to_docbin(train_recs, valid_labels, hf_model_name)
    dev_db, _ = records_to_docbin(dev_recs, valid_labels, hf_model_name)
    test_db, _ = records_to_docbin(test_recs, valid_labels, hf_model_name)

    train_path = run_dir / "train.spacy"
    dev_path = run_dir / "dev.spacy"
    test_path = run_dir / "test.spacy"
    train_db.to_disk(train_path)
    dev_db.to_disk(dev_path)
    test_db.to_disk(test_path)

    # Write Config
    cfg_text = CONFIG_TEMPLATE.format(
        train_path=str(train_path).replace("\\", "/"),
        dev_path=str(dev_path).replace("\\", "/"),
        hf_model_name=hf_model_name,
        seed=seed,
        max_steps=max_steps,
    )
    cfg_path = run_dir / "train.cfg"
    cfg_path.write_text(cfg_text, encoding="utf-8")

    model_dir = run_dir / "model"
    log_path = run_dir / "train.log"

    cmd = [
        sys.executable, "-m", "spacy", "train",
        str(cfg_path),
        "--output", str(model_dir),
        "--gpu-id", str(gpu_id),
    ]
    if ref_scorer_path.exists():
        cmd.extend(["--code", str(ref_scorer_path)])

    env = os.environ.copy()
    env.update({"NO_COLOR": "1", "PYTHONUNBUFFERED": "1"})

    with open(log_path, "w", encoding="utf-8") as f_log:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        for line in proc.stdout:
            clean_l = clean_terminal_text(line)
            f_log.write(clean_l + "\n")
            f_log.flush()
            
            # Parse step progress for live updates
            parts = clean_l.strip().split()
            if len(parts) >= 8 and parts[0].isdigit() and parts[1].isdigit():
                try:
                    step = int(parts[1])
                    f1_score = float(parts[4])
                    if progress_callback:
                        progress_callback({"type": "train_step", "model": model_name, "seed": seed,
                                           "gpu_id": gpu_id, "step": step, "f1": f1_score})
                except Exception:
                    pass
        proc.wait()

    if proc.returncode != 0:
        raise RuntimeError(f"Training failed for {model_name} seed {seed}. Check {log_path}")

    # Evaluate model-best
    best_model = model_dir / "model-best"
    if not best_model.exists():
        raise FileNotFoundError(f"Model best not found: {best_model}")

    if gpu_id >= 0:
        try:
            spacy.require_gpu(gpu_id)
        except Exception:
            spacy.require_cpu()
    else:
        spacy.require_cpu()

    nlp_eval = spacy.load(str(best_model))
    nlp_blank = spacy.blank("en")
    test_docs = list(DocBin().from_disk(test_path).get_docs(nlp_blank.vocab))

    all_rows = []
    text_iter = (d.text for d in test_docs)
    pred_iter = nlp_eval.pipe(text_iter, batch_size=64)

    for sent_id, (gold_doc, pred_doc) in enumerate(zip(test_docs, pred_iter)):
        g_ents = [(e.start_char, e.end_char, e.label_) for e in gold_doc.ents]
        p_ents = [(e.start_char, e.end_char, e.label_) for e in pred_doc.ents]
        rows = align_entities(gold_doc.text, g_ents, p_ents)
        for r in rows:
            r["model"] = model_name
            r["seed"] = seed
            r["sent_id"] = sent_id
            r["sentence"] = gold_doc.text
        all_rows.extend(rows)

    raw_df = pd.DataFrame(all_rows)
    overall, cat_df = compute_metrics(raw_df, model_name, seed)

    # Save run results
    raw_xlsx = run_dir / f"{model_name}_seed_{seed}_raw.xlsx"
    perf_xlsx = run_dir / f"{model_name}_seed_{seed}_metrics.xlsx"
    with pd.ExcelWriter(raw_xlsx, engine="openpyxl") as w:
        raw_df.to_excel(w, sheet_name="Raw_Results", index=False)
    with pd.ExcelWriter(perf_xlsx, engine="openpyxl") as w:
        pd.DataFrame([overall]).to_excel(w, sheet_name="Overall", index=False)
        cat_df.to_excel(w, sheet_name="Categories", index=False)

    if progress_callback:
        progress_callback({"type": "job_done", "model": model_name, "seed": seed, "gpu_id": gpu_id, "overall": overall})

    del nlp_eval
    gc.collect()
    return overall, cat_df


# ==============================================================================
# MULTI-GPU WORKER POOL
# ==============================================================================

def _gpu_worker_loop(gpu_id: int, task_list: list[dict], event_queue, result_queue):
    for task in task_list:
        m_name = task["model_name"]
        seed = task["seed"]
        try:
            overall, cat_df = run_single_job(
                model_name=m_name,
                hf_model_name=task["hf_model_name"],
                seed=seed,
                records=task["records"],
                split_ratios=task["split_ratios"],
                max_steps=task["max_steps"],
                gpu_id=gpu_id,
                work_dir=task["work_dir"],
                ref_scorer_path=task["ref_scorer_path"],
                progress_callback=lambda evt: event_queue.put(evt),
            )
            result_queue.put({"status": "success", "model": m_name, "seed": seed, "overall": overall, "cat_df": cat_df})
        except Exception:
            tb = traceback.format_exc()
            event_queue.put({"type": "job_failed", "model": m_name, "seed": seed, "gpu_id": gpu_id, "traceback": tb})
            result_queue.put({"status": "failed", "model": m_name, "seed": seed, "error": tb})

    event_queue.put({"type": "worker_done", "gpu_id": gpu_id})


def run_parallel_ablation(task_list: list[dict], gpu_ids: list[int], max_steps: int):
    ctx = mp.get_context("spawn")
    event_queue = ctx.Queue()
    result_queue = ctx.Queue()

    # Distribute tasks round-robin across available GPU IDs
    assignments = {gpu_id: [] for gpu_id in gpu_ids}
    for idx, task in enumerate(task_list):
        gpu_id = gpu_ids[idx % len(gpu_ids)]
        assignments[gpu_id].append(task)

    active_gpus = [g for g in gpu_ids if assignments[g]]
    processes = []
    for g_id in active_gpus:
        proc = ctx.Process(
            target=_gpu_worker_loop,
            args=(g_id, assignments[g_id], event_queue, result_queue),
            name=f"bert-ablation-gpu-{g_id}",
        )
        proc.start()
        processes.append(proc)

    # Master progress bar & Per-GPU status bars
    job_bar = tqdm(total=len(task_list), desc="Total Ablation Runs", unit="job", position=0, dynamic_ncols=True)
    gpu_bars = {}
    for pos, g_id in enumerate(active_gpus, start=1):
        gpu_bars[g_id] = tqdm(total=max_steps, desc=f"GPU {g_id}: initializing", unit="step", position=pos, dynamic_ncols=True, leave=True)

    all_overalls = []
    all_cats = []
    n_completed = 0

    while n_completed < len(task_list):
        while True:
            try:
                evt = event_queue.get_nowait()
                e_type = evt.get("type")
                g_id = evt.get("gpu_id")
                bar = gpu_bars.get(g_id)
                
                if e_type == "job_start" and bar:
                    bar.reset(total=max_steps)
                    bar.set_description_str(f"GPU {g_id} | {evt['model']} (S{evt['seed']})")
                elif e_type == "train_step" and bar:
                    bar.n = evt.get("step", 0)
                    bar.set_postfix_str(f"F1={evt.get('f1', 0.0):.2f}%")
                    bar.refresh()
                elif e_type == "job_done" and bar:
                    bar.set_postfix_str(f"Strict F1={evt['overall']['strict_f1']:.4f}")
                elif e_type == "job_failed":
                    console_print(f"\n[ERROR] Job {evt['model']} Seed {evt['seed']} FAILED on GPU {g_id}:\n{evt.get('traceback')}")
            except queue.Empty:
                break

        try:
            res = result_queue.get(timeout=0.25)
            n_completed += 1
            job_bar.update(1)
            if res["status"] == "success":
                all_overalls.append(res["overall"])
                all_cats.append(res["cat_df"])
                console_print(f"✓ Completed {res['model']} (Seed {res['seed']}) -> Strict F1: {res['overall']['strict_f1']:.4f} | Adapted ADE F1: {res['overall']['ade_f1']:.4f}")
            else:
                console_print(f"✗ Failed {res['model']} (Seed {res['seed']})")
        except queue.Empty:
            if all(not p.is_alive() for p in processes):
                break

    for p in processes:
        p.join()

    job_bar.close()
    for bar in gpu_bars.values():
        bar.close()

    return all_overalls, all_cats


# ==============================================================================
# MASTER SUMMARY EXCEL BUILDER
# ==============================================================================

def build_master_summary(results_dir: Path, all_overalls: list[dict], all_cats: list[pd.DataFrame]):
    if not all_overalls:
        print("No completed runs found to summarize.")
        return

    df_overalls = pd.DataFrame(all_overalls)
    df_cats = pd.concat(all_cats, ignore_index=True)

    summary_rows = []
    for model, grp in df_overalls.groupby("model"):
        summary_rows.append({
            "Model Variant": model,
            "Pretrained HuggingFace Checkpoint": BERT_MODELS.get(model, model),
            "Runs (Seeds Completed)": len(grp),
            "Strict Exact F1 (Mean ± SD)": f"{grp['strict_f1'].mean():.4f} ± {grp['strict_f1'].std():.4f}",
            "Strict Precision": f"{grp['strict_precision'].mean():.4f} ± {grp['strict_precision'].std():.4f}",
            "Strict Recall": f"{grp['strict_recall'].mean():.4f} ± {grp['strict_recall'].std():.4f}",
            "Adapted ADE F1 (Mean ± SD)": f"{grp['ade_f1'].mean():.4f} ± {grp['ade_f1'].std():.4f}",
            "Adapted Precision": f"{grp['ade_precision'].mean():.4f} ± {grp['ade_precision'].std():.4f}",
            "Adapted Recall": f"{grp['ade_recall'].mean():.4f} ± {grp['ade_recall'].std():.4f}",
        })
    df_model_summary = pd.DataFrame(summary_rows)

    cat_summary = (
        df_cats.groupby(["model", "category"], as_index=False)
        .agg(
            strict_f1_mean=("strict_f1", "mean"),
            strict_f1_std=("strict_f1", "std"),
            ade_f1_mean=("ade_f1", "mean"),
            ade_f1_std=("ade_f1", "std"),
            strict_p_mean=("strict_precision", "mean"),
            strict_r_mean=("strict_recall", "mean"),
            ade_p_mean=("ade_precision", "mean"),
            ade_r_mean=("ade_recall", "mean"),
        )
        .round(4)
    )

    out_xlsx = results_dir / "bert_model_ablation_summary.xlsx"
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df_model_summary.to_excel(writer, sheet_name="Model_Comparison_Overall", index=False)
        df_overalls.to_excel(writer, sheet_name="Per_Run_All_Models", index=False)
        cat_summary.to_excel(writer, sheet_name="Category_Summary_By_Model", index=False)
        df_cats.to_excel(writer, sheet_name="All_Runs_Categories", index=False)

    print(f"\n=======================================================")
    print(f"Master Ablation Summary written to:\n  {out_xlsx}")
    print(f"=======================================================\n")
    print(df_model_summary.to_string(index=False))


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Multi-GPU Parallel Ablation Analysis of BERT Models on VAERS")
    parser.add_argument("--data-dir", type=str, default=None, help="Path to VAERS JSON dataset directory")
    parser.add_argument("--results-dir", type=str, default=None, help="Output directory for ablation results")
    parser.add_argument("--models", nargs="+", default=list(BERT_MODELS.keys()), choices=list(BERT_MODELS.keys()),
                        help="BERT model variants to benchmark")
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS, help="Random initialization seeds")
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS, help="Max spaCy training steps per run")
    parser.add_argument("--gpu-ids", nargs="+", type=int, default=[0, 1, 2, 3, 4, 5, 6, 7], help="GPU device IDs for parallel execution")
    parser.add_argument("--split", nargs=3, type=float, default=[0.8, 0.1, 0.1], help="Train/Dev/Test split ratios")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    data_dir = Path(args.data_dir) if args.data_dir else repo_root / "Datasets" / "VAERS"
    if not data_dir.exists():
        data_dir = repo_root / "publication" / "Datasets" / "VAERS"

    results_dir = Path(args.results_dir) if args.results_dir else repo_root / "results" / "bert_replim_VAERS"
    results_dir.mkdir(parents=True, exist_ok=True)

    ref_scorer_path = repo_root / "publication" / "code" / "custom_scorer_v5.py"

    print("=================================================================")
    print("Multi-GPU BERT Model Ablation Study on VAERS (N = 1,000 Reports)")
    print(f"Models to Evaluate: {args.models}")
    print(f"Random Seeds:       {args.seeds} (Total Runs: {len(args.models) * len(args.seeds)})")
    print(f"Active GPU IDs:     {args.gpu_ids} ({len(args.gpu_ids)} GPUs)")
    print(f"Data Directory:     {data_dir}")
    print(f"Results Directory:  {results_dir}")
    print("=================================================================")

    records = load_vaers_records(data_dir)
    print(f"Loaded {len(records)} VAERS narratives.")

    # Prepare job list
    task_list = []
    for model_name in args.models:
        hf_model = BERT_MODELS[model_name]
        for seed in args.seeds:
            task_list.append({
                "model_name": model_name,
                "hf_model_name": hf_model,
                "seed": seed,
                "records": records,
                "split_ratios": tuple(args.split),
                "max_steps": args.max_steps,
                "work_dir": results_dir,
                "ref_scorer_path": ref_scorer_path,
            })

    if len(args.gpu_ids) > 1:
        all_overalls, all_cats = run_parallel_ablation(task_list, args.gpu_ids, args.max_steps)
    else:
        all_overalls = []
        all_cats = []
        gpu_id = args.gpu_ids[0]
        for task in task_list:
            overall, cat_df = run_single_job(
                model_name=task["model_name"],
                hf_model_name=task["hf_model_name"],
                seed=task["seed"],
                records=task["records"],
                split_ratios=task["split_ratios"],
                max_steps=task["max_steps"],
                gpu_id=gpu_id,
                work_dir=results_dir,
                ref_scorer_path=ref_scorer_path,
            )
            all_overalls.append(overall)
            all_cats.append(cat_df)

    build_master_summary(results_dir, all_overalls, all_cats)


if __name__ == "__main__":
    main()
