#!/usr/bin/env python3
"""
generate_table4.py

Generates publication-ready Table 4 (FAERS 17-Category Evaluation Table)
in both Markdown (.md) and Excel (.xlsx with ESM Metadata Cover Sheet) formats.

Compares per-category performance across all 17 clinical concept categories for:
1. BioBERT (Supervised Fine-Tuned Encoder)
2. LLaMA 4 (1-shot, Inline Tagged XML P2_TAG)
3. Claude 4.6 Sonnet (1-shot In-Context Tagged XML P2_TAG)
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

    data_17 = [
        {"Category": "sDrug", "Gold_N": 4665, "BioBERT_Strict": "0.6025", "LLaMA4_Strict": "0.3181", "Sonnet_Strict": "0.4006", "BioBERT_ADE": "0.7376", "LLaMA4_ADE": "0.5463", "Sonnet_ADE": "0.5619"},
        {"Category": "cDrug", "Gold_N": 2995, "BioBERT_Strict": "0.7433", "LLaMA4_Strict": "0.3443", "Sonnet_Strict": "0.5689", "BioBERT_ADE": "0.8451", "LLaMA4_ADE": "0.6013", "Sonnet_ADE": "0.7130"},
        {"Category": "oDrug", "Gold_N": 0,    "BioBERT_Strict": "0.0000", "LLaMA4_Strict": "0.0000", "Sonnet_Strict": "0.0000", "BioBERT_ADE": "0.0000", "LLaMA4_ADE": "0.4804", "Sonnet_ADE": "0.4848"},
        {"Category": "Dose",  "Gold_N": 1668, "BioBERT_Strict": "0.6100", "LLaMA4_Strict": "0.2752", "Sonnet_Strict": "0.4300", "BioBERT_ADE": "0.7427", "LLaMA4_ADE": "0.5783", "Sonnet_ADE": "0.6826"},
        {"Category": "Indication", "Gold_N": 202, "BioBERT_Strict": "0.1335", "LLaMA4_Strict": "0.0690", "Sonnet_Strict": "0.1042", "BioBERT_ADE": "0.5021", "LLaMA4_ADE": "0.4913", "Sonnet_ADE": "0.5194"},
        {"Category": "Treatment",  "Gold_N": 1490, "BioBERT_Strict": "0.6260", "LLaMA4_Strict": "0.1832", "Sonnet_Strict": "0.3189", "BioBERT_ADE": "0.7775", "LLaMA4_ADE": "0.4647", "Sonnet_ADE": "0.5355"},
        {"Category": "AE",    "Gold_N": 12010,"BioBERT_Strict": "0.5931", "LLaMA4_Strict": "0.3582", "Sonnet_Strict": "0.4401", "BioBERT_ADE": "0.7066", "LLaMA4_ADE": "0.5635", "Sonnet_ADE": "0.5678"},
        {"Category": "mAE",   "Gold_N": 113,  "BioBERT_Strict": "0.0480", "LLaMA4_Strict": "0.0405", "Sonnet_Strict": "0.0594", "BioBERT_ADE": "0.0507", "LLaMA4_ADE": "0.4604", "Sonnet_ADE": "0.4574"},
        {"Category": "Dx",    "Gold_N": 64,   "BioBERT_Strict": "0.0670", "LLaMA4_Strict": "0.0016", "Sonnet_Strict": "0.0000", "BioBERT_ADE": "0.4536", "LLaMA4_ADE": "0.4016", "Sonnet_ADE": "0.3704"},
        {"Category": "Lab",   "Gold_N": 3482, "BioBERT_Strict": "0.5964", "LLaMA4_Strict": "0.1575", "Sonnet_Strict": "0.3742", "BioBERT_ADE": "0.7637", "LLaMA4_ADE": "0.4912", "Sonnet_ADE": "0.6105"},
        {"Category": "Status","Gold_N": 1910, "BioBERT_Strict": "0.7169", "LLaMA4_Strict": "0.1304", "Sonnet_Strict": "0.2741", "BioBERT_ADE": "0.8386", "LLaMA4_ADE": "0.2676", "Sonnet_ADE": "0.4547"},
        {"Category": "R/O",   "Gold_N": 9,    "BioBERT_Strict": "0.0000", "LLaMA4_Strict": "0.0073", "Sonnet_Strict": "0.0094", "BioBERT_ADE": "0.0000", "LLaMA4_ADE": "0.4444", "Sonnet_ADE": "0.4539"},
        {"Category": "CoD",   "Gold_N": 3,    "BioBERT_Strict": "0.0000", "LLaMA4_Strict": "0.0052", "Sonnet_Strict": "0.0165", "BioBERT_ADE": "0.0000", "LLaMA4_ADE": "0.4610", "Sonnet_ADE": "0.4686"},
        {"Category": "MHx",   "Gold_N": 2370, "BioBERT_Strict": "0.4621", "LLaMA4_Strict": "0.3474", "Sonnet_Strict": "0.4896", "BioBERT_ADE": "0.7138", "LLaMA4_ADE": "0.6121", "Sonnet_ADE": "0.6888"},
        {"Category": "FHx",   "Gold_N": 105,  "BioBERT_Strict": "0.0727", "LLaMA4_Strict": "0.0606", "Sonnet_Strict": "0.1395", "BioBERT_ADE": "0.0818", "LLaMA4_ADE": "0.1736", "Sonnet_ADE": "0.2130"},
        {"Category": "Age",   "Gold_N": 787,  "BioBERT_Strict": "0.9009", "LLaMA4_Strict": "0.7335", "Sonnet_Strict": "0.8752", "BioBERT_ADE": "0.9525", "LLaMA4_ADE": "0.8590", "Sonnet_ADE": "0.9238"},
        {"Category": "Sex",   "Gold_N": 777,  "BioBERT_Strict": "0.9037", "LLaMA4_Strict": "0.7551", "Sonnet_Strict": "0.8829", "BioBERT_ADE": "0.9570", "LLaMA4_ADE": "0.8575", "Sonnet_ADE": "0.9376"},
        {"Category": "OVERALL", "Gold_N": 32650, "BioBERT_Strict": "0.6032", "LLaMA4_Strict": "0.2982", "Sonnet_Strict": "0.4189", "BioBERT_ADE": "0.7477", "LLaMA4_ADE": "0.5515", "Sonnet_ADE": "0.6060"}
    ]

    df_table4 = pd.DataFrame(data_17)

    # 1. Generate Markdown File
    md_lines = [
        "# Table 4: Per-Category Performance Breakdown on FAERS Across All 17 Clinical Concept Categories (N = 829 Reports)",
        "",
        "Fine-grained concept extraction performance across all 17 clinical concept categories on the FAERS benchmark corpus under the Two-Tier Evaluation Framework.",
        "",
        "| Clinical Category | Gold Mentions (N) | BioBERT (Strict F1) | LLaMA 4 (Strict F1) | Claude Sonnet (Strict F1) | BioBERT (Adapted F1) | LLaMA 4 (Adapted F1) | Claude Sonnet (Adapted F1) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    for _, r in df_table4.iterrows():
        is_ov = (r['Category'] == 'OVERALL')
        prefix = "**" if is_ov else ""
        md_lines.append(
            f"| {prefix}{r['Category']}{prefix} | {r['Gold_N']:,} | "
            f"{prefix}{r['BioBERT_Strict']}{prefix} | {prefix}{r['LLaMA4_Strict']}{prefix} | {prefix}{r['Sonnet_Strict']}{prefix} | "
            f"{prefix}{r['BioBERT_ADE']}{prefix} | {prefix}{r['LLaMA4_ADE']}{prefix} | {prefix}{r['Sonnet_ADE']}{prefix} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "### Category Definitions & Footnotes:",
        "- **Drug-Related:** `sDrug` (Suspect Drug), `cDrug` (Concomitant Drug), `oDrug` (Other Drug), `Dose` (Dosage), `Indication` (Drug Indication), `Treatment` (Drug used for treatment).",
        "- **Adverse Event / Clinical Finding:** `AE` (Adverse Event), `mAE` (AE Manifestations/Sequelae), `Dx` (Diagnostic Test Results), `Lab` (Laboratory Findings), `Status` (Patient Status), `R/O` (Rule-Out Diagnosis), `CoD` (Cause of Death).",
        "- **Medical / Family History:** `MHx` (Medical History), `FHx` (Family History).",
        "- **Demographics:** `Age` (Patient Age), `Sex` (Patient Sex).",
        "- **Primary Tier (Strict Exact-Match NER F1):** Requires identical character span boundaries and category assignment.",
        "- **Secondary Tier (Adapted ADE-Eval Clinical Weighted F1):** Grants 0.5 partial credit to boundary shifts and adjacent category confusions, applying a 0.25 penalty to ungrounded false positives.",
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
        {"Metadata Field": "Table Identifier", "Value": "Table 4: FAERS 17-Category Performance Breakdown"},
        {"Metadata Field": "Corpus", "Value": "FDA Adverse Event Reporting System (FAERS D1, N = 829 Reports)"},
        {"Metadata Field": "Evaluation Framework", "Value": "Two-Tier Evaluation Framework across all 17 clinical concept categories"},
        {"Metadata Field": "Generated By", "Value": "publication/scripts/generate_table4.py"}
    ])

    out_excel = tables_dir / "table4_category_breakdown_faers.xlsx"
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        esm_cover.to_excel(writer, sheet_name="ESM_Cover_Sheet", index=False)
        df_table4.to_excel(writer, sheet_name="Table_4_17_Categories", index=False)

    print(f"Table 4 (17 categories) successfully exported to:\n  - {out_md_tables}\n  - {out_md_manuscript}\n  - {out_excel}")


if __name__ == "__main__":
    main()
