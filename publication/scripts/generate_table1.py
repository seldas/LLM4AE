#!/usr/bin/env python3
"""Generate manuscript Table 1 from the canonical SQLite database.

Despite the historical script name requested for this repository, this script
reproduces Table 1 ("Descriptive statistics of the annotated corpora") in
``publication/manuscripts/LLM4AE_rev1.docx``.  Every reported value is computed
from ``publication/dataset.db``; the manuscript is not used as a data source.

Default output:
    publication/manuscripts/Tables/table1_descriptive_statistics.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"[\u21b5\n]+|(?<=[.!?])\s+")

# These label groups reproduce the definitions used by manuscript Table 1.
# FAERS temporal relations are excluded from the table's clinical-entity count.
FAERS_EXCLUDED_ANNOTATION_LABELS = frozenset({"tempo"})
AE_LABELS = {
    "FAERS": frozenset({"ae", "mae"}),
    "VAERS": frozenset({"sym", "pdx", "sdx"}),
}
DRUG_VACCINE_LABELS = {
    "FAERS": frozenset({"drug", "cdrug", "sdrug"}),
    "VAERS": frozenset({"vax"}),
}


@dataclass(frozen=True)
class CorpusStatistics:
    reports: int
    total_tokens: int
    total_sentences: int
    mean_tokens: float
    stdev_tokens: float
    median_tokens: float
    sme_annotations: int
    unique_ae_terms: int
    unique_drug_vaccine_terms: int


def normalized_term(raw_term: object, display_term: object) -> str:
    """Return the annotation surface form used for unique-term counting."""
    candidate = raw_term if raw_term is not None and str(raw_term).strip() else display_term
    return str(candidate or "").strip().lower()


def sentence_count(text: str) -> int:
    """Count sentence-like segments using the manuscript corpus convention."""
    return sum(1 for segment in SENTENCE_SPLIT_RE.split(text) if segment.strip())


def sample_stdev(values: list[int]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def load_documents(connection: sqlite3.Connection, dataset: str) -> list[str]:
    rows = connection.execute(
        "SELECT page_text FROM documents WHERE dataset = ? ORDER BY doc_id",
        (dataset,),
    ).fetchall()
    if not rows:
        raise ValueError(f"No documents found for dataset {dataset!r}")
    return [str(row[0]) for row in rows]


def load_sme_annotations(
    connection: sqlite3.Connection,
    dataset: str,
) -> list[tuple[str, str]]:
    """Load normalized ``(label, surface form)`` pairs for SME1 annotations."""
    rows = connection.execute(
        """
        SELECT lower(trim(a.label)), a.tc_text_raw, a.tc_text
        FROM annotations AS a
        JOIN documents AS d ON d.doc_id = a.doc_id
        WHERE d.dataset = ? AND a.note = 'SME1'
        """,
        (dataset,),
    ).fetchall()
    if not rows:
        raise ValueError(f"No SME1 annotations found for dataset {dataset!r}")
    return [
        (str(label), normalized_term(raw_term, display_term))
        for label, raw_term, display_term in rows
    ]


def compute_statistics(
    connection: sqlite3.Connection,
    dataset: str,
) -> CorpusStatistics:
    documents = load_documents(connection, dataset)
    annotations = load_sme_annotations(connection, dataset)

    token_counts = [len(TOKEN_RE.findall(text)) for text in documents]
    sentence_counts = [sentence_count(text) for text in documents]

    excluded_labels: Iterable[str]
    if dataset == "FAERS":
        excluded_labels = FAERS_EXCLUDED_ANNOTATION_LABELS
    else:
        excluded_labels = ()

    excluded = set(excluded_labels)
    sme_annotations = sum(1 for label, _ in annotations if label not in excluded)
    unique_ae_terms = {
        term for label, term in annotations if label in AE_LABELS[dataset] and term
    }
    unique_drug_vaccine_terms = {
        term
        for label, term in annotations
        if label in DRUG_VACCINE_LABELS[dataset] and term
    }

    return CorpusStatistics(
        reports=len(documents),
        total_tokens=sum(token_counts),
        total_sentences=sum(sentence_counts),
        mean_tokens=statistics.mean(token_counts),
        stdev_tokens=sample_stdev(token_counts),
        median_tokens=statistics.median(token_counts),
        sme_annotations=sme_annotations,
        unique_ae_terms=len(unique_ae_terms),
        unique_drug_vaccine_terms=len(unique_drug_vaccine_terms),
    )


def format_integer(value: int | float) -> str:
    return f"{int(value):,}"


def format_median(value: float) -> str:
    return format_integer(value) if float(value).is_integer() else f"{value:,.1f}"


def table_rows(
    faers: CorpusStatistics,
    vaers: CorpusStatistics,
) -> list[list[str]]:
    """Return the exact row/column structure used by manuscript Table 1."""
    return [
        ["Statistic", "FAERS D1", "VAERS"],
        ["#Reports", format_integer(faers.reports), format_integer(vaers.reports)],
        ["Total tokens", format_integer(faers.total_tokens), format_integer(vaers.total_tokens)],
        [
            "Total sentences",
            format_integer(faers.total_sentences),
            format_integer(vaers.total_sentences),
        ],
        [
            "Avg tokens per report",
            f"{faers.mean_tokens:,.1f} ± {faers.stdev_tokens:,.1f}",
            f"{vaers.mean_tokens:,.1f} ± {vaers.stdev_tokens:,.1f}",
        ],
        [
            "Median tokens per report",
            format_median(faers.median_tokens),
            format_median(vaers.median_tokens),
        ],
        [
            "SME annotations",
            format_integer(faers.sme_annotations),
            format_integer(vaers.sme_annotations),
        ],
        [
            "Unique AE terms",
            format_integer(faers.unique_ae_terms),
            format_integer(vaers.unique_ae_terms),
        ],
        [
            "Unique Drug/Vaccine terms",
            format_integer(faers.unique_drug_vaccine_terms),
            format_integer(vaers.unique_drug_vaccine_terms),
        ],
    ]


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
        "--output",
        type=Path,
        default=(
            repo_root
            / "publication"
            / "manuscripts"
            / "Tables"
            / "table1_descriptive_statistics.csv"
        ),
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_path = args.database.resolve()
    output_path = args.output.resolve()

    if not database_path.is_file():
        raise FileNotFoundError(f"Database not found: {database_path}")

    with sqlite3.connect(database_path) as connection:
        faers = compute_statistics(connection, "FAERS")
        vaers = compute_statistics(connection, "VAERS")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(table_rows(faers, vaers))

    print(f"Generated manuscript Table 1: {output_path}")


if __name__ == "__main__":
    main()
