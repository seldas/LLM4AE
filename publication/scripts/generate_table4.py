#!/usr/bin/env python3
"""
generate_table4.py

Generates publication-ready Table 4 (FAERS 11-Category Evaluation Table)
in both Markdown (.md) and Excel (.xlsx with ESM Metadata Cover Sheet) formats.

Compares per-category performance across:
1. BioBERT (4-Fold LOO, 5-Seed Pooled / Mean +- SD)
2. Claude 4.6 Sonnet (1-shot In-Context Prompting)
3. LLaMA 4 (1-shot, Inline Tagged XML)
4. LLaMA 4 (1-shot, Structured JSON)

Reads directly from:
- publication/results/comparison_three_schemes/three_schemes_summary.xlsx
- publication/results/bert_runs_FAERS_LOO/loo_evaluation_summary.xlsx
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
    loo_summary_path = results_dir / "bert_runs_FAERS_LOO" / "loo_evaluation_summary.xlsx"

    print(f"Loading category breakdown data from {three_schemes_path} and {loo_summary_path}...")
    df_sonnet_cat = pd.read_excel(three_schemes_path, sheet_name="Sonnet_FAERS_Categories")
    df_llama4_cat = pd.read_excel(three_schemes_path, sheet_name="LLaMA4_FAERS_Categories")
    df_llama4_json_cat = pd.read_excel(three_schemes_path, sheet_name="LLaMA4_FAERS_JSON_Categories")
    df_loo_cat = pd.read_excel(loo_summary_path, sheet_name="Per_Category_Summary")

    # Map BioBERT LOO categories
    loo_cat_map = {}
    for _, r in df_loo_cat.iterrows():
        c_name = str(r["category"]).upper()
        s_f1 = f"${r['strict_F1_mean']:.4f} \\pm {r['strict_F1_std']:.4f}$"
        a_f1 = f"${r['ade_F1_mean']:.4f} \\pm {r['ade_F1_std']:.4f}$"
        loo_cat_map[c_name] = {"Strict_F1": s_f1, "ADE_F1": a_f1}

    # Extract all categories from Sonnet gold counts
    categories = sorted(df_sonnet_cat["Category"].unique())

    table4_rows = []
    for cat in categories:
        s_row = df_sonnet_cat[df_sonnet_cat["Category"] == cat].iloc[0]
        l_row = df_llama4_cat[df_llama4_cat["Category"] == cat].iloc[0]
        lj_rows = df_llama4_json_cat[df_llama4_json_cat["Category"] == cat]
        lj_row = lj_rows.iloc[0] if len(lj_rows) > 0 else None

        gold_total = int(s_row["Gold_Total"])
        loo_entry = loo_cat_map.get(cat, {"Strict_F1": "N/A", "ADE_F1": "N/A"})

        table4_rows.append({
            "Category": cat,
            "Gold Support (N)": gold_total,
            "BioBERT LOO Strict F1": loo_entry["Strict_F1"],
            "BioBERT LOO ADE-Eval F1": loo_entry["ADE_F1"],
            "Claude Sonnet Strict F1": f"{s_row['Strict_F1']:.4f}",
            "Claude Sonnet ADE-Eval F1": f"{s_row['ADE_F1']:.4f}",
            "LLaMA 4 (Tagged) Strict F1": f"{l_row['Strict_F1']:.4f}",
            "LLaMA 4 (Tagged) ADE-Eval F1": f"{l_row['ADE_F1']:.4f}",
            "LLaMA 4 (JSON) Strict F1": f"{lj_row['Strict_F1']:.4f}" if lj_row is not None else "N/A",
            "LLaMA 4 (JSON) ADE-Eval F1": f"{lj_row['ADE_F1']:.4f}" if lj_row is not None else "N/A",
        })

    df_table4 = pd.DataFrame(table4_rows)

    # 1. Generate Markdown File
    md_lines = [
        "# Table 4: Per-Category Performance Breakdown on FAERS (N = 829 Reports)",
        "",
        "Fine-grained concept extraction performance across all clinical categories on the FAERS benchmark corpus under the Two-Tier Evaluation Framework. Values report Strict Exact-Match NER F1 and Adapted ADE-Eval Clinical Weighted F1.",
        "",
        "| Clinical Category | Gold Support (N) | BioBERT (4-Fold LOO)$^\\dagger$ || Claude 4.6 Sonnet (1-shot) || LLaMA 4 (1-shot, Tagged) || LLaMA 4 (1-shot, JSON) ||",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        "| | | **Strict F1** | **ADE-Eval F1** | **Strict F1** | **ADE-Eval F1** | **Strict F1** | **ADE-Eval F1** | **Strict F1** | **ADE-Eval F1** |"
    ]

    for _, r in df_table4.iterrows():
        md_lines.append(
            f"| **{r['Category']}** | {r['Gold Support (N)']:,} | "
            f"{r['BioBERT LOO Strict F1']} | {r['BioBERT LOO ADE-Eval F1']} | "
            f"{r['Claude Sonnet Strict F1']} | {r['Claude Sonnet ADE-Eval F1']} | "
            f"{r['LLaMA 4 (Tagged) Strict F1']} | {r['LLaMA 4 (Tagged) ADE-Eval F1']} | "
            f"{r['LLaMA 4 (JSON) Strict F1']} | {r['LLaMA 4 (JSON) ADE-Eval F1']} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "### Footnotes & Clinical Interpretations:",
        "- **Primary Tier (Strict Exact-Match NER):** Requires identical character span boundaries and category assignment. Partial overlaps receive 0 credit.",
        "- **Secondary Tier (Adapted ADE-Eval Weighted Metric):** Grants 0.5 partial credit to boundary shifts and adjacent category confusions, applying a 0.25 denominator penalty to ungrounded non-overlapping false positives.",
        "- $^\\dagger$ **BioBERT (4-Fold LOO, 5-Seed Pooled):** Reports mean $\\pm$ standard deviation across the 4 held-out case series and 5 random initialization seeds (`42, 123, 456, 789, 1011`).",
        "- **Key Observations:**",
        "  1. **Demographic Entities (`AGE`, `SEX`):** Extremely high precision and boundary agreement across all models (F1 $> 0.82 - 0.95$).",
        "  2. **Core Clinical Concepts (`AE`, `DRUG`):** BioBERT maintains highest exact-boundary capture (Strict F1: 0.5115 for AE, 0.5280 for DRUG), while LLMs achieve strong semantic detection under ADE-Eval (ADE F1: 0.6259 for Sonnet, 0.6508 for LLaMA 4).",
        "  3. **The `INDICATION` Generalization Contrast:** BioBERT exhibits severe out-of-distribution transfer degradation when encountering unseen indication contexts in held-out case series (Strict F1: 0.0368, ADE F1: 0.0864). In contrast, zero/few-shot LLMs leverage broad pre-trained medical knowledge to preserve robust indication recognition (ADE F1: 0.4617 for Sonnet, 0.4493 for LLaMA 4 Tagged).",
        "  4. **Output Format Contrast (Tagged vs. JSON):** Structured JSON increases exact-match precision for discrete entities like `AE` (+3.8% Strict F1) by eliminating loose descriptive boundaries, but slightly impairs multi-word modifier categories.",
        ""
    ])

    md_content = "\n".join(md_lines)

    # Write Markdown outputs
    out_md_tables = tables_dir / "table4_category_breakdown_faers.md"
    out_md_manuscript = manuscript_dir / "table4.md"
    out_md_results = results_dir / "table4.md"

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
        {"Metadata Field": "Table Identifier", "Value": "Table 4: FAERS Per-Category Performance Breakdown"},
        {"Metadata Field": "Corpus", "Value": "FDA Adverse Event Reporting System (FAERS D1, N = 829 Reports)"},
        {"Metadata Field": "Evaluation Framework", "Value": "Two-Tier Evaluation Framework (Tier 1: Strict CoNLL; Tier 2: Adapted ADE-Eval)"},
        {"Metadata Field": "Generated By", "Value": "publication/scripts/generate_table4.py"}
    ])

    out_excel = tables_dir / "table4_category_breakdown_faers.xlsx"
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        esm_cover.to_excel(writer, sheet_name="ESM_Cover_Sheet", index=False)
        df_table4.to_excel(writer, sheet_name="Table_4_Category_Breakdown", index=False)

    print(f"Table 4 successfully exported to:\n  - {out_md_tables}\n  - {out_md_manuscript}\n  - {out_excel}")


if __name__ == "__main__":
    main()
