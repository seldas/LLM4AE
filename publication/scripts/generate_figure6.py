#!/usr/bin/env python3
"""
generate_figure6.py

Generates publication-ready Figure 6: Cross-Domain Benchmark and Error Anatomy on VAERS Vaccine Safety Narratives
Addressing Reviewer #3, Comment 3.21 (Providing the complete error breakdown schematic for VAERS)
and Comment 3.14 (Horizontal axis alignment for confusion bar charts).

Panels:
- (a) Per-Category Annotation Performance on VAERS Testing Dataset (BERT vs. LLM)
- (b) M/C/S/N Error Distribution on VAERS for BERT vs. LLM
- (c) BERT: Top Label Misclassifications on VAERS (X-axis: 0 - 650)
- (d) LLM: Top Label Misclassifications on VAERS (X-axis: 0 - 650, matched to 6c)

Standard Manuscript Color Palette:
- ETHER: Gray (#616161)
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


def span_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    results_dir = repo_root / "publication" / "results"
    figures_dir = results_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    manuscript_dir = repo_root / "publication" / "manuscripts"

    vaers_perf_path = repo_root / "development" / "BERT" / "Error_analysis" / "VAERS_performance_uw.xlsx"
    vaers_test_path = repo_root / "development" / "BERT" / "Error_analysis" / "VAERS-BERT-TEST.xlsx"

    print(f"Loading VAERS benchmark data from {vaers_perf_path} and {vaers_test_path}...")
    df_perf = pd.read_excel(vaers_perf_path)
    df_test = pd.read_excel(vaers_test_path)

    df_human = df_test[df_test["Note"] == "Human"].copy()
    df_bert  = df_test[df_test["Note"] == "BERT"].copy()
    df_llm   = df_test[df_test["Note"] == "LLM"].copy()

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

        # Misses N
        n_count = 0
        for f, h_spans in human_map.items():
            p_spans = model_map.get(f, [])
            for h_start, h_end, h_lab, h_txt in h_spans:
                has_ov = any(span_overlap(p_start, p_end, h_start, h_end) > 0 for p_start, p_end, _, _ in p_spans)
                if not has_ov:
                    n_count += 1
        pred_counts["N"] = n_count

        return pred_counts, confusion

    bert_counts, bert_conf = analyze(bert_map, human_map)
    llm_counts, llm_conf   = analyze(llm_map, human_map)

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
    # Top Left: Panel (a) Per-Category F1, Precision, Recall
    # Top Right: Panel (b) M/C/S/N Error Distribution on VAERS
    # Bottom Left: Panel (c) BERT Top Confusions (0 - 650)
    # Bottom Right: Panel (d) LLM Top Confusions (0 - 650)
    fig, ((ax_a, ax_b), (ax_c, ax_d)) = plt.subplots(2, 2, figsize=(16, 11.5), dpi=300)
    plt.subplots_adjust(hspace=0.32, wspace=0.22)

    # -------------------------------------------------------------
    # Panel (a): Per-Category Performance on VAERS
    # -------------------------------------------------------------
    cats = ["DX", "HX", "LAB", "RO", "STATUS", "SYM", "TX", "VAX", "TOTAL"]
    df_bert_perf = df_perf[df_perf["Model"] == "BERT"].set_index("Label_Norm")
    df_llm_perf  = df_perf[df_perf["Model"] == "LLM"].set_index("Label_Norm")

    b_f1 = [df_bert_perf.loc[c, "F1"] for c in cats]
    l_f1 = [df_llm_perf.loc[c, "F1"] for c in cats]
    b_p  = [df_bert_perf.loc[c, "Precision"] for c in cats]
    l_p  = [df_llm_perf.loc[c, "Precision"] for c in cats]
    b_r  = [df_bert_perf.loc[c, "Recall"] for c in cats]
    l_r  = [df_llm_perf.loc[c, "Recall"] for c in cats]

    x_a = np.arange(len(cats))
    width_a = 0.38

    bars_ba = ax_a.bar(x_a - width_a/2, b_f1, width_a, label="BERT F1", color=c_bert, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    bars_la = ax_a.bar(x_a + width_a/2, l_f1, width_a, label="LLM F1", color=c_llm, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)

    # Overlay lines for Precision and Recall
    ax_a.plot(x_a - width_a/2, b_r, color="#0B3C5D", marker="o", markersize=5, linestyle="--", linewidth=1.2, label="BERT Recall (dashed)", zorder=4)
    ax_a.plot(x_a - width_a/2, b_p, color="#0B3C5D", marker="s", markersize=5, linestyle=":", linewidth=1.2, label="BERT Precision (dotted)", zorder=4)
    ax_a.plot(x_a + width_a/2, l_r, color="#922B21", marker="o", markersize=5, linestyle="--", linewidth=1.2, label="LLM Recall (dashed)", zorder=4)
    ax_a.plot(x_a + width_a/2, l_p, color="#922B21", marker="s", markersize=5, linestyle=":", linewidth=1.2, label="LLM Precision (dotted)", zorder=4)

    for i in range(len(cats)):
        if cats[i] == "RO":
            ax_a.text(x_a[i] - width_a/2, b_f1[i] + 0.025, f"{b_f1[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#0B3C5D")
            ax_a.text(x_a[i] + width_a/2, l_f1[i] + 0.025, f"{l_f1[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#922B21")
        elif cats[i] == "STATUS":
            ax_a.text(x_a[i] - width_a/2, b_f1[i] + 0.025, f"{b_f1[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#0B3C5D")
            ax_a.text(x_a[i] + width_a/2, l_f1[i] + 0.025, f"{l_f1[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#922B21")
        elif cats[i] == "TX":
            ax_a.text(x_a[i] - width_a/2, b_f1[i] - 0.08, f"{b_f1[i]:.2f}", ha="center", va="top", fontsize=8.5, fontweight="bold", color="white")
            ax_a.text(x_a[i] + width_a/2, l_f1[i] + 0.025, f"{l_f1[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#922B21")
        elif cats[i] == "VAX":
            ax_a.text(x_a[i] - width_a/2, b_f1[i] - 0.08, f"{b_f1[i]:.2f}", ha="center", va="top", fontsize=8.5, fontweight="bold", color="white")
            ax_a.text(x_a[i] + width_a/2, l_f1[i] + 0.025, f"{l_f1[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#922B21")
        elif cats[i] == "TOTAL":
            ax_a.text(x_a[i] - width_a/2, b_f1[i] + 0.025, f"{b_f1[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#0B3C5D")
            ax_a.text(x_a[i] + width_a/2, l_f1[i] + 0.025, f"{l_f1[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#922B21")
        else:
            ax_a.text(x_a[i] - width_a/2, b_f1[i] + 0.025, f"{b_f1[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#0B3C5D")
            ax_a.text(x_a[i] + width_a/2, l_f1[i] + 0.025, f"{l_f1[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#922B21")

    ax_a.set_title("(a) Per-Category Performance on VAERS Testing Dataset", fontsize=12, fontweight="bold", loc="left", pad=10)
    ax_a.set_xticks(x_a)
    ax_a.set_xticklabels(cats, fontsize=9.5, fontweight="bold")
    ax_a.set_ylim(0, 1.12)
    ax_a.set_ylabel("F1 Score / Metric", fontsize=10.5, fontweight="bold")
    ax_a.set_xlabel("Entity Category", fontsize=10.5, fontweight="bold", labelpad=6)
    ax_a.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    # Custom compact legend for Panel a
    handles_a = [
        mpatches.Patch(facecolor=c_bert, edgecolor="#111", label="BERT F1"),
        mpatches.Patch(facecolor=c_llm, edgecolor="#111", label="LLM F1"),
        plt.Line2D([0], [0], color="#0B3C5D", marker="o", linestyle="--", markersize=5, label="BERT Recall"),
        plt.Line2D([0], [0], color="#0B3C5D", marker="s", linestyle=":", markersize=5, label="BERT Precision"),
        plt.Line2D([0], [0], color="#922B21", marker="o", linestyle="--", markersize=5, label="LLM Recall"),
        plt.Line2D([0], [0], color="#922B21", marker="s", linestyle=":", markersize=5, label="LLM Precision"),
    ]
    ax_a.legend(handles=handles_a, loc="upper right", fontsize=8.5, framealpha=0.95, ncol=3)

    # -------------------------------------------------------------
    # Panel (b): M/C/S/N Error Distribution on VAERS (Comment 3.21)
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

        ax_b.text(x_b[i] - width_b/2, b_pct + 1.0, f"{b_cnt}\n({b_pct:.1f}%)", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#0B3C5D")
        ax_b.text(x_b[i] + width_b/2, l_pct + 1.0, f"{l_cnt}\n({l_pct:.1f}%)", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#922B21")

    ax_b.set_title("(b) M/C/S/N Error Distribution on VAERS (Test Set)", fontsize=12, fontweight="bold", loc="left", pad=10)
    ax_b.set_xticks(x_b)
    ax_b.set_xticklabels(err_labels, fontsize=10, fontweight="bold")
    ax_b.set_ylim(0, max(max(bert_pcts), max(llm_pcts)) * 1.25)
    ax_b.set_ylabel("Proportion of Spans (%)", fontsize=10.5, fontweight="bold")
    ax_b.set_xlabel("Error Type", fontsize=10.5, fontweight="bold", labelpad=6)
    ax_b.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax_b.legend(title="Model", title_fontsize=9.5, loc="upper right", fontsize=9, framealpha=0.95)

    # -------------------------------------------------------------
    # Panel (c): BERT Top Label Confusions on VAERS (Axis 0 - 650)
    # -------------------------------------------------------------
    def get_top_confusions(conf_dict, top_k=8):
        pairs = []
        for t_lab, preds in conf_dict.items():
            for p_lab, cnt in preds.items():
                if t_lab != p_lab and cnt > 0:
                    pairs.append((f"{t_lab} → {p_lab}", cnt))
        pairs.sort(key=lambda x: x[1])
        return pairs[-top_k:]

    bert_top = get_top_confusions(bert_conf, top_k=8)
    b_pairs = [p[0] for p in bert_top]
    b_vals  = [p[1] for p in bert_top]

    y_c = np.arange(len(b_pairs))
    ax_c.barh(y_c, b_vals, height=0.62, color=c_bert, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    for i, v in enumerate(b_vals):
        ax_c.text(v + 10, y_c[i], f"{v}", va="center", ha="left", fontsize=9, fontweight="bold", color="#0B3C5D")

    ax_c.set_title("(c) BERT: Top Label Misclassifications on VAERS", fontsize=12, fontweight="bold", loc="left", pad=10)
    ax_c.set_yticks(y_c)
    ax_c.set_yticklabels(b_pairs, fontsize=9.5, fontweight="bold")
    ax_c.set_xlim(0, 660)  # ALIGNED TO IDENTICAL 0-660 SCALE PER COMMENT 3.14
    ax_c.set_xlabel("Number of Confusions", fontsize=10.5, fontweight="bold")
    ax_c.set_ylabel("True → Predicted", fontsize=10.5, fontweight="bold")
    ax_c.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)

    # -------------------------------------------------------------
    # Panel (d): LLM Top Label Confusions on VAERS (Axis 0 - 650)
    # -------------------------------------------------------------
    llm_top = get_top_confusions(llm_conf, top_k=8)
    l_pairs = [p[0] for p in llm_top]
    l_vals  = [p[1] for p in llm_top]

    y_d = np.arange(len(l_pairs))
    ax_d.barh(y_d, l_vals, height=0.62, color=c_llm, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    for i, v in enumerate(l_vals):
        ax_d.text(v + 10, y_d[i], f"{v}", va="center", ha="left", fontsize=9, fontweight="bold", color="#922B21")

    ax_d.set_title("(d) LLM: Top Label Misclassifications on VAERS", fontsize=12, fontweight="bold", loc="left", pad=10)
    ax_d.set_yticks(y_d)
    ax_d.set_yticklabels(l_pairs, fontsize=9.5, fontweight="bold")
    ax_d.set_xlim(0, 660)  # ALIGNED TO IDENTICAL 0-660 SCALE PER COMMENT 3.14
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
