#!/usr/bin/env python3
"""Persist reviewed FAERS case-series assignments in ``dataset.db``.

The trial classifier CSV is the starting point. Assignments resolved through
the openFDA Drug Event API are applied as explicit reviewed overrides. Report
``3047591-1`` remains in the database for auditability but is excluded from
BERT LOO because it has no usable narrative or study-relevant annotations.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from collections import Counter
from pathlib import Path


CASE_SERIES = (
    "Azacitidine-QT",
    "Tramadol-Hypoglycemia",
    "Baricitinib-Hypersensitivity",
    "Erenumab-Stroke",
)

OPENFDA_EXACT_OVERRIDES = {
    "10305563-1": "Azacitidine-QT",
    "10625821-4": "Azacitidine-QT",
    "11283592-2": "Baricitinib-Hypersensitivity",
    "15446077-1": "Azacitidine-QT",
    "15544212-4": "Erenumab-Stroke",
    "15587045-1": "Baricitinib-Hypersensitivity",
    "15723842-1": "Erenumab-Stroke",
    "15943492-1": "Baricitinib-Hypersensitivity",
    "15943643-1": "Baricitinib-Hypersensitivity",
    "16215485-1": "Baricitinib-Hypersensitivity",
    "16430031-1": "Baricitinib-Hypersensitivity",
    "16485683-1": "Baricitinib-Hypersensitivity",
    "16518066-1": "Baricitinib-Hypersensitivity",
    "16606869-1": "Baricitinib-Hypersensitivity",
    "16624350-1": "Baricitinib-Hypersensitivity",
    "16692955-1": "Erenumab-Stroke",
    "16715419-1": "Baricitinib-Hypersensitivity",
    "17044300-1": "Baricitinib-Hypersensitivity",
    "17156928-1": "Baricitinib-Hypersensitivity",
    "17880116-1": "Baricitinib-Hypersensitivity",
    "6458448-2": "Tramadol-Hypoglycemia",
}

OPENFDA_LATER_VERSION_OVERRIDES = {
    "16405917-5": "Baricitinib-Hypersensitivity",
    "17587785-8": "Azacitidine-QT",
}

EXCLUDED_REPORTS = {
    "3047591-1": (
        "No narrative is stored; the only SME1 annotation is TEMPO and is not "
        "useful for the present case-series LOO evaluation."
    ),
}


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database", type=Path,
        default=repo_root / "publication" / "dataset.db",
    )
    parser.add_argument(
        "--classification", type=Path,
        default=(repo_root / "publication" / "results"
                 / "faers_case_series_classification.csv"),
    )
    return parser.parse_args()


def load_seed_assignments(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"Classification CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assignments = {
        str(row["doc_id"]): str(row["assigned_series"]) for row in rows
    }
    if len(assignments) != len(rows):
        raise ValueError("Classification CSV contains duplicate doc_id values")
    return assignments


def main() -> None:
    args = parse_args()
    database_path = args.database.resolve()
    assignments = load_seed_assignments(args.classification.resolve())
    assignments.update(OPENFDA_EXACT_OVERRIDES)
    assignments.update(OPENFDA_LATER_VERSION_OVERRIDES)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        faers_ids = {
            str(row[0]) for row in connection.execute(
                "SELECT doc_id FROM documents WHERE dataset = 'FAERS'"
            )
        }
        if set(assignments) != faers_ids:
            missing = sorted(faers_ids - set(assignments))
            extra = sorted(set(assignments) - faers_ids)
            raise ValueError(
                "Classification/document mismatch: "
                f"missing={missing[:10]}, extra={extra[:10]}"
            )

        bad_series = {
            value for doc_id, value in assignments.items()
            if doc_id not in EXCLUDED_REPORTS and value not in CASE_SERIES
        }
        if bad_series:
            raise ValueError(f"Unresolved or invalid included assignments: {bad_series}")

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS faers_case_series (
                doc_id             TEXT PRIMARY KEY REFERENCES documents(doc_id),
                case_series        TEXT,
                include_in_loo     INTEGER NOT NULL
                                   CHECK (include_in_loo IN (0, 1)),
                assignment_source  TEXT NOT NULL,
                assignment_note    TEXT,
                CHECK (case_series IS NULL OR case_series IN (
                    'Azacitidine-QT',
                    'Tramadol-Hypoglycemia',
                    'Baricitinib-Hypersensitivity',
                    'Erenumab-Stroke'
                )),
                CHECK (
                    (include_in_loo = 1 AND case_series IS NOT NULL) OR
                    include_in_loo = 0
                )
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_faers_case_series_name "
            "ON faers_case_series(case_series)"
        )
        connection.execute("DELETE FROM faers_case_series")

        rows = []
        for doc_id in sorted(faers_ids):
            if doc_id in EXCLUDED_REPORTS:
                row = (
                    doc_id, None, 0, "excluded_no_usable_narrative",
                    EXCLUDED_REPORTS[doc_id],
                )
            elif doc_id in OPENFDA_EXACT_OVERRIDES:
                row = (
                    doc_id, assignments[doc_id], 1,
                    "openfda_exact_report_version",
                    "Reviewed using safetyreportid and safetyreportversion.",
                )
            elif doc_id in OPENFDA_LATER_VERSION_OVERRIDES:
                row = (
                    doc_id, assignments[doc_id], 1,
                    "openfda_later_report_version",
                    "Exact version unavailable; reviewed using a later version.",
                )
            else:
                row = (
                    doc_id, assignments[doc_id], 1,
                    "local_reviewed_classification", None,
                )
            rows.append(row)

        connection.executemany(
            """
            INSERT INTO faers_case_series (
                doc_id, case_series, include_in_loo,
                assignment_source, assignment_note
            ) VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )

    distribution = Counter(
        assignments[doc_id]
        for doc_id in faers_ids if doc_id not in EXCLUDED_REPORTS
    )
    print(f"Stored FAERS case-series records: {len(faers_ids):,}")
    for series in CASE_SERIES:
        print(f"  {series}: {distribution[series]:,}")
    print(f"  Excluded from LOO: {len(EXCLUDED_REPORTS):,}")


if __name__ == "__main__":
    main()
