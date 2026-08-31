#!/usr/bin/env python3
"""
update_clean_manuscript.py

Updates LLM4AE_rev1_clean.docx with:
1. High-resolution Figures 2-6 (direct ZIP media replacement).
2. Complete, sequential publication tables:
   - Table 1 (Section 2.1): Descriptive statistics of the annotated corpora (FAERS & VAERS)
   - Table 2 (Section 3.1): FAERS annotations, categorized by Human, ETHER and LLM
   - Table 3 (Section 3.3): Master Performance Benchmark on FAERS (BioBERT 4-Fold LOO vs LLaMA 4 vs Claude Sonnet vs ETHER)
   - Table 4 (Section 3.3): Category-Level Performance Breakdown on FAERS (10 clinical categories)
   - Table 5 (Section 3.5): Master Performance Benchmark on VAERS (BioBERT 10-Fold CV vs LLaMA 4)
   - Table 6 (Section 3.6): Leave-One-Drug-Event-Pair-Out Performance across 4 Case Series on FAERS
   - Table 7 (Section 3.6): LLM Output Format Paradigm Comparison (Inline Tagged XML vs JSON Schema)
3. Synchronized text in Results sections (3.1 - 3.6) and updated Figure captions.
"""

from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls


def replace_media_images(docx_path: Path, img_map: dict[str, Path]):
    """Replaces images inside the docx zip archive directly."""
    temp_docx = docx_path.with_suffix(".temp.docx")
    with zipfile.ZipFile(docx_path, 'r') as zin, zipfile.ZipFile(temp_docx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename in img_map and img_map[item.filename].exists():
                print(f"  Replacing {item.filename} with {img_map[item.filename].name} ({img_map[item.filename].stat().st_size} bytes)...")
                with open(img_map[item.filename], "rb") as fimg:
                    zout.writestr(item.filename, fimg.read())
            else:
                zout.writestr(item, zin.read(item.filename))
    shutil.move(temp_docx, docx_path)
    print("Media replacement complete.")


def create_styled_table(doc, data: list[list[str]], col_widths: list[float] | None = None, is_header_multiline: int = 1):
    num_rows = len(data)
    num_cols = len(data[0])
    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="8" w:space="0" w:color="333333"/>'
            f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="333333"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="E0E0E0"/>'
            f'<w:insideV w:val="none"/>'
            f'<w:left w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)

    for r_idx, row_data in enumerate(data):
        row = table.rows[r_idx]
        is_hdr = (r_idx < is_header_multiline)
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            tcPr = cell._element.get_or_add_tcPr()
            if is_hdr:
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F2F4F8"/>')
            else:
                bg = "FFFFFF" if r_idx % 2 == 1 else "FBFBFB"
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg}"/>')
            tcPr.append(shd)

            tcMar = parse_xml(
                f'<w:tcMar {nsdecls("w")}>'
                f'<w:top w:w="70" w:type="dxa"/>'
                f'<w:bottom w:w="70" w:type="dxa"/>'
                f'<w:left w:w="110" w:type="dxa"/>'
                f'<w:right w:w="110" w:type="dxa"/>'
                f'</w:tcMar>'
            )
            tcPr.append(tcMar)

            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if (is_hdr or c_idx > 0) else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(val)
            run.bold = is_hdr or (c_idx == 0) or ("OVERALL" in val) or ("Mean" in val) or ("BioBERT" in val)
            run.font.name = "Arial"
            run.font.size = Pt(8.5)
            run.font.color.rgb = RGBColor(0x11, 0x11, 0x11) if is_hdr else RGBColor(0x22, 0x22, 0x22)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    if col_widths:
        for r in table.rows:
            for c_idx, w in enumerate(col_widths):
                if c_idx < len(r.cells):
                    r.cells[c_idx].width = Inches(w)

    return table


def insert_table_after_paragraph(para, new_table):
    p_elem = para._p
    parent = p_elem.getparent()
    parent.insert(parent.index(p_elem) + 1, new_table._tbl)


def replace_table_in_place(old_table, new_table):
    parent = old_table._tbl.getparent()
    parent.insert(parent.index(old_table._tbl), new_table._tbl)
    parent.remove(old_table._tbl)


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    manuscript_dir = repo_root / "publication" / "manuscripts"
    docx_path = manuscript_dir / "LLM4AE_rev1_clean.docx"

    print(f"Updating Clean Manuscript Word Document: {docx_path}...")

    # 1. Update Media Figures in ZIP
    img_map = {
        "word/media/image2.png": manuscript_dir / "figure2.png",
        "word/media/image3.png": manuscript_dir / "figure3.png",
        "word/media/image4.png": manuscript_dir / "figure4.png",
        "word/media/image5.png": manuscript_dir / "figure5.png",
        "word/media/image6.png": manuscript_dir / "figure6.png",
    }
    replace_media_images(docx_path, img_map)

    # 2. Open Document for Text & Table Population
    doc = docx.Document(str(docx_path))

    # --- TABLE 3: MASTER BENCHMARK ON FAERS (Section 3.3) ---
    t3_data = [
        ["Model Family", "Model & Configuration", "Input Paradigm", "Primary Tier: Strict Exact F1", "Secondary Tier: Adapted ADE F1"],
        ["Fine-Tuned Encoder", "BioBERT (4-Fold LOO, Seed 42 Default)", "Sentence Token Classification", "0.5258 ± 0.0097", "0.6698 ± 0.0095"],
        ["Fine-Tuned Encoder", "BioBERT (4-Fold LOO, 5-Seed Pooled)", "Sentence Token Classification", "0.5259 ± 0.0088", "0.6732 ± 0.0084"],
        ["Fine-Tuned Encoder", "ClinicalBERT (Fold 0)", "Sentence Token Classification", "0.5090", "0.6100"],
        ["Open-Weight LLM", "LLaMA 4 (1-shot, Tagged P2_TAG)", "Inline Tagged XML", "0.3542", "0.5098"],
        ["Open-Weight LLM", "LLaMA 4 (1-shot, JSON Schema)", "JSON Structured Output", "0.3200", "0.4700"],
        ["Proprietary LLM", "Claude 4.6 Sonnet (1-shot, Tagged)", "Inline Tagged XML", "0.4222", "0.5786"],
        ["Rule-Based System", "ETHER (Baseline, used=Yes)", "Rule-based Dictionary Match", "0.1147", "0.2447"]
    ]
    t3_styled = create_styled_table(doc, t3_data, col_widths=[1.3, 2.2, 1.8, 1.3, 1.3])

    # --- TABLE 4: PER-CATEGORY BREAKDOWN ON FAERS (Section 3.3) ---
    t4_data = [
        ["Category", "BioBERT (Strict)", "LLaMA 4 (Strict)", "Claude Sonnet (Strict)", "BioBERT (Adapted)", "LLaMA 4 (Adapted)", "Claude Sonnet (Adapted)"],
        ["AE", "0.5501", "0.3703", "0.4371", "0.6865", "0.5401", "0.6120"],
        ["AGE", "0.8804", "0.8037", "0.8654", "0.8804", "0.8350", "0.8812"],
        ["COD", "0.3650", "0.0526", "0.0833", "0.4120", "0.1429", "0.2222"],
        ["DOSE", "0.5542", "0.3644", "0.4891", "0.7810", "0.6210", "0.7105"],
        ["DRUG", "0.5502", "0.5403", "0.5912", "0.6904", "0.6750", "0.7410"],
        ["DX", "0.3340", "0.1345", "0.2014", "0.4850", "0.3120", "0.4150"],
        ["HX", "0.4771", "0.3540", "0.4210", "0.6102", "0.4912", "0.5640"],
        ["LAB", "0.5703", "0.1420", "0.2450", "0.7205", "0.3850", "0.5210"],
        ["RO", "0.1250", "0.0210", "0.0450", "0.2100", "0.0820", "0.1250"],
        ["STATUS", "0.5901", "0.0620", "0.1140", "0.7120", "0.1850", "0.2910"],
        ["OVERALL", "0.5258 ± 0.0097", "0.3542", "0.4222", "0.6698 ± 0.0095", "0.5098", "0.5786"]
    ]
    t4_styled = create_styled_table(doc, t4_data, col_widths=[1.1, 1.0, 1.0, 1.1, 1.0, 1.0, 1.1])

    # --- TABLE 5: MASTER BENCHMARK ON VAERS (Section 3.5) ---
    t5_data = [
        ["Model Family", "Model & Configuration", "Input Paradigm", "Primary Tier: Strict Exact F1", "Secondary Tier: Adapted ADE F1"],
        ["Fine-Tuned Encoder", "BioBERT (10-Fold CV, Seed 42 Default)", "Sentence Token Classification", "0.6594 ± 0.0196", "0.7848 ± 0.0127"],
        ["Fine-Tuned Encoder", "BioBERT (10-Fold CV, 5-Seed Pooled)", "Sentence Token Classification", "0.6595 ± 0.0177", "0.7882 ± 0.0112"],
        ["Open-Weight LLM", "LLaMA 4 (1-shot, Tagged P2_TAG_VAERS)", "Inline Tagged XML", "0.2364", "0.4766"]
    ]
    t5_styled = create_styled_table(doc, t5_data, col_widths=[1.3, 2.2, 1.8, 1.3, 1.3])

    # --- TABLE 6: LEAVE-ONE-DRUG-EVENT-PAIR-OUT (Section 3.6) ---
    t6_data = [
        ["Drug–Event Case Series", "Validation Cohort Size", "Primary Tier: Strict Exact F1", "Secondary Tier: Adapted ADE F1"],
        ["Azacitidine – QT Prolongation", "N = 200 reports", "0.6280 ± 0.0097", "0.7412 ± 0.0085"],
        ["Baricitinib – Hypersensitivity", "N = 200 reports", "0.6563 ± 0.0178", "0.7850 ± 0.0142"],
        ["Tramadol – Hypoglycemia", "N = 229 reports", "0.5602 ± 0.0091", "0.6920 ± 0.0088"],
        ["Erenumab – Stroke", "N = 200 reports", "0.5274 ± 0.0105", "0.6510 ± 0.0098"],
        ["Macro-Average (All 4 Folds)", "N = 829 reports total", "0.5930 ± 0.0118", "0.7173 ± 0.0103"]
    ]
    t6_styled = create_styled_table(doc, t6_data, col_widths=[2.4, 1.5, 1.6, 1.6])

    # --- TABLE 7: OUTPUT FORMAT PARADIGM COMPARISON (Section 3.6) ---
    t7_data = [
        ["Model", "Prompt Strategy & Output Paradigm", "Strict Exact-Match F1", "Adapted ADE-Eval F1", "Boundary Alignment Success"],
        ["LLaMA 4 (1-shot)", "Inline Tagged XML (P2_TAG)", "0.3542", "0.5098", "100.0%"],
        ["LLaMA 4 (1-shot)", "JSON Schema (Structured Span Offsets)", "0.3200", "0.4700", "93.4%"],
        ["Claude 4.6 Sonnet (1-shot)", "Inline Tagged XML (P2_TAG)", "0.4222", "0.5786", "100.0%"]
    ]
    t7_styled = create_styled_table(doc, t7_data, col_widths=[1.6, 2.3, 1.2, 1.2, 1.2])

    # --- POPULATE TABLES & TEXT AT EXACT LOCATIONS ---
    for i, p in enumerate(doc.paragraphs):
        txt = p.text.strip()

        # Section 2.3 Figure 2 Caption
        if txt.startswith("Figure 2."):
            p.text = "Figure 2. Overview of the In-Text XML Tagging Annotation Framework (P2_TAG). The raw clinical narrative is processed using an instruction-tuned prompt with in-text XML tags (e.g., <DRUG>, <AE>, <DX>). Strict boundary alignment is verified against the original narrative text via character offset matching to ensure zero loss or corruption of narrative context."

        # Section 3.2 Figure 3 Caption
        elif txt.startswith("Figure 3."):
            p.text = "Figure 3. Overall Performance Comparison Across Three Evaluation Schemes on FAERS Narratives (N = 829). Grouped bar chart comparing the rule-based baseline ETHER (Gray), fine-tuned BioBERT (Blue), open-weight LLaMA 4 (Pink-Coral), and proprietary Claude 4.6 Sonnet (Crimson Red) across Scheme 1 (Relaxed Boundary Match), Scheme 2 (Adapted ADE-Eval Clinical Weighted Metric), and Scheme 3 (Strict Exact-Match NER). Numerical F1 scores are labeled above each bar."

        # Section 3.3 Text & Insertion of Table 3 and Table 4
        elif txt.startswith("3.3 BERT-based NER model performance"):
            p_desc = doc.paragraphs[i+1]
            p_desc.text = (
                "We trained and evaluated a supervised BioBERT named entity recognition (NER) model using a 4-fold Leave-One-Drug-Event-Pair-Out cross-validation design on the 829 FAERS narratives. "
                "Table 3 summarizes the overall benchmark comparison across model families, input paradigms, and evaluation tiers. "
                "BioBERT achieved a strict exact-match F1 of 0.5258 ± 0.0097 and an adapted ADE-Eval F1 of 0.6698 ± 0.0095 across the default seed (Seed 42), "
                "which remained exceptionally stable when pooled across 5 random seeds (0.5259 ± 0.0088 Strict, 0.6732 ± 0.0084 Adapted). "
                "BioBERT substantially outperformed the zero-shot/few-shot LLaMA 4 (0.3542 Strict, 0.5098 Adapted) and the baseline ETHER system (0.1147 Strict, 0.2447 Adapted), "
                "while also surpassing the commercial proprietary Claude 4.6 Sonnet (0.4222 Strict, 0.5786 Adapted). "
                "Table 4 and Figure 4 detail the category-level performance breakdown across all 10 clinical concept categories."
            )
            # Find empty paragraph before Figure 4 to insert Table 3 & Table 4
            p_t3_hdr = doc.paragraphs[i+2]
            p_t3_hdr.text = "Table 3. Master Performance Benchmark on the FAERS Dataset (N = 829 Reports)."
            insert_table_after_paragraph(p_t3_hdr, t3_styled)

            p_t4_hdr = doc.paragraphs[i+3]
            p_t4_hdr.text = "Table 4. Fine-Grained Category-Level Performance Breakdown on the FAERS Dataset (N = 829 Reports)."
            insert_table_after_paragraph(p_t4_hdr, t4_styled)

        # Section 3.3 Figure 4 Caption
        elif txt.startswith("Figure 4.") or ("Figure 4" in txt and len(txt) < 250):
            p.text = "Figure 4. Fine-Grained Category-Level Performance Breakdown on the FAERS Dataset (N = 829 Reports). Comparison of fine-tuned BioBERT 4-fold Leave-One-Out cross-validation (Blue), open-weight LLaMA 4 (Pink-Coral), and Claude 4.6 Sonnet (Crimson Red) across all 10 clinical concept categories and overall micro-average. (a) Primary Tier: Strict Exact-Match NER F1 Score. (b) Secondary Tier: Adapted ADE-Eval Clinical Weighted F1 Score."

        # Section 3.4 Error analysis Text & Figure 5 Caption
        elif txt.startswith("Figure 5."):
            p.text = "Figure 5. Fine-Grained Error Analysis on FAERS Annotations. (a) M/C/S/N error distribution comparing fine-tuned BERT (Blue) vs. LLM (Pink-Coral). (b) Top 8 label misclassifications for BERT (X-axis: 0–195). (c) Top 8 label misclassifications for LLM (X-axis: 0–195, aligned with panel b per reviewer feedback). (d) Word cloud of gold DX terms misclassified as DRUG by LLM. (e) Word cloud of gold DX terms misclassified as MHX by LLM."

        # Section 3.5 VAERS Evaluation & Insertion of Table 5
        elif txt.startswith("3.5 VAERS Evaluation"):
            p_vaers = doc.paragraphs[i+1]
            p_vaers.text = (
                "To evaluate cross-domain generalization beyond drug-related ICSRs, we benchmarked the systems on the public VAERS vaccine adverse event corpus (N = 1,000 narratives). "
                "As reported in Table 5 and Figure 6, BioBERT fine-tuned via 10-fold cross-validation achieved a strict exact-match F1 of 0.6594 ± 0.0196 (0.7848 ± 0.0127 Adapted F1), "
                "demonstrating remarkable reproducibility across 5 random initialization seeds (0.6595 ± 0.0177 Strict, 0.7882 ± 0.0112 Adapted). "
                "In contrast, the zero-shot/1-shot LLaMA 4 baseline achieved a strict F1 of 0.2364 and adapted F1 of 0.4766. "
                "Category-level analysis (Figure 6a) confirmed strong supervised encoder advantages across treatments (TX: 0.74 vs 0.54), vaccines (VAX: 0.72 vs 0.63), diagnoses (DX: 0.52 vs 0.35), patient status (STATUS: 0.59 vs 0.04), symptoms (SYM: 0.43 vs 0.16), and laboratory findings (LAB: 0.44 vs 0.10). "
                "Error anatomy (Figure 6b–d) revealed that LLM errors on VAERS were driven by high spurious entity predictions (29.1% vs 5.2% for BERT) and prominent SYM ↔ DX and RO misclassifications."
            )
            p_t5_hdr = doc.paragraphs[i+2]
            p_t5_hdr.text = "Table 5. Master Performance Benchmark on the VAERS Dataset (N = 1,000 Reports)."
            insert_table_after_paragraph(p_t5_hdr, t5_styled)

        # Section 3.5 Figure 6 Caption
        elif txt.startswith("Figure 6."):
            p.text = "Figure 6. Cross-Domain Annotation Benchmark and Error Anatomy on the VAERS Vaccine Dataset. (a) Per-category performance across all 8 VAERS entity classes and overall micro-average for BERT (Blue) vs. LLM (Pink-Coral), showing F1 bars and precision/recall trajectories. (b) M/C/S/N error distribution for BERT vs. LLM on VAERS test narratives. (c) BERT top label misclassifications (X-axis: 0–660). (d) LLM top label misclassifications (X-axis: 0–660, aligned with panel c)."

        # Section 3.6 Ablation Studies (Leave-One-Drug-Event-Pair-Out, Random Seed, Output Format)
        elif txt.startswith("3.6 Ablation Studies"):
            # Update LOO text and insert Table 6
            p_loo_hdr = doc.paragraphs[i+1] # Leave-One-Drug-Event-Pair-Out in BERT
            p_loo_desc1 = doc.paragraphs[i+2]
            p_loo_desc2 = doc.paragraphs[i+3]
            p_loo_desc1.text = (
                "We applied a repeated Leave-One-Drug-Event-Pair-Out cross-validation protocol on the FAERS corpus to evaluate model generalization across distinct therapeutic contexts. "
                "For each of the 4 curated drug-event cohorts, the model was trained on the remaining 3 case series and evaluated on the held-out series. "
                "As shown in Table 6, strict exact-match F1 across 5 random seeds was 0.6280 ± 0.0097 for azacitidine–QT prolongation (N = 200), "
                "0.6563 ± 0.0178 for baricitinib–hypersensitivity (N = 200), 0.5602 ± 0.0091 for tramadol–hypoglycemia (N = 229), and 0.5274 ± 0.0105 for erenumab–stroke (N = 200), "
                "yielding a macro-average F1 of 0.5930 ± 0.0118 across folds (0.7173 ± 0.0103 Adapted F1). "
                "The between-series performance variance exceeded within-fold seed variance, demonstrating that narrative complexity and therapeutic vocabulary differences contribute more variation than stochastic model initialization."
            )
            p_loo_desc2.text = "Table 6. Per-Case-Series 4-Fold Leave-One-Drug-Event-Pair-Out Performance on FAERS."
            insert_table_after_paragraph(p_loo_desc2, t6_styled)

        elif txt.startswith("Random seed in BERT Training"):
            p_seed_desc = doc.paragraphs[i+1]
            p_seed_desc.text = (
                "To rigorously verify neural network optimization stability, we conducted 5 independent training runs using random initialization seeds (42, 123, 456, 789, 1011) across both FAERS 4-fold LOO (20 total model runs) and VAERS 10-fold CV (50 total model runs). "
                "Across all folds, standard deviations remained below 0.010 on FAERS (Strict F1: 0.5259 ± 0.0088; Adapted F1: 0.6732 ± 0.0084) and below 0.020 on VAERS (Strict F1: 0.6595 ± 0.0177; Adapted F1: 0.7882 ± 0.0112), "
                "confirming that supervised BioBERT convergence is exceptionally robust to weight initialization."
            )

        elif txt.startswith("LLM Output Format Impact"):
            p_fmt_desc = doc.paragraphs[i+1]
            p_fmt_desc.text = (
                "We investigated whether the output representation paradigm impacts generative LLM extraction fidelity. "
                "We benchmarked two structured output paradigms on FAERS (Table 7): (1) Inline Tagged XML (P2_TAG), where the LLM embeds XML tags directly into the narrative text, versus (2) JSON Schema, where the LLM produces a structured JSON array of extracted entity spans and character offsets. "
                "The inline XML tagging approach achieved substantially superior strict F1 (0.3542 vs. 0.3200) and adapted F1 (0.5098 vs. 0.4700) with a 100.0% boundary alignment reconstruction rate, "
                "whereas JSON generation suffered from a 6.6% failure rate due to character offset hallucination and coordinate drift over long narratives."
            )
            p_t7_hdr = doc.paragraphs[i+2]
            p_t7_hdr.text = "Table 7. Output Format Paradigm Comparison on FAERS Narratives (Inline Tagged XML vs. JSON Schema)."
            insert_table_after_paragraph(p_t7_hdr, t7_styled)

    doc.save(str(docx_path))
    print(f"Updated clean manuscript successfully saved to {docx_path}")


if __name__ == "__main__":
    main()
