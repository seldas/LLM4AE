#!/usr/bin/env python3
"""
generate_figure6.py

Generates publication-ready Figure 6: Cross-Domain Benchmark and Error Anatomy on VAERS Vaccine Safety Narratives
Evaluated on the FULL VAERS benchmark corpus (N = 1,000 reports) across all 14 distinct clinical and contextual categories.

Panels:
- (a) Per-Category Annotation Performance on Full VAERS Corpus across all 14 categories (BioBERT vs. LLaMA 4)
- (b) M/C/S/N Error Distribution on Full VAERS Corpus (N = 1,000 Reports)
- (c) BioBERT: Top Label Misclassifications on VAERS (X-axis aligned 0 - 5,200)
- (d) LLaMA 4: Top Label Misclassifications on VAERS (X-axis aligned 0 - 5,200)

Standard Manuscript Color Palette:
- BERT: Blue (#1F77B4)
- LLaMA 4 / LLM: Pink close to red (#FF6F61)
- Claude Sonnet: Red (#C0392B)
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    results_dir = repo_root / "publication" / "results"
    figures_dir = results_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    manuscript_dir = repo_root / "publication" / "manuscripts"

    # All 14 VAERS Categories + Overall TOTAL
    cats = [
        "VAX", "Tx", "STATUS", "MHx", "sDx", "pDx", "SYM", "Lab",
        "FHx", "DX", "TEMPO", "DOSE", "Age", "Sex", "TOTAL"
    ]

    # Full VAERS Corpus (N = 1,000 reports) 14-Category Performance Metrics
    # BioBERT 10-Fold CV
    b_f1 = [0.8633, 0.8363, 0.7096, 0.7481, 0.6878, 0.6180, 0.6257, 0.5856, 0.3506, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.7021]
    b_p  = [0.8505, 0.8343, 0.6864, 0.7305, 0.7456, 0.7008, 0.5919, 0.5951, 0.4286, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.6958]
    b_r  = [0.8764, 0.8384, 0.7344, 0.7666, 0.6382, 0.5526, 0.6635, 0.5765, 0.2967, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.7085]

    # LLaMA 4 (1-shot Tagged P2_TAG_VAERS)
    l_f1 = [0.6012, 0.3987, 0.2980, 0.2373, 0.0837, 0.0731, 0.2228, 0.1626, 0.0957, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.2216]
    l_p  = [0.6427, 0.3607, 0.2411, 0.2047, 0.2117, 0.0990, 0.2429, 0.1424, 0.0994, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.1984]
    l_r  = [0.5648, 0.4456, 0.3898, 0.2823, 0.0522, 0.0579, 0.2058, 0.1894, 0.0923, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.2509]

    # Overall Error Distribution (Full VAERS N = 1,000)
    # M, C, S, N
    bert_counts = {"M": 15068, "C": 1741, "S": 4846, "N": 4459}
    llm_counts  = {"M": 10154, "C": 7608, "S": 33421, "N": 22711}

    # Top Label Misclassifications (Full VAERS N = 1,000, 14 Categories)
    bert_top = [
        ("RO → VAX", 305),
        ("SYM → Lab", 305),
        ("RO → SYM", 385),
        ("SYM → MHx", 436),
        ("sDx → SYM", 851),
        ("pDx → DX", 875),
        ("SYM → DX", 2782),
        ("sDx → DX", 4902)
    ]

    llm_top = [
        ("RO → TEMPO", 286),
        ("RO → VAX", 340),
        ("RO → DX", 487),
        ("SYM → Lab", 541),
        ("SYM → MHx", 558),
        ("Lab → TX", 625),
        ("pDx → DX", 947),
        ("sDx → SYM", 2147),
        ("SYM → DX", 2999),
        ("sDx → DX", 3116)
    ][-8:]

    # -------------------------------------------------------------
    # Styling & Palette
    # -------------------------------------------------------------
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Calibri", "DejaVu Sans", "Helvetica"]
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 0.9

    c_bert = "#1F77B4"      # Blue for BERT
    c_llm  = "#FF6F61"      # Warm Pink close to red for LLM

    # Figure Layout: 2 Rows x 2 Columns
    # Top Left: Panel (a) Per-Category F1, Precision, Recall (14 Categories)
    # Top Right: Panel (b) M/C/S/N Error Distribution on Full VAERS
    # Bottom Left: Panel (c) BioBERT Top Confusions (0 - 5,200)
    # Bottom Right: Panel (d) LLaMA 4 Top Confusions (0 - 5,200)
    fig, ((ax_a, ax_b), (ax_c, ax_d)) = plt.subplots(2, 2, figsize=(17, 12), dpi=300)
    plt.subplots_adjust(hspace=0.34, wspace=0.22)

    # -------------------------------------------------------------
    # Panel (a): Per-Category Performance on VAERS (14 Categories)
    # -------------------------------------------------------------
    x_a = np.arange(len(cats))
    width_a = 0.38

    bars_ba = ax_a.bar(x_a - width_a/2, b_f1, width_a, label="BERT F1", color=c_bert, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    bars_la = ax_a.bar(x_a + width_a/2, l_f1, width_a, label="LLM F1", color=c_llm, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)

    # Overlay lines for Precision and Recall
    ax_a.plot(x_a - width_a/2, b_r, color="#0B3C5D", marker="o", markersize=4.5, linestyle="--", linewidth=1.1, label="BERT Recall (dashed)", zorder=4)
    ax_a.plot(x_a - width_a/2, b_p, color="#0B3C5D", marker="s", markersize=4.5, linestyle=":", linewidth=1.1, label="BERT Precision (dotted)", zorder=4)
    ax_a.plot(x_a + width_a/2, l_r, color="#922B21", marker="o", markersize=4.5, linestyle="--", linewidth=1.1, label="LLM Recall (dashed)", zorder=4)
    ax_a.plot(x_a + width_a/2, l_p, color="#922B21", marker="s", markersize=4.5, linestyle=":", linewidth=1.1, label="LLM Precision (dotted)", zorder=4)

    for i in range(len(cats)):
        if cats[i] in ["VAX", "Tx"]:
            ax_a.text(x_a[i] - width_a/2, b_f1[i] - 0.08, f"{b_f1[i]:.2f}", ha="center", va="top", fontsize=8, fontweight="bold", color="white")
            ax_a.text(x_a[i] + width_a/2, l_f1[i] + 0.02, f"{l_f1[i]:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#922B21")
        elif b_f1[i] > 0 or l_f1[i] > 0:
            ax_a.text(x_a[i] - width_a/2, b_f1[i] + 0.02, f"{b_f1[i]:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#0B3C5D")
            ax_a.text(x_a[i] + width_a/2, l_f1[i] + 0.02, f"{l_f1[i]:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#922B21")

    ax_a.set_title("(a) Per-Category Performance on Full VAERS Corpus (14 Concept Categories)", fontsize=12, fontweight="bold", loc="left", pad=10)
    ax_a.set_xticks(x_a)
    ax_a.set_xticklabels(cats, fontsize=8.5, fontweight="bold", rotation=25, ha="right")
    ax_a.set_ylim(0, 1.12)
    ax_a.set_ylabel("F1 Score / Metric", fontsize=10.5, fontweight="bold")
    ax_a.set_xlabel("Entity Category", fontsize=10.5, fontweight="bold", labelpad=6)
    ax_a.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    # Custom compact legend for Panel a
    handles_a = [
        mpatches.Patch(facecolor=c_bert, edgecolor="#111", label="BERT F1"),
        mpatches.Patch(facecolor=c_llm, edgecolor="#111", label="LLM F1"),
        plt.Line2D([0], [0], color="#0B3C5D", marker="o", linestyle="--", markersize=4.5, label="BERT Recall"),
        plt.Line2D([0], [0], color="#0B3C5D", marker="s", linestyle=":", markersize=4.5, label="BERT Precision"),
        plt.Line2D([0], [0], color="#922B21", marker="o", linestyle="--", markersize=4.5, label="LLM Recall"),
        plt.Line2D([0], [0], color="#922B21", marker="s", linestyle=":", markersize=4.5, label="LLM Precision"),
    ]
    ax_a.legend(handles=handles_a, loc="upper right", fontsize=8, framealpha=0.95, ncol=3)

    # -------------------------------------------------------------
    # Panel (b): M/C/S/N Error Distribution on Full VAERS
    # -------------------------------------------------------------
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

    x_b = np.arange(len(err_codes))
    width_b = 0.35

    bars_bb = ax_b.bar(x_b - width_b/2, bert_pcts, width_b, label="BERT", color=c_bert, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    bars_lb = ax_b.bar(x_b + width_b/2, llm_pcts, width_b, label="LLM", color=c_llm, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)

    for i in range(len(err_codes)):
        b_cnt = bert_counts[err_codes[i]]
        b_pct = bert_pcts[i]
        l_cnt = llm_counts[err_codes[i]]
        l_pct = llm_pcts[i]

        ax_b.text(x_b[i] - width_b/2, b_pct + 1.0, f"{b_cnt:,}\n({b_pct:.1f}%)", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#0B3C5D")
        ax_b.text(x_b[i] + width_b/2, l_pct + 1.0, f"{l_cnt:,}\n({l_pct:.1f}%)", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#922B21")

    ax_b.set_title("(b) M/C/S/N Error Distribution on Full VAERS Corpus (N = 1,000 Reports)", fontsize=12, fontweight="bold", loc="left", pad=10)
    ax_b.set_xticks(x_b)
    ax_b.set_xticklabels(err_labels, fontsize=10, fontweight="bold")
    ax_b.set_ylim(0, max(max(bert_pcts), max(llm_pcts)) * 1.25)
    ax_b.set_ylabel("Proportion of Spans (%)", fontsize=10.5, fontweight="bold")
    ax_b.set_xlabel("Error Type", fontsize=10.5, fontweight="bold", labelpad=6)
    ax_b.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax_b.legend(title="Model", title_fontsize=9.5, loc="upper right", fontsize=9, framealpha=0.95)

    # -------------------------------------------------------------
    # Panel (c): BioBERT Top Label Confusions on VAERS (Aligned to 5,200)
    # -------------------------------------------------------------
    b_pairs = [p[0] for p in bert_top]
    b_vals  = [p[1] for p in bert_top]

    y_c = np.arange(len(b_pairs))
    ax_c.barh(y_c, b_vals, height=0.62, color=c_bert, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    for i, v in enumerate(b_vals):
        ax_c.text(v + 70, y_c[i], f"{v:,}", va="center", ha="left", fontsize=9, fontweight="bold", color="#0B3C5D")

    ax_c.set_title("(c) BioBERT: Top Label Misclassifications on VAERS", fontsize=12, fontweight="bold", loc="left", pad=10)
    ax_c.set_yticks(y_c)
    ax_c.set_yticklabels(b_pairs, fontsize=9.5, fontweight="bold")
    ax_c.set_xlim(0, 5400)  # ALIGNED TO IDENTICAL 0-5400 SCALE PER COMMENT 3.14
    ax_c.set_xlabel("Number of Confusions", fontsize=10.5, fontweight="bold")
    ax_c.set_ylabel("True → Predicted", fontsize=10.5, fontweight="bold")
    ax_c.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)

    # -------------------------------------------------------------
    # Panel (d): LLaMA 4 Top Label Confusions on VAERS (Aligned to 5,200)
    # -------------------------------------------------------------
    l_pairs = [p[0] for p in llm_top]
    l_vals  = [p[1] for p in llm_top]

    y_d = np.arange(len(l_pairs))
    ax_d.barh(y_d, l_vals, height=0.62, color=c_llm, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    for i, v in enumerate(l_vals):
        ax_d.text(v + 70, y_d[i], f"{v:,}", va="center", ha="left", fontsize=9, fontweight="bold", color="#922B21")

    ax_d.set_title("(d) LLaMA 4: Top Label Misclassifications on VAERS", fontsize=12, fontweight="bold", loc="left", pad=10)
    ax_d.set_yticks(y_d)
    ax_d.set_yticklabels(l_pairs, fontsize=9.5, fontweight="bold")
    ax_d.set_xlim(0, 5400)  # ALIGNED TO IDENTICAL 0-5400 SCALE PER COMMENT 3.14
    ax_d.set_xlabel("Number of Confusions", fontsize=10.5, fontweight="bold")
    ax_d.set_ylabel("True → Predicted", fontsize=10.5, fontweight="bold")
    ax_d.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)

    plt.tight_layout()

    out_fig_path = figures_dir / "figure6.png"
    out_manuscript_fig = manuscript_dir / "figure6.png"
    out_docx_img = manuscript_dir / "extracted_images" / "image_02.png"

    plt.savefig(out_fig_path, dpi=300, bbox_inches="tight")
    plt.savefig(out_manuscript_fig, dpi=300, bbox_inches="tight")
    plt.savefig(out_docx_img, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Figure 6 successfully generated and saved to:\n  - {out_fig_path}\n  - {out_manuscript_fig}\n  - {out_docx_img}")


if __name__ == "__main__":
    main()
