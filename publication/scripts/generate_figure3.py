#!/usr/bin/env python3
"""
generate_figure3.py

Regenerates publication-ready Figure 3: Performance of Instruction-Tuned LLMs
and Rule-Based Baseline (ETHER) in FAERS Annotation.

Panels:
- Panel (a): Per-Category Performance of Instruction-Tuned LLMs (Claude 4.6 Sonnet vs. LLaMA 4)
             across all 10 core clinical categories + Overall on FAERS (N = 829).
- Panel (b): Head-to-Head Comparison: ETHER vs. LLaMA 4 vs. Claude 4.6 Sonnet
             on the shared 4-category common schema (AE, DRUG, DX, HX, and Shared TOTAL).

Standard Manuscript Color Palette:
- ETHER: Gray (#616161)
- BERT: Blue (#1F77B4)
- LLaMA 4: Pink close to red (#FF6F61)
- Claude Sonnet: Red (#C0392B)
"""

from __future__ import annotations

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

    three_schemes_path = results_dir / "comparison_three_schemes" / "three_schemes_summary.xlsx"
    error_summary_path = results_dir / "error_analysis" / "error_breakdown_summary.xlsx"

    print(f"Loading benchmark data from {three_schemes_path}...")
    df_sonnet_cat = pd.read_excel(three_schemes_path, sheet_name="Sonnet_FAERS_Categories")
    df_llama4_cat = pd.read_excel(three_schemes_path, sheet_name="LLaMA4_FAERS_Categories")
    df_ether_cat = pd.read_excel(error_summary_path, sheet_name="ETHER_Categories")
    df_ether_ov = pd.read_excel(error_summary_path, sheet_name="ETHER_Overall")

    # Set matplotlib style
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Calibri", "DejaVu Sans", "Helvetica"]
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 0.9

    fig = plt.figure(figsize=(15, 9.5), dpi=300)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.1, 1.2], hspace=0.35)

    # -------------------------------------------------------------
    # Consistent Color Scheme
    # -------------------------------------------------------------
    c_ether = "#616161"        # Gray for ETHER
    c_llama = "#FF6F61"        # Warm Pink close to red for LLaMA 4
    c_sonnet = "#C0392B"       # Deep Red for Claude Sonnet

    # -------------------------------------------------------------
    # Panel (a): Per-Category Performance of LLMs across FAERS
    # -------------------------------------------------------------
    ax0 = fig.add_subplot(gs[0, 0])

    target_cats = ["AE", "AGE", "DOSE", "DRUG", "DX", "HX", "INDICATION", "LAB", "SEX", "STATUS"]
    
    sonnet_f1_ade, sonnet_f1_strict = [], []
    llama_f1_ade, llama_f1_strict = [], []

    for c in target_cats:
        s_row = df_sonnet_cat[df_sonnet_cat["Category"] == c].iloc[0]
        l_row = df_llama4_cat[df_llama4_cat["Category"] == c].iloc[0]
        sonnet_f1_ade.append(s_row["ADE_F1"])
        sonnet_f1_strict.append(s_row["Strict_F1"])
        llama_f1_ade.append(l_row["ADE_F1"])
        llama_f1_strict.append(l_row["Strict_F1"])

    # Overall metrics
    s_tot_m = df_sonnet_cat["M"].sum()
    s_tot_c = df_sonnet_cat["C_total"].sum()
    s_tot_s = df_sonnet_cat["S_non_overlap"].sum()
    s_tot_n = df_sonnet_cat["N"].sum()
    s_ov_p3 = s_tot_m / (s_tot_m + s_tot_c + s_tot_s)
    s_ov_r3 = s_tot_m / (s_tot_m + s_tot_c + s_tot_n)
    s_ov_f1_3 = 2 * s_ov_p3 * s_ov_r3 / (s_ov_p3 + s_ov_r3)
    s_ov_p2 = (s_tot_m + 0.5 * s_tot_c) / (s_tot_m + s_tot_c + 0.25 * s_tot_s)
    s_ov_r2 = (s_tot_m + 0.5 * s_tot_c) / (s_tot_m + s_tot_c + s_tot_n)
    s_ov_f1_2 = 2 * s_ov_p2 * s_ov_r2 / (s_ov_p2 + s_ov_r2)

    l_tot_m = df_llama4_cat["M"].sum()
    l_tot_c = df_llama4_cat["C_total"].sum()
    l_tot_s = df_llama4_cat["S_non_overlap"].sum()
    l_tot_n = df_llama4_cat["N"].sum()
    l_ov_p3 = l_tot_m / (l_tot_m + l_tot_c + l_tot_s)
    l_ov_r3 = l_tot_m / (l_tot_m + l_tot_c + l_tot_n)
    l_ov_f1_3 = 2 * l_ov_p3 * l_ov_r3 / (l_ov_p3 + l_ov_r3)
    l_ov_p2 = (l_tot_m + 0.5 * l_tot_c) / (l_tot_m + l_tot_c + 0.25 * l_tot_s)
    l_ov_r2 = (l_tot_m + 0.5 * l_tot_c) / (l_tot_m + l_tot_c + l_tot_n)
    l_ov_f1_2 = 2 * l_ov_p2 * l_ov_r2 / (l_ov_p2 + l_ov_r2)

    plot_cats = target_cats + ["TOTAL"]
    sonnet_f1_ade.append(s_ov_f1_2)
    sonnet_f1_strict.append(s_ov_f1_3)
    llama_f1_ade.append(l_ov_f1_2)
    llama_f1_strict.append(l_ov_f1_3)

    x = np.arange(len(plot_cats))
    width = 0.38

    # Bars: ADE F1
    bars_s = ax0.bar(x - width/2, sonnet_f1_ade, width, label="Claude 4.6 Sonnet (Adapted ADE-Eval F1)",
                     color=c_sonnet, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_l = ax0.bar(x + width/2, llama_f1_ade, width, label="LLaMA 4 (Adapted ADE-Eval F1)",
                     color=c_llama, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)

    # Line/Point overlay for Strict F1
    ax0.plot(x - width/2, sonnet_f1_strict, color="#641E16", marker="o", markersize=6, linestyle="", label="Claude 4.6 Sonnet (Strict Exact F1)", zorder=5)
    ax0.plot(x + width/2, llama_f1_strict, color="#922B21", marker="s", markersize=6, linestyle="", label="LLaMA 4 (Strict Exact F1)", zorder=5)

    # Value labels
    for i in range(len(plot_cats)):
        ax0.text(x[i] - width/2, sonnet_f1_ade[i] + 0.025, f"{sonnet_f1_ade[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#641E16")
        ax0.text(x[i] + width/2, llama_f1_ade[i] + 0.025, f"{llama_f1_ade[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#922B21")

    ax0.set_title("(a) Per-Category Performance of Instruction-Tuned LLMs on FAERS (N = 829 Reports)", fontsize=13, fontweight="bold", loc="left", pad=12)
    ax0.set_xticks(x)
    ax0.set_xticklabels(plot_cats, fontsize=10.5, fontweight="bold")
    ax0.set_ylim(0, 1.20)
    ax0.set_ylabel("F1 Score", fontsize=11, fontweight="bold")
    ax0.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax0.legend(loc="upper left", bbox_to_anchor=(0.01, 0.98), fontsize=9, framealpha=0.95, ncol=2)

    # -------------------------------------------------------------
    # Panel (b): Head-to-Head Comparison: ETHER vs. LLMs (Shared Schema)
    # -------------------------------------------------------------
    ax1 = fig.add_subplot(gs[1, 0])

    shared_cats = ["AE", "DRUG", "DX", "HX"]
    
    ether_f1_s2, ether_f1_s3, ether_p_s2, ether_r_s2 = [], [], [], []
    llama_shared_f1_s2, llama_shared_f1_s3, llama_shared_p_s2, llama_shared_r_s2 = [], [], [], []
    sonnet_shared_f1_s2, sonnet_shared_f1_s3, sonnet_shared_p_s2, sonnet_shared_r_s2 = [], [], [], []

    for c in shared_cats:
        e_row = df_ether_cat[df_ether_cat["Category"] == c].iloc[0]
        l_row = df_llama4_cat[df_llama4_cat["Category"] == c].iloc[0]
        s_row = df_sonnet_cat[df_sonnet_cat["Category"] == c].iloc[0]

        ether_f1_s2.append(e_row["S2_F1"])
        ether_f1_s3.append(e_row["S3_F1"])
        ether_p_s2.append(e_row["S2_Precision"])
        ether_r_s2.append(e_row["S2_Recall"])

        llama_shared_f1_s2.append(l_row["ADE_F1"])
        llama_shared_f1_s3.append(l_row["Strict_F1"])
        llama_shared_p_s2.append(l_row["ADE_Precision"])
        llama_shared_r_s2.append(l_row["ADE_Recall"])

        sonnet_shared_f1_s2.append(s_row["ADE_F1"])
        sonnet_shared_f1_s3.append(s_row["Strict_F1"])
        sonnet_shared_p_s2.append(s_row["ADE_Precision"])
        sonnet_shared_r_s2.append(s_row["ADE_Recall"])

    # Shared Overall
    e_ov_row = df_ether_ov.iloc[0]
    plot_shared_cats = shared_cats + ["TOTAL (Shared)"]

    ether_f1_s2.append(e_ov_row["S2 (Weighted) F1"])
    ether_f1_s3.append(e_ov_row["S3 (Strict) F1"])
    ether_p_s2.append(e_ov_row["S2 (Weighted) P"])
    ether_r_s2.append(e_ov_row["S2 (Weighted) R"])

    llama_shared_f1_s2.append(l_ov_f1_2)
    llama_shared_f1_s3.append(l_ov_f1_3)
    llama_shared_p_s2.append(l_ov_p2)
    llama_shared_r_s2.append(l_ov_r2)

    sonnet_shared_f1_s2.append(s_ov_f1_2)
    sonnet_shared_f1_s3.append(s_ov_f1_3)
    sonnet_shared_p_s2.append(s_ov_p2)
    sonnet_shared_r_s2.append(s_ov_r2)

    x2 = np.arange(len(plot_shared_cats))
    width2 = 0.26

    # Grouped Bars: Adapted ADE-Eval F1
    bars_e = ax1.bar(x2 - width2, ether_f1_s2, width2, label="ETHER (Dictionary Baseline)", color=c_ether, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_l2 = ax1.bar(x2, llama_shared_f1_s2, width2, label="LLaMA 4 (1-shot, Tagged)", color=c_llama, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_s2 = ax1.bar(x2 + width2, sonnet_shared_f1_s2, width2, label="Claude 4.6 Sonnet (1-shot)", color=c_sonnet, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)

    # Point Overlays for Strict Exact-Match F1
    ax1.plot(x2 - width2, ether_f1_s3, color="#212121", marker="D", markersize=6, linestyle="", label="Strict Exact F1 (◆)", zorder=5)
    ax1.plot(x2, llama_shared_f1_s3, color="#922B21", marker="s", markersize=6, linestyle="", label="Strict Exact F1 (■)", zorder=5)
    ax1.plot(x2 + width2, sonnet_shared_f1_s3, color="#641E16", marker="o", markersize=6, linestyle="", label="Strict Exact F1 (●)", zorder=5)

    # Clean Value labels above bars
    for i in range(len(plot_shared_cats)):
        ax1.text(x2[i] - width2, ether_f1_s2[i] + 0.025, f"{ether_f1_s2[i]:.2f}", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#212121")
        ax1.text(x2[i], llama_shared_f1_s2[i] + 0.025, f"{llama_shared_f1_s2[i]:.2f}", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#922B21")
        ax1.text(x2[i] + width2, sonnet_shared_f1_s2[i] + 0.025, f"{sonnet_shared_f1_s2[i]:.2f}", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#641E16")

    ax1.set_title("(b) Head-to-Head Comparison: Rule-Based Baseline (ETHER) vs. LLMs on Shared Schema (AE, DRUG, DX, HX)", fontsize=13, fontweight="bold", loc="left", pad=12)
    ax1.set_xticks(x2)
    ax1.set_xticklabels(plot_shared_cats, fontsize=11, fontweight="bold")
    ax1.set_ylim(0, 1.05)
    ax1.set_ylabel("F1 Score", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Clinical Category", fontsize=11, fontweight="bold", labelpad=8)
    ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    # Custom legend for panel b
    custom_handles = [
        mpatches.Patch(facecolor=c_ether, edgecolor="#111", label="ETHER (Adapted ADE F1)"),
        mpatches.Patch(facecolor=c_llama, edgecolor="#111", label="LLaMA 4 (Adapted ADE F1)"),
        mpatches.Patch(facecolor=c_sonnet, edgecolor="#111", label="Claude 4.6 Sonnet (Adapted ADE F1)"),
        plt.Line2D([0], [0], color="#212121", marker="D", linestyle="", markersize=6, label="ETHER Strict F1"),
        plt.Line2D([0], [0], color="#922B21", marker="s", linestyle="", markersize=6, label="LLaMA 4 Strict F1"),
        plt.Line2D([0], [0], color="#641E16", marker="o", linestyle="", markersize=6, label="Claude Sonnet Strict F1"),
    ]
    ax1.legend(handles=custom_handles, loc="upper right", bbox_to_anchor=(0.99, 0.98), fontsize=9, framealpha=0.95, ncol=3)

    out_fig_path = figures_dir / "figure3.png"
    out_manuscript_fig = manuscript_dir / "figure3.png"
    out_docx_img = manuscript_dir / "extracted_images" / "image_00.png"

    plt.savefig(out_fig_path, dpi=300, bbox_inches="tight")
    plt.savefig(out_manuscript_fig, dpi=300, bbox_inches="tight")
    plt.savefig(out_docx_img, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Figure 3 successfully generated and saved to:\n  - {out_fig_path}\n  - {out_manuscript_fig}\n  - {out_docx_img}")


if __name__ == "__main__":
    main()
