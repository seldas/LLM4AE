#!/usr/bin/env python3
"""Generate Figure 6 directly from the current VAERS raw result workbooks.

The figure compares BERT (10-fold cross-validation, pooled test predictions for
one seed) with LLaMA-4 on the full VAERS benchmark. No plotted result is
hard-coded. Wrong-label predictions that overlap missed gold spans are paired
one-to-one and represented as class errors, matching Table 6's Two-Tier
evaluation logic.

Default output:
    publication/manuscripts/Figures/figure6.png
"""

from __future__ import annotations

import argparse
import math
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


MATCH_TYPES = frozenset({"M", "C", "S", "N"})
EXPECTED_FOLDS = tuple(range(10))
BERT_FILENAME = re.compile(r"fold_(\d{2})_seed_(\d+)_raw\.xlsx$")
CATEGORY_ORDER = (
    "vax", "tx", "status", "mhx", "sdx", "pdx",
    "sym", "lab", "fhx", "cod", "ro",
)
CATEGORY_DISPLAY = {
    "vax": "VAX", "tx": "TX", "status": "STATUS", "mhx": "MHx",
    "sdx": "sDx", "pdx": "pDx", "sym": "SYM", "lab": "Lab",
    "fhx": "FHx", "cod": "CoD", "ro": "R/O",
}


@dataclass
class CategoryCounts:
    exact: int = 0
    boundary: int = 0
    wrong_gold: int = 0
    wrong_pred: int = 0
    spurious: int = 0
    missed: int = 0


@dataclass(frozen=True)
class Metrics:
    precision: float
    recall: float
    f1: float


@dataclass
class Evaluation:
    counts: Counter[str]
    strict: Metrics
    adapted: Metrics
    per_category: dict[str, Metrics]
    confusions: Counter[tuple[str, str]]
    correction_count: int
    gold_total: int
    prediction_total: int


def canonical_label(value: object) -> str:
    if pd.isna(value):
        return ""
    label = str(value).strip().casefold()
    return "ro" if label == "r/o" else label


def display_label(label: str) -> str:
    return CATEGORY_DISPLAY.get(label, label.upper())


def harmonic_mean(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def spans_overlap(a0: object, a1: object, b0: object, b1: object) -> bool:
    if any(pd.isna(value) for value in (a0, a1, b0, b1)):
        return False
    return max(int(a0), int(b0)) < min(int(a1), int(b1))


def span_iou(a0: object, a1: object, b0: object, b1: object) -> float:
    a_start, a_end, b_start, b_end = int(a0), int(a1), int(b0), int(b1)
    intersection = max(0, min(a_end, b_end) - max(a_start, b_start))
    union = max(a_end, b_end) - min(a_start, b_start)
    return intersection / union if union else 0.0


def match_wrong_label_pairs(group: pd.DataFrame) -> list[tuple[int, int]]:
    """Return maximum-cardinality (gold N index, prediction S index) pairs."""
    gold_indices = sorted(
        (int(index) for index in group.index[group["match_type"] == "N"]),
        key=lambda index: (
            int(group.at[index, "gold_start"])
            if pd.notna(group.at[index, "gold_start"])
            else math.inf,
            int(group.at[index, "gold_end"])
            if pd.notna(group.at[index, "gold_end"])
            else math.inf,
            canonical_label(group.at[index, "label_gold"]),
            index,
        ),
    )
    pred_indices = [int(index) for index in group.index[group["match_type"] == "S"]]
    edges: dict[int, list[int]] = {}
    for gold_index in gold_indices:
        gold_label = canonical_label(group.at[gold_index, "label_gold"])
        candidates = []
        for pred_index in pred_indices:
            pred_label = canonical_label(group.at[pred_index, "label_pred"])
            if not gold_label or not pred_label or gold_label == pred_label:
                continue
            if spans_overlap(
                group.at[gold_index, "gold_start"], group.at[gold_index, "gold_end"],
                group.at[pred_index, "pred_start"], group.at[pred_index, "pred_end"],
            ):
                candidates.append(pred_index)
        candidates.sort(
            key=lambda pred_index: (
                -span_iou(
                    group.at[gold_index, "gold_start"], group.at[gold_index, "gold_end"],
                    group.at[pred_index, "pred_start"], group.at[pred_index, "pred_end"],
                ),
                int(group.at[pred_index, "pred_start"]),
                int(group.at[pred_index, "pred_end"]),
                canonical_label(group.at[pred_index, "label_pred"]),
                pred_index,
            )
        )
        edges[gold_index] = candidates

    pred_to_gold: dict[int, int] = {}

    def augment(gold_index: int, visited: set[int]) -> bool:
        for pred_index in edges.get(gold_index, []):
            if pred_index in visited:
                continue
            visited.add(pred_index)
            previous_gold = pred_to_gold.get(pred_index)
            if previous_gold is None or augment(previous_gold, visited):
                pred_to_gold[pred_index] = gold_index
                return True
        return False

    for gold_index in gold_indices:
        augment(gold_index, set())
    return sorted((gold_index, pred_index) for pred_index, gold_index in pred_to_gold.items())


def overall_metrics(counts: Counter[str]) -> tuple[Metrics, Metrics]:
    exact, class_error = counts["M"], counts["C"]
    spurious, missed = counts["S"], counts["N"]
    strict_precision = exact / (exact + class_error + spurious)
    strict_recall = exact / (exact + class_error + missed)
    strict = Metrics(
        strict_precision, strict_recall, harmonic_mean(strict_precision, strict_recall)
    )
    credit = exact + 0.5 * class_error
    adapted_precision = credit / (exact + class_error + 0.25 * spurious)
    adapted_recall = credit / (exact + class_error + missed)
    adapted = Metrics(
        adapted_precision, adapted_recall,
        harmonic_mean(adapted_precision, adapted_recall),
    )
    return strict, adapted


def category_metrics(counts: CategoryCounts) -> Metrics:
    """Calculate label-level Adapted ADE-Eval precision, recall, and F1."""
    precision_credit = counts.exact + 0.5 * (counts.boundary + counts.wrong_pred)
    precision_denominator = (
        counts.exact + counts.boundary + counts.wrong_pred + 0.25 * counts.spurious
    )
    recall_credit = counts.exact + 0.5 * (counts.boundary + counts.wrong_gold)
    recall_denominator = counts.exact + counts.boundary + counts.wrong_gold + counts.missed
    precision = precision_credit / precision_denominator if precision_denominator else 0.0
    recall = recall_credit / recall_denominator if recall_denominator else 0.0
    return Metrics(precision, recall, harmonic_mean(precision, recall))


def evaluate(frame: pd.DataFrame, group_column: str) -> Evaluation:
    required = {
        group_column, "match_type", "label_gold", "gold_start", "gold_end",
        "label_pred", "pred_start", "pred_end",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Raw results are missing columns: {sorted(missing)}")
    unknown = set(frame["match_type"].dropna().unique()).difference(MATCH_TYPES)
    if unknown:
        raise ValueError(f"Unknown match types: {sorted(unknown)}")

    frame = frame.reset_index(drop=True)
    pairs = []
    for _, group in frame.groupby(group_column, sort=False, dropna=False):
        pairs.extend(match_wrong_label_pairs(group))
    matched_gold = {gold_index for gold_index, _ in pairs}
    matched_pred = {pred_index for _, pred_index in pairs}

    corrected_counts: Counter[str] = Counter(frame["match_type"])
    corrected_counts["C"] += len(pairs)
    corrected_counts["S"] -= len(pairs)
    corrected_counts["N"] -= len(pairs)
    categories: defaultdict[str, CategoryCounts] = defaultdict(CategoryCounts)
    confusions: Counter[tuple[str, str]] = Counter()

    for index, row in frame.iterrows():
        match_type = row["match_type"]
        gold_label = canonical_label(row["label_gold"])
        pred_label = canonical_label(row["label_pred"])
        if match_type == "M":
            categories[gold_label].exact += 1
        elif match_type == "C":
            if gold_label == pred_label:
                categories[gold_label].boundary += 1
            else:
                categories[gold_label].wrong_gold += 1
                categories[pred_label].wrong_pred += 1
                confusions[(gold_label, pred_label)] += 1
        elif match_type == "N" and index not in matched_gold:
            categories[gold_label].missed += 1
        elif match_type == "S" and index not in matched_pred:
            categories[pred_label].spurious += 1

    for gold_index, pred_index in pairs:
        gold_label = canonical_label(frame.at[gold_index, "label_gold"])
        pred_label = canonical_label(frame.at[pred_index, "label_pred"])
        categories[gold_label].wrong_gold += 1
        categories[pred_label].wrong_pred += 1
        confusions[(gold_label, pred_label)] += 1

    observed_labels = set(categories).difference({""})
    unexpected_labels = observed_labels.difference(CATEGORY_ORDER)
    if unexpected_labels:
        raise ValueError(f"Unexpected VAERS labels: {sorted(unexpected_labels)}")

    strict, adapted = overall_metrics(corrected_counts)
    prediction_total = sum(bool(canonical_label(value)) for value in frame["label_pred"])
    gold_total = sum(bool(canonical_label(value)) for value in frame["label_gold"])
    if corrected_counts["M"] + corrected_counts["C"] + corrected_counts["S"] != prediction_total:
        raise ValueError("Corrected M+C+S does not equal the prediction total")
    if corrected_counts["M"] + corrected_counts["C"] + corrected_counts["N"] != gold_total:
        raise ValueError("Corrected M+C+N does not equal the gold total")

    return Evaluation(
        counts=corrected_counts,
        strict=strict,
        adapted=adapted,
        per_category={label: category_metrics(categories[label]) for label in CATEGORY_ORDER},
        confusions=confusions,
        correction_count=len(pairs),
        gold_total=gold_total,
        prediction_total=prediction_total,
    )


def load_bert(raw_dir: Path, seed: int) -> pd.DataFrame:
    paths: dict[int, Path] = {}
    for path in raw_dir.glob(f"fold_*_seed_{seed}_raw.xlsx"):
        match = BERT_FILENAME.fullmatch(path.name)
        if match and int(match.group(2)) == seed:
            paths[int(match.group(1))] = path
    if set(paths) != set(EXPECTED_FOLDS):
        raise ValueError(
            f"Expected BERT folds {EXPECTED_FOLDS} for seed {seed}; found {sorted(paths)}"
        )

    columns = [
        "fold", "seed", "sent_id", "match_type", "label_gold", "gold_start",
        "gold_end", "label_pred", "pred_start", "pred_end",
    ]
    frames = []
    for fold in EXPECTED_FOLDS:
        frame = pd.read_excel(paths[fold], sheet_name="Raw_Results", usecols=columns)
        if set(frame["fold"].dropna().astype(int).unique()) != {fold}:
            raise ValueError(f"Fold metadata mismatch in {paths[fold]}")
        if set(frame["seed"].dropna().astype(int).unique()) != {seed}:
            raise ValueError(f"Seed metadata mismatch in {paths[fold]}")
        frame["evaluation_group"] = frame["fold"].astype(str) + ":" + frame["sent_id"].astype(str)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def load_llama(raw_path: Path) -> pd.DataFrame:
    if not raw_path.is_file():
        raise FileNotFoundError(f"LLaMA-4 raw workbook not found: {raw_path}")
    columns = [
        "document", "match_type", "label_gold", "gold_start", "gold_end",
        "label_pred", "pred_start", "pred_end",
    ]
    return pd.read_excel(raw_path, sheet_name="Raw_Results", usecols=columns)


def load_database_gold_counts(database_path: Path) -> Counter[str]:
    """Load the authoritative VAERS SME1 annotation counts used by Table 4."""
    if not database_path.is_file():
        raise FileNotFoundError(f"Database not found: {database_path}")
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT lower(trim(a.label)), count(*)
            FROM annotations AS a
            JOIN documents AS d ON d.doc_id = a.doc_id
            WHERE d.dataset = 'VAERS' AND a.note = 'SME1'
            GROUP BY lower(trim(a.label))
            """
        ).fetchall()
    counts = Counter({canonical_label(label): int(count) for label, count in rows})
    unexpected = set(counts).difference(CATEGORY_ORDER)
    if unexpected:
        raise ValueError(f"Unexpected VAERS database labels: {sorted(unexpected)}")
    return counts


def reconcile_llama_gold(
    frame: pd.DataFrame,
    database_gold: Counter[str],
) -> tuple[pd.DataFrame, Counter[str]]:
    """Add database-only gold annotations as misses.

    The LLaMA raw workbook contains all predictions but is short of the current
    Table 4 gold counts in a few categories. Because these annotations have no
    aligned outcome in the raw workbook, their conservative evaluation outcome
    is N (miss). This preserves every raw match and prediction while making the
    Figure 6 gold accounting exactly equal to the authoritative database.
    """
    raw_gold = Counter(
        canonical_label(label)
        for label in frame.loc[frame["label_gold"].notna(), "label_gold"]
    )
    excess = raw_gold - database_gold
    if excess:
        raise ValueError(
            "LLaMA raw gold exceeds the database for categories: "
            f"{dict(sorted(excess.items()))}"
        )
    missing = database_gold - raw_gold
    additions = []
    for label in CATEGORY_ORDER:
        for index in range(missing[label]):
            additions.append(
                {
                    "document": f"__database_only__{label}_{index}",
                    "match_type": "N",
                    "label_gold": label,
                    # Sentinel offsets are never matched because this unique
                    # group contains no prediction rows.
                    "gold_start": -1,
                    "gold_end": -1,
                    "label_pred": "",
                    "pred_start": -1,
                    "pred_end": -1,
                }
            )
    if additions:
        frame = pd.concat([frame, pd.DataFrame(additions)], ignore_index=True)
    return frame, missing


def add_bar_labels(axis: plt.Axes, bars, values: list[float], color: str) -> None:
    for bar, value in zip(bars, values):
        if value <= 0:
            continue
        inside = value >= 0.72
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value - 0.055 if inside else value + 0.015,
            f"{value:.2f}",
            ha="center", va="top" if inside else "bottom",
            fontsize=7.5, fontweight="bold",
            color="white" if inside else color,
        )


def top_confusions(evaluation: Evaluation, limit: int = 8) -> list[tuple[str, int]]:
    rows = [
        (f"{display_label(gold)} → {display_label(pred)}", count)
        for (gold, pred), count in evaluation.confusions.most_common(limit)
    ]
    return list(reversed(rows))


def plot_figure(bert: Evaluation, llama: Evaluation, output_path: Path, seed: int) -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Calibri", "DejaVu Sans", "Helvetica"],
        "axes.edgecolor": "#333333", "axes.linewidth": 0.9,
    })
    bert_color, llama_color = "#1F77B4", "#FF6F61"
    bert_dark, llama_dark = "#0B3C5D", "#922B21"
    fig, ((ax_a, ax_b), (ax_c, ax_d)) = plt.subplots(
        2, 2, figsize=(17, 12), dpi=300, constrained_layout=True
    )

    labels = [CATEGORY_DISPLAY[label] for label in CATEGORY_ORDER] + ["TOTAL"]
    bert_metrics = [bert.per_category[label] for label in CATEGORY_ORDER] + [bert.adapted]
    llama_metrics = [llama.per_category[label] for label in CATEGORY_ORDER] + [llama.adapted]
    bert_f1 = [metric.f1 for metric in bert_metrics]
    llama_f1 = [metric.f1 for metric in llama_metrics]
    x = np.arange(len(labels))
    width = 0.38
    bert_bars = ax_a.bar(
        x - width / 2, bert_f1, width, color=bert_color, edgecolor="#111111",
        linewidth=0.6, label="BERT adapted F1", zorder=2,
    )
    llama_bars = ax_a.bar(
        x + width / 2, llama_f1, width, color=llama_color, edgecolor="#111111",
        linewidth=0.6, label="LLaMA-4 adapted F1", zorder=2,
    )
    for offset, metrics, color, model in (
        (-width / 2, bert_metrics, bert_dark, "BERT"),
        (width / 2, llama_metrics, llama_dark, "LLaMA-4"),
    ):
        ax_a.plot(
            x + offset, [metric.recall for metric in metrics], color=color,
            marker="o", markersize=4, linestyle="--", linewidth=1,
            label=f"{model} recall", zorder=4,
        )
        ax_a.plot(
            x + offset, [metric.precision for metric in metrics], color=color,
            marker="s", markersize=4, linestyle=":", linewidth=1,
            label=f"{model} precision", zorder=4,
        )
    add_bar_labels(ax_a, bert_bars, bert_f1, bert_dark)
    add_bar_labels(ax_a, llama_bars, llama_f1, llama_dark)
    ax_a.set_title(
        f"(a) Adapted ADE-Eval Performance by VAERS Category (BERT seed {seed})",
        fontsize=11.5, fontweight="bold", loc="left",
    )
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(labels, fontsize=8.5, fontweight="bold", rotation=25, ha="right")
    ax_a.set_ylim(0, 1.12)
    ax_a.set_ylabel("Score", fontsize=10, fontweight="bold")
    ax_a.set_xlabel("Entity category", fontsize=10, fontweight="bold")
    ax_a.grid(axis="y", linestyle="--", alpha=0.3, zorder=0)
    ax_a.legend(loc="upper right", fontsize=7.5, ncol=3, framealpha=0.95)

    codes = ["M", "C", "S", "N"]
    error_labels = [
        "M: exact match", "C: partial/class error",
        "S: spurious (FP)", "N: miss (FN)",
    ]
    bert_total = sum(bert.counts[code] for code in codes)
    llama_total = sum(llama.counts[code] for code in codes)
    bert_pct = [100 * bert.counts[code] / bert_total for code in codes]
    llama_pct = [100 * llama.counts[code] / llama_total for code in codes]
    x_error = np.arange(len(codes))
    error_width = 0.35
    ax_b.bar(
        x_error - error_width / 2, bert_pct, error_width, color=bert_color,
        edgecolor="#111111", linewidth=0.6, label="BERT", zorder=2,
    )
    ax_b.bar(
        x_error + error_width / 2, llama_pct, error_width, color=llama_color,
        edgecolor="#111111", linewidth=0.6, label="LLaMA-4", zorder=2,
    )
    for index, code in enumerate(codes):
        for offset, evaluation, pct, color in (
            (-error_width / 2, bert, bert_pct, bert_dark),
            (error_width / 2, llama, llama_pct, llama_dark),
        ):
            ax_b.text(
                x_error[index] + offset, pct[index] + 0.8,
                f"{evaluation.counts[code]:,}\n({pct[index]:.1f}%)",
                ha="center", va="bottom", fontsize=8,
                fontweight="bold", color=color,
            )
    ax_b.set_title(
        "(b) Corrected M/C/S/N Distribution on the Full VAERS Benchmark",
        fontsize=11.5, fontweight="bold", loc="left",
    )
    ax_b.set_xticks(x_error)
    ax_b.set_xticklabels(error_labels, fontsize=9, fontweight="bold")
    ax_b.set_ylim(0, max(bert_pct + llama_pct) * 1.25)
    ax_b.set_ylabel("Proportion of outcomes (%)", fontsize=10, fontweight="bold")
    ax_b.set_xlabel("Outcome type", fontsize=10, fontweight="bold")
    ax_b.grid(axis="y", linestyle="--", alpha=0.3, zorder=0)
    ax_b.legend(loc="upper right", fontsize=9, framealpha=0.95)

    bert_top, llama_top = top_confusions(bert), top_confusions(llama)
    common_max = max([value for _, value in bert_top + llama_top], default=1)
    x_limit = max(10, math.ceil(common_max * 1.15 / 100) * 100)
    for axis, rows, color, dark, title in (
        (ax_c, bert_top, bert_color, bert_dark, "(c) BERT: Top VAERS Label Misclassifications"),
        (ax_d, llama_top, llama_color, llama_dark, "(d) LLaMA-4: Top VAERS Label Misclassifications"),
    ):
        pair_labels = [label for label, _ in rows]
        values = [value for _, value in rows]
        y = np.arange(len(rows))
        axis.barh(
            y, values, height=0.62, color=color, edgecolor="#111111",
            linewidth=0.6, zorder=2,
        )
        for y_value, value in zip(y, values):
            axis.text(
                value + x_limit * 0.01, y_value, f"{value:,}",
                va="center", ha="left", fontsize=8.5,
                fontweight="bold", color=dark,
            )
        axis.set_title(title, fontsize=11.5, fontweight="bold", loc="left")
        axis.set_yticks(y)
        axis.set_yticklabels(pair_labels, fontsize=9, fontweight="bold")
        axis.set_xlim(0, x_limit)
        axis.set_xlabel("Number of one-to-one class-error pairs", fontsize=10, fontweight="bold")
        axis.set_ylabel("Gold → predicted", fontsize=10, fontweight="bold")
        axis.grid(axis="x", linestyle="--", alpha=0.3, zorder=0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="BERT seed to plot (default: 42).")
    parser.add_argument(
        "--bert-raw-dir", type=Path,
        default=repo_root / "publication" / "results" / "bert_runs_VAERS",
        help="Directory containing BERT VAERS fold-level raw workbooks.",
    )
    parser.add_argument(
        "--llama-raw", type=Path,
        default=repo_root / "publication" / "results" / "llama4_runs_VAERS" / "llama4_raw.xlsx",
        help="LLaMA-4 VAERS raw workbook.",
    )
    parser.add_argument(
        "--database", type=Path,
        default=repo_root / "publication" / "dataset.db",
        help="Canonical database containing VAERS SME1 gold annotations.",
    )
    parser.add_argument(
        "--output", type=Path,
        default=repo_root / "publication" / "manuscripts" / "Figures" / "figure6.png",
        help="Output PNG path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bert = evaluate(load_bert(args.bert_raw_dir.resolve(), args.seed), "evaluation_group")
    llama_frame = load_llama(args.llama_raw.resolve())
    database_gold = load_database_gold_counts(args.database.resolve())
    llama_frame, database_only_gold = reconcile_llama_gold(llama_frame, database_gold)
    llama = evaluate(llama_frame, "document")
    output_path = args.output.resolve()
    plot_figure(bert, llama, output_path, args.seed)

    print(f"Created {output_path}")
    print(
        f"BERT seed {args.seed}: M/C/S/N="
        f"{bert.counts['M']:,}/{bert.counts['C']:,}/{bert.counts['S']:,}/{bert.counts['N']:,}; "
        f"Strict F1={bert.strict.f1:.4f}; Adapted F1={bert.adapted.f1:.4f}; "
        f"wrong-label corrections={bert.correction_count:,}"
    )
    print(
        "LLaMA-4: M/C/S/N="
        f"{llama.counts['M']:,}/{llama.counts['C']:,}/{llama.counts['S']:,}/{llama.counts['N']:,}; "
        f"Strict F1={llama.strict.f1:.4f}; Adapted F1={llama.adapted.f1:.4f}; "
        f"wrong-label corrections={llama.correction_count:,}"
    )
    print(
        "LLaMA-4 database-only gold added as N: "
        f"{sum(database_only_gold.values()):,} "
        f"{dict((display_label(label), database_only_gold[label]) for label in CATEGORY_ORDER if database_only_gold[label])}"
    )
    print(
        f"Conservation checks: BERT gold/pred={bert.gold_total:,}/{bert.prediction_total:,}; "
        f"LLaMA-4 gold/pred={llama.gold_total:,}/{llama.prediction_total:,}"
    )


if __name__ == "__main__":
    main()
