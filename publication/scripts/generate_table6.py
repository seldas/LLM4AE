#!/usr/bin/env python3
"""Generate manuscript Table 6 from current BERT raw result workbooks.

Every displayed value is calculated at runtime from the permitted canonical
sources under ``publication/results``:

* FAERS: ``bert_runs_FAERS_LOO/raw.xlsx`` (four held-out case-series folds)
* VAERS: ``bert_runs_VAERS/fold_XX_seed_YYYY_raw.xlsx`` (ten folds per seed)

Default output:
    publication/manuscripts/Tables/table6_bert_seed_reproducibility.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


SEEDS = (42, 123, 456, 789, 1011)
FAERS_FOLDS = (
    "Azacitidine-QT",
    "Baricitinib-Hypersensitivity",
    "Tramadol-Hypoglycemia",
    "Erenumab-Stroke",
)
VAERS_FOLDS = tuple(range(10))
MATCH_TYPES = frozenset({"M", "C", "S", "N"})
VAERS_FILENAME = re.compile(r"fold_(\d{2})_seed_(\d+)_raw\.xlsx$")


@dataclass(frozen=True)
class Scores:
    strict_f1: float
    adapted_f1: float


@dataclass(frozen=True)
class Summary:
    strict_mean: float
    strict_sd: float
    adapted_mean: float
    adapted_sd: float


def score_counts(counts: Counter[str]) -> Scores:
    """Apply the manuscript's Strict Exact and Adapted ADE-Eval formulas."""
    exact = int(counts["M"])
    class_error = int(counts["C"])
    spurious = int(counts["S"])
    missed = int(counts["N"])

    strict_precision = (
        exact / (exact + class_error + spurious)
        if exact + class_error + spurious
        else 0.0
    )
    strict_recall = (
        exact / (exact + class_error + missed)
        if exact + class_error + missed
        else 0.0
    )
    strict_f1 = harmonic_mean(strict_precision, strict_recall)

    adapted_matches = exact + 0.5 * class_error
    adapted_precision = (
        adapted_matches / (exact + class_error + 0.25 * spurious)
        if exact + class_error + 0.25 * spurious
        else 0.0
    )
    adapted_recall = (
        adapted_matches / (exact + class_error + missed)
        if exact + class_error + missed
        else 0.0
    )
    return Scores(
        strict_f1=strict_f1,
        adapted_f1=harmonic_mean(adapted_precision, adapted_recall),
    )


def harmonic_mean(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def summarize(scores: list[Scores]) -> Summary:
    if len(scores) < 2:
        raise ValueError("At least two scores are required to calculate sample SD")
    strict = [score.strict_f1 for score in scores]
    adapted = [score.adapted_f1 for score in scores]
    return Summary(
        strict_mean=statistics.mean(strict),
        strict_sd=statistics.stdev(strict),
        adapted_mean=statistics.mean(adapted),
        adapted_sd=statistics.stdev(adapted),
    )


def validate_match_types(frame: pd.DataFrame, source: Path) -> None:
    observed = set(frame["match_type"].dropna().astype(str).unique())
    unknown = observed.difference(MATCH_TYPES)
    if unknown:
        raise ValueError(f"{source} has unknown match types: {sorted(unknown)}")


def load_faers_scores(raw_path: Path) -> dict[int, Scores]:
    """Pool the four current LOO folds within each FAERS seed (micro F1)."""
    if not raw_path.is_file():
        raise FileNotFoundError(f"FAERS raw workbook not found: {raw_path}")
    frame = pd.read_excel(
        raw_path,
        sheet_name="Raw_Results",
        usecols=["fold_name", "seed", "match_type"],
    )
    validate_match_types(frame, raw_path)
    actual_folds = set(frame["fold_name"].dropna().astype(str).unique())
    if actual_folds != set(FAERS_FOLDS):
        raise ValueError(
            f"Unexpected FAERS folds: expected {sorted(FAERS_FOLDS)}, "
            f"found {sorted(actual_folds)}"
        )
    actual_seeds = tuple(sorted(int(value) for value in frame["seed"].unique()))
    if actual_seeds != tuple(sorted(SEEDS)):
        raise ValueError(f"Expected FAERS seeds {SEEDS}; found {actual_seeds}")

    results: dict[int, Scores] = {}
    for seed, group in frame.groupby("seed", sort=True):
        if set(group["fold_name"].unique()) != set(FAERS_FOLDS):
            raise ValueError(f"FAERS seed {seed} does not contain all four folds")
        results[int(seed)] = score_counts(Counter(group["match_type"]))
    return results


def spans_overlap(start_a: object, end_a: object, start_b: object, end_b: object) -> bool:
    if any(pd.isna(value) for value in (start_a, end_a, start_b, end_b)):
        return False
    a_start, a_end = int(start_a), int(end_a)
    b_start, b_end = int(start_b), int(end_b)
    return max(a_start, b_start) < min(a_end, b_end)


def normalized_label(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip().casefold()


def maximum_cardinality(edges: dict[int, list[int]]) -> int:
    """Return a deterministic maximum one-to-one matching size."""
    matched_right: dict[int, int] = {}

    def augment(left: int, visited: set[int]) -> bool:
        for right in edges.get(left, []):
            if right in visited:
                continue
            visited.add(right)
            if right not in matched_right or augment(matched_right[right], visited):
                matched_right[right] = left
                return True
        return False

    return sum(augment(left, set()) for left in sorted(edges))


def corrected_vaers_counts(frame: pd.DataFrame) -> tuple[Counter[str], int]:
    """Collapse overlapping wrong-label S/N pairs into class errors.

    VAERS raw exports encode a wrong-label overlapping span as two outcome rows:
    one spurious prediction (S) and one missed gold span (N). The manuscript's
    two-tier evaluation treats the one-to-one pair as one class error (C).
    """
    counts: Counter[str] = Counter(frame["match_type"])
    correction_count = 0
    for _, sentence in frame.groupby("sent_id", sort=False, dropna=False):
        spurious = sentence[sentence["match_type"] == "S"]
        missed = sentence[sentence["match_type"] == "N"]
        edges: dict[int, list[int]] = {}
        for spurious_index, pred in spurious.iterrows():
            candidates = []
            for missed_index, gold in missed.iterrows():
                if normalized_label(pred["label_pred"]) == normalized_label(gold["label_gold"]):
                    continue
                if spans_overlap(
                    pred["pred_start"],
                    pred["pred_end"],
                    gold["gold_start"],
                    gold["gold_end"],
                ):
                    candidates.append(int(missed_index))
            if candidates:
                edges[int(spurious_index)] = sorted(candidates)
        correction_count += maximum_cardinality(edges)

    counts["S"] -= correction_count
    counts["N"] -= correction_count
    counts["C"] += correction_count
    if counts["S"] < 0 or counts["N"] < 0:
        raise ValueError("VAERS S/N correction produced a negative count")
    if sum(counts.values()) != len(frame) - correction_count:
        raise ValueError("VAERS corrected outcome count failed consistency check")
    return counts, correction_count


def discover_vaers_files(raw_dir: Path) -> dict[tuple[int, int], Path]:
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"VAERS raw result directory not found: {raw_dir}")
    files: dict[tuple[int, int], Path] = {}
    for path in raw_dir.glob("fold_*_seed_*_raw.xlsx"):
        match = VAERS_FILENAME.fullmatch(path.name)
        if match is None:
            continue
        key = (int(match.group(1)), int(match.group(2)))
        if key in files:
            raise ValueError(f"Duplicate VAERS raw workbook for fold/seed {key}")
        files[key] = path
    expected = {(fold, seed) for fold in VAERS_FOLDS for seed in SEEDS}
    if set(files) != expected:
        missing = sorted(expected.difference(files))
        extra = sorted(set(files).difference(expected))
        raise ValueError(f"Unexpected VAERS workbook set; missing={missing}, extra={extra}")
    return files


def load_vaers_scores(raw_dir: Path) -> tuple[dict[int, Scores], int]:
    """Pool the ten held-out VAERS folds within each seed (micro F1)."""
    files = discover_vaers_files(raw_dir)
    by_seed: dict[int, Counter[str]] = {seed: Counter() for seed in SEEDS}
    fold_count_by_seed: Counter[int] = Counter()
    total_corrections = 0
    columns = [
        "fold",
        "seed",
        "sent_id",
        "match_type",
        "label_gold",
        "gold_start",
        "gold_end",
        "label_pred",
        "pred_start",
        "pred_end",
    ]
    for fold in VAERS_FOLDS:
        for seed in SEEDS:
            path = files[(fold, seed)]
            frame = pd.read_excel(path, sheet_name="Raw_Results", usecols=columns)
            validate_match_types(frame, path)
            observed_folds = set(int(value) for value in frame["fold"].dropna().unique())
            observed_seeds = set(int(value) for value in frame["seed"].dropna().unique())
            if observed_folds != {fold} or observed_seeds != {seed}:
                raise ValueError(
                    f"Workbook metadata disagrees with filename {path.name}: "
                    f"folds={observed_folds}, seeds={observed_seeds}"
                )
            counts, corrections = corrected_vaers_counts(frame)
            total_corrections += corrections
            by_seed[seed].update(counts)
            fold_count_by_seed[seed] += 1

    scores = {}
    for seed in SEEDS:
        if fold_count_by_seed[seed] != len(VAERS_FOLDS):
            raise ValueError(f"VAERS seed {seed} does not contain ten fold scores")
        scores[seed] = score_counts(by_seed[seed])
    return scores, total_corrections


def format_value(mean: float, sd: float | None = None) -> str:
    return f"{mean:.4f}" if sd is None else f"{mean:.4f} ± {sd:.4f}"


def table_rows(
    faers: dict[int, Scores], vaers: dict[int, Scores]
) -> list[list[str]]:
    rows = [["Dataset", "Random Seed", "Strict Exact F1", "Adapted ADE-Eval F1"]]
    faers_scores = [faers[seed] for seed in SEEDS]
    for run, seed in enumerate(SEEDS, start=1):
        rows.append(
            [
                f"FAERS Run {run}",
                str(seed),
                format_value(faers[seed].strict_f1),
                format_value(faers[seed].adapted_f1),
            ]
        )
    faers_average = summarize(faers_scores)
    rows.append(
        [
            "FAERS Average",
            "—",
            format_value(faers_average.strict_mean, faers_average.strict_sd),
            format_value(faers_average.adapted_mean, faers_average.adapted_sd),
        ]
    )

    for run, seed in enumerate(SEEDS, start=1):
        score = vaers[seed]
        rows.append(
            [
                f"VAERS Run {run}",
                str(seed),
                format_value(score.strict_f1),
                format_value(score.adapted_f1),
            ]
        )
    vaers_average = summarize([vaers[seed] for seed in SEEDS])
    rows.append(
        [
            "VAERS Average",
            "—",
            format_value(vaers_average.strict_mean, vaers_average.strict_sd),
            format_value(vaers_average.adapted_mean, vaers_average.adapted_sd),
        ]
    )
    return rows


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--faers-raw",
        type=Path,
        default=repo_root / "publication" / "results" / "bert_runs_FAERS_LOO" / "raw.xlsx",
        help="Current FAERS leave-one-out raw workbook.",
    )
    parser.add_argument(
        "--vaers-raw-dir",
        type=Path,
        default=repo_root / "publication" / "results" / "bert_runs_VAERS",
        help="Directory containing the 50 VAERS fold/seed raw workbooks.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            repo_root
            / "publication"
            / "manuscripts"
            / "Tables"
            / "table6_bert_seed_reproducibility.csv"
        ),
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    faers_path = args.faers_raw.resolve()
    vaers_dir = args.vaers_raw_dir.resolve()
    output_path = args.output.resolve()

    faers = load_faers_scores(faers_path)
    vaers, correction_count = load_vaers_scores(vaers_dir)
    rows = table_rows(faers, vaers)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerows(rows)

    print(f"Created {output_path}")
    print(f"FAERS source: {faers_path}")
    print(f"VAERS sources: 50 raw workbooks in {vaers_dir}")
    print(f"VAERS overlapping wrong-label S/N pairs converted to C: {correction_count}")


if __name__ == "__main__":
    main()
