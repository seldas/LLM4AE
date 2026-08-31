#!/usr/bin/env python3
"""
generate_figure4.py

Generates publication-ready Figure 4: Comparative Concept Extraction Performance on FAERS (N = 829 Reports)
Across All 17 Clinical Concept Categories:
Fine-Tuned BioBERT vs. Instruction-Tuned LLMs (Claude 4.6 Sonnet & LLaMA 4).

Single unified figure layout (similar to Figure 3a):
- Grouped Bars: Secondary Tier (Adapted ADE-Eval Clinical Weighted F1)
- Point/Shape Overlays: Primary Tier (Strict Exact-Match NER F1)

Standard Manuscript Color Palette:
- BioBERT: Steel Blue (#1F77B4)
- Claude Sonnet: Crimson Red (#C0392B)
- LLaMA 4: Warm Pink close to red (#FF6F61)
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

    # Set matplotlib style
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Calibri", "DejaVu Sans", "Helvetica"]
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 0.9

    fig, ax = plt.subplots(figsize=(16.5, 7.8), dpi=300)

    # 17 Categories + OVERALL
    cats_17 = [
        "sDrug", "cDrug", "oDrug", "Dose", "Indication", "Treatment",
        "AE", "mAE", "Dx", "Lab", "Status", "R/O", "CoD",
        "MHx", "FHx", "Age", "Sex", "OVERALL"
    ]

    # Model Performance across all 17 categories on FAERS (N = 829)
    # BioBERT
    bert_ade = [0.7376, 0.8451, 0.0000, 0.7427, 0.5021, 0.7775, 0.7066, 0.0507, 0.4536, 0.7637, 0.8386, 0.0000, 0.0000, 0.7138, 0.0818, 0.9525, 0.9570, 0.7477]
    bert_strict = [0.6025, 0.7433, 0.0000, 0.6100, 0.1335, 0.6260, 0.5931, 0.0480, 0.0670, 0.5964, 0.7169, 0.0000, 0.0000, 0.4621, 0.0727, 0.9009, 0.9037, 0.6032]

    # Claude 4.6 Sonnet
    sonnet_ade = [0.5619, 0.7130, 0.4848, 0.6826, 0.5194, 0.5355, 0.5678, 0.4574, 0.3704, 0.6105, 0.4547, 0.4539, 0.4686, 0.6888, 0.2130, 0.9238, 0.9376, 0.6060]
    sonnet_strict = [0.4006, 0.5689, 0.0000, 0.4300, 0.1042, 0.3189, 0.4401, 0.0594, 0.0000, 0.3742, 0.2741, 0.0094, 0.0165, 0.4896, 0.1395, 0.8752, 0.8829, 0.4189]

    # LLaMA 4
    llama_ade = [0.5463, 0.6013, 0.4804, 0.5783, 0.4913, 0.4647, 0.5635, 0.4604, 0.4016, 0.4912, 0.2676, 0.4444, 0.4610, 0.6121, 0.1736, 0.8590, 0.8575, 0.5515]
    llama_strict = [0.3181, 0.3443, 0.0000, 0.2752, 0.0690, 0.1832, 0.3582, 0.0405, 0.0016, 0.1575, 0.1304, 0.0073, 0.0052, 0.3474, 0.0606, 0.7335, 0.7551, 0.2982]

    x = np.arange(len(cats_17))
    width = 0.27

    # Colors
    c_bert = "#1F77B4"       # Strong Blue for BioBERT
    c_sonnet = "#C0392B"     # Deep Crimson Red for Claude Sonnet
    c_llama = "#FF6F61"      # Warm Pink close to red for LLaMA 4

    # Grouped Bars: Adapted ADE-Eval F1
    bars_b = ax.bar(x - width, bert_ade, width, label="BioBERT (Adapted ADE-Eval F1)",
                    color=c_bert, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_s = ax.bar(x, sonnet_ade, width, label="Claude 4.6 Sonnet (Adapted ADE-Eval F1)",
                    color=c_sonnet, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)
    bars_l = ax.bar(x + width, llama_ade, width, label="LLaMA 4 (Adapted ADE-Eval F1)",
                    color=c_llama, alpha=0.92, edgecolor="#111111", linewidth=0.7, zorder=2)

    # Point Overlays: Strict Exact-Match F1
    ax.plot(x - width, bert_strict, color="#0B3C5D", marker="D", markersize=6, linestyle="", label="BioBERT (Strict Exact F1, ◆)", zorder=5)
    ax.plot(x, sonnet_strict, color="#641E16", marker="o", markersize=6, linestyle="", label="Claude Sonnet (Strict Exact F1, ●)", zorder=5)
    ax.plot(x + width, llama_strict, color="#922B21", marker="s", markersize=6, linestyle="", label="LLaMA 4 (Strict Exact F1, ■)", zorder=5)

    # Clean Value Labels above bars
    for i in range(len(cats_17)):
        if bert_ade[i] > 0.02:
            ax.text(x[i] - width, bert_ade[i] + 0.02, f"{bert_ade[i]:.2f}", ha="center", va="bottom", fontsize=7.2, fontweight="bold", color="#0B3C5D")
        if sonnet_ade[i] > 0.02:
            ax.text(x[i], sonnet_ade[i] + 0.02, f"{sonnet_ade[i]:.2f}", ha="center", va="bottom", fontsize=7.2, fontweight="bold", color="#641E16")
        if llama_ade[i] > 0.02:
            ax.text(x[i] + width, llama_ade[i] + 0.02, f"{llama_ade[i]:.2f}", ha="center", va="bottom", fontsize=7.2, fontweight="bold", color="#922B21")

    ax.set_title("Comparative Concept Extraction Performance across All 17 Clinical Concept Categories on FAERS (N = 829 Reports)\nFine-Tuned Encoder (BioBERT) vs. Instruction-Tuned LLMs (Claude 4.6 Sonnet & LLaMA 4)",
                 fontsize=13, fontweight="bold", loc="left", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(cats_17, fontsize=10, fontweight="bold", rotation=25)
    ax.set_ylim(0, 1.22)
    ax.set_ylabel("F1 Score", fontsize=11.5, fontweight="bold")
    ax.set_xlabel("Clinical Concept Category", fontsize=11.5, fontweight="bold", labelpad=8)
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    # Legend with clear grouping
    custom_handles = [
        mpatches.Patch(facecolor=c_bert, edgecolor="#111", label="BioBERT (Adapted ADE F1)"),
        mpatches.Patch(facecolor=c_sonnet, edgecolor="#111", label="Claude 4.6 Sonnet (Adapted ADE F1)"),
        mpatches.Patch(facecolor=c_llama, edgecolor="#111", label="LLaMA 4 (Adapted ADE F1)"),
        plt.Line2D([0], [0], color="#0B3C5D", marker="D", linestyle="", markersize=6, label="BioBERT Strict F1"),
        plt.Line2D([0], [0], color="#641E16", marker="o", linestyle="", markersize=6, label="Claude Sonnet Strict F1"),
        plt.Line2D([0], [0], color="#922B21", marker="s", linestyle="", markersize=6, label="LLaMA 4 Strict F1"),
    ]
    ax.legend(handles=custom_handles, loc="upper left", bbox_to_anchor=(0.01, 0.98), fontsize=9, framealpha=0.95, ncol=3)

    plt.tight_layout()

    out_fig_path = figures_dir / "figure4.png"
    out_manuscript_fig = manuscript_dir / "figure4.png"
    out_docx_img = manuscript_dir / "extracted_images" / "image_03.png"

    plt.savefig(out_fig_path, dpi=300, bbox_inches="tight")
    plt.savefig(out_manuscript_fig, dpi=300, bbox_inches="tight")
    plt.savefig(out_docx_img, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Figure 4 (17 Categories BioBERT vs. LLMs) successfully generated and saved to:\n  - {out_fig_path}\n  - {out_manuscript_fig}\n  - {out_docx_img}")


if __name__ == "__main__":
    main()
