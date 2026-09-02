#!/usr/bin/env python3
"""Generate publication-ready Figure 3: Overall Performance Comparison on FAERS.

Computes metrics directly from raw spans and predictions according to the
canonical Two-Tier Evaluation Framework:
- 'M': Exact boundary & exact category match.
- 'C': Partial boundary match (C_boundary) OR category misclassification with gold overlap (C_class).
- 'S': Spurious prediction with zero gold overlap (S_non_overlap).
- 'N': Missed gold entity with zero pred overlap.

Data sources:
1. Ground Truth (SME1) & ETHER baseline: SQLite database (publication/dataset.db)
2. LLaMA-4 predictions: publication/results/llama4_runs_FAERS/predictions.jsonl (or raw)
3. Claude 4.6 Sonnet predictions: publication/results/sonnet_runs_FAERS/predictions.jsonl (or raw)

Outputs:
- publication/manuscripts/Figures/figure3.png
- publication/manuscripts/Figures/figure3_data.json
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Keep Matplotlib's cache outside the repository and avoid lock issues
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "llm4ae-matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH_DEFAULT = PROJECT_ROOT / "dataset.db"
RESULTS_DIR_DEFAULT = PROJECT_ROOT / "results"
FIGURE_OUTPUT_DIR_DEFAULT = PROJECT_ROOT / "manuscripts" / "Figures"

# 17 Fine-grained clinical concept categories for Panel (a)
CATS_17 = [
    ("sDrug", "sdrug"),
    ("cDrug", "cdrug"),
    ("oDrug", "odrug"),
    ("Dose", "dose"),
    ("Indication", "indication"),
    ("Treatment", "treatment"),
    ("AE", "ae"),
    ("mAE", "mae"),
    ("Dx", "diagnostic"),
    ("Lab", "lab"),
    ("Status", "status"),
    ("R/O", "ro"),
    ("CoD", "cod"),
    ("MHx", "mhx"),
    ("FHx", "fhx"),
    ("Age", "age"),
    ("Sex", "sex"),
]

# Raw ground truth mapping to standard 17 categories (with bSYM -> diagnostic)
RAW_GOLD_MAP_17 = {
    "ae": "ae", "mae": "mae", "mae": "mae",
    "sdrug": "sdrug", "cdrug": "cdrug", "odrug": "odrug", "drug": "odrug",
    "dose": "dose", "indication": "indication", "treatment": "treatment",
    "diagnostic": "diagnostic", "dx": "diagnostic", "bsym": "diagnostic", "baseline symptom": "diagnostic",
    "lab": "lab", "status": "status", "ro": "ro", "r/o": "ro",
    "cod": "cod", "cause of death": "cod",
    "mhx": "mhx", "medical history": "mhx", "fhx": "fhx", "family history": "fhx",
    "age": "age", "sex": "sex",
}

# Raw LLM label mapping to standard 17 categories
RAW_LLM_MAP_17 = {
    "ae": "ae", "mae": "mae",
    "sdrug": "sdrug", "cdrug": "cdrug", "odrug": "odrug", "drug": "odrug",
    "dose": "dose", "indication": "indication", "treatment": "treatment",
    "diagnostic": "diagnostic", "dx": "diagnostic", "bsym": "diagnostic",
    "lab": "lab", "status": "status", "ro": "ro", "r/o": "ro",
    "cod": "cod", "cause of death": "cod",
    "mhx": "mhx", "fhx": "fhx", "age": "age", "sex": "sex",
}

# Combined 4 schemas for Panel (b) Head-to-Head comparison
LABEL_TO_COMBINED_SCHEMA = {
    "ae": "AE", "mae": "AE",
    "sdrug": "DRUG", "cdrug": "DRUG", "odrug": "DRUG", "drug": "DRUG", "treatment": "DRUG",
    "diagnostic": "DX", "dx": "DX", "bsym": "DX", "baseline symptom": "DX",
    "mhx": "HX", "medical history": "HX", "fhx": "HX", "family history": "HX",
}

ETHER_LABEL_TO_COMBINED_SCHEMA = {
    "symptom": "AE",
    "drug": "DRUG", "vaccine": "DRUG",
    "diagnosis": "DX", "second_level_diagnosis": "DX",
    "medical_history": "HX", "family_history": "HX",
}

COMBINED_PANEL_B_CATS = [
    ("AE\n(AE + mAE)", "AE"),
    ("DRUG\n(sDrug + cDrug + oDrug + Tx)", "DRUG"),
    ("DX", "DX"),
    ("HX\n(MHx + FHx)", "HX"),
]


def spans_overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    """True if span A overlaps span B."""
    return (a0 == b0) or (a1 == b1) or (a0 < b0 < a1) or (a0 < b1 < a1) or (b0 < a0 < b1)


def align_and_classify_spans(
    text: str,
    gold_ents: List[Tuple[int, int, str]],
    pred_ents: List[Tuple[int, int, str, float]],
) -> List[dict]:
    """Align gold and predicted spans into the paper's Two-Tier error taxonomy:
    
    - 'M': Exact boundary AND exact category match.
    - 'C': Inexact boundary (C_boundary) OR category misclassification with overlap (C_class).
    - 'S': Spurious ungrounded prediction with zero gold overlap (Non-overlapping FP).
    - 'N': Missed gold entity with zero pred overlap (False Negative).
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
            if spans_overlap(g0, g1, p0, p1):
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
            })
        elif diff_label_partial_j is not None:
            p0, p1, plab, pconf = pred_sorted[diff_label_partial_j]
            pred_used[diff_label_partial_j] = True
            rows.append({
                # Category misclassification on overlapping entity is treated as Conflation (C), NOT Spurious (S)
                "match_type": "C",
                "error_subtype": "class_confusion",
                "label_gold": glab,
                "gold_start": g0, "gold_end": g1, "gold_text": text[g0:g1],
                "label_pred": plab,
                "pred_start": p0, "pred_end": p1, "pred_text": text[p0:p1],
            })
        else:
            rows.append({
                "match_type": "N",
                "error_subtype": "missed",
                "label_gold": glab,
                "gold_start": g0, "gold_end": g1, "gold_text": text[g0:g1],
                "label_pred": None,
                "pred_start": None, "pred_end": None, "pred_text": None,
            })

    for j, (p0, p1, plab, pconf) in enumerate(pred_sorted):
        if not pred_used[j]:
            rows.append({
                "match_type": "S",
                "error_subtype": "non_overlap_spurious",
                "label_gold": None,
                "gold_start": None, "gold_end": None, "gold_text": None,
                "label_pred": plab,
                "pred_start": p0, "pred_end": p1, "pred_text": text[p0:p1],
            })

    return rows


def compute_metrics_from_aligned_df(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute Strict (Scheme 3) and Adapted ADE-Eval (Scheme 2) metrics from aligned dataframe."""
    if df.empty:
        return {
            "M": 0, "C_boundary": 0, "C_class": 0, "C_total": 0, "S_non_overlap": 0, "N": 0,
            "strict_P": 0.0, "strict_R": 0.0, "strict_F1": 0.0,
            "ade_P": 0.0, "ade_R": 0.0, "ade_F1": 0.0,
        }

    counts = df["match_type"].value_counts().to_dict()
    M = int(counts.get("M", 0))
    class_confusion_mask = (df["match_type"] == "C") & (df["error_subtype"] == "class_confusion")
    C_class = int(class_confusion_mask.sum())
    C_total = int(counts.get("C", 0))
    C_boundary = C_total - C_class
    S_non_overlap = int(counts.get("S", 0))
    N = int(counts.get("N", 0))

    # Scheme 3: Strict Exact-Match Standard NER
    p3_den = M + C_total + S_non_overlap
    r3_den = M + C_total + N
    p3 = M / p3_den if p3_den > 0 else 0.0
    r3 = M / r3_den if r3_den > 0 else 0.0
    f3 = 2 * p3 * r3 / (p3 + r3) if (p3 + r3) > 0 else 0.0

    # Scheme 2: Adapted ADE-Eval Weighted Metric
    m2 = M + 0.5 * C_total
    p2_den = M + C_total + 0.25 * S_non_overlap
    r2_den = M + C_total + N
    p2 = m2 / p2_den if p2_den > 0 else 0.0
    r2 = m2 / r2_den if r2_den > 0 else 0.0
    f2 = 2 * p2 * r2 / (p2 + r2) if (p2 + r2) > 0 else 0.0

    return {
        "M": M,
        "C_boundary": C_boundary,
        "C_class": C_class,
        "C_total": C_total,
        "S_non_overlap": S_non_overlap,
        "N": N,
        "strict_P": round(p3, 4),
        "strict_R": round(r3, 4),
        "strict_F1": round(f3, 4),
        "ade_P": round(p2, 4),
        "ade_R": round(r2, 4),
        "ade_F1": round(f2, 4),
    }


def load_db_narratives_and_annotations(db_path: Path) -> Tuple[List[dict], Dict[str, list], Dict[str, list]]:
    """Load FAERS narratives, SME1 annotations, and ETHER annotations from dataset.db."""
    with sqlite3.connect(db_path) as conn:
        doc_rows = conn.execute(
            "SELECT doc_id, page_text FROM documents WHERE dataset = 'FAERS' ORDER BY doc_id"
        ).fetchall()
        sme1_rows = conn.execute(
            "SELECT doc_id, label, tc_start, tc_end FROM annotations WHERE note = 'SME1' ORDER BY doc_id, tc_start"
        ).fetchall()
        ether_rows = conn.execute(
            "SELECT doc_id, label, tc_start, tc_end, used FROM annotations WHERE note = 'ETHER' ORDER BY doc_id, tc_start"
        ).fetchall()

    sme1_by_doc = defaultdict(list)
    for doc_id, label, start, end in sme1_rows:
        sme1_by_doc[str(doc_id)].append({"label": str(label), "start": int(start), "end": int(end)})

    ether_by_doc = defaultdict(list)
    for doc_id, label, start, end, used in ether_rows:
        if str(used).strip() == "Yes":
            ether_by_doc[str(doc_id)].append({"label": str(label), "start": int(start), "end": int(end)})

    documents = [{"doc_id": str(d[0]), "document": f"{d[0]}.json", "text": str(d[1])} for d in doc_rows]
    return documents, dict(sme1_by_doc), dict(ether_by_doc)


def load_prediction_cache(path: Path) -> Dict[str, dict]:
    """Load predictions from jsonl file."""
    cache = {}
    if not path.exists():
        return cache
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("status") == "ok" and row.get("document"):
                cache[str(row["document"])] = row
    return cache


def prepare_gold_spans(raw_annotations: list, text: str, label_mapping: dict) -> List[Tuple[int, int, str]]:
    """Convert raw annotations to cleaned, trimmed gold spans."""
    gold = []
    for ann in raw_annotations:
        mapped_label = label_mapping.get(str(ann.get("label", "")).strip().casefold())
        if mapped_label is None:
            continue
        try:
            start, end = int(ann["start"]), int(ann["end"])
        except (KeyError, TypeError, ValueError):
            continue
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if 0 <= start < end <= len(text):
            gold.append((start, end, mapped_label))
    return gold


def prepare_pred_spans(raw_preds: list, text: str, label_mapping: dict) -> List[Tuple[int, int, str, float]]:
    """Convert model predicted entities to cleaned predicted spans."""
    preds = []
    for ent in raw_preds:
        mapped_label = label_mapping.get(str(ent.get("label", "")).strip().casefold())
        if mapped_label is None:
            continue
        try:
            start, end = int(ent["start"]), int(ent["end"])
        except (KeyError, TypeError, ValueError):
            continue
        while start < end and start < len(text) and text[start].isspace():
            start += 1
        while end > start and end <= len(text) and text[end - 1].isspace():
            end -= 1
        if 0 <= start < end <= len(text):
            preds.append((start, end, mapped_label, 1.0))
    return preds


def generate_figure3(
    db_path: Path,
    llama_predictions_path: Path,
    sonnet_predictions_path: Path,
    output_png_path: Path,
    output_json_path: Path,
) -> None:
    """Generate Figure 3 directly from raw spans with canonical Two-Tier evaluation."""
    print(f"Loading SQLite database from: {db_path}")
    docs, sme1_annotations, ether_annotations = load_db_narratives_and_annotations(db_path)

    print(f"Loading LLaMA-4 predictions from: {llama_predictions_path}")
    llama_cache = load_prediction_cache(llama_predictions_path)

    print(f"Loading Claude 4.6 Sonnet predictions from: {sonnet_predictions_path}")
    sonnet_cache = load_prediction_cache(sonnet_predictions_path)

    # -------------------------------------------------------------
    # 1. Panel (a): All 17 Categories Alignment for LLMs
    # -------------------------------------------------------------
    print("Aligning raw spans for Panel (a) [17 fine-grained categories]...")
    llama_aligned_17_rows, sonnet_aligned_17_rows = [], []

    for doc in docs:
        text = doc["text"]
        doc_id = doc["doc_id"]
        doc_name = doc["document"]
        gold_17 = prepare_gold_spans(sme1_annotations.get(doc_id, []), text, RAW_GOLD_MAP_17)

        # LLaMA
        llama_doc_pred = llama_cache.get(doc_name, {}).get("predicted_entities", [])
        llama_preds_17 = prepare_pred_spans(llama_doc_pred, text, RAW_LLM_MAP_17)
        rows_l = align_and_classify_spans(text, gold_17, llama_preds_17)
        for r in rows_l:
            r["document"] = doc_name
        llama_aligned_17_rows.extend(rows_l)

        # Sonnet
        sonnet_doc_pred = sonnet_cache.get(doc_name, {}).get("predicted_entities", [])
        sonnet_preds_17 = prepare_pred_spans(sonnet_doc_pred, text, RAW_LLM_MAP_17)
        rows_s = align_and_classify_spans(text, gold_17, sonnet_preds_17)
        for r in rows_s:
            r["document"] = doc_name
        sonnet_aligned_17_rows.extend(rows_s)

    df_llama_17 = pd.DataFrame(llama_aligned_17_rows)
    df_sonnet_17 = pd.DataFrame(sonnet_aligned_17_rows)

    panel_a_labels = [display_name for display_name, _ in CATS_17] + ["TOTAL"]
    sonnet_f1_strict_list, sonnet_f1_ade_list = [], []
    llama_f1_strict_list, llama_f1_ade_list = [], []
    panel_a_audit: Dict[str, dict] = {"Sonnet_4.6": {}, "LLaMA_4": {}}

    for display_name, internal_key in CATS_17:
        s_cat_df = df_sonnet_17[(df_sonnet_17["label_gold"] == internal_key) | (df_sonnet_17["label_pred"] == internal_key)]
        s_metrics = compute_metrics_from_aligned_df(s_cat_df)
        sonnet_f1_strict_list.append(s_metrics["strict_F1"])
        sonnet_f1_ade_list.append(s_metrics["ade_F1"])
        panel_a_audit["Sonnet_4.6"][display_name] = s_metrics

        l_cat_df = df_llama_17[(df_llama_17["label_gold"] == internal_key) | (df_llama_17["label_pred"] == internal_key)]
        l_metrics = compute_metrics_from_aligned_df(l_cat_df)
        llama_f1_strict_list.append(l_metrics["strict_F1"])
        llama_f1_ade_list.append(l_metrics["ade_F1"])
        panel_a_audit["LLaMA_4"][display_name] = l_metrics

    # Overall TOTAL for Panel (a)
    s_tot_metrics = compute_metrics_from_aligned_df(df_sonnet_17)
    sonnet_f1_strict_list.append(s_tot_metrics["strict_F1"])
    sonnet_f1_ade_list.append(s_tot_metrics["ade_F1"])
    panel_a_audit["Sonnet_4.6"]["TOTAL"] = s_tot_metrics

    l_tot_metrics = compute_metrics_from_aligned_df(df_llama_17)
    llama_f1_strict_list.append(l_tot_metrics["strict_F1"])
    llama_f1_ade_list.append(l_tot_metrics["ade_F1"])
    panel_a_audit["LLaMA_4"]["TOTAL"] = l_tot_metrics

    # -------------------------------------------------------------
    # 2. Panel (b): Combined Schemas Alignment (ETHER vs LLaMA vs Sonnet)
    # -------------------------------------------------------------
    print("Aligning raw spans for Panel (b) [Combined schemas: AE, DRUG, DX, HX]...")
    ether_comb_rows, llama_comb_rows, sonnet_comb_rows = [], [], []

    for doc in docs:
        text = doc["text"]
        doc_id = doc["doc_id"]
        doc_name = doc["document"]

        gold_comb = prepare_gold_spans(sme1_annotations.get(doc_id, []), text, LABEL_TO_COMBINED_SCHEMA)

        # ETHER
        ether_doc_raw = ether_annotations.get(doc_id, [])
        ether_preds_comb = prepare_pred_spans(ether_doc_raw, text, ETHER_LABEL_TO_COMBINED_SCHEMA)
        rows_e = align_and_classify_spans(text, gold_comb, ether_preds_comb)
        for r in rows_e:
            r["document"] = doc_name
        ether_comb_rows.extend(rows_e)

        # LLaMA
        llama_doc_pred = llama_cache.get(doc_name, {}).get("predicted_entities", [])
        llama_preds_comb = prepare_pred_spans(llama_doc_pred, text, LABEL_TO_COMBINED_SCHEMA)
        rows_l = align_and_classify_spans(text, gold_comb, llama_preds_comb)
        for r in rows_l:
            r["document"] = doc_name
        llama_comb_rows.extend(rows_l)

        # Sonnet
        sonnet_doc_pred = sonnet_cache.get(doc_name, {}).get("predicted_entities", [])
        sonnet_preds_comb = prepare_pred_spans(sonnet_doc_pred, text, LABEL_TO_COMBINED_SCHEMA)
        rows_s = align_and_classify_spans(text, gold_comb, sonnet_preds_comb)
        for r in rows_s:
            r["document"] = doc_name
        sonnet_comb_rows.extend(rows_s)

    df_ether_comb = pd.DataFrame(ether_comb_rows)
    df_llama_comb = pd.DataFrame(llama_comb_rows)
    df_sonnet_comb = pd.DataFrame(sonnet_comb_rows)

    panel_b_labels = [display_label for display_label, _ in COMBINED_PANEL_B_CATS] + ["TOTAL"]
    ether_b_strict, ether_b_ade = [], []
    llama_b_strict, llama_b_ade = [], []
    sonnet_b_strict, sonnet_b_ade = [], []
    panel_b_audit: Dict[str, dict] = {"ETHER": {}, "LLaMA_4": {}, "Sonnet_4.6": {}}

    for display_label, ckey in COMBINED_PANEL_B_CATS:
        # ETHER
        e_sub = df_ether_comb[(df_ether_comb["label_gold"] == ckey) | (df_ether_comb["label_pred"] == ckey)]
        e_met = compute_metrics_from_aligned_df(e_sub)
        ether_b_strict.append(e_met["strict_F1"])
        ether_b_ade.append(e_met["ade_F1"])
        panel_b_audit["ETHER"][ckey] = e_met

        # LLaMA-4
        l_sub = df_llama_comb[(df_llama_comb["label_gold"] == ckey) | (df_llama_comb["label_pred"] == ckey)]
        l_met = compute_metrics_from_aligned_df(l_sub)
        llama_b_strict.append(l_met["strict_F1"])
        llama_b_ade.append(l_met["ade_F1"])
        panel_b_audit["LLaMA_4"][ckey] = l_met

        # Sonnet 4.6
        s_sub = df_sonnet_comb[(df_sonnet_comb["label_gold"] == ckey) | (df_sonnet_comb["label_pred"] == ckey)]
        s_met = compute_metrics_from_aligned_df(s_sub)
        sonnet_b_strict.append(s_met["strict_F1"])
        sonnet_b_ade.append(s_met["ade_F1"])
        panel_b_audit["Sonnet_4.6"][ckey] = s_met

    # Overall TOTAL for Panel (b)
    e_tot_comb = compute_metrics_from_aligned_df(df_ether_comb)
    ether_b_strict.append(e_tot_comb["strict_F1"])
    ether_b_ade.append(e_tot_comb["ade_F1"])
    panel_b_audit["ETHER"]["TOTAL"] = e_tot_comb

    l_tot_comb = compute_metrics_from_aligned_df(df_llama_comb)
    llama_b_strict.append(l_tot_comb["strict_F1"])
    llama_b_ade.append(l_tot_comb["ade_F1"])
    panel_b_audit["LLaMA_4"]["TOTAL"] = l_tot_comb

    s_tot_comb = compute_metrics_from_aligned_df(df_sonnet_comb)
    sonnet_b_strict.append(s_tot_comb["strict_F1"])
    sonnet_b_ade.append(s_tot_comb["ade_F1"])
    panel_b_audit["Sonnet_4.6"]["TOTAL"] = s_tot_comb

    # -------------------------------------------------------------
    # 3. Plotting Publication Figure 3
    # -------------------------------------------------------------
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Calibri", "DejaVu Sans", "Helvetica"]
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 0.9

    fig = plt.figure(figsize=(16, 10.5), dpi=300)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.2, 1.0], hspace=0.38)

    c_ether = "#616161"        # Gray for ETHER
    c_llama = "#FF6F61"        # Coral/Pink for LLaMA 4
    c_sonnet = "#C0392B"       # Deep Red for Claude Sonnet

    # -------------------------------------------------------------
    # Subplot (a): 17 Categories + TOTAL
    # -------------------------------------------------------------
    ax0 = fig.add_subplot(gs[0, 0])
    n_cats_a = len(CATS_17)
    x_a = np.arange(len(panel_a_labels))
    width_a = 0.38
    idx_ov_a = n_cats_a

    # Background shading & dashed separator for TOTAL
    ax0.axvspan(n_cats_a - 0.5, n_cats_a + 0.5, color="#F0F3F4", alpha=0.7, zorder=0)
    ax0.axvline(x=n_cats_a - 0.5, color="#666666", linestyle="--", linewidth=1.2, alpha=0.75, zorder=1)

    # Individual 17 categories
    idx_17_a = np.arange(n_cats_a)
    ax0.bar(idx_17_a - width_a/2, sonnet_f1_ade_list[:n_cats_a], width_a, label="Claude 4.6 Sonnet (Adapted F1)",
            color=c_sonnet, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    ax0.bar(idx_17_a + width_a/2, llama_f1_ade_list[:n_cats_a], width_a, label="Llama-4 (Adapted F1)",
            color=c_llama, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)

    ax0.plot(idx_17_a - width_a/2, sonnet_f1_strict_list[:n_cats_a], color="#641E16", marker="o", markersize=5.5,
             linestyle="", label="Claude 4.6 Sonnet (Strict F1)", zorder=5)
    ax0.plot(idx_17_a + width_a/2, llama_f1_strict_list[:n_cats_a], color="#922B21", marker="s", markersize=5.5,
             linestyle="", label="Llama-4 (Strict F1)", zorder=5)

    # TOTAL bars with hatching and thicker border
    ax0.bar(idx_ov_a - width_a/2, sonnet_f1_ade_list[idx_ov_a], width_a,
            color=c_sonnet, alpha=0.95, edgecolor="#641E16", linewidth=1.5, hatch="//", zorder=3)
    ax0.bar(idx_ov_a + width_a/2, llama_f1_ade_list[idx_ov_a], width_a,
            color=c_llama, alpha=0.95, edgecolor="#922B21", linewidth=1.5, hatch="//", zorder=3)

    ax0.plot(idx_ov_a - width_a/2, sonnet_f1_strict_list[idx_ov_a], color="#641E16", marker="o",
             markersize=7.5, markeredgewidth=1.2, markeredgecolor="#FFFFFF", linestyle="", zorder=6)
    ax0.plot(idx_ov_a + width_a/2, llama_f1_strict_list[idx_ov_a], color="#922B21", marker="s",
             markersize=7.5, markeredgewidth=1.2, markeredgecolor="#FFFFFF", linestyle="", zorder=6)

    # Value Labels above bars
    for i in range(len(panel_a_labels)):
        is_tot = (i == idx_ov_a)
        fsize = 8.5 if is_tot else 7.5
        ax0.text(x_a[i] - width_a/2, sonnet_f1_ade_list[i] + 0.025, f"{sonnet_f1_ade_list[i]:.2f}",
                 ha="center", va="bottom", fontsize=fsize, fontweight="bold", color="#641E16")
        ax0.text(x_a[i] + width_a/2, llama_f1_ade_list[i] + 0.025, f"{llama_f1_ade_list[i]:.2f}",
                 ha="center", va="bottom", fontsize=fsize, fontweight="bold", color="#922B21")

    ax0.set_title("(a) Per-Category Performance of LLMs on FAERS Across All 17 Categories",
                  fontsize=12.5, fontweight="bold", loc="left", pad=12)
    ax0.set_xticks(x_a)
    ax0.set_xticklabels(panel_a_labels, fontsize=9.5, fontweight="bold", rotation=25)
    for label in ax0.get_xticklabels():
        if label.get_text() == "TOTAL":
            label.set_fontsize(11.5)
            label.set_fontweight("bold")
            label.set_color("#000000")

    ax0.set_ylim(0, 1.18)
    ax0.set_ylabel("F1 Score", fontsize=11, fontweight="bold")
    ax0.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax0.legend(loc="upper left", bbox_to_anchor=(0.01, 0.98), fontsize=8.5, framealpha=0.95, ncol=2)

    # -------------------------------------------------------------
    # Subplot (b): Combined Schema + TOTAL
    # -------------------------------------------------------------
    ax1 = fig.add_subplot(gs[1, 0])
    n_cats_b = len(COMBINED_PANEL_B_CATS)
    x_b = np.arange(len(panel_b_labels))
    width_b = 0.26
    idx_ov_b = n_cats_b

    # Background shading & dashed separator for TOTAL
    ax1.axvspan(n_cats_b - 0.5, n_cats_b + 0.5, color="#F0F3F4", alpha=0.7, zorder=0)
    ax1.axvline(x=n_cats_b - 0.5, color="#666666", linestyle="--", linewidth=1.2, alpha=0.75, zorder=1)

    # Individual combined categories
    idx_comb_b = np.arange(n_cats_b)
    ax1.bar(idx_comb_b - width_b, ether_b_ade[:n_cats_b], width_b, label="ETHER (Adapted F1)",
            color=c_ether, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    ax1.bar(idx_comb_b, llama_b_ade[:n_cats_b], width_b, label="Llama-4 (Adapted F1)",
            color=c_llama, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    ax1.bar(idx_comb_b + width_b, sonnet_b_ade[:n_cats_b], width_b, label="Claude 4.6 Sonnet (Adapted F1)",
            color=c_sonnet, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)

    ax1.plot(idx_comb_b - width_b, ether_b_strict[:n_cats_b], color="#212121", marker="D", markersize=6, linestyle="", label="ETHER (Strict F1)", zorder=5)
    ax1.plot(idx_comb_b, llama_b_strict[:n_cats_b], color="#922B21", marker="s", markersize=6, linestyle="", label="Llama-4 (Strict F1)", zorder=5)
    ax1.plot(idx_comb_b + width_b, sonnet_b_strict[:n_cats_b], color="#641E16", marker="o", markersize=6, linestyle="", label="Claude Sonnet (Strict F1)", zorder=5)

    # TOTAL bars with hatching and thicker border
    ax1.bar(idx_ov_b - width_b, ether_b_ade[idx_ov_b], width_b,
            color=c_ether, alpha=0.95, edgecolor="#212121", linewidth=1.5, hatch="//", zorder=3)
    ax1.bar(idx_ov_b, llama_b_ade[idx_ov_b], width_b,
            color=c_llama, alpha=0.95, edgecolor="#922B21", linewidth=1.5, hatch="//", zorder=3)
    ax1.bar(idx_ov_b + width_b, sonnet_b_ade[idx_ov_b], width_b,
            color=c_sonnet, alpha=0.95, edgecolor="#641E16", linewidth=1.5, hatch="//", zorder=3)

    ax1.plot(idx_ov_b - width_b, ether_b_strict[idx_ov_b], color="#212121", marker="D",
             markersize=7.5, markeredgewidth=1.2, markeredgecolor="#FFFFFF", linestyle="", zorder=6)
    ax1.plot(idx_ov_b, llama_b_strict[idx_ov_b], color="#922B21", marker="s",
             markersize=7.5, markeredgewidth=1.2, markeredgecolor="#FFFFFF", linestyle="", zorder=6)
    ax1.plot(idx_ov_b + width_b, sonnet_b_strict[idx_ov_b], color="#641E16", marker="o",
             markersize=7.5, markeredgewidth=1.2, markeredgecolor="#FFFFFF", linestyle="", zorder=6)

    # Value Labels above bars
    for i in range(len(panel_b_labels)):
        is_tot = (i == idx_ov_b)
        fsize = 9.2 if is_tot else 8.5
        ax1.text(x_b[i] - width_b, ether_b_ade[i] + 0.025, f"{ether_b_ade[i]:.2f}",
                 ha="center", va="bottom", fontsize=fsize, fontweight="bold", color="#212121")
        ax1.text(x_b[i], llama_b_ade[i] + 0.025, f"{llama_b_ade[i]:.2f}",
                 ha="center", va="bottom", fontsize=fsize, fontweight="bold", color="#922B21")
        ax1.text(x_b[i] + width_b, sonnet_b_ade[i] + 0.025, f"{sonnet_b_ade[i]:.2f}",
                 ha="center", va="bottom", fontsize=fsize, fontweight="bold", color="#641E16")

    ax1.set_title("(b) Head-to-Head Comparison: Rule-Based Baseline (ETHER) vs. LLMs on Combined Schema",
                  fontsize=12.5, fontweight="bold", loc="left", pad=12)
    ax1.set_xticks(x_b)
    ax1.set_xticklabels(panel_b_labels, fontsize=10, fontweight="bold")
    for label in ax1.get_xticklabels():
        if label.get_text() == "TOTAL":
            label.set_fontsize(11.5)
            label.set_fontweight("bold")
            label.set_color("#000000")

    ax1.set_ylim(0, 1.05)
    ax1.set_ylabel("F1 Score", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Category (Adapted to ETHER)", fontsize=11, fontweight="bold", labelpad=8)
    ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    custom_handles = [
        mpatches.Patch(facecolor=c_ether, edgecolor="#111", label="ETHER (Adapted F1)"),
        mpatches.Patch(facecolor=c_llama, edgecolor="#111", label="Llama-4 (Adapted F1)"),
        mpatches.Patch(facecolor=c_sonnet, edgecolor="#111", label="Claude 4.6 Sonnet (Adapted F1)"),
        plt.Line2D([0], [0], color="#212121", marker="D", linestyle="", markersize=6, label="ETHER (Strict F1)"),
        plt.Line2D([0], [0], color="#922B21", marker="s", linestyle="", markersize=6, label="Llama-4 (Strict F1)"),
        plt.Line2D([0], [0], color="#641E16", marker="o", linestyle="", markersize=6, label="Claude Sonnet (Strict F1)"),
    ]
    ax1.legend(handles=custom_handles, loc="upper left", bbox_to_anchor=(0.01, 0.98), fontsize=8.5, framealpha=0.95, ncol=3)

    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png_path, dpi=300, bbox_inches="tight")
    print(f"Saved figure: {output_png_path}")
    plt.close()

    audit_data = {
        "framework": "Two-Tier Evaluation Framework (Class Confusion -> Conflation C)",
        "panel_a_17_categories": panel_a_audit,
        "panel_b_combined_schema": panel_b_audit,
    }
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with output_json_path.open("w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)
    print(f"Saved audit data: {output_json_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=DB_PATH_DEFAULT, help="Path to dataset.db")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR_DEFAULT, help="Path to results directory")
    parser.add_argument("--output-dir", type=Path, default=FIGURE_OUTPUT_DIR_DEFAULT, help="Canonical figure and audit-data output directory")
    args = parser.parse_args()

    llama_preds = args.results_dir / "llama4_runs_FAERS" / "predictions.jsonl"
    sonnet_preds = args.results_dir / "sonnet_runs_FAERS" / "predictions.jsonl"

    png_output = args.output_dir / "figure3.png"
    json_output = args.output_dir / "figure3_data.json"

    generate_figure3(
        db_path=args.db_path,
        llama_predictions_path=llama_preds,
        sonnet_predictions_path=sonnet_preds,
        output_png_path=png_output,
        output_json_path=json_output,
    )


if __name__ == "__main__":
    main()
