#!/usr/bin/env python3
"""
generate_table6.py

Generates publication-ready Table 6: BioBERT Optimization Stability and Performance
Invariance Across Five Independent Random Initialization Seeds on FAERS (4-Fold LOO, 17 Categories)
and VAERS (10-Fold CV, 14 Categories).

Exports in both Markdown (.md) and Excel (.xlsx with ESM Metadata Cover Sheet) formats.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    results_dir = repo_root / "publication" / "results"
    tables_dir = results_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    manuscript_dir = repo_root / "publication" / "manuscripts"

    # FAERS LOO Data (17 Categories)
    loo_summary_path = results_dir / "bert_runs_FAERS_LOO" / "loo_evaluation_summary.xlsx"
    print(f"Loading FAERS LOO data from {loo_summary_path}...")
    df_faers_runs = pd.read_excel(loo_summary_path, sheet_name="All_Runs_Per_Seed")

    # VAERS 10-Fold CV Data (14 Categories)
    vaers_summary_path = results_dir / "comparison_three_schemes" / "three_schemes_summary.xlsx"
    print(f"Loading VAERS CV data from {vaers_summary_path}...")
    df_vaers_seeds = pd.read_excel(vaers_summary_path, sheet_name="Seed_Ablation_VAERS")

    seeds = [42, 123, 456, 789, 1011]
    t6_rows = []

    # 1. FAERS Seeds
    for seed in seeds:
        df_s = df_faers_runs[df_faers_runs["seed"] == seed]
        s_mean = df_s["strict_F1"].mean()
        s_std = df_s["strict_F1"].std()
        a_mean = df_s["ade_F1"].mean()
        a_std = df_s["ade_F1"].std()

        t6_rows.append({
            "Dataset & Evaluation Protocol": "FAERS (4-Fold LOO, N = 829)",
            "Random Seed": f"Seed {seed}",
            "Primary Tier: Strict Exact F1": f"{s_mean:.4f} ± {s_std:.4f}",
            "Secondary Tier: Adapted ADE F1": f"{a_mean:.4f} ± {a_std:.4f}",
        })

    # FAERS Pooled
    f_strict_pooled = df_faers_runs.groupby("seed")["strict_F1"].mean()
    f_ade_pooled = df_faers_runs.groupby("seed")["ade_F1"].mean()
    t6_rows.append({
        "Dataset & Evaluation Protocol": "FAERS (4-Fold LOO, Pooled)",
        "Random Seed": "Mean ± SD (5 Seeds)",
        "Primary Tier: Strict Exact F1": f"{f_strict_pooled.mean():.4f} ± {f_strict_pooled.std():.4f}",
        "Secondary Tier: Adapted ADE F1": f"{f_ade_pooled.mean():.4f} ± {f_ade_pooled.std():.4f}",
    })

    # 2. VAERS Seeds
    for _, r in df_vaers_seeds.iterrows():
        seed_val = int(r["seed"])
        t6_rows.append({
            "Dataset & Evaluation Protocol": "VAERS (10-Fold CV, N = 1,000)",
            "Random Seed": f"Seed {seed_val}",
            "Primary Tier: Strict Exact F1": f"{r['Strict_F1_mean']:.4f} ± {r['Strict_F1_std']:.4f}",
            "Secondary Tier: Adapted ADE F1": f"{r['ADE_F1_mean']:.4f} ± {r['ADE_F1_std']:.4f}",
        })

    # VAERS Pooled
    v_strict_mean = df_vaers_seeds["Strict_F1_mean"].mean()
    v_strict_std = df_vaers_seeds["Strict_F1_mean"].std()
    v_ade_mean = df_vaers_seeds["ADE_F1_mean"].mean()
    v_ade_std = df_vaers_seeds["ADE_F1_mean"].std()
    t6_rows.append({
        "Dataset & Evaluation Protocol": "VAERS (10-Fold CV, Pooled)",
        "Random Seed": "Mean ± SD (5 Seeds)",
        "Primary Tier: Strict Exact F1": f"{v_strict_mean:.4f} ± {v_strict_std:.4f}",
        "Secondary Tier: Adapted ADE F1": f"{v_ade_mean:.4f} ± {v_ade_std:.4f}",
    })

    df_table6 = pd.DataFrame(t6_rows)

    # 1. Generate Markdown File
    md_lines = [
        "# Table 6: BioBERT Optimization Stability and Performance Invariance Across Five Independent Random Initialization Seeds",
        "",
        "Evaluation of neural network optimization stability across 5 independent training runs (seeds 42, 123, 456, 789, 1011) for supervised BioBERT on the FAERS 4-fold LOO benchmark (20 total model runs, 17 categories) and VAERS 10-fold CV benchmark (50 total model runs).",
        "",
        "| Dataset & Evaluation Protocol | Random Seed | Primary Tier: Strict Exact F1 | Secondary Tier: Adapted ADE F1 |",
        "| :--- | :--- | :---: | :---: |"
    ]

    for _, r in df_table6.iterrows():
        is_pooled = "Pooled" in r["Dataset & Evaluation Protocol"]
        ds_name = f"**{r['Dataset & Evaluation Protocol']}**" if is_pooled else r['Dataset & Evaluation Protocol']
        seed_name = f"**{r['Random Seed']}**" if is_pooled else r['Random Seed']
        f1_s = f"**{r['Primary Tier: Strict Exact F1']}**" if is_pooled else r['Primary Tier: Strict Exact F1']
        f1_a = f"**{r['Secondary Tier: Adapted ADE F1']}**" if is_pooled else r['Secondary Tier: Adapted ADE F1']

        md_lines.append(
            f"| {ds_name} | {seed_name} | {f1_s} | {f1_a} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "### Footnotes & Methodological Notes:",
        "1. **FAERS Protocol:** 4-fold Leave-One-Drug-Event-Pair-Out cross-validation evaluated across all 17 clinical concept categories. For each seed, Mean $\\pm$ SD represents out-of-fold cross-series variation.",
        "2. **VAERS Protocol:** 10-fold cross-validation on the 1,000 VAERS reports. For each seed, Mean $\\pm$ SD represents cross-fold variation across the 10 test partitions.",
        "3. **Pooled Invariance:** The pooled summary represents the Mean $\\pm$ SD across the 5 independent random initialization seeds, demonstrating minimal stochastic variation ($SD = 0.0080$ on FAERS, $SD = 0.0015$ on VAERS).",
        ""
    ])

    md_content = "\n".join(md_lines)

    out_md_tables = tables_dir / "table6_random_seed_invariance.md"
    out_md_manuscript = manuscript_dir / "table6.md"
    with open(out_md_tables, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(out_md_manuscript, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 2. Generate Excel Workbook
    esm_cover = pd.DataFrame([
        {"Metadata Field": "Article Title", "Value": "Benchmarking Fine-Tuned Encoders and Instruction-Tuned Large Language Models for Adverse Event Clinical Concept Extraction from Spontaneous Reporting Narratives"},
        {"Metadata Field": "Journal", "Value": "Drug Safety"},
        {"Metadata Field": "Table Identifier", "Value": "Table 6: BioBERT Optimization Stability and Random Seed Invariance"},
        {"Metadata Field": "Datasets", "Value": "FAERS 4-Fold LOO (N = 829, 17 Categories) & VAERS 10-Fold CV (N = 1,000 Reports)"},
        {"Metadata Field": "Random Seeds", "Value": "5 Independent Initialization Seeds (42, 123, 456, 789, 1011)"},
        {"Metadata Field": "Generated By", "Value": "publication/scripts/generate_table6.py"}
    ])

    out_excel = tables_dir / "table6_random_seed_invariance.xlsx"
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        esm_cover.to_excel(writer, sheet_name="ESM_Cover_Sheet", index=False)
        df_table6.to_excel(writer, sheet_name="Table_6_Seed_Invariance", index=False)

    print(f"Table 6 successfully generated:\n  - {out_md_tables}\n  - {out_excel}")


if __name__ == "__main__":
    main()
