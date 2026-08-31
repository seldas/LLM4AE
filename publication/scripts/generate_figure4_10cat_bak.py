#!/usr/bin/env python3
"""
generate_figure4.py

Generates publication-ready Figure 4: Comparative Concept Extraction Performance on FAERS (N = 829 Reports)
Fine-Tuned BioBERT (4-Fold LOO, 5-Seed Pooled) vs. Instruction-Tuned LLMs (LLaMA 4 & Claude 4.6 Sonnet)

Structure:
- Panel (a): Primary Tier: Strict Exact-Match NER F1 Score across all clinical categories + Overall
- Panel (b): Secondary Tier: Adapted ADE-Eval Clinical Weighted F1 Score across all clinical categories + Overall

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

    bert_summary_path = results_dir / "bert_runs_FAERS_LOO" / "loo_evaluation_summary.xlsx"
    three_schemes_path = results_dir / "comparison_three_schemes" / "three_schemes_summary.xlsx"

    print(f"Loading benchmark data from {bert_summary_path} and {three_schemes_path}...")
    df_bert_cat = pd.read_excel(bert_summary_path, sheet_name="Per_Category_Summary")
    df_bert_all = pd.read_excel(bert_summary_path, sheet_name="All_Runs_Per_Seed")
    df_sonnet_cat = pd.read_excel(three_schemes_path, sheet_name="Sonnet_FAERS_Categories")
    df_llama4_cat = pd.read_excel(three_schemes_path, sheet_name="LLaMA4_FAERS_Categories")

    # Set matplotlib style
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Calibri", "DejaVu Sans", "Helvetica"]
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 0.9

    categories = ["AE", "AGE", "DOSE", "DRUG", "DX", "HX", "INDICATION", "LAB", "SEX", "STATUS"]
    
    # 1. Collect BioBERT metrics
    bert_strict_mean, bert_strict_std = [], []
    bert_ade_mean, bert_ade_std = [], []

    for c in categories:
        b_row = df_bert_cat[df_bert_cat["category"] == c].iloc[0]
        bert_strict_mean.append(b_row["strict_F1_mean"])
        bert_strict_std.append(b_row["strict_F1_std"])
        bert_ade_mean.append(b_row["ade_F1_mean"])
        bert_ade_std.append(b_row["ade_F1_std"])

    # BioBERT Overall
    bert_strict_mean.append(df_bert_all["strict_F1"].mean())
    bert_strict_std.append(df_bert_all["strict_F1"].std())
    bert_ade_mean.append(df_bert_all["ade_F1"].mean())
    bert_ade_std.append(df_bert_all["ade_F1"].std())

    # 2. Collect LLaMA 4 metrics
    llama_strict, llama_ade = [], []
    for c in categories:
        l_row = df_llama4_cat[df_llama4_cat["Category"] == c].iloc[0]
        llama_strict.append(l_row["Strict_F1"])
        llama_ade.append(l_row["ADE_F1"])

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
    llama_strict.append(l_ov_f1_3)
    llama_ade.append(l_ov_f1_2)

    # 3. Collect Claude Sonnet metrics
    sonnet_strict, sonnet_ade = [], []
    for c in categories:
        s_row = df_sonnet_cat[df_sonnet_cat["Category"] == c].iloc[0]
        sonnet_strict.append(s_row["Strict_F1"])
        sonnet_ade.append(s_row["ADE_F1"])

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
    sonnet_strict.append(s_ov_f1_3)
    sonnet_ade.append(s_ov_f1_2)

    plot_cats = categories + ["OVERALL"]

    # -------------------------------------------------------------
    # Render Figure (2 Vertical Panels)
    # -------------------------------------------------------------
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(15.5, 11), dpi=300, sharex=True)
    plt.subplots_adjust(hspace=0.25)

    x = np.arange(len(plot_cats))
    width = 0.26

    # Colors: BioBERT = Blue; LLaMA = Pink close to red; Claude Sonnet = Red
    c_bert = "#1F77B4"       # Strong Blue for BioBERT
    c_llama = "#FF6F61"      # Warm Pink close to red for LLaMA 4
    c_sonnet = "#C0392B"     # Deep Red for Claude Sonnet

    # -------------------------------------------------------------
    # Panel (a): Primary Tier: Strict Exact-Match NER F1
    # -------------------------------------------------------------
    bars_b0 = ax0.bar(x - width, bert_strict_mean, width, yerr=bert_strict_std, capsize=3.5,
                      error_kw={"elinewidth": 1.1, "ecolor": "#0B3C5D"},
                      label="BioBERT (4-Fold LOO, 5-Seed Pooled)", color=c_bert, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_l0 = ax0.bar(x, llama_strict, width, label="LLaMA 4 (1-shot, Tagged)", color=c_llama, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_s0 = ax0.bar(x + width, sonnet_strict, width, label="Claude 4.6 Sonnet (1-shot)", color=c_sonnet, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)

    for i in range(len(plot_cats)):
        b_top = bert_strict_mean[i] + bert_strict_std[i]
        ax0.text(x[i] - width, b_top + 0.02, f"{bert_strict_mean[i]:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#0B3C5D")
        ax0.text(x[i], llama_strict[i] + 0.02, f"{llama_strict[i]:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#922B21")
        ax0.text(x[i] + width, sonnet_strict[i] + 0.02, f"{sonnet_strict[i]:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#641E16")

    ax0.set_title("(a) Primary Tier: Strict Exact-Match NER F1 Score (FAERS Corpus, N = 829 Reports)",
                  fontsize=12.5, fontweight="bold", loc="left", pad=10)
    ax0.set_ylim(0, 1.15)
    ax0.set_ylabel("Strict Exact-Match F1", fontsize=11, fontweight="bold")
    ax0.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax0.legend(loc="upper right", bbox_to_anchor=(0.99, 0.98), fontsize=9.5, framealpha=0.95, ncol=3)

    # -------------------------------------------------------------
    # Panel (b): Secondary Tier: Adapted ADE-Eval Clinical Weighted F1
    # -------------------------------------------------------------
    bars_b1 = ax1.bar(x - width, bert_ade_mean, width, yerr=bert_ade_std, capsize=3.5,
                      error_kw={"elinewidth": 1.1, "ecolor": "#0B3C5D"},
                      label="BioBERT (4-Fold LOO, 5-Seed Pooled)", color=c_bert, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_l1 = ax1.bar(x, llama_ade, width, label="LLaMA 4 (1-shot, Tagged)", color=c_llama, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_s1 = ax1.bar(x + width, sonnet_ade, width, label="Claude 4.6 Sonnet (1-shot)", color=c_sonnet, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)

    for i in range(len(plot_cats)):
        b_top = bert_ade_mean[i] + bert_ade_std[i]
        ax1.text(x[i] - width, b_top + 0.02, f"{bert_ade_mean[i]:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#0B3C5D")
        ax1.text(x[i], llama_ade[i] + 0.02, f"{llama_ade[i]:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#922B21")
        ax1.text(x[i] + width, sonnet_ade[i] + 0.02, f"{sonnet_ade[i]:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#641E16")

    ax1.set_title("(b) Secondary Tier: Adapted ADE-Eval Clinical Weighted F1 Score (FAERS Corpus, N = 829 Reports)",
                  fontsize=12.5, fontweight="bold", loc="left", pad=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(plot_cats, fontsize=10.5, fontweight="bold")
    ax1.set_ylim(0, 1.15)
    ax1.set_ylabel("Adapted ADE-Eval F1", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Clinical Entity Category", fontsize=11, fontweight="bold", labelpad=8)
    ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax1.legend(loc="upper right", bbox_to_anchor=(0.99, 0.98), fontsize=9.5, framealpha=0.95, ncol=3)

    plt.tight_layout()

    out_fig_path = figures_dir / "figure4.png"
    out_manuscript_fig = manuscript_dir / "figure4.png"
    out_docx_img = manuscript_dir / "extracted_images" / "image_03.png"

    plt.savefig(out_fig_path, dpi=300, bbox_inches="tight")
    plt.savefig(out_manuscript_fig, dpi=300, bbox_inches="tight")
    plt.savefig(out_docx_img, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Figure 4 successfully generated and saved to:\n  - {out_fig_path}\n  - {out_manuscript_fig}\n  - {out_docx_img}")


if __name__ == "__main__":
    main()
