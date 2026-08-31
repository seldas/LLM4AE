#!/usr/bin/env python3
"""
generate_table3.py

Generates publication-ready Table 3 (VAERS Master Performance Benchmark)
in both Markdown (.md) and Excel (.xlsx with ESM Metadata Cover Sheet) formats.

Reads directly from:
- publication/results/comparison_three_schemes/three_schemes_summary.xlsx
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

    three_schemes_path = results_dir / "comparison_three_schemes" / "three_schemes_summary.xlsx"
    print(f"Loading VAERS benchmark data from {three_schemes_path}...")
    df_vaers_master = pd.read_excel(three_schemes_path, sheet_name="VAERS_Master_Benchmark")

    table3_rows = []
    for _, r in df_vaers_master.iterrows():
        model_name = r["Model"]
        if "BioBERT" in model_name:
            family = "Fine-Tuned Encoder"
            paradigm = "Sentence Token Classification"
        elif "LLaMA" in model_name:
            family = "Open-Weight LLM"
            paradigm = "Inline Tagged XML (`P2_TAG_VAERS`)"
        else:
            family = "Model Family"
            paradigm = "Text Processing"

        table3_rows.append({
            "Model Family": family,
            "Model & Configuration": model_name,
            "Input Paradigm": paradigm,
            "Strict Precision": r["Strict P"],
            "Strict Recall": r["Strict R"],
            "Strict F1": r["Strict F1"],
            "ADE-Eval Precision": r["ADE-Eval P"],
            "ADE-Eval Recall": r["ADE-Eval R"],
            "ADE-Eval F1": r["ADE-Eval F1"],
        })

    df_table3 = pd.DataFrame(table3_rows)

    # 1. Generate Markdown File
    md_lines = [
        "# Table 3: Master Performance Benchmark on the VAERS Dataset (N = 1,000 Reports)",
        "",
        "Overall performance of evaluated model families across the Two-Tier Evaluation Framework on the Vaccine Adverse Event Reporting System (VAERS) benchmark corpus. Micro-averaged precision (P), recall (R), and F1 scores are reported.",
        "",
        "| Model Family | Model & Configuration | Input Paradigm | Primary Tier: Strict Exact-Match NER ||| Secondary Tier: Adapted ADE-Eval Weighted Metric |||",
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        "| | | | **P** | **R** | **F1** | **P** | **R** | **F1** |"
    ]

    def fmt_stat(val: str) -> str:
        s = str(val)
        if "+-" in s:
            return "$" + s.replace("+-", r"\pm") + "$"
        return s

    for _, r in df_table3.iterrows():
        fam = f"**{r['Model Family']}**" if ("Seed 42" in r["Model & Configuration"] or "LLaMA" in r["Model & Configuration"]) else ""
        m_cfg = r["Model & Configuration"]
        if "Seed 42 Default" in m_cfg:
            m_cfg = m_cfg + "$^\\dagger$"
        elif "5-Seed Pooled" in m_cfg:
            m_cfg = m_cfg + "$^\\ddagger$"
            
        p_strict = fmt_stat(r['Strict Precision'])
        r_strict = fmt_stat(r['Strict Recall'])
        f1_strict = fmt_stat(r['Strict F1'])
        p_ade = fmt_stat(r['ADE-Eval Precision'])
        r_ade = fmt_stat(r['ADE-Eval Recall'])
        f1_ade = fmt_stat(r['ADE-Eval F1'])

        md_lines.append(
            f"| {fam} | {m_cfg} | {r['Input Paradigm']} | "
            f"{p_strict} | {r_strict} | **{f1_strict}** | "
            f"{p_ade} | {r_ade} | **{f1_ade}** |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "### Footnotes & Methodological Notes:",
        "- **Primary Tier (Strict Exact-Match NER / Scheme 3):** Standard exact character-boundary and exact-category match. $\\text{Precision} = M / (M + C_{\\text{total}} + S_{\\text{non\\_overlap}})$, $\\text{Recall} = M / (M + C_{\\text{total}} + N)$, $\\text{F1} = 2PR / (P+R)$, where $M$ is exact match, $C_{\\text{total}} = C_{\\text{boundary}} + C_{\\text{class}}$ represents boundary inexactness and category misclassification, $S_{\\text{non\\_overlap}}$ represents ungrounded false positives with zero gold overlap, and $N$ represents false negatives.",
        "- **Secondary Tier (Adapted ADE-Eval Clinical Weighted Metric / Scheme 2):** Grants partial credit (0.5 weight) to partially localized/misclassified clinical mentions ($C_{\\text{total}}$) and applies a 0.25 denominator weight to non-overlapping false positives ($S_{\\text{non\\_overlap}}$). $\\text{Precision} = (M + 0.5 C_{\\text{total}}) / (M + C_{\\text{total}} + 0.25 S_{\\text{non\\_overlap}})$, $\\text{Recall} = (M + 0.5 C_{\\text{total}}) / (M + C_{\\text{total}} + N)$.",
        "- $^\\dagger$ **BioBERT (Seed 42 Default):** Primary in-distribution 10-fold cross-validation on the 1,000 VAERS reports using random initialization seed 42. Mean $\\pm$ SD reflects variance across the 10 test folds.",
        "- $^\\ddagger$ **BioBERT (5-Seed Pooled):** 10-fold cross-validation repeated across 5 independent random initialization seeds (`42, 123, 456, 789, 1011`), summarizing cross-fold variance and optimization stability ($N = 50$ total training runs).",
        "- **Target Schema Filtering:** Performance is evaluated against the 6 core VAERS gold target categories (`AE`, `HX`, `LAB`, `STATUS`, `TX`, `VAX`). Non-gold categories extracted by the LLM (e.g., `DOSE`, `AGE`, `SEX`) are filtered prior to scoring to prevent artificial false positive penalties.",
        ""
    ])

    md_content = "\n".join(md_lines)

    # Write Markdown outputs
    out_md_tables = tables_dir / "table3_master_benchmark_vaers.md"
    out_md_manuscript = manuscript_dir / "table3.md"
    out_md_results = results_dir / "table3.md"

    with open(out_md_tables, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(out_md_manuscript, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(out_md_results, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 2. Generate Excel Workbook with ESM Cover Sheet
    esm_cover = pd.DataFrame([
        {"Metadata Field": "Article Title", "Value": "Benchmarking Fine-Tuned Encoders and Instruction-Tuned Large Language Models for Adverse Event Clinical Concept Extraction from Spontaneous Reporting Narratives"},
        {"Metadata Field": "Journal", "Value": "Drug Safety"},
        {"Metadata Field": "Table Identifier", "Value": "Table 3: VAERS Master Performance Benchmark"},
        {"Metadata Field": "Corpus", "Value": "Vaccine Adverse Event Reporting System (VAERS, N = 1,000 Reports)"},
        {"Metadata Field": "Evaluation Framework", "Value": "Two-Tier Evaluation Framework (Tier 1: Strict CoNLL; Tier 2: Adapted ADE-Eval)"},
        {"Metadata Field": "Generated By", "Value": "publication/scripts/generate_table3.py"}
    ])

    out_excel = tables_dir / "table3_master_benchmark_vaers.xlsx"
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        esm_cover.to_excel(writer, sheet_name="ESM_Cover_Sheet", index=False)
        df_table3.to_excel(writer, sheet_name="Table_3_VAERS_Benchmark", index=False)

    print(f"Table 3 successfully exported to:\n  - {out_md_tables}\n  - {out_md_manuscript}\n  - {out_excel}")


if __name__ == "__main__":
    main()
