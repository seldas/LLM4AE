#!/usr/bin/env python3
"""
generate_figure5.py

Generates publication-ready Figure 5: Error Analysis on FAERS Annotations
Addressing Reviewer #3, Comment 3.14 (Horizontal axes of 5b and 5c aligned to identical 0-190 range)
and enforcing the unified manuscript color palette.

Panels:
- (a) M/C/S/N Error Distribution for BERT vs. LLM (FAERS Test Set)
- (b) BERT: Top Label Misclassifications (X-axis: 0 - 190)
- (c) LLM: Top Label Misclassifications (X-axis: 0 - 190, matched to 5b)
- (d) LLM: DX terms misclassified as DRUG (Word Cloud)
- (e) LLM: DX terms misclassified as MHX (Word Cloud)

Standard Manuscript Color Palette:
- ETHER: Gray (#616161)
- BERT: Blue (#1F77B4)
- LLaMA 4 / LLM: Pink close to red (#FF6F61)
- Claude Sonnet: Red (#C0392B)
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from wordcloud import WordCloud


def span_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    results_dir = repo_root / "publication" / "results"
    figures_dir = results_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    manuscript_dir = repo_root / "publication" / "manuscripts"

    test_file_path = repo_root / "development" / "BERT" / "Error_analysis" / "FAERS-BERT-TEST.xlsx"

    print(f"Loading data from {test_file_path}...")
    df = pd.read_excel(test_file_path)

    df_human = df[df["Note"] == "Human"].copy()
    df_bert  = df[df["Note"] == "BERT"].copy()
    df_llm   = df[df["Note"] == "LLM"].copy()

    # Pre-group spans by file for ultra-fast lookup
    def make_file_map(df_sub):
        m = defaultdict(list)
        for row in df_sub.itertuples(index=False):
            m[row.File].append((int(row.Start), int(row.End), str(row.Label_Norm), str(row.Text)))
        return m

    human_map = make_file_map(df_human)
    bert_map  = make_file_map(df_bert)
    llm_map   = make_file_map(df_llm)

    def analyze(model_map, human_map):
        pred_counts = {"M": 0, "C": 0, "S": 0}
        confusion = defaultdict(lambda: defaultdict(int))
        dx_to_drug_terms = []
        dx_to_mhx_terms = []

        for f, p_spans in model_map.items():
            h_spans = human_map.get(f, [])
            for p_start, p_end, p_lab, p_txt in p_spans:
                best_ov = 0
                best_h = None
                for h_start, h_end, h_lab, h_txt in h_spans:
                    ov = span_overlap(p_start, p_end, h_start, h_end)
                    if ov > best_ov:
                        best_ov = ov
                        best_h = (h_start, h_end, h_lab, h_txt)
                if best_ov == 0:
                    pred_counts["S"] += 1
                else:
                    h_start, h_end, h_lab, h_txt = best_h
                    if p_start == h_start and p_end == h_end and p_lab == h_lab:
                        pred_counts["M"] += 1
                    else:
                        pred_counts["C"] += 1
                        if p_lab != h_lab:
                            confusion[h_lab][p_lab] += 1
                            if h_lab == "DX" and p_lab in ("DRUG", "CDRUG", "SDRUG", "ODRUG"):
                                dx_to_drug_terms.append(h_txt.strip().lower())
                            elif h_lab == "DX" and p_lab in ("MHX", "HX", "FHX"):
                                dx_to_mhx_terms.append(h_txt.strip().lower())

        # Misses N
        n_count = 0
        for f, h_spans in human_map.items():
            p_spans = model_map.get(f, [])
            for h_start, h_end, h_lab, h_txt in h_spans:
                has_ov = any(span_overlap(p_start, p_end, h_start, h_end) > 0 for p_start, p_end, _, _ in p_spans)
                if not has_ov:
                    n_count += 1
        pred_counts["N"] = n_count

        return pred_counts, confusion, dx_to_drug_terms, dx_to_mhx_terms

    bert_counts, bert_conf, _, _ = analyze(bert_map, human_map)
    llm_counts, llm_conf, llm_dx_drug, llm_dx_mhx = analyze(llm_map, human_map)

    # -------------------------------------------------------------
    # Styling & Palette
    # -------------------------------------------------------------
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Calibri", "DejaVu Sans", "Helvetica"]
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 0.9

    c_bert = "#1F77B4"      # Blue for BERT
    c_llm  = "#FF6F61"      # Warm Pink close to red for LLM

    # Figure Layout: 3 Rows
    # Row 0: Panel (a) spans full width
    # Row 1: Panel (b) and Panel (c) side-by-side with identical X axis range
    # Row 2: Panel (d) and Panel (e) side-by-side (word clouds)
    fig = plt.figure(figsize=(15, 14), dpi=300)
    gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.1, 1.0], hspace=0.32, wspace=0.18)

    # -------------------------------------------------------------
    # Panel (a): M/C/S/N Error Distribution
    # -------------------------------------------------------------
    ax_a = fig.add_subplot(gs[0, :])

    err_codes = ["M", "C", "S", "N"]
    err_labels = [
        "M: exact match",
        "C: coverage error",
        "S: spurious (FP)",
        "N: miss (FN)"
    ]

    bert_tot = sum(bert_counts.values())
    llm_tot = sum(llm_counts.values())

    bert_pcts = [bert_counts[c] / bert_tot * 100 for c in err_codes]
    llm_pcts  = [llm_counts[c] / llm_tot * 100 for c in err_codes]

    x = np.arange(len(err_codes))
    width = 0.35

    bars_ba = ax_a.bar(x - width/2, bert_pcts, width, label="BERT", color=c_bert, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    bars_la = ax_a.bar(x + width/2, llm_pcts, width, label="LLM", color=c_llm, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)

    for i in range(len(err_codes)):
        b_cnt = bert_counts[err_codes[i]]
        b_pct = bert_pcts[i]
        l_cnt = llm_counts[err_codes[i]]
        l_pct = llm_pcts[i]

        ax_a.text(x[i] - width/2, b_pct + 1.0, f"{b_cnt} ({b_pct:.1f}%)", ha="center", va="bottom", fontsize=9.5, fontweight="bold", color="#0B3C5D")
        ax_a.text(x[i] + width/2, l_pct + 1.0, f"{l_cnt} ({l_pct:.1f}%)", ha="center", va="bottom", fontsize=9.5, fontweight="bold", color="#922B21")

    ax_a.set_title("(a) M/C/S/N Error Distribution for BERT vs. LLM (FAERS Test Set)", fontsize=13, fontweight="bold", loc="left", pad=12)
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(err_labels, fontsize=11, fontweight="bold")
    ax_a.set_ylim(0, max(max(bert_pcts), max(llm_pcts)) * 1.22)
    ax_a.set_ylabel("Proportion of spans (%)", fontsize=11, fontweight="bold")
    ax_a.set_xlabel("Error Type", fontsize=11, fontweight="bold", labelpad=6)
    ax_a.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax_a.legend(title="Model", title_fontsize=10, loc="upper right", fontsize=10, framealpha=0.95)

    # -------------------------------------------------------------
    # Panel (b): BERT Top Label Confusions (Comment 3.14: Axis 0 - 195)
    # -------------------------------------------------------------
    ax_b = fig.add_subplot(gs[1, 0])

    def get_top_confusions(conf_dict, top_k=8):
        pairs = []
        for t_lab, preds in conf_dict.items():
            for p_lab, cnt in preds.items():
                if t_lab != p_lab and cnt > 0:
                    pairs.append((f"{t_lab} → {p_lab}", cnt))
        pairs.sort(key=lambda x: x[1])  # ascending for horizontal bar plot
        return pairs[-top_k:]

    bert_top = get_top_confusions(bert_conf, top_k=8)
    b_pairs = [p[0] for p in bert_top]
    b_vals  = [p[1] for p in bert_top]

    y_b = np.arange(len(b_pairs))
    ax_b.barh(y_b, b_vals, height=0.62, color=c_bert, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    for i, v in enumerate(b_vals):
        ax_b.text(v + 3, y_b[i], f"{v}", va="center", ha="left", fontsize=9.5, fontweight="bold", color="#0B3C5D")

    ax_b.set_title("(b) BERT: Top Label Misclassifications", fontsize=12.5, fontweight="bold", loc="left", pad=10)
    ax_b.set_yticks(y_b)
    ax_b.set_yticklabels(b_pairs, fontsize=10, fontweight="bold")
    ax_b.set_xlim(0, 195)  # ALIGNED WITH PANEL C PER COMMENT 3.14
    ax_b.set_xlabel("Number of Confusions", fontsize=10.5, fontweight="bold")
    ax_b.set_ylabel("True → Predicted", fontsize=10.5, fontweight="bold")
    ax_b.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)

    # -------------------------------------------------------------
    # Panel (c): LLM Top Label Confusions (Comment 3.14: Axis 0 - 195)
    # -------------------------------------------------------------
    ax_c = fig.add_subplot(gs[1, 1])

    llm_top = get_top_confusions(llm_conf, top_k=8)
    l_pairs = [p[0] for p in llm_top]
    l_vals  = [p[1] for p in llm_top]

    y_c = np.arange(len(l_pairs))
    ax_c.barh(y_c, l_vals, height=0.62, color=c_llm, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    for i, v in enumerate(l_vals):
        ax_c.text(v + 3, y_c[i], f"{v}", va="center", ha="left", fontsize=9.5, fontweight="bold", color="#922B21")

    ax_c.set_title("(c) LLM: Top Label Misclassifications", fontsize=12.5, fontweight="bold", loc="left", pad=10)
    ax_c.set_yticks(y_c)
    ax_c.set_yticklabels(l_pairs, fontsize=10, fontweight="bold")
    ax_c.set_xlim(0, 195)  # ALIGNED IDENTICALLY TO PANEL B PER COMMENT 3.14
    ax_c.set_xlabel("Number of Confusions", fontsize=10.5, fontweight="bold")
    ax_c.set_ylabel("True → Predicted", fontsize=10.5, fontweight="bold")
    ax_c.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)

    # -------------------------------------------------------------
    # Panel (d): Word Cloud: DX -> DRUG
    # -------------------------------------------------------------
    ax_d = fig.add_subplot(gs[2, 0])

    counts_drug = Counter(llm_dx_drug)
    wc_drug = WordCloud(
        width=800,
        height=450,
        background_color="white",
        colormap="Blues",
        random_state=42,
        max_words=60,
        prefer_horizontal=0.9
    ).generate_from_frequencies(counts_drug)

    ax_d.imshow(wc_drug, interpolation="bilinear")
    ax_d.axis("off")
    ax_d.set_title("(d) Typical Terms Misclassified as DRUG instead of DX by LLM", fontsize=12, fontweight="bold", pad=8)

    # -------------------------------------------------------------
    # Panel (e): Word Cloud: DX -> MHX
    # -------------------------------------------------------------
    ax_e = fig.add_subplot(gs[2, 1])

    counts_mhx = Counter(llm_dx_mhx)
    wc_mhx = WordCloud(
        width=800,
        height=450,
        background_color="white",
        colormap="Reds",
        random_state=42,
        max_words=60,
        prefer_horizontal=0.9
    ).generate_from_frequencies(counts_mhx)

    ax_e.imshow(wc_mhx, interpolation="bilinear")
    ax_e.axis("off")
    ax_e.set_title("(e) Typical Terms Misclassified as MHX instead of DX by LLM", fontsize=12, fontweight="bold", pad=8)

    plt.tight_layout()

    out_fig_path = figures_dir / "figure5.png"
    out_manuscript_fig = manuscript_dir / "figure5.png"
    out_docx_img = manuscript_dir / "extracted_images" / "image_01.png"

    plt.savefig(out_fig_path, dpi=300, bbox_inches="tight")
    plt.savefig(out_manuscript_fig, dpi=300, bbox_inches="tight")
    plt.savefig(out_docx_img, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Figure 5 successfully generated and saved to:\n  - {out_fig_path}\n  - {out_manuscript_fig}\n  - {out_docx_img}")


if __name__ == "__main__":
    main()
