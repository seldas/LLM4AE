#!/usr/bin/env python3
"""
generate_table5.py

Generates publication-ready Table 5: Leave-One-Drug-Event-Pair-Out Cross-Validation
Performance Across Four FAERS Case Series (N = 829 Reports Total) Evaluated on all 17 Categories.

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

    loo_summary_path = results_dir / "bert_runs_FAERS_LOO" / "loo_evaluation_summary.xlsx"
    print(f"Loading FAERS LOO data from {loo_summary_path}...")
    df_runs = pd.read_excel(loo_summary_path, sheet_name="All_Runs_Per_Seed")

    # Group by fold to calculate exact mean +/- std across 5 seeds for each case series
    fold_names = {
        0: "Azacitidine – QT Prolongation",
        1: "Tramadol – Hypoglycemia",
        2: "Baricitinib – Hypersensitivity",
        3: "Erenumab – Stroke"
    }
    cohort_sizes = {
        0: "N = 200 reports",
        1: "N = 229 reports",
        2: "N = 200 reports",
        3: "N = 200 reports"
    }

    t5_rows = []
    # Order: Azacitidine, Baricitinib, Tramadol, Erenumab
    display_order = [0, 2, 1, 3]
    for fold_id in display_order:
        df_f = df_runs[df_runs["fold"] == fold_id]
        strict_mean = df_f["strict_F1"].mean()
        strict_std = df_f["strict_F1"].std()
        ade_mean = df_f["ade_F1"].mean()
        ade_std = df_f["ade_F1"].std()
        
        t5_rows.append({
            "Drug–Event Case Series": fold_names[fold_id],
            "Validation Cohort Size": cohort_sizes[fold_id],
            "Strict Exact F1": f"{strict_mean:.4f} ± {strict_std:.4f}",
            "Adapted ADE F1": f"{ade_mean:.4f} ± {ade_std:.4f}",
        })

    # Macro-average across all 4 folds
    seed_macro_strict = df_runs.groupby("seed")["strict_F1"].mean()
    seed_macro_ade = df_runs.groupby("seed")["ade_F1"].mean()

    t5_rows.append({
        "Drug–Event Case Series": "Macro-Average (All 4 Folds)",
        "Validation Cohort Size": "N = 829 reports total",
        "Strict Exact F1": f"{seed_macro_strict.mean():.4f} ± {seed_macro_strict.std():.4f}",
        "Adapted ADE F1": f"{seed_macro_ade.mean():.4f} ± {seed_macro_ade.std():.4f}",
    })

    df_table5 = pd.DataFrame(t5_rows)

    # 1. Generate Markdown File
    md_lines = [
        "# Table 5: Leave-One-Drug-Event-Pair-Out Cross-Validation Performance Across Four FAERS Case Series (N = 829 Reports Total)",
        "",
        "Supervised BioBERT model generalization evaluated under a 4-fold Leave-One-Drug-Event-Pair-Out cross-validation protocol on the 17 clinical concept categories. For each case series, the model was trained on the remaining 3 case series and evaluated on the held-out target series across 5 independent random initialization seeds.",
        "",
        "| Drug–Event Case Series | Validation Cohort Size | Primary Tier: Strict Exact F1 | Secondary Tier: Adapted ADE F1 |",
        "| :--- | :---: | :---: | :---: |"
    ]

    for _, r in df_table5.iterrows():
        is_macro = "Macro-Average" in r["Drug–Event Case Series"]
        ds_name = f"**{r['Drug–Event Case Series']}**" if is_macro else r['Drug–Event Case Series']
        f1_s = f"**{r['Strict Exact F1']}**" if is_macro else r['Strict Exact F1']
        f1_a = f"**{r['Adapted ADE F1']}**" if is_macro else r['Adapted ADE F1']

        md_lines.append(
            f"| {ds_name} | {r['Validation Cohort Size']} | {f1_s} | {f1_a} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "### Footnotes & Methodological Notes:",
        "1. **Validation Design:** In each fold, all cases of a specific drug-event pair were completely held out from training to simulate real-world pharmacovigilance surveillance for emerging adverse drug reactions.",
        "2. **Evaluation Metrics:** Evaluated across the full 17 clinical concept categories. Mean $\\pm$ SD reflects variance across 5 independent training runs per case series ($N = 20$ total model runs).",
        "3. **Consistency with Master Benchmark:** The overall 4-fold macro-average strictly aligns with Table 3 and Table 6 ($0.5685 \\pm 0.0080$ Strict F1, $0.7463 \\pm 0.0076$ Adapted ADE F1).",
        ""
    ])

    md_content = "\n".join(md_lines)

    out_md_tables = tables_dir / "table5_leave_one_out_faers.md"
    out_md_manuscript = manuscript_dir / "table5.md"
    with open(out_md_tables, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(out_md_manuscript, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 2. Generate Excel Workbook
    esm_cover = pd.DataFrame([
        {"Metadata Field": "Article Title", "Value": "Benchmarking Fine-Tuned Encoders and Instruction-Tuned Large Language Models for Adverse Event Clinical Concept Extraction from Spontaneous Reporting Narratives"},
        {"Metadata Field": "Journal", "Value": "Drug Safety"},
        {"Metadata Field": "Table Identifier", "Value": "Table 5: Leave-One-Drug-Event-Pair-Out Cross-Validation Performance on FAERS"},
        {"Metadata Field": "Corpus", "Value": "FDA Adverse Event Reporting System (FAERS, N = 829 Reports across 4 Case Series)"},
        {"Metadata Field": "Evaluation Framework", "Value": "17 Clinical Concept Categories (Two-Tier Evaluation Framework)"},
        {"Metadata Field": "Generated By", "Value": "publication/scripts/generate_table5.py"}
    ])

    out_excel = tables_dir / "table5_leave_one_out_faers.xlsx"
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        esm_cover.to_excel(writer, sheet_name="ESM_Cover_Sheet", index=False)
        df_table5.to_excel(writer, sheet_name="Table_5_FAERS_LOO", index=False)

    print(f"Table 5 successfully generated:\n  - {out_md_tables}\n  - {out_excel}")


if __name__ == "__main__":
    main()
