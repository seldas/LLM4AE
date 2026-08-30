#!/usr/bin/env python3
"""
compare_output_formats.py

Compares Inline Tagged/XML output format vs Structured JSON output format
for LLaMA 4 on the FAERS D1 dataset across all three scoring schemes and categories.
"""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
import pandas as pd
import numpy as np

FAERS_TARGET_CATEGORIES = {
    "AE", "DRUG", "DX", "HX", "LAB", "DOSE", "AGE", "SEX", "STATUS", "TEMPORAL", "INDICATION", "RO", "COD"
}

EVAL_LABEL_POOL = {
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
}

def overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return (a0 == b0) or (a1 == b1) or (a0 < b0 < a1) or (a0 < b1 < a1) or (b0 < a0 < b1)

def evaluate_raw(df: pd.DataFrame, group_col: str = "document"):
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

    total_M = total_C = total_N = total_S_wc = total_S_hal = total_gold = total_gold_detected = 0
    cat_stats = defaultdict(lambda: {"M": 0, "C": 0, "N": 0, "S_wc": 0, "S_hal": 0, "gold_total": 0, "gold_detected": 0})

    for grp_val, rows in groups.items():
        gold_spans = []
        pred_spans = []
        for r in rows:
            mtype = r[mtype_idx]
            glab = str(r[glab_idx]) if pd.notna(r[glab_idx]) else None
            gcat = EVAL_LABEL_POOL.get(glab.lower(), glab.upper()) if glab else None
            if mtype in ("M", "C", "N") and gcat in FAERS_TARGET_CATEGORIES:
                g0, g1 = r[gstart_idx], r[gend_idx]
                if pd.notna(g0) and pd.notna(g1):
                    gold_spans.append((int(g0), int(g1), gcat))

            plab = str(r[plab_idx]) if pd.notna(r[plab_idx]) else None
            pcat = EVAL_LABEL_POOL.get(plab.lower(), plab.upper()) if plab else None
            if mtype in ("M", "C", "S") and pcat in FAERS_TARGET_CATEGORIES:
                p0, p1 = r[pstart_idx], r[pend_idx]
                if pd.notna(p0) and pd.notna(p1):
                    pred_spans.append((int(p0), int(p1), pcat))

        for g0, g1, gcat in gold_spans:
            total_gold += 1
            cat_stats[gcat]["gold_total"] += 1
            if any(overlap(g0, g1, p0, p1) for p0, p1, _ in pred_spans):
                total_gold_detected += 1
                cat_stats[gcat]["gold_detected"] += 1

        for r in rows:
            mtype = r[mtype_idx]
            glab = str(r[glab_idx]) if pd.notna(r[glab_idx]) else None
            plab = str(r[plab_idx]) if pd.notna(r[plab_idx]) else None
            gcat = EVAL_LABEL_POOL.get(glab.lower(), glab.upper()) if glab else None
            pcat = EVAL_LABEL_POOL.get(plab.lower(), plab.upper()) if plab else None

            if mtype == "M" and gcat in FAERS_TARGET_CATEGORIES:
                total_M += 1
                cat_stats[gcat]["M"] += 1
            elif mtype == "C" and gcat in FAERS_TARGET_CATEGORIES:
                total_C += 1
                cat_stats[gcat]["C"] += 1
            elif mtype == "N" and gcat in FAERS_TARGET_CATEGORIES:
                total_N += 1
                cat_stats[gcat]["N"] += 1
            elif mtype == "S" and pcat in FAERS_TARGET_CATEGORIES:
                p0, p1 = int(r[pstart_idx]), int(r[pend_idx])
                if any(overlap(p0, p1, g0, g1) for g0, g1, _ in gold_spans):
                    total_S_wc += 1
                    cat_stats[pcat]["S_wc"] += 1
                else:
                    total_S_hal += 1
                    cat_stats[pcat]["S_hal"] += 1

    tp1 = total_M + total_C + total_S_wc
    p1 = tp1 / (tp1 + 0.25 * total_S_hal)
    r1 = total_gold_detected / total_gold
    f1_1 = 2 * p1 * r1 / (p1 + r1)

    mc2 = total_M + 0.5 * total_C
    p2 = mc2 / (mc2 + 0.5 * total_C + 0.25 * (total_S_wc + total_S_hal))
    r2 = mc2 / (total_M + total_C + total_N)
    f1_2 = 2 * p2 * r2 / (p2 + r2)

    p3 = total_M / (total_M + total_C + total_S_wc + total_S_hal)
    r3 = total_M / (total_M + total_C + total_N)
    f1_3 = 2 * p3 * r3 / (p3 + r3)

    ov = {
        "M": total_M, "C": total_C, "N": total_N, "S_wc": total_S_wc, "S_hal": total_S_hal,
        "Total_Gold": total_gold, "Gold_Detected": total_gold_detected,
        "S1_Precision": round(p1, 4), "S1_Recall": round(r1, 4), "S1_F1": round(f1_1, 4),
        "S2_Precision": round(p2, 4), "S2_Recall": round(r2, 4), "S2_F1": round(f1_2, 4),
        "S3_Precision": round(p3, 4), "S3_Recall": round(r3, 4), "S3_F1": round(f1_3, 4),
    }

    cat_rows = []
    for cat in sorted(cat_stats.keys()):
        st = cat_stats[cat]
        # Scheme 1
        tp1_c = st["M"] + st["C"] + st["S_wc"]
        p1_c = tp1_c / (tp1_c + 0.25 * st["S_hal"]) if (tp1_c + 0.25 * st["S_hal"]) > 0 else 0.0
        r1_c = st["gold_detected"] / st["gold_total"] if st["gold_total"] > 0 else 0.0
        f1_1_c = 2 * p1_c * r1_c / (p1_c + r1_c) if (p1_c + r1_c) > 0 else 0.0

        # Scheme 2
        mc2_c = st["M"] + 0.5 * st["C"]
        p2_c = mc2_c / (mc2_c + 0.5 * st["C"] + 0.25 * (st["S_wc"] + st["S_hal"])) if (mc2_c + 0.5 * st["C"] + 0.25 * (st["S_wc"] + st["S_hal"])) > 0 else 0.0
        r2_c = mc2_c / (st["M"] + st["C"] + st["N"]) if (st["M"] + st["C"] + st["N"]) > 0 else 0.0
        f1_2_c = 2 * p2_c * r2_c / (p2_c + r2_c) if (p2_c + r2_c) > 0 else 0.0

        # Scheme 3
        p3_c = st["M"] / (st["M"] + st["C"] + st["S_wc"] + st["S_hal"]) if (st["M"] + st["C"] + st["S_wc"] + st["S_hal"]) > 0 else 0.0
        r3_c = st["M"] / (st["M"] + st["C"] + st["N"]) if (st["M"] + st["C"] + st["N"]) > 0 else 0.0
        f1_3_c = 2 * p3_c * r3_c / (p3_c + r3_c) if (p3_c + r3_c) > 0 else 0.0

        cat_rows.append({
            "Category": cat,
            "M": st["M"], "C": st["C"], "N": st["N"], "S_wc": st["S_wc"], "S_hal": st["S_hal"],
            "Gold_Total": st["gold_total"], "Gold_Detected": st["gold_detected"],
            "S1_Precision": round(p1_c, 4), "S1_Recall": round(r1_c, 4), "S1_F1": round(f1_1_c, 4),
            "S2_Precision": round(p2_c, 4), "S2_Recall": round(r2_c, 4), "S2_F1": round(f1_2_c, 4),
            "S3_Precision": round(p3_c, 4), "S3_Recall": round(r3_c, 4), "S3_F1": round(f1_3_c, 4),
        })

    return ov, pd.DataFrame(cat_rows)

def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    p_tagged = repo_root / "publication" / "results" / "llama4_runs_FAERS" / "llama4_raw.xlsx"
    p_json = repo_root / "publication" / "results" / "llama4_runs_FAERS_json" / "llama4_json_raw.xlsx"

    print("Loading Tagged XML and Structured JSON outputs for LLaMA 4...")
    df_tagged = pd.read_excel(p_tagged)
    df_json = pd.read_excel(p_json)

    ov_tagged, cat_tagged = evaluate_raw(df_tagged)
    ov_json, cat_json = evaluate_raw(df_json)

    print("\n=======================================================")
    print("OVERALL PERFORMANCE COMPARISON: TAGGED XML vs JSON")
    print("=======================================================")
    df_comp = pd.DataFrame([
        {
            "Format": "Inline Tagged (XML Markup)",
            "Scheme 1 P": ov_tagged["S1_Precision"], "Scheme 1 R": ov_tagged["S1_Recall"], "Scheme 1 F1": ov_tagged["S1_F1"],
            "Scheme 2 P": ov_tagged["S2_Precision"], "Scheme 2 R": ov_tagged["S2_Recall"], "Scheme 2 F1": ov_tagged["S2_F1"],
            "Scheme 3 P": ov_tagged["S3_Precision"], "Scheme 3 R": ov_tagged["S3_Recall"], "Scheme 3 F1": ov_tagged["S3_F1"],
            "M": ov_tagged["M"], "C": ov_tagged["C"], "N": ov_tagged["N"], "S_wc": ov_tagged["S_wc"], "S_hal": ov_tagged["S_hal"]
        },
        {
            "Format": "Structured JSON (Key-Value)",
            "Scheme 1 P": ov_json["S1_Precision"], "Scheme 1 R": ov_json["S1_Recall"], "Scheme 1 F1": ov_json["S1_F1"],
            "Scheme 2 P": ov_json["S2_Precision"], "Scheme 2 R": ov_json["S2_Recall"], "Scheme 2 F1": ov_json["S2_F1"],
            "Scheme 3 P": ov_json["S3_Precision"], "Scheme 3 R": ov_json["S3_Recall"], "Scheme 3 F1": ov_json["S3_F1"],
            "M": ov_json["M"], "C": ov_json["C"], "N": ov_json["N"], "S_wc": ov_json["S_wc"], "S_hal": ov_json["S_hal"]
        }
    ])
    print(df_comp.to_string(index=False))

    print("\n=======================================================")
    print("PER-CATEGORY F1 COMPARISON (Scheme 2 Weighted F1)")
    print("=======================================================")
    m_cat = cat_tagged[["Category", "Gold_Total", "S2_F1", "S1_F1", "S3_F1"]].merge(
        cat_json[["Category", "S2_F1", "S1_F1", "S3_F1"]],
        on="Category",
        suffixes=("_Tagged", "_JSON")
    )
    m_cat["S2_Delta (JSON - Tagged)"] = m_cat["S2_F1_JSON"] - m_cat["S2_F1_Tagged"]
    m_cat["S1_Delta (JSON - Tagged)"] = m_cat["S1_F1_JSON"] - m_cat["S1_F1_Tagged"]
    print(m_cat.to_string(index=False))

if __name__ == "__main__":
    main()
