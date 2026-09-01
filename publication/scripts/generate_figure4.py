#!/usr/bin/env python3
"""Generate publication-ready Figure 4: Comparative Concept Extraction Performance on FAERS.

Across All 17 Clinical Concept Categories (N = 829 Reports):
Fine-Tuned BioBERT (4-Fold LOO, Seed 42) vs. Instruction-Tuned LLMs (Claude 4.6 Sonnet & LLaMA 4).

All data are computed dynamically from raw model predictions and the Two-Tier Evaluation Framework:
- 'M': Exact boundary AND exact category match.
- 'C': Inexact boundary (C_boundary) OR category misclassification with overlap (C_class).
- 'S': Spurious ungrounded prediction with zero gold overlap (Non-overlapping FP).
- 'N': Missed gold entity with zero pred overlap (False Negative).

Outputs:
- publication/results/figures/figure4.png
- publication/manuscripts/Figures/figure4.png
- publication/manuscripts/figure4.png
- publication/results/figures/figure4_data.json
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
FIGURES_DIR_DEFAULT = RESULTS_DIR_DEFAULT / "figures"
MANUSCRIPT_DIR_DEFAULT = PROJECT_ROOT / "manuscripts"

# 17 Fine-grained clinical concept categories in canonical presentation order
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
    "ae": "ae", "mae": "mae",
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


def spans_overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    """True if span A overlaps span B."""
    return (a0 == b0) or (a1 == b1) or (a0 < b0 < a1) or (a0 < b1 < a1) or (b0 < a0 < b1)


def align_and_classify_spans(
    text: str,
    gold_ents: List[Tuple[int, int, str]],
    pred_ents: List[Tuple[int, int, str, float]],
) -> List[dict]:
    """Align gold and predicted spans into the paper's Two-Tier error taxonomy."""
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


def load_db_narratives_and_annotations(db_path: Path) -> Tuple[List[dict], Dict[str, list]]:
    """Load FAERS narratives and SME1 annotations from dataset.db."""
    with sqlite3.connect(db_path) as conn:
        doc_rows = conn.execute(
            "SELECT doc_id, page_text FROM documents WHERE dataset = 'FAERS' ORDER BY doc_id"
        ).fetchall()
        sme1_rows = conn.execute(
            "SELECT doc_id, label, tc_start, tc_end FROM annotations WHERE note = 'SME1' ORDER BY doc_id, tc_start"
        ).fetchall()

    sme1_by_doc = defaultdict(list)
    for doc_id, label, start, end in sme1_rows:
        sme1_by_doc[str(doc_id)].append({"label": str(label), "start": int(start), "end": int(end)})

    documents = [{"doc_id": str(d[0]), "document": f"{d[0]}.json", "text": str(d[1])} for d in doc_rows]
    return documents, dict(sme1_by_doc)


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


def load_biobert_seed_raw(bert_raw_path: Path, seed: int = 42) -> pd.DataFrame:
    """Load BioBERT LOO raw evaluation records for the designated random seed."""
    df_all = pd.read_excel(bert_raw_path, sheet_name="Raw_Results")
    df_seed = df_all[df_all["seed"] == seed].copy()
    if df_seed.empty:
        raise ValueError(f"No records found for seed {seed} in {bert_raw_path}")
    return df_seed


def generate_figure4(
    db_path: Path,
    bert_raw_path: Path,
    bert_seed: int,
    llama_predictions_path: Path,
    sonnet_predictions_path: Path,
    output_png_paths: List[Path],
    output_json_path: Path,
) -> None:
    """Generate Figure 4 comparing BioBERT, Claude 4.6 Sonnet, and LLaMA-4."""
    print(f"Loading SQLite database from: {db_path}")
    docs, sme1_annotations = load_db_narratives_and_annotations(db_path)

    print(f"Loading BioBERT LOO (Seed {bert_seed}) from: {bert_raw_path}")
    df_bert = load_biobert_seed_raw(bert_raw_path, seed=bert_seed)

    print(f"Loading LLaMA-4 predictions from: {llama_predictions_path}")
    llama_cache = load_prediction_cache(llama_predictions_path)

    print(f"Loading Claude 4.6 Sonnet predictions from: {sonnet_predictions_path}")
    sonnet_cache = load_prediction_cache(sonnet_predictions_path)

    # -------------------------------------------------------------
    # Align LLM predictions with Two-Tier error taxonomy
    # -------------------------------------------------------------
    print("Aligning raw spans for Claude 4.6 Sonnet and LLaMA-4...")
    llama_aligned_rows, sonnet_aligned_rows = [], []

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
        llama_aligned_rows.extend(rows_l)

        # Sonnet
        sonnet_doc_pred = sonnet_cache.get(doc_name, {}).get("predicted_entities", [])
        sonnet_preds_17 = prepare_pred_spans(sonnet_doc_pred, text, RAW_LLM_MAP_17)
        rows_s = align_and_classify_spans(text, gold_17, sonnet_preds_17)
        for r in rows_s:
            r["document"] = doc_name
        sonnet_aligned_rows.extend(rows_s)

    df_llama_17 = pd.DataFrame(llama_aligned_rows)
    df_sonnet_17 = pd.DataFrame(sonnet_aligned_rows)

    categories_display = [display_name for display_name, _ in CATS_17] + ["OVERALL"]

    bert_ade_list, bert_strict_list = [], []
    sonnet_ade_list, sonnet_strict_list = [], []
    llama_ade_list, llama_strict_list = [], []

    audit_data: Dict[str, dict] = {
        "BioBERT_LOO_Seed42": {},
        "Claude_4.6_Sonnet": {},
        "LLaMA_4": {},
    }

    # Compute metrics per category
    for display_name, internal_key in CATS_17:
        # BioBERT
        b_cat_df = df_bert[(df_bert["label_gold"] == internal_key) | (df_bert["label_pred"] == internal_key)]
        b_met = compute_metrics_from_aligned_df(b_cat_df)
        bert_ade_list.append(b_met["ade_F1"])
        bert_strict_list.append(b_met["strict_F1"])
        audit_data["BioBERT_LOO_Seed42"][display_name] = b_met

        # Claude 4.6 Sonnet
        s_cat_df = df_sonnet_17[(df_sonnet_17["label_gold"] == internal_key) | (df_sonnet_17["label_pred"] == internal_key)]
        s_met = compute_metrics_from_aligned_df(s_cat_df)
        sonnet_ade_list.append(s_met["ade_F1"])
        sonnet_strict_list.append(s_met["strict_F1"])
        audit_data["Claude_4.6_Sonnet"][display_name] = s_met

        # LLaMA-4
        l_cat_df = df_llama_17[(df_llama_17["label_gold"] == internal_key) | (df_llama_17["label_pred"] == internal_key)]
        l_met = compute_metrics_from_aligned_df(l_cat_df)
        llama_ade_list.append(l_met["ade_F1"])
        llama_strict_list.append(l_met["strict_F1"])
        audit_data["LLaMA_4"][display_name] = l_met

    # OVERALL metrics
    b_tot_met = compute_metrics_from_aligned_df(df_bert)
    bert_ade_list.append(b_tot_met["ade_F1"])
    bert_strict_list.append(b_tot_met["strict_F1"])
    audit_data["BioBERT_LOO_Seed42"]["OVERALL"] = b_tot_met

    s_tot_met = compute_metrics_from_aligned_df(df_sonnet_17)
    sonnet_ade_list.append(s_tot_met["ade_F1"])
    sonnet_strict_list.append(s_tot_met["strict_F1"])
    audit_data["Claude_4.6_Sonnet"]["OVERALL"] = s_tot_met

    l_tot_met = compute_metrics_from_aligned_df(df_llama_17)
    llama_ade_list.append(l_tot_met["ade_F1"])
    llama_strict_list.append(l_tot_met["strict_F1"])
    audit_data["LLaMA_4"]["OVERALL"] = l_tot_met

    # -------------------------------------------------------------
    # Plotting Figure 4
    # -------------------------------------------------------------
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Calibri", "DejaVu Sans", "Helvetica"]
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 0.9

    fig, ax = plt.subplots(figsize=(16.5, 7.2), dpi=300)

    n_cats = len(CATS_17)
    x = np.arange(len(categories_display))
    width = 0.27

    # Palette
    c_bert = "#1F77B4"       # Steel Blue for BioBERT
    c_sonnet = "#C0392B"     # Crimson Red for Claude Sonnet
    c_llama = "#FF6F61"      # Coral/Pink for LLaMA 4

    # Subtle background shading and vertical dashed divider for OVERALL section
    ax.axvspan(n_cats - 0.5, n_cats + 0.5, color="#F0F3F4", alpha=0.7, zorder=0)
    ax.axvline(x=n_cats - 0.5, color="#666666", linestyle="--", linewidth=1.2, alpha=0.75, zorder=1)

    # 1. Plot the 17 individual categories (Indices 0 to 16)
    idx_17 = np.arange(n_cats)
    ax.bar(idx_17 - width, bert_ade_list[:n_cats], width, color=c_bert, alpha=0.92,
           edgecolor="#111111", linewidth=0.7, zorder=2)
    ax.bar(idx_17, sonnet_ade_list[:n_cats], width, color=c_sonnet, alpha=0.92,
           edgecolor="#111111", linewidth=0.7, zorder=2)
    ax.bar(idx_17 + width, llama_ade_list[:n_cats], width, color=c_llama, alpha=0.92,
           edgecolor="#111111", linewidth=0.7, zorder=2)

    # Strict F1 Point Overlays for 17 individual categories
    ax.plot(idx_17 - width, bert_strict_list[:n_cats], color="#0B3C5D", marker="D",
            markersize=6, linestyle="", zorder=5)
    ax.plot(idx_17, sonnet_strict_list[:n_cats], color="#641E16", marker="o",
            markersize=6, linestyle="", zorder=5)
    ax.plot(idx_17 + width, llama_strict_list[:n_cats], color="#922B21", marker="s",
            markersize=6, linestyle="", zorder=5)

    # 2. Plot the OVERALL bar (Index 17) with prominent distinct styling (hatching + heavier border)
    idx_ov = n_cats
    ax.bar(idx_ov - width, bert_ade_list[idx_ov], width, color=c_bert, alpha=0.95,
           edgecolor="#0B3C5D", linewidth=1.5, hatch="//", zorder=3)
    ax.bar(idx_ov, sonnet_ade_list[idx_ov], width, color=c_sonnet, alpha=0.95,
           edgecolor="#641E16", linewidth=1.5, hatch="//", zorder=3)
    ax.bar(idx_ov + width, llama_ade_list[idx_ov], width, color=c_llama, alpha=0.95,
           edgecolor="#922B21", linewidth=1.5, hatch="//", zorder=3)

    # Strict F1 Point Overlays for OVERALL with prominent marker
    ax.plot(idx_ov - width, bert_strict_list[idx_ov], color="#0B3C5D", marker="D",
            markersize=7.5, markeredgewidth=1.2, markeredgecolor="#FFFFFF", linestyle="", zorder=6)
    ax.plot(idx_ov, sonnet_strict_list[idx_ov], color="#641E16", marker="o",
            markersize=7.5, markeredgewidth=1.2, markeredgecolor="#FFFFFF", linestyle="", zorder=6)
    ax.plot(idx_ov + width, llama_strict_list[idx_ov], color="#922B21", marker="s",
            markersize=7.5, markeredgewidth=1.2, markeredgecolor="#FFFFFF", linestyle="", zorder=6)

    # Value Labels above bars
    for i in range(len(categories_display)):
        is_overall = (i == idx_ov)
        fsize = 8.5 if is_overall else 7.2
        fweight = "bold"
        
        if bert_ade_list[i] > 0.02:
            ax.text(x[i] - width, bert_ade_list[i] + 0.02, f"{bert_ade_list[i]:.2f}",
                    ha="center", va="bottom", fontsize=fsize, fontweight=fweight, color="#0B3C5D")
        if sonnet_ade_list[i] > 0.02:
            ax.text(x[i], sonnet_ade_list[i] + 0.02, f"{sonnet_ade_list[i]:.2f}",
                    ha="center", va="bottom", fontsize=fsize, fontweight=fweight, color="#641E16")
        if llama_ade_list[i] > 0.02:
            ax.text(x[i] + width, llama_ade_list[i] + 0.02, f"{llama_ade_list[i]:.2f}",
                    ha="center", va="bottom", fontsize=fsize, fontweight=fweight, color="#922B21")

    # Clean formatting
    ax.set_xticks(x)
    ax.set_xticklabels(categories_display, fontsize=10.5, fontweight="bold", rotation=25)
    
    # Highlight OVERALL label on x-axis
    for label in ax.get_xticklabels():
        if label.get_text() == "OVERALL":
            label.set_fontsize(12.0)
            label.set_fontweight("bold")
            label.set_color("#000000")

    ax.set_ylim(0, 1.18)
    ax.set_ylabel("F1 Score", fontsize=11.5, fontweight="bold")
    ax.set_xlabel("Category", fontsize=11.5, fontweight="bold", labelpad=8)
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    # Legend handles
    h_b_bar = mpatches.Patch(facecolor=c_bert, edgecolor="#111", label="BioBERT (Adapted F1)")
    h_b_pt  = plt.Line2D([0], [0], color="#0B3C5D", marker="D", linestyle="", markersize=6.5, label="BioBERT (Strict F1)")
    
    h_s_bar = mpatches.Patch(facecolor=c_sonnet, edgecolor="#111", label="Claude 4.6 Sonnet (Adapted F1)")
    h_s_pt  = plt.Line2D([0], [0], color="#641E16", marker="o", linestyle="", markersize=6.5, label="Claude Sonnet (Strict F1)")
    
    h_l_bar = mpatches.Patch(facecolor=c_llama, edgecolor="#111", label="Llama-4 (Adapted F1)")
    h_l_pt  = plt.Line2D([0], [0], color="#922B21", marker="s", linestyle="", markersize=6.5, label="Llama-4 (Strict F1)")
    
    custom_handles = [h_b_bar, h_b_pt, h_s_bar, h_s_pt, h_l_bar, h_l_pt]
    ax.legend(handles=custom_handles, loc="upper left", bbox_to_anchor=(0.01, 0.98),
              fontsize=9.5, framealpha=0.96, ncol=3, columnspacing=1.8, handletextpad=0.6)

    primary_out = output_png_paths[0]
    primary_out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(primary_out, dpi=300, bbox_inches="tight")
    print(f"Saved figure: {primary_out}")
    plt.close()

    import shutil
    for out_path in output_png_paths[1:]:
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(primary_out), str(out_path))
            print(f"Saved figure: {out_path}")
        except Exception as e:
            print(f"Warning: Could not copy figure to {out_path}: {e}")

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with output_json_path.open("w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)
    print(f"Saved audit data: {output_json_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=DB_PATH_DEFAULT, help="Path to dataset.db")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR_DEFAULT, help="Path to results directory")
    parser.add_argument("--manuscript-dir", type=Path, default=MANUSCRIPT_DIR_DEFAULT, help="Path to manuscripts directory")
    parser.add_argument("--bert-seed", type=int, default=42, help="Random seed for BioBERT LOO (default: 42)")
    args = parser.parse_args()

    bert_raw = args.results_dir / "bert_runs_FAERS_LOO" / "raw.xlsx"
    llama_preds = args.results_dir / "llama4_runs_FAERS" / "predictions.jsonl"
    sonnet_preds = args.results_dir / "sonnet_runs_FAERS" / "predictions.jsonl"

    png_outputs = [
        args.results_dir / "figures" / "figure4.png",
        args.manuscript_dir / "Figures" / "figure4.png",
        args.manuscript_dir / "figure4.png",
    ]
    json_output = args.results_dir / "figures" / "figure4_data.json"

    generate_figure4(
        db_path=args.db_path,
        bert_raw_path=bert_raw,
        bert_seed=args.bert_seed,
        llama_predictions_path=llama_preds,
        sonnet_predictions_path=sonnet_preds,
        output_png_paths=png_outputs,
        output_json_path=json_output,
    )


if __name__ == "__main__":
    main()
