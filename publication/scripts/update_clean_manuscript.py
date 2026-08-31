#!/usr/bin/env python3
"""
update_clean_manuscript.py

Updates LLM4AE_rev1_clean.docx with:
1. High-resolution Figures 2-6 (direct ZIP media replacement).
2. Publication tables (with Table 4 removed from main text as Figure 4 presents the 17-category breakdown):
   - Table 1 (Section 2.1): Descriptive statistics of the annotated corpora (FAERS & VAERS)
   - Table 2 (Section 3.1): FAERS annotations, categorized by Human, ETHER and LLM
   - Table 3 (Section 3.3): Master Performance Benchmark on FAERS (BioBERT 4-Fold LOO vs LLaMA 4 vs Claude Sonnet vs ETHER)
   - Table 4 (Section 3.5, renumbered): Master Performance Benchmark on VAERS (BioBERT 10-Fold CV vs LLaMA 4)
   - Table 5 (Section 3.6, renumbered): Leave-One-Drug-Event-Pair-Out Performance across 4 Case Series on FAERS
   - Table 6 (Section 3.6, renumbered): LLM Output Format Paradigm Comparison (Inline Tagged XML vs JSON Schema)
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


def replace_media_images_in_memory(docx_path: Path, img_map: dict[str, Path]):
    """Replaces images inside the docx zip archive using an in-memory buffer."""
    with open(docx_path, 'rb') as f:
        in_buf = io.BytesIO(f.read())
    
    out_buf = io.BytesIO()
    with zipfile.ZipFile(in_buf, 'r') as zin, zipfile.ZipFile(out_buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename in img_map and img_map[item.filename].exists():
                print(f"  Replacing {item.filename} with {img_map[item.filename].name} ({img_map[item.filename].stat().st_size} bytes)...")
                with open(img_map[item.filename], "rb") as fimg:
                    zout.writestr(item.filename, fimg.read())
            else:
                zout.writestr(item, zin.read(item.filename))
    
    with open(docx_path, 'wb') as f:
        f.write(out_buf.getvalue())
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
                f'<w:top w:w="60" w:type="dxa"/>'
                f'<w:bottom w:w="60" w:type="dxa"/>'
                f'<w:left w:w="90" w:type="dxa"/>'
                f'<w:right w:w="90" w:type="dxa"/>'
                f'</w:tcMar>'
            )
            tcPr.append(tcMar)

            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if (is_hdr or c_idx > 0) else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val)
            run.bold = is_hdr or (c_idx == 0) or ("OVERALL" in val) or ("Mean" in val) or ("BioBERT" in val)
            run.font.name = "Arial"
            run.font.size = Pt(8.0)
            run.font.color.rgb = RGBColor(0x11, 0x11, 0x11) if is_hdr else RGBColor(0x22, 0x22, 0x22)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    if col_widths:
        for r in table.rows:
            for c_idx, w in enumerate(col_widths):
                if c_idx < len(r.cells):
                    r.cells[c_idx].width = Inches(w)

    return table


def replace_table_in_place(old_table, new_table):
    parent = old_table._tbl.getparent()
    parent.insert(parent.index(old_table._tbl), new_table._tbl)
    parent.remove(old_table._tbl)


def remove_table(table):
    parent = table._tbl.getparent()
    parent.remove(table._tbl)


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    manuscript_dir = repo_root / "publication" / "manuscripts"
    src_docx_path = manuscript_dir / "LLM4AE_rev1_clean.docx"
    dst_docx_path = manuscript_dir / "LLM4AE_rev1_clean.docx"

    print(f"Loading document from {src_docx_path}...")
    doc = docx.Document(str(src_docx_path))

    # 1. Update Media Figures in ZIP (Figures 2-6)
    img_map = {
        "word/media/image2.png": manuscript_dir / "figure2.png",
        "word/media/image3.png": manuscript_dir / "figure3.png",
        "word/media/image4.png": manuscript_dir / "figure4.png",
        "word/media/image5.png": manuscript_dir / "figure5.png",
        "word/media/image6.png": manuscript_dir / "figure6.png",
    }

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

    # --- TABLE 4 (formerly Table 5): MASTER BENCHMARK ON VAERS (Section 3.5) ---
    t4_data = [
        ["Model Family", "Model & Configuration", "Input Paradigm", "Primary Tier: Strict Exact F1", "Secondary Tier: Adapted ADE F1"],
        ["Fine-Tuned Encoder", "BioBERT (10-Fold CV, Seed 42 Default)", "Sentence Token Classification", "0.6594 ± 0.0196", "0.7848 ± 0.0127"],
        ["Fine-Tuned Encoder", "BioBERT (10-Fold CV, 5-Seed Pooled)", "Sentence Token Classification", "0.6595 ± 0.0177", "0.7882 ± 0.0112"],
        ["Open-Weight LLM", "LLaMA 4 (1-shot, Tagged P2_TAG_VAERS)", "Inline Tagged XML", "0.2364", "0.4766"]
    ]
    t4_styled = create_styled_table(doc, t4_data, col_widths=[1.3, 2.2, 1.8, 1.3, 1.3])

    # --- TABLE 5 (formerly Table 6): LEAVE-ONE-DRUG-EVENT-PAIR-OUT (Section 3.6) ---
    t5_data = [
        ["Drug–Event Case Series", "Validation Cohort Size", "Primary Tier: Strict Exact F1", "Secondary Tier: Adapted ADE F1"],
        ["Azacitidine – QT Prolongation", "N = 200 reports", "0.6280 ± 0.0097", "0.7412 ± 0.0085"],
        ["Baricitinib – Hypersensitivity", "N = 200 reports", "0.6563 ± 0.0178", "0.7850 ± 0.0142"],
        ["Tramadol – Hypoglycemia", "N = 229 reports", "0.5602 ± 0.0091", "0.6920 ± 0.0088"],
        ["Erenumab – Stroke", "N = 200 reports", "0.5274 ± 0.0105", "0.6510 ± 0.0098"],
        ["Macro-Average (All 4 Folds)", "N = 829 reports total", "0.5930 ± 0.0118", "0.7173 ± 0.0103"]
    ]
    t5_styled = create_styled_table(doc, t5_data, col_widths=[2.4, 1.5, 1.6, 1.6])

    # --- TABLE 6 (formerly Table 7): OUTPUT FORMAT PARADIGM COMPARISON (Section 3.6) ---
    t6_data = [
        ["Model", "Prompt Strategy & Output Paradigm", "Strict Exact-Match F1", "Adapted ADE-Eval F1", "Boundary Alignment Success"],
        ["LLaMA 4 (1-shot)", "Inline Tagged XML (P2_TAG)", "0.3542", "0.5098", "100.0%"],
        ["LLaMA 4 (1-shot)", "JSON Schema (Structured Span Offsets)", "0.3200", "0.4700", "93.4%"],
        ["Claude 4.6 Sonnet (1-shot)", "Inline Tagged XML (P2_TAG)", "0.4222", "0.5786", "100.0%"]
    ]
    t6_styled = create_styled_table(doc, t6_data, col_widths=[1.6, 2.3, 1.2, 1.2, 1.2])

    replace_table_in_place(doc.tables[2], t3_styled)
    
    # Check if doc has 7 or more tables:
    if len(doc.tables) >= 7:
        replace_table_in_place(doc.tables[4], t4_styled)
        replace_table_in_place(doc.tables[5], t5_styled)
        replace_table_in_place(doc.tables[6], t6_styled)
        # Remove old Table 4 table (index 3)
        remove_table(doc.tables[3])

    # Update Captions and references
    for p in doc.paragraphs:
        txt = p.text.strip()
        if "Table 4." in txt and "Fine-Grained" in txt:
            p.text = ""  # Remove old Table 4 caption paragraph
        elif "Table 5." in txt:
            p.text = "Table 4. Primary and Secondary Tier Clinical Concept Extraction Performance Benchmark on the VAERS Dataset (N = 1,000 Reports)."
        elif "Table 6." in txt:
            p.text = "Table 5. Leave-One-Drug-Event-Pair-Out Cross-Validation Performance Across Four FAERS Case Series (N = 829 Reports Total)."
        elif "Table 7." in txt:
            p.text = "Table 6. Impact of LLM Output Format Paradigm (Inline Tagged XML vs. Structured JSON Schema Offsets) on Entity Extraction and Offset Alignment."
        elif "Fig. 4" in txt or "Figure 4" in txt:
            if "Caption:" in txt or txt.startswith("Figure 4.") or txt.startswith("Fig. 4"):
                p.text = "Figure 4. Comparative Concept Extraction Performance Across All 17 Clinical Concept Categories on the FAERS Benchmark Corpus (N = 829 Reports) for Fine-Tuned BioBERT (Blue Diamond / Bar), Claude 4.6 Sonnet (Red Circle / Bar), and LLaMA 4 (Pink Square / Bar)."

    try:
        doc.save(str(dst_docx_path))
        print(f"Saved directly to {dst_docx_path}")
        replace_media_images_in_memory(dst_docx_path, img_map)
    except PermissionError:
        alt_path = manuscript_dir / "LLM4AE_rev1_clean_updated.docx"
        doc.save(str(alt_path))
        print(f"Saved to alternative path: {alt_path}")
        replace_media_images_in_memory(alt_path, img_map)


if __name__ == "__main__":
    main()
