#!/usr/bin/env python3
"""
generate_table5.py

Generates publication-ready Table 5: Impact of Output Format Paradigm
(Inline Tagged XML vs. Structured JSON for LLaMA 4 on FAERS D1, N = 829 Reports)
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
    print(f"Loading format comparison data from {three_schemes_path}...")
    df_tagged = pd.read_excel(three_schemes_path, sheet_name="LLaMA4_FAERS_Categories")
    df_json = pd.read_excel(three_schemes_path, sheet_name="LLaMA4_FAERS_JSON_Categories")

    # Overall Summary Table (Panel A)
    # Tagged Overall
    m_t = int(df_tagged["M"].sum())
    cb_t = int(df_tagged["C_boundary"].sum())
    cc_t = int(df_tagged["C_class"].sum())
    c_t = int(df_tagged["C_total"].sum())
    s_t = int(df_tagged["S_non_overlap"].sum())
    n_t = int(df_tagged["N"].sum())

    p3_t = m_t / (m_t + c_t + s_t)
    r3_t = m_t / (m_t + c_t + n_t)
    f1_3_t = 2 * p3_t * r3_t / (p3_t + r3_t)

    mc2_t = m_t + 0.5 * c_t
    p2_t = mc2_t / (m_t + c_t + 0.25 * s_t)
    r2_t = mc2_t / (m_t + c_t + n_t)
    f1_2_t = 2 * p2_t * r2_t / (p2_t + r2_t)

    # JSON Overall
    m_j = int(df_json["M"].sum())
    cb_j = int(df_json["C_boundary"].sum())
    cc_j = int(df_json["C_class"].sum())
    c_j = int(df_json["C_total"].sum())
    s_j = int(df_json["S_non_overlap"].sum())
    n_j = int(df_json["N"].sum())

    p3_j = m_j / (m_j + c_j + s_j)
    r3_j = m_j / (m_j + c_j + n_j)
    f1_3_j = 2 * p3_j * r3_j / (p3_j + r3_j)

    mc2_j = m_j + 0.5 * c_j
    p2_j = mc2_j / (m_j + c_j + 0.25 * s_j)
    r2_j = mc2_j / (m_j + c_j + n_j)
    f1_2_j = 2 * p2_j * r2_j / (p2_j + r2_j)

    # Relative change in S_non_overlap
    delta_s_pct = ((s_j - s_t) / s_t) * 100.0

    df_panel_a = pd.DataFrame([
        {
            "Output Format Paradigm": "Inline Tagged XML (`P2_TAG`)",
            "Prompt Template": "In-text XML tags",
            "Strict Precision": f"{p3_t:.4f}",
            "Strict Recall": f"{r3_t:.4f}",
            "Strict F1": f"{f1_3_t:.4f}",
            "ADE-Eval Precision": f"{p2_t:.4f}",
            "ADE-Eval Recall": f"{r2_t:.4f}",
            "ADE-Eval F1": f"{f1_2_t:.4f}",
            "Exact Matches (M)": f"{m_t:,}",
            "Boundary Inexact (C_boundary)": f"{cb_t:,}",
            "Class Confusion (C_class)": f"{cc_t:,}",
            "Non-Overlap FP (S_non_overlap)": f"{s_t:,}",
            "Missed Entities (N)": f"{n_t:,}",
        },
        {
            "Output Format Paradigm": "Structured JSON (`P1_JSON`)",
            "Prompt Template": "Key-value schema + character offsets",
            "Strict Precision": f"{p3_j:.4f}",
            "Strict Recall": f"{r3_j:.4f}",
            "Strict F1": f"{f1_3_j:.4f}",
            "ADE-Eval Precision": f"{p2_j:.4f}",
            "ADE-Eval Recall": f"{r2_j:.4f}",
            "ADE-Eval F1": f"{f1_2_j:.4f}",
            "Exact Matches (M)": f"{m_j:,}",
            "Boundary Inexact (C_boundary)": f"{cb_j:,}",
            "Class Confusion (C_class)": f"{cc_j:,}",
            "Non-Overlap FP (S_non_overlap)": f"{s_j:,}",
            "Missed Entities (N)": f"{n_j:,}",
        },
        {
            "Output Format Paradigm": "Format Delta (JSON - Tagged)",
            "Prompt Template": "-",
            "Strict Precision": f"{p3_j - p3_t:+.4f}",
            "Strict Recall": f"{r3_j - r3_t:+.4f}",
            "Strict F1": f"{f1_3_j - f1_3_t:+.4f}",
            "ADE-Eval Precision": f"{p2_j - p2_t:+.4f}",
            "ADE-Eval Recall": f"{r2_j - r2_t:+.4f}",
            "ADE-Eval F1": f"{f1_2_j - f1_2_t:+.4f}",
            "Exact Matches (M)": f"{m_j - m_t:+,}",
            "Boundary Inexact (C_boundary)": f"{cb_j - cb_t:+,}",
            "Class Confusion (C_class)": f"{cc_j - cc_t:+,}",
            "Non-Overlap FP (S_non_overlap)": f"{s_j - s_t:+,} ({delta_s_pct:.2f}%)",
            "Missed Entities (N)": f"{n_j - n_t:+,}",
        }
    ])

    # Per-Category Comparison (Panel B)
    panel_b_rows = []
    categories = sorted(df_tagged["Category"].unique())

    for cat in categories:
        r_t = df_tagged[df_tagged["Category"] == cat].iloc[0]
        r_j = df_json[df_json["Category"] == cat].iloc[0]

        delta_s3 = r_j["Strict_F1"] - r_t["Strict_F1"]
        delta_s2 = r_j["ADE_F1"] - r_t["ADE_F1"]

        panel_b_rows.append({
            "Category": cat,
            "Gold Total": int(r_t["Gold_Total"]),
            "Tagged Strict F1": f"{r_t['Strict_F1']:.4f}",
            "JSON Strict F1": f"{r_j['Strict_F1']:.4f}",
            "Strict Delta (JSON - Tagged)": f"{delta_s3:+.4f}",
            "Tagged ADE-Eval F1": f"{r_t['ADE_F1']:.4f}",
            "JSON ADE-Eval F1": f"{r_j['ADE_F1']:.4f}",
            "ADE-Eval Delta (JSON - Tagged)": f"{delta_s2:+.4f}",
        })
    df_panel_b = pd.DataFrame(panel_b_rows)

    # 1. Generate Markdown File
    md_lines = [
        "# Table 5: Impact of Output Format Paradigm on LLaMA 4 Concept Extraction (FAERS D1, N = 829 Reports)",
        "",
        "Empirical comparison between **Inline Tagged XML (`P2_TAG`)** and **Structured JSON (`P1_JSON`)** representations evaluated on the full FAERS corpus across overall metrics, error distributions, and per-category performance.",
        "",
        "### Panel A: Overall Performance and Error Count Distribution",
        "",
        "| Output Format Paradigm | Primary Tier: Strict Exact-Match NER ||| Secondary Tier: Adapted ADE-Eval Weighted Metric ||| Outcome Category Counts |||||",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        "| | **P** | **R** | **F1** | **P** | **R** | **F1** | **M** | **C_bound** | **C_class** | **S_non_overlap** | **N** |"
    ]

    for _, r in df_panel_a.iterrows():
        is_delta = "Delta" in r["Output Format Paradigm"]
        p_name = f"*{r['Output Format Paradigm']}*" if is_delta else f"**{r['Output Format Paradigm']}**"
        f1_str = f"**{r['Strict F1']}**" if not is_delta else r['Strict F1']
        ade_str = f"**{r['ADE-Eval F1']}**" if not is_delta else r['ADE-Eval F1']

        md_lines.append(
            f"| {p_name} | {r['Strict Precision']} | {r['Strict Recall']} | {f1_str} | "
            f"{r['ADE-Eval Precision']} | {r['ADE-Eval Recall']} | {ade_str} | "
            f"{r['Exact Matches (M)']} | {r['Boundary Inexact (C_boundary)']} | {r['Class Confusion (C_class)']} | {r['Non-Overlap FP (S_non_overlap)']} | {r['Missed Entities (N)']} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "### Panel B: Per-Category Performance Comparison",
        "",
        "| Clinical Category | Gold Support (N) | Strict Exact-Match F1 ||| Adapted ADE-Eval Weighted F1 |||",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        "| | | **Tagged XML** | **Structured JSON** | **$\\Delta$ (JSON - Tagged)** | **Tagged XML** | **Structured JSON** | **$\\Delta$ (JSON - Tagged)** |"
    ])

    for _, r in df_panel_b.iterrows():
        md_lines.append(
            f"| **{r['Category']}** | {r['Gold Total']:,} | "
            f"{r['Tagged Strict F1']} | {r['JSON Strict F1']} | {r['Strict Delta (JSON - Tagged)']} | "
            f"{r['Tagged ADE-Eval F1']} | {r['JSON ADE-Eval F1']} | {r['ADE-Eval Delta (JSON - Tagged)']} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "### Footnotes & Methodological Takeaways:",
        "1. **Spurious False Positive Suppression:** Formatting outputs as **Structured JSON suppresses non-overlapping spurious hallucinations ($S_{\\text{non\\_overlap}}$) by 46.52%** (from 15,269 spans in Tagged XML down to 8,166 in JSON), resulting in higher Strict Precision (0.3785 vs. 0.3470) and higher ADE-Eval Precision (0.7019 vs. 0.6763).",
        "2. **Narrative Token Grounding & Recall:** **Inline Tagged XML preserves narrative context alignment**, yielding fewer missed clinical entities ($N = 9,241$ in Tagged vs. $10,728$ in JSON) and higher ADE-Eval Recall (0.5673 vs. 0.5232). JSON generation occasionally experiences list truncation on long complex narratives.",
        "3. **Category Shifts:** Structured JSON substantially improves extraction of outcome disposition phrases (`STATUS`, $+0.1681$ ADE F1), but exhibits slight sensitivity to multi-token clinical modifier phrases (`DOSE`, $-0.0656$ ADE F1; `LAB`, $-0.0415$ ADE F1) where offset boundaries are harder for the autoregressive decoder to align exactly.",
        ""
    ])

    md_content = "\n".join(md_lines)

    # Write Markdown outputs
    out_md_tables = tables_dir / "table5_output_format_comparison.md"
    out_md_manuscript = manuscript_dir / "table5.md"
    out_md_results = results_dir / "table5.md"

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
        {"Metadata Field": "Table Identifier", "Value": "Table 5: Output Format Paradigm Comparison (Tagged XML vs. Structured JSON)"},
        {"Metadata Field": "Corpus", "Value": "FDA Adverse Event Reporting System (FAERS D1, N = 829 Reports)"},
        {"Metadata Field": "Model Evaluated", "Value": "LLaMA 4 (1-shot In-Context Prompting)"},
        {"Metadata Field": "Generated By", "Value": "publication/scripts/generate_table5.py"}
    ])

    out_excel = tables_dir / "table5_output_format_comparison.xlsx"
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        esm_cover.to_excel(writer, sheet_name="ESM_Cover_Sheet", index=False)
        df_panel_a.to_excel(writer, sheet_name="Panel_A_Overall_Comparison", index=False)
        df_panel_b.to_excel(writer, sheet_name="Panel_B_Category_Comparison", index=False)

    print(f"Table 5 successfully exported to:\n  - {out_md_tables}\n  - {out_md_manuscript}\n  - {out_excel}")


if __name__ == "__main__":
    main()
