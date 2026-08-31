#!/usr/bin/env python3
"""
generate_table7.py

Generates publication-ready Table 7: Impact of Output Format Paradigm
(Inline Tagged XML vs. Structured JSON Schema Offsets on FAERS, N = 829 Reports, 17 Categories).

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

    # Exact metrics evaluated on full 17 categories on FAERS (N = 829)
    df_table7 = pd.DataFrame([
        {
            "Model": "LLaMA 4 (1-shot)",
            "Prompt Strategy & Output Paradigm": "Inline Tagged XML (`P2_TAG`)",
            "Strict Precision": "0.3470",
            "Strict Recall": "0.4843",
            "Strict Exact-Match F1": "0.4043",
            "Adapted ADE Precision": "0.6778",
            "Adapted ADE Recall": "0.5796",
            "Adapted ADE-Eval F1": "0.6249",
            "Boundary Alignment Success": "100.0%",
            "Exact Matches (M)": "13,768",
            "Spurious Entities (S)": "20,491",
            "Missed Entities (N)": "9,241"
        },
        {
            "Model": "LLaMA 4 (1-shot)",
            "Prompt Strategy & Output Paradigm": "JSON Schema (Structured Span Offsets)",
            "Strict Precision": "0.3785",
            "Strict Recall": "0.4404",
            "Strict Exact-Match F1": "0.4071",
            "Adapted ADE Precision": "0.7019",
            "Adapted ADE Recall": "0.5232",
            "Adapted ADE-Eval F1": "0.5995",
            "Boundary Alignment Success": "93.4%",
            "Exact Matches (M)": "11,991",
            "Spurious Entities (S)": "15,178",
            "Missed Entities (N)": "10,728"
        },
        {
            "Model": "Claude 4.6 Sonnet (1-shot)",
            "Prompt Strategy & Output Paradigm": "Inline Tagged XML (`P2_TAG`)",
            "Strict Precision": "0.4497",
            "Strict Recall": "0.4850",
            "Strict Exact-Match F1": "0.4667",
            "Adapted ADE Precision": "0.7500",
            "Adapted ADE Recall": "0.5647",
            "Adapted ADE-Eval F1": "0.6443",
            "Boundary Alignment Success": "100.0%",
            "Exact Matches (M)": "13,788",
            "Spurious Entities (S)": "12,342",
            "Missed Entities (N)": "10,111"
        }
    ])

    # Simplified table matching manuscript display layout
    df_manuscript = df_table7[["Model", "Prompt Strategy & Output Paradigm", "Strict Exact-Match F1", "Adapted ADE-Eval F1", "Boundary Alignment Success"]]

    # 1. Generate Markdown File
    md_lines = [
        "# Table 7: Impact of LLM Output Format Paradigm (Inline Tagged XML vs. Structured JSON Schema Offsets)",
        "",
        "Empirical comparison between **Inline Tagged XML (`P2_TAG`)** and **Structured JSON Schema (`P1_JSON`)** representations evaluated on the full FAERS corpus (N = 829 Reports) across all 17 clinical concept categories.",
        "",
        "| Model | Prompt Strategy & Output Paradigm | Strict Exact-Match F1 | Adapted ADE-Eval F1 | Boundary Alignment Success |",
        "| :--- | :--- | :---: | :---: | :---: |"
    ]

    for _, r in df_manuscript.iterrows():
        md_lines.append(
            f"| **{r['Model']}** | {r['Prompt Strategy & Output Paradigm']} | **{r['Strict Exact-Match F1']}** | **{r['Adapted ADE-Eval F1']}** | {r['Boundary Alignment Success']} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "### Footnotes & Methodological Takeaways:",
        "1. **Spurious Entity Suppression:** Formatting outputs as **Structured JSON suppresses non-overlapping spurious false positives ($S$) by 25.9%** (from 20,491 down to 15,178 spans), yielding higher Strict Precision (0.3785 vs. 0.3470) and higher Adapted ADE Precision (0.7019 vs. 0.6778).",
        "2. **Narrative Grounding & Recall:** **Inline Tagged XML retains stronger narrative token alignment**, yielding fewer missed clinical entities ($N = 9,241$ in Tagged vs. $10,728$ in JSON) and higher Adapted ADE Recall (0.5796 vs. 0.5232).",
        "3. **Boundary Alignment:** Inline tagging guarantees 100% token character alignment, whereas JSON character offset prediction suffers a 6.6% misalignment rate due to subword tokenization boundary shifts.",
        ""
    ])

    md_content = "\n".join(md_lines)

    out_md_tables = tables_dir / "table7_output_format_comparison.md"
    out_md_manuscript = manuscript_dir / "table7.md"
    with open(out_md_tables, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(out_md_manuscript, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 2. Generate Excel Workbook
    esm_cover = pd.DataFrame([
        {"Metadata Field": "Article Title", "Value": "Benchmarking Fine-Tuned Encoders and Instruction-Tuned Large Language Models for Adverse Event Clinical Concept Extraction from Spontaneous Reporting Narratives"},
        {"Metadata Field": "Journal", "Value": "Drug Safety"},
        {"Metadata Field": "Table Identifier", "Value": "Table 7: LLM Output Format Paradigm Comparison"},
        {"Metadata Field": "Corpus", "Value": "FDA Adverse Event Reporting System (FAERS, N = 829 Reports, 17 Categories)"},
        {"Metadata Field": "Models Evaluated", "Value": "LLaMA 4 (Tagged vs JSON) & Claude 4.6 Sonnet (Tagged)"},
        {"Metadata Field": "Generated By", "Value": "publication/scripts/generate_table7.py"}
    ])

    out_excel = tables_dir / "table7_output_format_comparison.xlsx"
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        esm_cover.to_excel(writer, sheet_name="ESM_Cover_Sheet", index=False)
        df_manuscript.to_excel(writer, sheet_name="Table_7_Format_Comparison", index=False)
        df_table7.to_excel(writer, sheet_name="Detailed_Format_Metrics", index=False)

    print(f"Table 7 successfully generated:\n  - {out_md_tables}\n  - {out_excel}")


if __name__ == "__main__":
    main()
