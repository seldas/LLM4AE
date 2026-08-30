#!/usr/bin/env python3
"""
evaluate_three_schemes.py

Computes and compares NER performance across the Two-Tier Evaluation Framework on FAERS and VAERS,
with strict target-category filtering (ignoring predictions from categories not in the gold standard):

Target Categories:
  - FAERS: AE, DRUG, DX, HX, LAB, DOSE, AGE, SEX, STATUS, TEMPORAL, INDICATION, RO, COD
  - VAERS: AE, VAX, TX, LAB, STATUS, HX (Categories like TEMPORAL, DOSE, AGE, SEX, DX not in VAERS Gold are ignored)

Two-Tier Evaluation Framework:
  Tier 1 (Primary / Standard Benchmark): Strict Exact-Match NER (Scheme 3)
    - Precision = M / (M + C_total + S_non_overlap)
    - Recall    = M / (M + C_total + N)
    - F1        = 2 * P * R / (P + R)

  Tier 2 (Secondary / Clinical Utility): Refined ADE-Eval Clinical Weighted Metric (Scheme 2)
    - C_total = C_boundary (span mismatch) + C_class (category confusion / misclassification)
    - S_non_overlap = ungrounded spurious predictions (zero gold overlap)
    - Precision = (M + 0.5 * C_total) / (M + C_total + 0.25 * S_non_overlap)
    - Recall    = (M + 0.5 * C_total) / (M + C_total + N)
    - F1        = 2 * P * R / (P + R)

  (Note: Former Scheme 1 relaxed entity detection has been discontinued).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import numpy as np
import pandas as pd

# Category mappings
EVAL_LABEL_POOL = {
    # FAERS
    "ae": "AE", "mae": "AE",
    "cdrug": "DRUG", "sdrug": "DRUG", "odrug": "DRUG", "drug": "DRUG",
    "treatment": "DX", "bsym": "DX", "diagnostic": "DX",
    "mhx": "HX", "fhx": "HX",
    "indication": "INDICATION",
    "lab": "LAB",
    "dose": "DOSE",
    "age": "AGE",
    "sex": "SEX",
    "status": "STATUS",
    "temporal": "TEMPORAL",
    "ro": "RO",
    "cod": "COD",
    # VAERS
    "sym": "AE", "pdx": "AE", "sdx": "AE",
    "vax": "VAX",
    "tx": "TX",
}

FAERS_TARGET_CATEGORIES = {
    "AE", "DRUG", "DX", "HX", "LAB", "DOSE", "AGE", "SEX", "STATUS", "TEMPORAL", "INDICATION", "RO", "COD"
}

VAERS_TARGET_CATEGORIES = {
    "AE", "VAX", "TX", "LAB", "STATUS", "HX"
}


def overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return (a0 == b0) or (a1 == b1) or (a0 < b0 < a1) or (a0 < b1 < a1) or (b0 < a0 < b1)


def evaluate_raw_df(df: pd.DataFrame, target_cats: Set[str], group_col: str = "document") -> Tuple[dict, pd.DataFrame]:
    """
    Evaluates raw predictions across the Two-Tier framework, strictly filtering to target_cats.
    """
    total_M = 0
    total_C_bound = 0
    total_N = 0
    total_C_class = 0
    total_S_non_overlap = 0
    total_gold = 0

    cat_stats = defaultdict(lambda: {
        "M": 0, "C_boundary": 0, "C_class": 0, "N": 0, "S_non_overlap": 0,
        "gold_total": 0,
    })

    groups = defaultdict(list)
    cols = {c: i for i, c in enumerate(df.columns)}

    mtype_idx = cols["match_type"]
    gstart_idx = cols["gold_start"]
    gend_idx = cols["gold_end"]
    glab_idx = cols["label_gold"]
    pstart_idx = cols["pred_start"]
    pend_idx = cols["pred_end"]
    plab_idx = cols["label_pred"]
    grp_idx = cols[group_col]

    for row in df.itertuples(index=False):
        groups[row[grp_idx]].append(row)

    for grp_val, rows in groups.items():
        gold_spans = []
        pred_spans = []

        for r in rows:
            mtype = r[mtype_idx]
            glab = r[glab_idx] if pd.notna(r[glab_idx]) else None
            g_cat = EVAL_LABEL_POOL.get(str(glab).lower(), str(glab).upper()) if glab else None

            if mtype in ("M", "C", "N") and g_cat in target_cats:
                g0, g1 = r[gstart_idx], r[gend_idx]
                if pd.notna(g0) and pd.notna(g1):
                    gold_spans.append((int(g0), int(g1), glab, g_cat))

            plab = r[plab_idx] if pd.notna(r[plab_idx]) else None
            p_cat = EVAL_LABEL_POOL.get(str(plab).lower(), str(plab).upper()) if plab else None

            if mtype in ("M", "C", "S") and p_cat in target_cats:
                p0, p1 = r[pstart_idx], r[pend_idx]
                if pd.notna(p0) and pd.notna(p1):
                    pred_spans.append((int(p0), int(p1), plab, p_cat))

        for g0, g1, glab, g_cat in gold_spans:
            total_gold += 1
            cat_stats[g_cat]["gold_total"] += 1

        # Check predictions and match types
        for r in rows:
            mtype = r[mtype_idx]
            glab = r[glab_idx] if pd.notna(r[glab_idx]) else None
            plab = r[plab_idx] if pd.notna(r[plab_idx]) else None

            g_cat = EVAL_LABEL_POOL.get(str(glab).lower(), str(glab).upper()) if glab else None
            p_cat = EVAL_LABEL_POOL.get(str(plab).lower(), str(plab).upper()) if plab else None

            if mtype == "M" and g_cat in target_cats:
                total_M += 1
                cat_stats[g_cat]["M"] += 1
            elif mtype == "C" and g_cat in target_cats:
                total_C_bound += 1
                cat_stats[g_cat]["C_boundary"] += 1
            elif mtype == "N" and g_cat in target_cats:
                total_N += 1
                cat_stats[g_cat]["N"] += 1
            elif mtype in ("S", "S_wrong_class", "S_non_overlap") and p_cat in target_cats:
                p0, p1 = int(r[pstart_idx]), int(r[pend_idx])
                has_gold_overlap = any(overlap(p0, p1, g0, g1) for g0, g1, _, _ in gold_spans)
                if has_gold_overlap or mtype == "S_wrong_class":
                    total_C_class += 1
                    cat_stats[p_cat]["C_class"] += 1
                else:
                    total_S_non_overlap += 1
                    cat_stats[p_cat]["S_non_overlap"] += 1

    total_C_total = total_C_bound + total_C_class

    # --- Compute Overall Metrics ---
    # 1. Primary Tier: Strict Exact Match NER (Scheme 3)
    p3_den = total_M + total_C_total + total_S_non_overlap
    r3_den = total_M + total_C_total + total_N
    p3 = total_M / p3_den if p3_den > 0 else 0.0
    r3 = total_M / r3_den if r3_den > 0 else 0.0
    f1_3 = 2 * p3 * r3 / (p3 + r3) if (p3 + r3) > 0 else 0.0

    # 2. Secondary Tier: Refined ADE-Eval Weighted Metric (Scheme 2)
    #    C_total (boundary + category confusion) gets 0.5 partial credit
    mc2 = total_M + 0.5 * total_C_total
    p2_den = total_M + total_C_total + 0.25 * total_S_non_overlap
    r2_den = total_M + total_C_total + total_N
    p2 = mc2 / p2_den if p2_den > 0 else 0.0
    r2 = mc2 / r2_den if r2_den > 0 else 0.0
    f1_2 = 2 * p2 * r2 / (p2 + r2) if (p2 + r2) > 0 else 0.0

    overall = {
        "M": total_M,
        "C_boundary": total_C_bound,
        "C_class": total_C_class,
        "C_total": total_C_total,
        "S_non_overlap": total_S_non_overlap,
        "N": total_N,
        "Total_Gold": total_gold,
        "Strict_Precision": round(p3, 4), "Strict_Recall": round(r3, 4), "Strict_F1": round(f1_3, 4),
        "ADE_Precision": round(p2, 4), "ADE_Recall": round(r2, 4), "ADE_F1": round(f1_2, 4),
    }

    # --- Compute Per-Category Metrics ---
    cat_rows = []
    for cat in sorted(cat_stats.keys()):
        st = cat_stats[cat]
        c_tot = st["C_boundary"] + st["C_class"]

        # Strict
        p3_c_den = st["M"] + c_tot + st["S_non_overlap"]
        r3_c_den = st["M"] + c_tot + st["N"]
        p3_c = st["M"] / p3_c_den if p3_c_den > 0 else 0.0
        r3_c = st["M"] / r3_c_den if r3_c_den > 0 else 0.0
        f1_3_c = 2 * p3_c * r3_c / (p3_c + r3_c) if (p3_c + r3_c) > 0 else 0.0

        # ADE-Eval
        mc2_c = st["M"] + 0.5 * c_tot
        p2_c_den = st["M"] + c_tot + 0.25 * st["S_non_overlap"]
        r2_c_den = st["M"] + c_tot + st["N"]
        p2_c = mc2_c / p2_c_den if p2_c_den > 0 else 0.0
        r2_c = mc2_c / r2_c_den if r2_c_den > 0 else 0.0
        f1_2_c = 2 * p2_c * r2_c / (p2_c + r2_c) if (p2_c + r2_c) > 0 else 0.0

        cat_rows.append({
            "Category": cat,
            "M": st["M"], "C_boundary": st["C_boundary"], "C_class": st["C_class"],
            "C_total": c_tot, "S_non_overlap": st["S_non_overlap"], "N": st["N"],
            "Gold_Total": st["gold_total"],
            "Strict_Precision": round(p3_c, 4), "Strict_Recall": round(r3_c, 4), "Strict_F1": round(f1_3_c, 4),
            "ADE_Precision": round(p2_c, 4), "ADE_Recall": round(r2_c, 4), "ADE_F1": round(f1_2_c, 4),
        })

    return overall, pd.DataFrame(cat_rows)


def evaluate_bert_cv(results_dir: str, target_cats: Set[str]) -> Tuple[dict, pd.DataFrame]:
    fold_overalls = []
    fold_cats = []

    for fold in range(10):
        p = os.path.join(results_dir, f"fold_{fold:02d}_raw.xlsx")
        if not os.path.exists(p):
            continue
        df = pd.read_excel(p)
        ov, cat_df = evaluate_raw_df(df, target_cats=target_cats, group_col="sent_id")
        ov["fold"] = fold
        cat_df["fold"] = fold
        fold_overalls.append(ov)
        fold_cats.append(cat_df)

    df_ov = pd.DataFrame(fold_overalls)
    summary_ov = {}
    for metric in [
        "Strict_Precision", "Strict_Recall", "Strict_F1",
        "ADE_Precision", "ADE_Recall", "ADE_F1",
    ]:
        summary_ov[f"{metric}_mean"] = round(df_ov[metric].mean(), 4)
        summary_ov[f"{metric}_std"] = round(df_ov[metric].std(), 4)

    df_all_cats = pd.concat(fold_cats, ignore_index=True)
    cat_summary = []
    for cat, group in df_all_cats.groupby("Category"):
        row = {"Category": cat}
        for metric in [
            "Strict_Precision", "Strict_Recall", "Strict_F1",
            "ADE_Precision", "ADE_Recall", "ADE_F1",
        ]:
            row[f"{metric}_mean"] = round(group[metric].mean(), 4)
            row[f"{metric}_std"] = round(group[metric].std(), 4)
        cat_summary.append(row)

    return summary_ov, pd.DataFrame(cat_summary)


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    results_base = repo_root / "publication" / "results"

    print("=================================================================", flush=True)
    print("Evaluating Two-Tier Scoring Framework (Strict & Refined ADE-Eval)", flush=True)
    print("=================================================================", flush=True)

    # 1. FAERS BioBERT
    print("\n[1/5] Processing BioBERT FAERS (10-fold CV)...", flush=True)
    bert_faers_ov, bert_faers_cat = evaluate_bert_cv(str(results_base / "bert_runs_FAERS"), FAERS_TARGET_CATEGORIES)

    # 2. FAERS Claude 4.6 Sonnet
    print("[2/5] Processing Claude 4.6 Sonnet FAERS...", flush=True)
    sonnet_faers_raw = pd.read_excel(results_base / "sonnet_runs_FAERS" / "sonnet_raw.xlsx")
    sonnet_faers_ov, sonnet_faers_cat = evaluate_raw_df(sonnet_faers_raw, FAERS_TARGET_CATEGORIES, group_col="document")

    # 3. FAERS LLaMA 4
    print("[3/5] Processing LLaMA 4 FAERS...", flush=True)
    llama4_faers_raw = pd.read_excel(results_base / "llama4_runs_FAERS" / "llama4_raw.xlsx")
    llama4_faers_ov, llama4_faers_cat = evaluate_raw_df(llama4_faers_raw, FAERS_TARGET_CATEGORIES, group_col="document")

    # 4. VAERS BioBERT
    print("[4/5] Processing BioBERT VAERS (10-fold CV)...", flush=True)
    bert_vaers_ov, bert_vaers_cat = evaluate_bert_cv(str(results_base / "bert_runs_VAERS"), VAERS_TARGET_CATEGORIES)

    # 5. VAERS LLaMA 4
    print("[5/5] Processing LLaMA 4 VAERS (Target categories only)...", flush=True)
    llama4_vaers_raw = pd.read_excel(results_base / "llama4_runs_VAERS" / "llama4_raw.xlsx")
    llama4_vaers_ov, llama4_vaers_cat = evaluate_raw_df(llama4_vaers_raw, VAERS_TARGET_CATEGORIES, group_col="document")

    # Build Summary Table
    faers_summary = [
        {
            "Dataset": "FAERS D1",
            "Model": "BioBERT (10-fold CV)",
            "Strict P": f"{bert_faers_ov['Strict_Precision_mean']:.4f} +- {bert_faers_ov['Strict_Precision_std']:.4f}",
            "Strict R": f"{bert_faers_ov['Strict_Recall_mean']:.4f} +- {bert_faers_ov['Strict_Recall_std']:.4f}",
            "Strict F1": f"{bert_faers_ov['Strict_F1_mean']:.4f} +- {bert_faers_ov['Strict_F1_std']:.4f}",
            "ADE-Eval P": f"{bert_faers_ov['ADE_Precision_mean']:.4f} +- {bert_faers_ov['ADE_Precision_std']:.4f}",
            "ADE-Eval R": f"{bert_faers_ov['ADE_Recall_mean']:.4f} +- {bert_faers_ov['ADE_Recall_std']:.4f}",
            "ADE-Eval F1": f"{bert_faers_ov['ADE_F1_mean']:.4f} +- {bert_faers_ov['ADE_F1_std']:.4f}",
        },
        {
            "Dataset": "FAERS D1",
            "Model": "Claude 4.6 Sonnet (1-shot)",
            "Strict P": f"{sonnet_faers_ov['Strict_Precision']:.4f}",
            "Strict R": f"{sonnet_faers_ov['Strict_Recall']:.4f}",
            "Strict F1": f"{sonnet_faers_ov['Strict_F1']:.4f}",
            "ADE-Eval P": f"{sonnet_faers_ov['ADE_Precision']:.4f}",
            "ADE-Eval R": f"{sonnet_faers_ov['ADE_Recall']:.4f}",
            "ADE-Eval F1": f"{sonnet_faers_ov['ADE_F1']:.4f}",
        },
        {
            "Dataset": "FAERS D1",
            "Model": "LLaMA 4 (1-shot)",
            "Strict P": f"{llama4_faers_ov['Strict_Precision']:.4f}",
            "Strict R": f"{llama4_faers_ov['Strict_Recall']:.4f}",
            "Strict F1": f"{llama4_faers_ov['Strict_F1']:.4f}",
            "ADE-Eval P": f"{llama4_faers_ov['ADE_Precision']:.4f}",
            "ADE-Eval R": f"{llama4_faers_ov['ADE_Recall']:.4f}",
            "ADE-Eval F1": f"{llama4_faers_ov['ADE_F1']:.4f}",
        },
    ]

    vaers_summary = [
        {
            "Dataset": "VAERS",
            "Model": "BioBERT (10-fold CV)",
            "Strict P": f"{bert_vaers_ov['Strict_Precision_mean']:.4f} +- {bert_vaers_ov['Strict_Precision_std']:.4f}",
            "Strict R": f"{bert_vaers_ov['Strict_Recall_mean']:.4f} +- {bert_vaers_ov['Strict_Recall_std']:.4f}",
            "Strict F1": f"{bert_vaers_ov['Strict_F1_mean']:.4f} +- {bert_vaers_ov['Strict_F1_std']:.4f}",
            "ADE-Eval P": f"{bert_vaers_ov['ADE_Precision_mean']:.4f} +- {bert_vaers_ov['ADE_Precision_std']:.4f}",
            "ADE-Eval R": f"{bert_vaers_ov['ADE_Recall_mean']:.4f} +- {bert_vaers_ov['ADE_Recall_std']:.4f}",
            "ADE-Eval F1": f"{bert_vaers_ov['ADE_F1_mean']:.4f} +- {bert_vaers_ov['ADE_F1_std']:.4f}",
        },
        {
            "Dataset": "VAERS",
            "Model": "LLaMA 4 (Filtered)",
            "Strict P": f"{llama4_vaers_ov['Strict_Precision']:.4f}",
            "Strict R": f"{llama4_vaers_ov['Strict_Recall']:.4f}",
            "Strict F1": f"{llama4_vaers_ov['Strict_F1']:.4f}",
            "ADE-Eval P": f"{llama4_vaers_ov['ADE_Precision']:.4f}",
            "ADE-Eval R": f"{llama4_vaers_ov['ADE_Recall']:.4f}",
            "ADE-Eval F1": f"{llama4_vaers_ov['ADE_F1']:.4f}",
        },
    ]

    df_faers_summary = pd.DataFrame(faers_summary)
    df_vaers_summary = pd.DataFrame(vaers_summary)

    out_dir = results_base / "comparison_three_schemes"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_excel = out_dir / "three_schemes_summary.xlsx"

    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        df_faers_summary.to_excel(writer, sheet_name="FAERS_Overall", index=False)
        df_vaers_summary.to_excel(writer, sheet_name="VAERS_Overall", index=False)
        bert_faers_cat.to_excel(writer, sheet_name="BioBERT_FAERS_Categories", index=False)
        sonnet_faers_cat.to_excel(writer, sheet_name="Sonnet_FAERS_Categories", index=False)
        llama4_faers_cat.to_excel(writer, sheet_name="LLaMA4_FAERS_Categories", index=False)
        bert_vaers_cat.to_excel(writer, sheet_name="BioBERT_VAERS_Categories", index=False)
        llama4_vaers_cat.to_excel(writer, sheet_name="LLaMA4_VAERS_Categories", index=False)

    print(f"\nSaved complete multi-sheet Excel summary to: {out_excel}", flush=True)
    print("\n--- FAERS SUMMARY ---", flush=True)
    print(df_faers_summary.to_string(index=False), flush=True)
    print("\n--- VAERS SUMMARY ---", flush=True)
    print(df_vaers_summary.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
