#!/usr/bin/env python3
"""
generate_figure3.py

Regenerates publication-ready Figure 3: Performance of Instruction-Tuned LLMs
and Rule-Based Baseline (ETHER) in FAERS Annotation.

Panels:
- Panel (a): Per-Category Performance of Instruction-Tuned LLMs (Claude 4.6 Sonnet vs. LLaMA 4)
             across all 17 fine-grained clinical concept categories + TOTAL on FAERS (N = 829).
- Panel (b): Fair Head-to-Head Comparison: ETHER vs. LLaMA 4 vs. Claude 4.6 Sonnet
             on combined core schemas (AE [AE+mAE], DRUG [sDrug+cDrug+oDrug+Treatment], DX, HX [MHx+FHx], and Shared TOTAL).
             Evaluated against full ground truth context to ensure strict cross-class consistency.
             Note: RO is excluded per reviewer feedback.

Standard Manuscript Color Palette:
- ETHER: Gray (#616161)
- LLaMA 4: Warm Pink close to red (#FF6F61)
- Claude Sonnet: Crimson Red (#C0392B)
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    results_dir = repo_root / "publication" / "results" / "manuscripts"
    figures_dir = results_dir / "Figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    manuscript_dir = repo_root / "publication" / "manuscripts"

    # Set matplotlib style
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Calibri", "DejaVu Sans", "Helvetica"]
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 0.9

    fig = plt.figure(figsize=(16, 10.5), dpi=300)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.2, 1.0], hspace=0.38)

    # -------------------------------------------------------------
    # Consistent Color Scheme
    # -------------------------------------------------------------
    c_ether = "#616161"        # Gray for ETHER
    c_llama = "#FF6F61"        # Warm Pink close to red for LLaMA 4
    c_sonnet = "#C0392B"       # Deep Red for Claude Sonnet

    # -------------------------------------------------------------
    # Panel (a): All 17 Categories + TOTAL for LLMs
    # -------------------------------------------------------------
    ax0 = fig.add_subplot(gs[0, 0])

    cats_17 = [
        "sDrug", "cDrug", "oDrug", "Dose", "Indication", "Treatment",
        "AE", "mAE", "Dx", "Lab", "Status", "R/O", "CoD",
        "MHx", "FHx", "Age", "Sex", "TOTAL"
    ]

    # Metrics computed directly across all 829 reports
    sonnet_f1_ade = [0.5620, 0.7137, 0.4848, 0.6835, 0.5195, 0.5355, 0.5678, 0.4576, 0.3709, 0.6107, 0.4548, 0.4545, 0.4690, 0.6891, 0.2130, 0.9241, 0.9379, 0.6062]
    sonnet_f1_strict = [0.4008, 0.5711, 0.0000, 0.4320, 0.1043, 0.3190, 0.4403, 0.0595, 0.0000, 0.3747, 0.2744, 0.0095, 0.0166, 0.4904, 0.1395, 0.8764, 0.8840, 0.4195]

    llama_f1_ade = [0.5465, 0.6021, 0.4807, 0.5790, 0.4914, 0.4649, 0.5635, 0.4607, 0.4020, 0.4916, 0.2676, 0.4444, 0.4614, 0.6124, 0.1736, 0.8593, 0.8578, 0.5517]
    llama_f1_strict = [0.3184, 0.3461, 0.0000, 0.2761, 0.0691, 0.1834, 0.3583, 0.0406, 0.0017, 0.1579, 0.1305, 0.0073, 0.0052, 0.3481, 0.0606, 0.7344, 0.7560, 0.2986]

    x = np.arange(len(cats_17))
    width = 0.38

    # Bars: ADE F1
    bars_s = ax0.bar(x - width/2, sonnet_f1_ade, width, label="Claude 4.6 Sonnet (Adapted F1)",
                     color=c_sonnet, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_l = ax0.bar(x + width/2, llama_f1_ade, width, label="Llama-4 (Adapted F1)",
                     color=c_llama, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)

    # Line/Point overlay for Strict F1
    ax0.plot(x - width/2, sonnet_f1_strict, color="#641E16", marker="o", markersize=5.5, linestyle="", label="Claude 4.6 Sonnet (Strict F1)", zorder=5)
    ax0.plot(x + width/2, llama_f1_strict, color="#922B21", marker="s", markersize=5.5, linestyle="", label="Llama-4 (Strict F1)", zorder=5)

    # Clean Value labels above bars
    for i in range(len(cats_17)):
        ax0.text(x[i] - width/2, sonnet_f1_ade[i] + 0.025, f"{sonnet_f1_ade[i]:.2f}", ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#641E16")
        ax0.text(x[i] + width/2, llama_f1_ade[i] + 0.025, f"{llama_f1_ade[i]:.2f}", ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#922B21")

    ax0.set_title("(a) Per-Category Performance of LLMs on FAERS Across All 17 Categories", fontsize=12.5, fontweight="bold", loc="left", pad=12)
    ax0.set_xticks(x)
    ax0.set_xticklabels(cats_17, fontsize=9.5, fontweight="bold", rotation=25)
    ax0.set_ylim(0, 1.18)
    ax0.set_ylabel("F1 Score", fontsize=11, fontweight="bold")
    ax0.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax0.legend(loc="upper left", bbox_to_anchor=(0.01, 0.98), fontsize=8.5, framealpha=0.95, ncol=2)

    # -------------------------------------------------------------
    # Panel (b): Fair Head-to-Head Comparison: ETHER vs. LLMs (Harmonized Ground Truth Context)
    # -------------------------------------------------------------
    ax1 = fig.add_subplot(gs[1, 0])

    shared_cats = [
        "AE\n(AE + mAE)",
        "DRUG\n(sDrug + cDrug + oDrug + Tx)",
        "DX",
        "HX\n(MHx + FHx)",
        "TOTAL"
    ]

    # Harmonized Fair Combined Metrics (Preserving Full Document Ground Truth Context for Partial Credit)
    ether_f1_ade = [0.3717, 0.5953, 0.4657, 0.2039, 0.4436]
    ether_f1_strict = [0.0409, 0.3551, 0.0004, 0.0624, 0.1467]

    llama_sh_ade = [0.5750, 0.6295, 0.4020, 0.6073, 0.5971]
    llama_sh_strict = [0.3624, 0.3808, 0.0017, 0.3467, 0.3597]

    sonnet_sh_ade = [0.5802, 0.6763, 0.3709, 0.6823, 0.6281]
    sonnet_sh_strict = [0.4497, 0.5184, 0.0000, 0.4867, 0.4726]

    x2 = np.arange(len(shared_cats))
    width2 = 0.26

    # Grouped Bars: Adapted ADE-Eval F1
    bars_e = ax1.bar(x2 - width2, ether_f1_ade, width2, label="ETHER", color=c_ether, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_l2 = ax1.bar(x2, llama_sh_ade, width2, label="Llama-4", color=c_llama, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_s2 = ax1.bar(x2 + width2, sonnet_sh_ade, width2, label="Claude 4.6 Sonnet", color=c_sonnet, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)

    # Point Overlays for Strict Exact-Match F1
    ax1.plot(x2 - width2, ether_f1_strict, color="#212121", marker="D", markersize=6, linestyle="", label="Strict F1 (◆)", zorder=5)
    ax1.plot(x2, llama_sh_strict, color="#922B21", marker="s", markersize=6, linestyle="", label="Strict F1 (■)", zorder=5)
    ax1.plot(x2 + width2, sonnet_sh_strict, color="#641E16", marker="o", markersize=6, linestyle="", label="Strict F1 (●)", zorder=5)

    # Clean Value labels above bars
    for i in range(len(shared_cats)):
        ax1.text(x2[i] - width2, ether_f1_ade[i] + 0.025, f"{ether_f1_ade[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#212121")
        ax1.text(x2[i], llama_sh_ade[i] + 0.025, f"{llama_sh_ade[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#922B21")
        ax1.text(x2[i] + width2, sonnet_sh_ade[i] + 0.025, f"{sonnet_sh_ade[i]:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#641E16")

    ax1.set_title("(b) Head-to-Head Comparison: Rule-Based Baseline (ETHER) vs. LLMs on Combined Schema", fontsize=12.5, fontweight="bold", loc="left", pad=12)
    ax1.set_xticks(x2)
    ax1.set_xticklabels(shared_cats, fontsize=10, fontweight="bold")
    ax1.set_ylim(0, 1.05)
    ax1.set_ylabel("F1 Score", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Category (Adapted to ETHER)", fontsize=11, fontweight="bold", labelpad=8)
    ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    # Custom legend for panel b
    custom_handles = [
        mpatches.Patch(facecolor=c_ether, edgecolor="#111", label="ETHER (Adapted F1)"),
        mpatches.Patch(facecolor=c_llama, edgecolor="#111", label="Llama-4 (Adapted F1)"),
        mpatches.Patch(facecolor=c_sonnet, edgecolor="#111", label="Claude 4.6 Sonnet (Adapted F1)"),
        plt.Line2D([0], [0], color="#212121", marker="D", linestyle="", markersize=6, label="ETHER F1"),
        plt.Line2D([0], [0], color="#922B21", marker="s", linestyle="", markersize=6, label="Llama-4 F1"),
        plt.Line2D([0], [0], color="#641E16", marker="o", linestyle="", markersize=6, label="Claude Sonnet F1"),
    ]
    ax1.legend(handles=custom_handles, loc="upper left", bbox_to_anchor=(0.01, 0.98), fontsize=8.5, framealpha=0.95, ncol=3)

    out_fig_path = figures_dir / "figure3.png"
    out_manuscript_fig = manuscript_dir / "figure3.png"

    plt.savefig(out_fig_path, dpi=300, bbox_inches="tight")
    plt.savefig(out_manuscript_fig, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Figure 3 (Fully Harmonized Dx & Fair Combined Schema) successfully saved")


if __name__ == "__main__":
    main()
