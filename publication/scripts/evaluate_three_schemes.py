#!/usr/bin/env python3
"""
evaluate_three_schemes.py

Computes and compares NER performance across the Two-Tier Evaluation Framework on FAERS and VAERS,
incorporating methodological updates:
  1. FAERS BioBERT: Evaluated under 4-Fold Leave-One-Drug-AE-Pair-Out (LOO) cross-validation
     across the 4 distinct case series (Azacitidine-QT, Tramadol-Hypoglycemia,
     Baricitinib-Hypersensitivity, Erenumab-Stroke) replacing the former 10-fold CV.
  2. Default Experiments: Uses Random Seed 42 as the primary reported baseline across all models.
  3. Multi-Seed Ablation Analysis: Evaluates 5 independent random initialization seeds
     (42, 123, 456, 789, 1011) for both FAERS (20 runs total) and VAERS (50 runs total)
     to quantify stochastic optimization stability vs. data partition variance.
  4. Target-Category Filtering:
     - FAERS: AE, DRUG, DX, HX, LAB, DOSE, AGE, SEX, STATUS, TEMPORAL, INDICATION, RO, COD
     - VAERS: AE, VAX, TX, LAB, STATUS, HX (unsupported categories filtered out)

Two-Tier Evaluation Framework:
  - Primary Tier (Standard Benchmark): Strict Exact-Match NER (Scheme 3)
      Precision = M / (M + C_total + S_non_overlap)
      Recall    = M / (M + C_total + N)
      F1        = 2 * P * R / (P + R)

  - Secondary Tier (Clinical Utility): Refined ADE-Eval Clinical Weighted Metric (Scheme 2)
      C_total = C_boundary (span mismatch) + C_class (category confusion / misclassification)
      S_non_overlap = ungrounded spurious predictions (zero gold overlap)
      Precision = (M + 0.5 * C_total) / (M + C_total + 0.25 * S_non_overlap)
      Recall    = (M + 0.5 * C_total) / (M + C_total + N)
      F1        = 2 * P * R / (P + R)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

# -----------------------------------------------------------------------------
# Category Taxonomy and Mappings
# -----------------------------------------------------------------------------
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

SEEDS = [42, 123, 456, 789, 1011]
DEFAULT_SEED = 42

FAERS_CASE_SERIES = [
    "Azacitidine-QT",
    "Tramadol-Hypoglycemia",
    "Baricitinib-Hypersensitivity",
    "Erenumab-Stroke",
]


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

    # 1. Primary Tier: Strict Exact Match NER (Scheme 3)
    p3_den = total_M + total_C_total + total_S_non_overlap
    r3_den = total_M + total_C_total + total_N
    p3 = total_M / p3_den if p3_den > 0 else 0.0
    r3 = total_M / r3_den if r3_den > 0 else 0.0
    f1_3 = 2 * p3 * r3 / (p3 + r3) if (p3 + r3) > 0 else 0.0

    # 2. Secondary Tier: Refined ADE-Eval Weighted Metric (Scheme 2)
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

    # Per-Category Metrics
    cat_rows = []
    for cat in sorted(cat_stats.keys()):
        st = cat_stats[cat]
        c_tot = st["C_boundary"] + st["C_class"]

        p3_c_den = st["M"] + c_tot + st["S_non_overlap"]
        r3_c_den = st["M"] + c_tot + st["N"]
        p3_c = st["M"] / p3_c_den if p3_c_den > 0 else 0.0
        r3_c = st["M"] / r3_c_den if r3_c_den > 0 else 0.0
        f1_3_c = 2 * p3_c * r3_c / (p3_c + r3_c) if (p3_c + r3_c) > 0 else 0.0

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


def load_vaers_bert_runs(results_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads all VAERS BioBERT runs (10 folds x 5 seeds).
    Returns (all_runs_df, seed_summary_df, fold_summary_df).
    """
    all_runs = []
    all_cats = []

    for seed in SEEDS:
        for fold in range(10):
            p = results_dir / f"fold_{fold:02d}_seed_{seed}_raw.xlsx"
            if not p.exists() and seed == 42:
                p = results_dir / f"fold_{fold:02d}_raw.xlsx"
            if not p.exists():
                continue
            df = pd.read_excel(p)
            ov, cat_df = evaluate_raw_df(df, target_cats=VAERS_TARGET_CATEGORIES, group_col="sent_id")
            ov["fold"] = fold
            ov["seed"] = seed
            cat_df["fold"] = fold
            cat_df["seed"] = seed
            all_runs.append(ov)
            all_cats.append(cat_df)

    df_all_runs = pd.DataFrame(all_runs)
    df_all_cats = pd.concat(all_cats, ignore_index=True) if all_cats else pd.DataFrame()

    seed_agg = []
    for s, grp in df_all_runs.groupby("seed"):
        seed_agg.append({
            "seed": s,
            "num_folds": len(grp),
            "Strict_Precision_mean": round(grp["Strict_Precision"].mean(), 4),
            "Strict_Precision_std": round(grp["Strict_Precision"].std(), 4),
            "Strict_Recall_mean": round(grp["Strict_Recall"].mean(), 4),
            "Strict_Recall_std": round(grp["Strict_Recall"].std(), 4),
            "Strict_F1_mean": round(grp["Strict_F1"].mean(), 4),
            "Strict_F1_std": round(grp["Strict_F1"].std(), 4),
            "ADE_Precision_mean": round(grp["ADE_Precision"].mean(), 4),
            "ADE_Precision_std": round(grp["ADE_Precision"].std(), 4),
            "ADE_Recall_mean": round(grp["ADE_Recall"].mean(), 4),
            "ADE_Recall_std": round(grp["ADE_Recall"].std(), 4),
            "ADE_F1_mean": round(grp["ADE_F1"].mean(), 4),
            "ADE_F1_std": round(grp["ADE_F1"].std(), 4),
        })
    df_seed_summary = pd.DataFrame(seed_agg)

    return df_all_runs, df_seed_summary, df_all_cats


def load_faers_loo_runs(loo_summary_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads FAERS BioBERT 4-Fold LOO runs from loo_evaluation_summary.xlsx.
    Returns (all_runs_df, seed_summary_df, per_cat_df).
    """
    if not loo_summary_path.exists():
        raise FileNotFoundError(f"FAERS LOO summary file not found: {loo_summary_path}")

    df_runs = pd.read_excel(loo_summary_path, sheet_name="All_Runs_Per_Seed")
    df_fold_summary = pd.read_excel(loo_summary_path, sheet_name="Fold_Summary_Across_Seeds")
    df_cat = pd.read_excel(loo_summary_path, sheet_name="Per_Category_Summary")

    rename_map = {
        "strict_P": "Strict_Precision",
        "strict_R": "Strict_Recall",
        "strict_F1": "Strict_F1",
        "ade_P": "ADE_Precision",
        "ade_R": "ADE_Recall",
        "ade_F1": "ADE_F1",
    }
    df_runs = df_runs.rename(columns=rename_map)

    seed_agg = []
    for s, grp in df_runs.groupby("seed"):
        seed_agg.append({
            "seed": s,
            "num_folds": len(grp),
            "Strict_Precision_mean": round(grp["Strict_Precision"].mean(), 4),
            "Strict_Precision_std": round(grp["Strict_Precision"].std(), 4),
            "Strict_Recall_mean": round(grp["Strict_Recall"].mean(), 4),
            "Strict_Recall_std": round(grp["Strict_Recall"].std(), 4),
            "Strict_F1_mean": round(grp["Strict_F1"].mean(), 4),
            "Strict_F1_std": round(grp["Strict_F1"].std(), 4),
            "ADE_Precision_mean": round(grp["ADE_Precision"].mean(), 4),
            "ADE_Precision_std": round(grp["ADE_Precision"].std(), 4),
            "ADE_Recall_mean": round(grp["ADE_Recall"].mean(), 4),
            "ADE_Recall_std": round(grp["ADE_Recall"].std(), 4),
            "ADE_F1_mean": round(grp["ADE_F1"].mean(), 4),
            "ADE_F1_std": round(grp["ADE_F1"].std(), 4),
        })
    df_seed_summary = pd.DataFrame(seed_agg)

    return df_runs, df_seed_summary, df_cat


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    results_base = repo_root / "publication" / "results"

    print("=" * 80, flush=True)
    print(" Two-Tier Evaluation Suite: 4-Fold FAERS LOO & Multi-Seed CV Ablation", flush=True)
    print("=" * 80, flush=True)

    # 1. FAERS BioBERT (4-Fold LOO Case Series Across 5 Seeds)
    print("\n[1/5] Loading FAERS BioBERT 4-Fold LOO runs...", flush=True)
    faers_loo_path = results_base / "bert_runs_FAERS_LOO" / "loo_evaluation_summary.xlsx"
    faers_bert_runs, faers_bert_seeds, faers_bert_cat = load_faers_loo_runs(faers_loo_path)

    faers_bert_s42_runs = faers_bert_runs[faers_bert_runs["seed"] == DEFAULT_SEED]
    faers_bert_s42_ov = {
        "Strict_Precision_mean": faers_bert_s42_runs["Strict_Precision"].mean(),
        "Strict_Precision_std": faers_bert_s42_runs["Strict_Precision"].std(),
        "Strict_Recall_mean": faers_bert_s42_runs["Strict_Recall"].mean(),
        "Strict_Recall_std": faers_bert_s42_runs["Strict_Recall"].std(),
        "Strict_F1_mean": faers_bert_s42_runs["Strict_F1"].mean(),
        "Strict_F1_std": faers_bert_s42_runs["Strict_F1"].std(),
        "ADE_Precision_mean": faers_bert_s42_runs["ADE_Precision"].mean(),
        "ADE_Precision_std": faers_bert_s42_runs["ADE_Precision"].std(),
        "ADE_Recall_mean": faers_bert_s42_runs["ADE_Recall"].mean(),
        "ADE_Recall_std": faers_bert_s42_runs["ADE_Recall"].std(),
        "ADE_F1_mean": faers_bert_s42_runs["ADE_F1"].mean(),
        "ADE_F1_std": faers_bert_s42_runs["ADE_F1"].std(),
    }

    faers_bert_pooled_ov = {
        "Strict_Precision_mean": faers_bert_runs["Strict_Precision"].mean(),
        "Strict_Precision_std": faers_bert_runs["Strict_Precision"].std(),
        "Strict_Recall_mean": faers_bert_runs["Strict_Recall"].mean(),
        "Strict_Recall_std": faers_bert_runs["Strict_Recall"].std(),
        "Strict_F1_mean": faers_bert_runs["Strict_F1"].mean(),
        "Strict_F1_std": faers_bert_runs["Strict_F1"].std(),
        "ADE_Precision_mean": faers_bert_runs["ADE_Precision"].mean(),
        "ADE_Precision_std": faers_bert_runs["ADE_Precision"].std(),
        "ADE_Recall_mean": faers_bert_runs["ADE_Recall"].mean(),
        "ADE_Recall_std": faers_bert_runs["ADE_Recall"].std(),
        "ADE_F1_mean": faers_bert_runs["ADE_F1"].mean(),
        "ADE_F1_std": faers_bert_runs["ADE_F1"].std(),
    }

    # 2. FAERS Claude 4.6 Sonnet (1-shot)
    print("[2/5] Evaluating Claude 4.6 Sonnet on FAERS...", flush=True)
    sonnet_faers_raw = pd.read_excel(results_base / "sonnet_runs_FAERS" / "sonnet_raw.xlsx")
    sonnet_faers_ov, sonnet_faers_cat = evaluate_raw_df(sonnet_faers_raw, FAERS_TARGET_CATEGORIES, group_col="document")

    # 3. FAERS LLaMA 4 (1-shot Tagged & JSON)
    print("[3/5] Evaluating LLaMA 4 on FAERS...", flush=True)
    llama4_faers_raw = pd.read_excel(results_base / "llama4_runs_FAERS" / "llama4_raw.xlsx")
    llama4_faers_ov, llama4_faers_cat = evaluate_raw_df(llama4_faers_raw, FAERS_TARGET_CATEGORIES, group_col="document")

    llama4_json_path = results_base / "llama4_runs_FAERS_json" / "llama4_json_raw.xlsx"
    if llama4_json_path.exists():
        llama4_json_raw = pd.read_excel(llama4_json_path)
        llama4_json_ov, llama4_json_cat = evaluate_raw_df(llama4_json_raw, FAERS_TARGET_CATEGORIES, group_col="document")
    else:
        llama4_json_ov, llama4_json_cat = None, None

    # 4. VAERS BioBERT (10-Fold CV Across 5 Seeds)
    print("[4/5] Loading VAERS BioBERT 10-Fold CV runs across 5 seeds...", flush=True)
    vaers_bert_dir = results_base / "bert_runs_VAERS"
    vaers_bert_runs, vaers_bert_seeds, vaers_bert_cats = load_vaers_bert_runs(vaers_bert_dir)

    vaers_bert_s42_runs = vaers_bert_runs[vaers_bert_runs["seed"] == DEFAULT_SEED]
    vaers_bert_s42_ov = {
        "Strict_Precision_mean": vaers_bert_s42_runs["Strict_Precision"].mean(),
        "Strict_Precision_std": vaers_bert_s42_runs["Strict_Precision"].std(),
        "Strict_Recall_mean": vaers_bert_s42_runs["Strict_Recall"].mean(),
        "Strict_Recall_std": vaers_bert_s42_runs["Strict_Recall"].std(),
        "Strict_F1_mean": vaers_bert_s42_runs["Strict_F1"].mean(),
        "Strict_F1_std": vaers_bert_s42_runs["Strict_F1"].std(),
        "ADE_Precision_mean": vaers_bert_s42_runs["ADE_Precision"].mean(),
        "ADE_Precision_std": vaers_bert_s42_runs["ADE_Precision"].std(),
        "ADE_Recall_mean": vaers_bert_s42_runs["ADE_Recall"].mean(),
        "ADE_Recall_std": vaers_bert_s42_runs["ADE_Recall"].std(),
        "ADE_F1_mean": vaers_bert_s42_runs["ADE_F1"].mean(),
        "ADE_F1_std": vaers_bert_s42_runs["ADE_F1"].std(),
    }

    vaers_bert_pooled_ov = {
        "Strict_Precision_mean": vaers_bert_runs["Strict_Precision"].mean(),
        "Strict_Precision_std": vaers_bert_runs["Strict_Precision"].std(),
        "Strict_Recall_mean": vaers_bert_runs["Strict_Recall"].mean(),
        "Strict_Recall_std": vaers_bert_runs["Strict_Recall"].std(),
        "Strict_F1_mean": vaers_bert_runs["Strict_F1"].mean(),
        "Strict_F1_std": vaers_bert_runs["Strict_F1"].std(),
        "ADE_Precision_mean": vaers_bert_runs["ADE_Precision"].mean(),
        "ADE_Precision_std": vaers_bert_runs["ADE_Precision"].std(),
        "ADE_Recall_mean": vaers_bert_runs["ADE_Recall"].mean(),
        "ADE_Recall_std": vaers_bert_runs["ADE_Recall"].std(),
        "ADE_F1_mean": vaers_bert_runs["ADE_F1"].mean(),
        "ADE_F1_std": vaers_bert_runs["ADE_F1"].std(),
    }

    vaers_bert_s42_cats = vaers_bert_cats[vaers_bert_cats["seed"] == DEFAULT_SEED]
    vaers_cat_summary = []
    for cat, grp in vaers_bert_s42_cats.groupby("Category"):
        vaers_cat_summary.append({
            "Category": cat,
            "Strict_Precision_mean": round(grp["Strict_Precision"].mean(), 4),
            "Strict_Precision_std": round(grp["Strict_Precision"].std(), 4),
            "Strict_Recall_mean": round(grp["Strict_Recall"].mean(), 4),
            "Strict_Recall_std": round(grp["Strict_Recall"].std(), 4),
            "Strict_F1_mean": round(grp["Strict_F1"].mean(), 4),
            "Strict_F1_std": round(grp["Strict_F1"].std(), 4),
            "ADE_Precision_mean": round(grp["ADE_Precision"].mean(), 4),
            "ADE_Precision_std": round(grp["ADE_Precision"].std(), 4),
            "ADE_Recall_mean": round(grp["ADE_Recall"].mean(), 4),
            "ADE_Recall_std": round(grp["ADE_Recall"].std(), 4),
            "ADE_F1_mean": round(grp["ADE_F1"].mean(), 4),
            "ADE_F1_std": round(grp["ADE_F1"].std(), 4),
        })
    df_vaers_bert_cat_s42 = pd.DataFrame(vaers_cat_summary)

    # 5. VAERS LLaMA 4 (1-shot Target Filtered)
    print("[5/5] Evaluating LLaMA 4 on VAERS (Target Filtered)...", flush=True)
    llama4_vaers_raw = pd.read_excel(results_base / "llama4_runs_VAERS" / "llama4_raw.xlsx")
    llama4_vaers_ov, llama4_vaers_cat = evaluate_raw_df(llama4_vaers_raw, VAERS_TARGET_CATEGORIES, group_col="document")

    # Build Master Summary Tables
    faers_master_table = [
        {
            "Dataset": "FAERS D1",
            "Model": f"BioBERT (4-Fold LOO, Seed {DEFAULT_SEED} Default)",
            "Strict P": f"{faers_bert_s42_ov['Strict_Precision_mean']:.4f} +- {faers_bert_s42_ov['Strict_Precision_std']:.4f}",
            "Strict R": f"{faers_bert_s42_ov['Strict_Recall_mean']:.4f} +- {faers_bert_s42_ov['Strict_Recall_std']:.4f}",
            "Strict F1": f"{faers_bert_s42_ov['Strict_F1_mean']:.4f} +- {faers_bert_s42_ov['Strict_F1_std']:.4f}",
            "ADE-Eval P": f"{faers_bert_s42_ov['ADE_Precision_mean']:.4f} +- {faers_bert_s42_ov['ADE_Precision_std']:.4f}",
            "ADE-Eval R": f"{faers_bert_s42_ov['ADE_Recall_mean']:.4f} +- {faers_bert_s42_ov['ADE_Recall_std']:.4f}",
            "ADE-Eval F1": f"{faers_bert_s42_ov['ADE_F1_mean']:.4f} +- {faers_bert_s42_ov['ADE_F1_std']:.4f}",
        },
        {
            "Dataset": "FAERS D1",
            "Model": "BioBERT (4-Fold LOO, 5-Seed Pooled)",
            "Strict P": f"{faers_bert_pooled_ov['Strict_Precision_mean']:.4f} +- {faers_bert_pooled_ov['Strict_Precision_std']:.4f}",
            "Strict R": f"{faers_bert_pooled_ov['Strict_Recall_mean']:.4f} +- {faers_bert_pooled_ov['Strict_Recall_std']:.4f}",
            "Strict F1": f"{faers_bert_pooled_ov['Strict_F1_mean']:.4f} +- {faers_bert_pooled_ov['Strict_F1_std']:.4f}",
            "ADE-Eval P": f"{faers_bert_pooled_ov['ADE_Precision_mean']:.4f} +- {faers_bert_pooled_ov['ADE_Precision_std']:.4f}",
            "ADE-Eval R": f"{faers_bert_pooled_ov['ADE_Recall_mean']:.4f} +- {faers_bert_pooled_ov['ADE_Recall_std']:.4f}",
            "ADE-Eval F1": f"{faers_bert_pooled_ov['ADE_F1_mean']:.4f} +- {faers_bert_pooled_ov['ADE_F1_std']:.4f}",
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
            "Model": "LLaMA 4 (1-shot, Tagged)",
            "Strict P": f"{llama4_faers_ov['Strict_Precision']:.4f}",
            "Strict R": f"{llama4_faers_ov['Strict_Recall']:.4f}",
            "Strict F1": f"{llama4_faers_ov['Strict_F1']:.4f}",
            "ADE-Eval P": f"{llama4_faers_ov['ADE_Precision']:.4f}",
            "ADE-Eval R": f"{llama4_faers_ov['ADE_Recall']:.4f}",
            "ADE-Eval F1": f"{llama4_faers_ov['ADE_F1']:.4f}",
        },
    ]

    vaers_master_table = [
        {
            "Dataset": "VAERS",
            "Model": f"BioBERT (10-Fold CV, Seed {DEFAULT_SEED} Default)",
            "Strict P": f"{vaers_bert_s42_ov['Strict_Precision_mean']:.4f} +- {vaers_bert_s42_ov['Strict_Precision_std']:.4f}",
            "Strict R": f"{vaers_bert_s42_ov['Strict_Recall_mean']:.4f} +- {vaers_bert_s42_ov['Strict_Recall_std']:.4f}",
            "Strict F1": f"{vaers_bert_s42_ov['Strict_F1_mean']:.4f} +- {vaers_bert_s42_ov['Strict_F1_std']:.4f}",
            "ADE-Eval P": f"{vaers_bert_s42_ov['ADE_Precision_mean']:.4f} +- {vaers_bert_s42_ov['ADE_Precision_std']:.4f}",
            "ADE-Eval R": f"{vaers_bert_s42_ov['ADE_Recall_mean']:.4f} +- {vaers_bert_s42_ov['ADE_Recall_std']:.4f}",
            "ADE-Eval F1": f"{vaers_bert_s42_ov['ADE_F1_mean']:.4f} +- {vaers_bert_s42_ov['ADE_F1_std']:.4f}",
        },
        {
            "Dataset": "VAERS",
            "Model": "BioBERT (10-Fold CV, 5-Seed Pooled)",
            "Strict P": f"{vaers_bert_pooled_ov['Strict_Precision_mean']:.4f} +- {vaers_bert_pooled_ov['Strict_Precision_std']:.4f}",
            "Strict R": f"{vaers_bert_pooled_ov['Strict_Recall_mean']:.4f} +- {vaers_bert_pooled_ov['Strict_Recall_std']:.4f}",
            "Strict F1": f"{vaers_bert_pooled_ov['Strict_F1_mean']:.4f} +- {vaers_bert_pooled_ov['Strict_F1_std']:.4f}",
            "ADE-Eval P": f"{vaers_bert_pooled_ov['ADE_Precision_mean']:.4f} +- {vaers_bert_pooled_ov['ADE_Precision_std']:.4f}",
            "ADE-Eval R": f"{vaers_bert_pooled_ov['ADE_Recall_mean']:.4f} +- {vaers_bert_pooled_ov['ADE_Recall_std']:.4f}",
            "ADE-Eval F1": f"{vaers_bert_pooled_ov['ADE_F1_mean']:.4f} +- {vaers_bert_pooled_ov['ADE_F1_std']:.4f}",
        },
        {
            "Dataset": "VAERS",
            "Model": "LLaMA 4 (1-shot, Target Filtered)",
            "Strict P": f"{llama4_vaers_ov['Strict_Precision']:.4f}",
            "Strict R": f"{llama4_vaers_ov['Strict_Recall']:.4f}",
            "Strict F1": f"{llama4_vaers_ov['Strict_F1']:.4f}",
            "ADE-Eval P": f"{llama4_vaers_ov['ADE_Precision']:.4f}",
            "ADE-Eval R": f"{llama4_vaers_ov['ADE_Recall']:.4f}",
            "ADE-Eval F1": f"{llama4_vaers_ov['ADE_F1']:.4f}",
        },
    ]

    df_faers_master = pd.DataFrame(faers_master_table)
    df_vaers_master = pd.DataFrame(vaers_master_table)

    # Save to Excel Workbook
    out_dir = results_base / "comparison_three_schemes"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_excel = out_dir / "three_schemes_summary.xlsx"

    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        df_faers_master.to_excel(writer, sheet_name="FAERS_Master_Benchmark", index=False)
        df_vaers_master.to_excel(writer, sheet_name="VAERS_Master_Benchmark", index=False)
        faers_bert_s42_runs.to_excel(writer, sheet_name="FAERS_BioBERT_4Fold_Seed42", index=False)
        vaers_bert_s42_runs.to_excel(writer, sheet_name="VAERS_BioBERT_10Fold_Seed42", index=False)
        faers_bert_seeds.to_excel(writer, sheet_name="Seed_Ablation_FAERS", index=False)
        vaers_bert_seeds.to_excel(writer, sheet_name="Seed_Ablation_VAERS", index=False)
        faers_bert_cat.to_excel(writer, sheet_name="BioBERT_FAERS_Categories", index=False)
        df_vaers_bert_cat_s42.to_excel(writer, sheet_name="BioBERT_VAERS_Categories", index=False)
        sonnet_faers_cat.to_excel(writer, sheet_name="Sonnet_FAERS_Categories", index=False)
        llama4_faers_cat.to_excel(writer, sheet_name="LLaMA4_FAERS_Categories", index=False)
        llama4_vaers_cat.to_excel(writer, sheet_name="LLaMA4_VAERS_Categories", index=False)
        if llama4_json_cat is not None:
            llama4_json_cat.to_excel(writer, sheet_name="LLaMA4_FAERS_JSON_Categories", index=False)

    print(f"\n[OK] Saved comprehensive multi-sheet Excel summary to:\n     {out_excel}", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(" FAERS MASTER BENCHMARK (Table 2)", flush=True)
    print("=" * 80, flush=True)
    print(df_faers_master.to_string(index=False), flush=True)

    print("\n" + "=" * 80, flush=True)
    print(" VAERS MASTER BENCHMARK (Table 3)", flush=True)
    print("=" * 80, flush=True)
    print(df_vaers_master.to_string(index=False), flush=True)

    print("\n" + "=" * 80, flush=True)
    print(f" FAERS BioBERT 4-Fold LOO Case-Series Detail (Seed {DEFAULT_SEED} Default)", flush=True)
    print("=" * 80, flush=True)
    for _, r in faers_bert_s42_runs.iterrows():
        print(f"  * {r['fold_name']:<30}: Strict F1 = {r['Strict_F1']:.4f} | ADE F1 = {r['ADE_F1']:.4f}")

    print("\n" + "=" * 80, flush=True)
    print(" SEED ABLATION ANALYSIS (5 Random Seeds: 42, 123, 456, 789, 1011)", flush=True)
    print("=" * 80, flush=True)
    print("FAERS (4 Folds per Seed):")
    print(faers_bert_seeds[["seed", "num_folds", "Strict_F1_mean", "Strict_F1_std", "ADE_F1_mean", "ADE_F1_std"]].to_string(index=False))
    print("\nVAERS (10 Folds per Seed):")
    print(vaers_bert_seeds[["seed", "num_folds", "Strict_F1_mean", "Strict_F1_std", "ADE_F1_mean", "ADE_F1_std"]].to_string(index=False))


if __name__ == "__main__":
    main()
