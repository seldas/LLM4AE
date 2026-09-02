#!/usr/bin/env python3
"""Generate manuscript Table 5 from current FAERS leave-one-out data.

Every displayed value is calculated at runtime from the permitted canonical
sources:

* Validation cohort sizes and SME1 labels: ``publication/dataset.db``
* BERT outcomes: ``publication/results/bert_runs_FAERS_LOO/raw.xlsx``

Default output:
    publication/manuscripts/Tables/table5_faers_case_series_performance.csv
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


CASE_SERIES = (
    ("Azacitidine-QT", "Azacitidine – QT Prolongation"),
    ("Baricitinib-Hypersensitivity", "Baricitinib – Hypersensitivity"),
    ("Tramadol-Hypoglycemia", "Tramadol – Hypoglycemia"),
    ("Erenumab-Stroke", "Erenumab – Stroke"),
)

# This is the case-series classification rule used to build the current LOO
# raw results. It is methodology, not embedded result data: report text and
# annotation spans are read from dataset.db and classified at runtime.
CASE_SERIES_KEYWORDS = {
    "Azacitidine-QT": {
        "drugs": ("azacitidine", "vidaza", "5-aza", "azacytidine", "aza"),
        "events": (
            "qt",
            "torsade",
            "ventricular",
            "cardiac",
            "arrhythmia",
            "ecg",
            "electrocardiogram",
            "prolongation",
            "myelodysplastic",
            "raeb",
            "leukemia",
            "aml",
        ),
    },
    "Tramadol-Hypoglycemia": {
        "drugs": (
            "tramadol",
            "ultram",
            "tramacet",
            "ixprim",
            "trarmadol",
            "tremadol",
            "tramal",
            "zydol",
        ),
        "events": (
            "hypoglyc",
            "glucose",
            "glycemia",
            "sweating",
            "coma",
            "blood sugar",
            "insulin",
        ),
    },
    "Baricitinib-Hypersensitivity": {
        "drugs": ("baricitinib", "olumiant", "barcitinib", "olimiant"),
        "events": (
            "hypersensitiv",
            "allergic",
            "allergy",
            "anaphylax",
            "rash",
            "urticaria",
            "hives",
            "swelling",
            "angioedema",
            "face swollen",
            "lip",
            "tongue",
            "erythema",
            "pruritus",
            "dermatitis",
            "rheumatoid",
            "arthritis",
        ),
    },
    "Erenumab-Stroke": {
        "drugs": ("erenumab", "aimovig"),
        "events": (
            "stroke",
            "cva",
            "cerebrovascular",
            "ischemi",
            "infarct",
            "transient ischemic",
            "tia",
            "migraine",
            "headache",
            "hemiplegia",
        ),
    },
}

DRUG_LABELS = frozenset({"sdrug", "cdrug", "odrug", "drug"})
AE_LABELS = frozenset({"ae", "mae"})
MATCH_TYPES = frozenset({"M", "C", "S", "N"})
EXPECTED_SEED_COUNT = 5


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


def canonical_label(value: object) -> str:
    return "" if value is None else str(value).strip().lower()


def score_counts(counts: Counter[str]) -> Scores:
    M = int(counts["M"])
    C = int(counts["C"])
    S = int(counts["S"])
    N = int(counts["N"])

    strict_precision = M / (M + C + S) if M + C + S else 0.0
    strict_recall = M / (M + C + N) if M + C + N else 0.0
    strict_f1 = (
        2
        * strict_precision
        * strict_recall
        / (strict_precision + strict_recall)
        if strict_precision + strict_recall
        else 0.0
    )

    matched_credit = M + 0.5 * C
    adapted_precision = (
        matched_credit / (M + C + 0.25 * S) if M + C + 0.25 * S else 0.0
    )
    adapted_recall = matched_credit / (M + C + N) if M + C + N else 0.0
    adapted_f1 = (
        2
        * adapted_precision
        * adapted_recall
        / (adapted_precision + adapted_recall)
        if adapted_precision + adapted_recall
        else 0.0
    )
    return Scores(strict_f1=strict_f1, adapted_f1=adapted_f1)


def summarize(scores: list[Scores]) -> Summary:
    if len(scores) != EXPECTED_SEED_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_SEED_COUNT} seed results; found {len(scores)}"
        )
    strict = [score.strict_f1 for score in scores]
    adapted = [score.adapted_f1 for score in scores]
    return Summary(
        strict_mean=statistics.mean(strict),
        strict_sd=statistics.stdev(strict),
        adapted_mean=statistics.mean(adapted),
        adapted_sd=statistics.stdev(adapted),
    )


def load_raw_scores(raw_path: Path) -> tuple[dict[str, Summary], Summary]:
    if not raw_path.is_file():
        raise FileNotFoundError(f"Raw BERT workbook not found: {raw_path}")

    frame = pd.read_excel(
        raw_path,
        sheet_name="Raw_Results",
        usecols=["fold_name", "seed", "match_type"],
    )
    unknown_match_types = set(frame["match_type"].dropna().unique()).difference(
        MATCH_TYPES
    )
    if unknown_match_types:
        raise ValueError(
            f"{raw_path} has unknown match types: {sorted(unknown_match_types)}"
        )

    expected_folds = {internal_name for internal_name, _ in CASE_SERIES}
    actual_folds = set(frame["fold_name"].dropna().unique())
    if actual_folds != expected_folds:
        raise ValueError(
            "Unexpected LOO fold names; "
            f"expected {sorted(expected_folds)}, found {sorted(actual_folds)}"
        )

    seeds = sorted(int(seed) for seed in frame["seed"].dropna().unique())
    if len(seeds) != EXPECTED_SEED_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_SEED_COUNT} BERT seeds; found {seeds}"
        )

    fold_scores: dict[str, list[Scores]] = defaultdict(list)
    for (fold_name, seed), group in frame.groupby(
        ["fold_name", "seed"], sort=True
    ):
        counts = Counter(group["match_type"])
        fold_scores[str(fold_name)].append(score_counts(counts))

    by_fold = {fold: summarize(scores) for fold, scores in fold_scores.items()}

    micro_scores = []
    for _, group in frame.groupby("seed", sort=True):
        micro_scores.append(score_counts(Counter(group["match_type"])))
    return by_fold, summarize(micro_scores)


def classify_case_series(
    text: str,
    annotations: list[tuple[int, int, str]],
) -> str:
    normalized_text = text.replace("↵", "\n")
    drug_terms = " ".join(
        normalized_text[start:end].lower()
        for start, end, label in annotations
        if label in DRUG_LABELS
    )
    ae_terms = " ".join(
        normalized_text[start:end].lower()
        for start, end, label in annotations
        if label in AE_LABELS
    )
    combined = f"{normalized_text.lower()} {drug_terms} {ae_terms}"

    weighted_counts = {}
    for series_name, keywords in CASE_SERIES_KEYWORDS.items():
        drug_matches = sum(combined.count(term) for term in keywords["drugs"])
        event_matches = sum(combined.count(term) for term in keywords["events"])
        weighted_counts[series_name] = 10 * drug_matches + event_matches
    return max(weighted_counts, key=weighted_counts.get)


def validation_cohort_sizes(database_path: Path) -> dict[str, int]:
    if not database_path.is_file():
        raise FileNotFoundError(f"Database not found: {database_path}")

    with sqlite3.connect(database_path) as connection:
        documents = connection.execute(
            """
            SELECT doc_id, page_text
            FROM documents
            WHERE dataset = 'FAERS'
            ORDER BY doc_id
            """
        ).fetchall()
        annotation_rows = connection.execute(
            """
            SELECT a.doc_id, lower(trim(a.label)), a.tc_start, a.tc_end
            FROM annotations AS a
            JOIN documents AS d ON d.doc_id = a.doc_id
            WHERE d.dataset = 'FAERS' AND a.note = 'SME1'
            ORDER BY a.doc_id, a.tc_start
            """
        ).fetchall()
    if not documents:
        raise ValueError("No FAERS documents found in the database")

    annotations_by_document: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for document, label, start, end in annotation_rows:
        annotations_by_document[str(document)].append(
            (int(start), int(end), canonical_label(label))
        )

    counts: Counter[str] = Counter()
    for document, text in documents:
        series = classify_case_series(
            str(text), annotations_by_document.get(str(document), [])
        )
        counts[series] += 1
    return {series: counts[series] for series, _ in CASE_SERIES}


def format_summary(summary: Summary, metric: str) -> str:
    mean = getattr(summary, f"{metric}_mean")
    sd = getattr(summary, f"{metric}_sd")
    return f"{mean:.4f} ± {sd:.4f}"


def table_rows(
    cohort_sizes: dict[str, int],
    fold_summaries: dict[str, Summary],
    micro_summary: Summary,
) -> list[list[str]]:
    rows = [
        [
            "Drug–Event Case Series",
            "Validation Cohort Size",
            "Strict Exact F1",
            "Adapted ADE-Eval F1",
        ]
    ]
    for internal_name, display_name in CASE_SERIES:
        summary = fold_summaries[internal_name]
        rows.append(
            [
                display_name,
                f"{cohort_sizes[internal_name]:,}",
                format_summary(summary, "strict"),
                format_summary(summary, "adapted"),
            ]
        )
    rows.append(
        [
            "Total (Micro-Average)",
            f"{sum(cohort_sizes.values()):,}",
            format_summary(micro_summary, "strict"),
            format_summary(micro_summary, "adapted"),
        ]
    )
    return rows


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=repo_root / "publication" / "dataset.db",
        help="Canonical SQLite database (default: publication/dataset.db).",
    )
    parser.add_argument(
        "--bert-raw",
        type=Path,
        default=(
            repo_root
            / "publication"
            / "results"
            / "bert_runs_FAERS_LOO"
            / "raw.xlsx"
        ),
        help="BERT FAERS leave-one-out raw workbook.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            repo_root
            / "publication"
            / "manuscripts"
            / "Tables"
            / "table5_faers_case_series_performance.csv"
        ),
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cohort_sizes = validation_cohort_sizes(args.database.resolve())
    fold_summaries, micro_summary = load_raw_scores(args.bert_raw.resolve())

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(
            table_rows(cohort_sizes, fold_summaries, micro_summary)
        )

    print(f"Generated updated manuscript Table 5: {output_path}")
    print(
        "Validation cohort sizes from current database: "
        + ", ".join(
            f"{series}={cohort_sizes[series]:,}" for series, _ in CASE_SERIES
        )
    )


if __name__ == "__main__":
    main()
