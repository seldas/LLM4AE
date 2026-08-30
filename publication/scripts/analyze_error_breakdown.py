#!/usr/bin/env python3
"""
analyze_error_breakdown.py

Performs deep in-depth analysis on:
  1. ETHER comparison against SME1 gold annotations on FAERS (All 3 Schemes).
  2. Granular breakdown of Category 'C' (Partial Match) boundaries:
     - IoU distributions, character length delta distributions,
     - Root causes: Punctuation/Whitespace, Articles/Stopwords, Clinical Modifiers, Composite Phrases.
  3. Detailed confusion matrix for 'S' Misclassifications (S_wrong_class):
     - Gold Category vs Predicted Category mapping for all models.
     - Identification of the highest misclassification rates and most frequent confusion pairs.
  4. Root cause analysis for 'S' Hallucinations (S_hallucination):
     - Frequency distribution across categories and linguistic pattern classification.
  5. Cross-dataset performance differential (FAERS vs VAERS).

Filtering:
  - VAERS strictly filters to target categories: AE, VAX, TX, LAB, STATUS, HX
  - FAERS evaluates all standard FAERS target categories: AE, DRUG, DX, HX, LAB, DOSE, AGE, SEX, STATUS, TEMPORAL, INDICATION, RO, COD

Outputs:
  - publication/results/error_analysis/error_breakdown_summary.xlsx
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import string
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import numpy as np
import pandas as pd

# Standard Label Mapping
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

ETHER_LABEL_MAP = {
    "SYMPTOM": "AE",
    "DRUG": "DRUG",
    "SECOND_LEVEL_DIAGNOSIS": "DX",
    "DIAGNOSIS": "DX",
    "MEDICAL_HISTORY": "HX",
    "CAUSE_OF_DEATH": "COD",
    "VACCINE": "DRUG",
    "RULE_OUT": "RO",
    "FAMILY_HISTORY": "HX",
}

STOPWORDS_ARTICLES = {"a", "an", "the", "of", "in", "on", "at", "for", "with", "by", "to", "and", "or", "as"}
CLINICAL_MODIFIERS = {
    "acute", "chronic", "severe", "mild", "moderate", "recurrent", "suspected",
    "possible", "probable", "intermittent", "unspecified", "secondary", "primary",
    "multiple", "episodes", "episode", "signs", "symptoms", "history", "hx"
}


def overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return (a0 == b0) or (a1 == b1) or (a0 < b0 < a1) or (a0 < b1 < a1) or (b0 < a0 < b1)


def compute_iou(a0: int, a1: int, b0: int, b1: int) -> float:
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    return inter / union if union > 0 else 0.0


def classify_boundary_discrepancy(gold_text: str, pred_text: str) -> str:
    gt = gold_text.strip().lower()
    pt = pred_text.strip().lower()

    if not gt or not pt:
        return "Empty/Invalid"

    gt_clean = gt.strip(string.punctuation)
    pt_clean = pt.strip(string.punctuation)
    if gt_clean == pt_clean:
        return "Punctuation/Whitespace Only"

    g_tokens = gt.split()
    p_tokens = pt.split()

    if set(g_tokens) ^ set(p_tokens) <= STOPWORDS_ARTICLES:
        return "Articles/Stopwords Difference"

    if any(mod in (set(g_tokens) ^ set(p_tokens)) for mod in CLINICAL_MODIFIERS):
        return "Clinical Modifier Inclusion/Exclusion"

    if gt in pt or pt in gt:
        return "Subphrase/Superphrase Extension"

    return "Complex Boundary Shift"


def analyze_model_raw(df: pd.DataFrame, model_name: str, dataset_name: str, target_cats: Set[str], group_col: str = "document"):
    c_records = []
    s_wc_records = []
    s_hal_records = []

    groups = defaultdict(list)
    cols = {c: i for i, c in enumerate(df.columns)}

    mtype_idx = cols["match_type"]
    gstart_idx = cols["gold_start"]
    gend_idx = cols["gold_end"]
    gtxt_idx = cols["gold_text"]
    glab_idx = cols["label_gold"]
    pstart_idx = cols["pred_start"]
    pend_idx = cols["pred_end"]
    ptxt_idx = cols["pred_text"]
    plab_idx = cols["label_pred"]
    grp_idx = cols[group_col]

    for row in df.itertuples(index=False):
        groups[row[grp_idx]].append(row)

    for grp_val, rows in groups.items():
        gold_spans = []
        for r in rows:
            mtype = r[mtype_idx]
            glab = str(r[glab_idx]) if pd.notna(r[glab_idx]) else ""
            g_cat = EVAL_LABEL_POOL.get(glab.lower(), glab.upper()) if glab else None
            if mtype in ("M", "C", "N") and g_cat in target_cats:
                g0, g1 = r[gstart_idx], r[gend_idx]
                if pd.notna(g0) and pd.notna(g1):
                    gtxt = str(r[gtxt_idx]) if pd.notna(r[gtxt_idx]) else ""
                    gold_spans.append((int(g0), int(g1), glab, g_cat, gtxt))

        for r in rows:
            mtype = r[mtype_idx]
            glab = str(r[glab_idx]) if pd.notna(r[glab_idx]) else None
            plab = str(r[plab_idx]) if pd.notna(r[plab_idx]) else None
            ptxt = str(r[ptxt_idx]) if pd.notna(r[ptxt_idx]) else ""
            gtxt = str(r[gtxt_idx]) if pd.notna(r[gtxt_idx]) else ""

            g_cat = EVAL_LABEL_POOL.get(glab.lower(), glab.upper()) if glab else None
            p_cat = EVAL_LABEL_POOL.get(plab.lower(), plab.upper()) if plab else None

            if mtype == "C" and g_cat in target_cats:
                p0, p1 = int(r[pstart_idx]), int(r[pend_idx])
                g0, g1 = int(r[gstart_idx]), int(r[gend_idx])
                iou = compute_iou(g0, g1, p0, p1)
                len_delta = abs((p1 - p0) - (g1 - g0))
                cause = classify_boundary_discrepancy(gtxt, ptxt)
                c_records.append({
                    "Model": model_name, "Dataset": dataset_name, "Category": g_cat,
                    "Gold_Text": gtxt, "Pred_Text": ptxt,
                    "IoU": round(iou, 4), "Len_Delta": len_delta, "Discrepancy_Type": cause,
                })

            elif mtype == "S" and p_cat in target_cats:
                p0, p1 = int(r[pstart_idx]), int(r[pend_idx])
                overlapping_golds = [g for g in gold_spans if overlap(p0, p1, g[0], g[1])]
                if overlapping_golds:
                    best_g = max(overlapping_golds, key=lambda g: compute_iou(g[0], g[1], p0, p1))
                    s_wc_records.append({
                        "Model": model_name, "Dataset": dataset_name,
                        "Gold_Category": best_g[3], "Pred_Category": p_cat,
                        "Gold_Label": best_g[2], "Pred_Label": plab,
                        "Gold_Text": best_g[4], "Pred_Text": ptxt,
                        "IoU": round(compute_iou(best_g[0], best_g[1], p0, p1), 4),
                    })
                else:
                    s_hal_records.append({
                        "Model": model_name, "Dataset": dataset_name,
                        "Pred_Category": p_cat, "Pred_Label": plab, "Pred_Text": ptxt,
                    })

    return pd.DataFrame(c_records), pd.DataFrame(s_wc_records), pd.DataFrame(s_hal_records)


def evaluate_ether(db_path: str) -> Tuple[dict, pd.DataFrame]:
    conn = sqlite3.connect(db_path)
    q_sme = "SELECT a.doc_id, a.label, a.tc_start, a.tc_end, a.tc_text FROM annotations a JOIN documents d ON a.doc_id = d.doc_id WHERE d.dataset = 'FAERS' AND a.note = 'SME1'"
    df_sme = pd.read_sql(q_sme, conn)
    q_ether = "SELECT a.doc_id, a.label, a.tc_start, a.tc_end, a.tc_text, a.used FROM annotations a JOIN documents d ON a.doc_id = d.doc_id WHERE d.dataset = 'FAERS' AND a.note = 'ETHER'"
    df_ether = pd.read_sql(q_ether, conn)

    sme_by_doc = defaultdict(list)
    for r in df_sme.itertuples(index=False):
        cat = EVAL_LABEL_POOL.get(r.label.lower(), r.label.upper())
        if cat in FAERS_TARGET_CATEGORIES:
            sme_by_doc[r.doc_id].append((r.tc_start, r.tc_end, r.label.lower(), cat, r.tc_text))

    ether_by_doc = defaultdict(list)
    for r in df_ether.itertuples(index=False):
        cat = ETHER_LABEL_MAP.get(r.label, "OTHERS")
        if cat in FAERS_TARGET_CATEGORIES:
            ether_by_doc[r.doc_id].append((r.tc_start, r.tc_end, r.label, cat, r.tc_text, r.used))

    M = C = N = S_wc = S_hal = gold_total = gold_detected = 0
    cat_counts = defaultdict(lambda: {"M": 0, "C": 0, "N": 0, "S_wc": 0, "S_hal": 0, "gold_total": 0, "gold_detected": 0})

    for doc_id, g_spans in sme_by_doc.items():
        e_spans = [e for e in ether_by_doc[doc_id] if e[5] == "Yes"]
        pred_matched = [False] * len(e_spans)

        for g0, g1, glab, gcat, gtxt in g_spans:
            gold_total += 1
            cat_counts[gcat]["gold_total"] += 1
            exact_j = None
            partial_j = None
            best_ol = 0

            for j, (p0, p1, plab, pcat, ptxt, used) in enumerate(e_spans):
                if pred_matched[j]:
                    continue
                if p0 == g0 and p1 == g1 and pcat == gcat:
                    exact_j = j
                    break
                if pcat == gcat and overlap(g0, g1, p0, p1):
                    ol = max(0, min(g1, p1) - max(g0, p0))
                    if ol > best_ol:
                        best_ol = ol
                        partial_j = j

            if exact_j is not None:
                M += 1
                cat_counts[gcat]["M"] += 1
                pred_matched[exact_j] = True
                gold_detected += 1
                cat_counts[gcat]["gold_detected"] += 1
            elif partial_j is not None:
                C += 1
                cat_counts[gcat]["C"] += 1
                pred_matched[partial_j] = True
                gold_detected += 1
                cat_counts[gcat]["gold_detected"] += 1
            else:
                N += 1
                cat_counts[gcat]["N"] += 1
                if any(overlap(g0, g1, p0, p1) for p0, p1, _, _, _, _ in e_spans):
                    gold_detected += 1
                    cat_counts[gcat]["gold_detected"] += 1

        for j, (p0, p1, plab, pcat, ptxt, used) in enumerate(e_spans):
            if pred_matched[j]:
                continue
            if any(overlap(p0, p1, g0, g1) for g0, g1, _, _, _ in g_spans):
                S_wc += 1
                cat_counts[pcat]["S_wc"] += 1
            else:
                S_hal += 1
                cat_counts[pcat]["S_hal"] += 1

    # Scheme 1
    tp1 = M + C + S_wc
    p1 = tp1 / (tp1 + 0.25 * S_hal) if (tp1 + 0.25 * S_hal) > 0 else 0.0
    r1 = gold_detected / gold_total if gold_total > 0 else 0.0
    f1_1 = 2 * p1 * r1 / (p1 + r1) if (p1 + r1) > 0 else 0.0

    # Scheme 2
    mc2 = M + 0.5 * C
    p2 = mc2 / (mc2 + 0.5 * C + 0.25 * (S_wc + S_hal)) if (mc2 + 0.5 * C + 0.25 * (S_wc + S_hal)) > 0 else 0.0
    r2 = mc2 / (M + C + N) if (M + C + N) > 0 else 0.0
    f1_2 = 2 * p2 * r2 / (p2 + r2) if (p2 + r2) > 0 else 0.0

    # Scheme 3
    p3 = M / (M + C + S_wc + S_hal) if (M + C + S_wc + S_hal) > 0 else 0.0
    r3 = M / (M + C + N) if (M + C + N) > 0 else 0.0
    f1_3 = 2 * p3 * r3 / (p3 + r3) if (p3 + r3) > 0 else 0.0

    ov = {
        "Dataset": "FAERS D1", "Model": "ETHER (used=Yes)",
        "S1 (Relaxed) P": f"{p1:.4f}", "S1 (Relaxed) R": f"{r1:.4f}", "S1 (Relaxed) F1": f"{f1_1:.4f}",
        "S2 (Weighted) P": f"{p2:.4f}", "S2 (Weighted) R": f"{r2:.4f}", "S2 (Weighted) F1": f"{f1_2:.4f}",
        "S3 (Strict) P": f"{p3:.4f}", "S3 (Strict) R": f"{r3:.4f}", "S3 (Strict) F1": f"{f1_3:.4f}",
    }

    cat_rows = []
    for cat in sorted(cat_counts.keys()):
        cnt = cat_counts[cat]
        # Scheme 1
        tp1_c = cnt["M"] + cnt["C"] + cnt["S_wc"]
        p1_c = tp1_c / (tp1_c + 0.25 * cnt["S_hal"]) if (tp1_c + 0.25 * cnt["S_hal"]) > 0 else 0.0
        r1_c = cnt["gold_detected"] / cnt["gold_total"] if cnt["gold_total"] > 0 else 0.0
        f1_1_c = 2 * p1_c * r1_c / (p1_c + r1_c) if (p1_c + r1_c) > 0 else 0.0

        # Scheme 2
        mc2_c = cnt["M"] + 0.5 * cnt["C"]
        p2_c = mc2_c / (mc2_c + 0.5 * cnt["C"] + 0.25 * (cnt["S_wc"] + cnt["S_hal"])) if (mc2_c + 0.5 * cnt["C"] + 0.25 * (cnt["S_wc"] + cnt["S_hal"])) > 0 else 0.0
        r2_c = mc2_c / (cnt["M"] + cnt["C"] + cnt["N"]) if (cnt["M"] + cnt["C"] + cnt["N"]) > 0 else 0.0
        f1_2_c = 2 * p2_c * r2_c / (p2_c + r2_c) if (p2_c + r2_c) > 0 else 0.0

        # Scheme 3
        p3_c = cnt["M"] / (cnt["M"] + cnt["C"] + cnt["S_wc"] + cnt["S_hal"]) if (cnt["M"] + cnt["C"] + cnt["S_wc"] + cnt["S_hal"]) > 0 else 0.0
        r3_c = cnt["M"] / (cnt["M"] + cnt["C"] + cnt["N"]) if (cnt["M"] + cnt["C"] + cnt["N"]) > 0 else 0.0
        f1_3_c = 2 * p3_c * r3_c / (p3_c + r3_c) if (p3_c + r3_c) > 0 else 0.0

        cat_rows.append({
            "Category": cat,
            "M": cnt["M"], "C": cnt["C"], "N": cnt["N"], "S_wrong_class": cnt["S_wc"], "S_hallucination": cnt["S_hal"],
            "Gold_Total": cnt["gold_total"], "Gold_Detected": cnt["gold_detected"],
            "S1_Precision": round(p1_c, 4), "S1_Recall": round(r1_c, 4), "S1_F1": round(f1_1_c, 4),
            "S2_Precision": round(p2_c, 4), "S2_Recall": round(r2_c, 4), "S2_F1": round(f1_2_c, 4),
            "S3_Precision": round(p3_c, 4), "S3_Recall": round(r3_c, 4), "S3_F1": round(f1_3_c, 4),
        })

    return ov, pd.DataFrame(cat_rows)


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    results_base = repo_root / "publication" / "results"
    db_path = str(repo_root / "publication" / "dataset.db")

    print("=================================================================", flush=True)
    print("Running In-depth Error Breakdown & ETHER Comparison (Filtered)", flush=True)
    print("=================================================================", flush=True)

    # 1. ETHER Evaluation
    print("[1/5] Evaluating ETHER system against SME1 Gold on FAERS...", flush=True)
    ether_ov, ether_cat = evaluate_ether(db_path)

    # 2. Loading model raw data
    print("[2/5] Analyzing Category C and S across models...", flush=True)
    df_sonnet_raw = pd.read_excel(results_base / "sonnet_runs_FAERS" / "sonnet_raw.xlsx")
    df_l4_faers_raw = pd.read_excel(results_base / "llama4_runs_FAERS" / "llama4_raw.xlsx")
    df_l4_vaers_raw = pd.read_excel(results_base / "llama4_runs_VAERS" / "llama4_raw.xlsx")
    df_bert_faers_f0 = pd.read_excel(results_base / "bert_runs_FAERS" / "fold_00_raw.xlsx")
    df_bert_vaers_f0 = pd.read_excel(results_base / "bert_runs_VAERS" / "fold_00_raw.xlsx")

    c_sonnet, s_wc_sonnet, s_hal_sonnet = analyze_model_raw(df_sonnet_raw, "Claude 4.6 Sonnet", "FAERS", FAERS_TARGET_CATEGORIES, "document")
    c_l4_f, s_wc_l4_f, s_hal_l4_f = analyze_model_raw(df_l4_faers_raw, "LLaMA 4", "FAERS", FAERS_TARGET_CATEGORIES, "document")
    c_l4_v, s_wc_l4_v, s_hal_l4_v = analyze_model_raw(df_l4_vaers_raw, "LLaMA 4", "VAERS", VAERS_TARGET_CATEGORIES, "document")
    c_b_f, s_wc_b_f, s_hal_b_f = analyze_model_raw(df_bert_faers_f0, "BioBERT (Fold 0)", "FAERS", FAERS_TARGET_CATEGORIES, "sent_id")
    c_b_v, s_wc_b_v, s_hal_b_v = analyze_model_raw(df_bert_vaers_f0, "BioBERT (Fold 0)", "VAERS", VAERS_TARGET_CATEGORIES, "sent_id")

    all_c = pd.concat([c_sonnet, c_l4_f, c_l4_v, c_b_f, c_b_v], ignore_index=True)
    all_s_wc = pd.concat([s_wc_sonnet, s_wc_l4_f, s_wc_l4_v, s_wc_b_f, s_wc_b_v], ignore_index=True)
    all_s_hal = pd.concat([s_hal_sonnet, s_hal_l4_f, s_hal_l4_v, s_hal_b_f, s_hal_b_v], ignore_index=True)

    # 3. Category C Discrepancy Summary
    print("[3/5] Summarizing Category C boundary overlap distributions...", flush=True)
    c_summary = []
    for (m, d), grp in all_c.groupby(["Model", "Dataset"]):
        total_c = len(grp)
        iou_gte_08 = (grp["IoU"] >= 0.8).sum() / total_c * 100
        iou_05_08 = ((grp["IoU"] >= 0.5) & (grp["IoU"] < 0.8)).sum() / total_c * 100
        iou_lt_05 = (grp["IoU"] < 0.5).sum() / total_c * 100

        cause_counts = grp["Discrepancy_Type"].value_counts(normalize=True) * 100

        c_summary.append({
            "Model": m, "Dataset": d, "Total_C_Spans": total_c,
            "Mean_IoU": round(grp["IoU"].mean(), 4),
            "Median_IoU": round(grp["IoU"].median(), 4),
            "IoU >= 0.8 (%)": round(iou_gte_08, 2),
            "0.5 <= IoU < 0.8 (%)": round(iou_05_08, 2),
            "IoU < 0.5 (%)": round(iou_lt_05, 2),
            "Punctuation/Whitespace (%)": round(cause_counts.get("Punctuation/Whitespace Only", 0), 2),
            "Articles/Stopwords (%)": round(cause_counts.get("Articles/Stopwords Difference", 0), 2),
            "Clinical Modifier (%)": round(cause_counts.get("Clinical Modifier Inclusion/Exclusion", 0), 2),
            "Subphrase/Superphrase (%)": round(cause_counts.get("Subphrase/Superphrase Extension", 0), 2),
            "Complex Boundary Shift (%)": round(cause_counts.get("Complex Boundary Shift", 0), 2),
        })
    df_c_summary = pd.DataFrame(c_summary)

    # 4. Confusion Matrix for S_wrong_class
    print("[4/5] Computing S_wrong_class confusion matrices...", flush=True)
    confusion_sonnet = pd.crosstab(s_wc_sonnet["Gold_Category"], s_wc_sonnet["Pred_Category"], margins=True)
    confusion_l4_f = pd.crosstab(s_wc_l4_f["Gold_Category"], s_wc_l4_f["Pred_Category"], margins=True)
    confusion_l4_v = pd.crosstab(s_wc_l4_v["Gold_Category"], s_wc_l4_v["Pred_Category"], margins=True)

    # 5. Hallucination Breakdown
    print("[5/5] Analyzing S_hallucination patterns...", flush=True)
    hal_summary = []
    for (m, d), grp in all_s_hal.groupby(["Model", "Dataset"]):
        total_hal = len(grp)
        top_cats = grp["Pred_Category"].value_counts().head(5).to_dict()
        top_texts = grp["Pred_Text"].value_counts().head(10).to_dict()
        hal_summary.append({
            "Model": m, "Dataset": d, "Total_Hallucinations": total_hal,
            "Top_Categories": str(top_cats),
            "Top_Hallucinated_Terms": str(top_texts),
        })
    df_hal_summary = pd.DataFrame(hal_summary)

    # Save to Excel
    out_dir = results_base / "error_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_excel = out_dir / "error_breakdown_summary.xlsx"

    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        pd.DataFrame([ether_ov]).to_excel(writer, sheet_name="ETHER_Overall", index=False)
        ether_cat.to_excel(writer, sheet_name="ETHER_Categories", index=False)
        df_c_summary.to_excel(writer, sheet_name="Category_C_Granularity", index=False)
        confusion_sonnet.to_excel(writer, sheet_name="Confusion_Sonnet_FAERS")
        confusion_l4_f.to_excel(writer, sheet_name="Confusion_LLaMA4_FAERS")
        confusion_l4_v.to_excel(writer, sheet_name="Confusion_LLaMA4_VAERS")
        df_hal_summary.to_excel(writer, sheet_name="Hallucination_Summary", index=False)

    print(f"\nSaved Error Breakdown summary to: {out_excel}", flush=True)
    print("\n--- ETHER OVERALL SUMMARY ---", flush=True)
    print(pd.DataFrame([ether_ov]).to_string(index=False), flush=True)
    print("\n--- CATEGORY C GRANULARITY SUMMARY ---", flush=True)
    print(df_c_summary.to_string(index=False), flush=True)
    print("\n--- TOP CONFUSION PAIRS (Claude 4.6 Sonnet FAERS) ---", flush=True)
    print(s_wc_sonnet.groupby(["Gold_Category", "Pred_Category"]).size().sort_values(ascending=False).head(10), flush=True)
    print("\n--- TOP CONFUSION PAIRS (LLaMA 4 FAERS) ---", flush=True)
    print(s_wc_l4_f.groupby(["Gold_Category", "Pred_Category"]).size().sort_values(ascending=False).head(10), flush=True)
    print("\n--- TOP CONFUSION PAIRS (LLaMA 4 VAERS) ---", flush=True)
    print(s_wc_l4_v.groupby(["Gold_Category", "Pred_Category"]).size().sort_values(ascending=False).head(10), flush=True)


if __name__ == "__main__":
    main()
