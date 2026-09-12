#!/usr/bin/env python3
"""Generate manuscript Table 4 from current VAERS source data.

The manuscript is used only to define the row and column structure. Every
reported count is calculated at runtime from these canonical sources:

* Human annotations: ``publication/dataset.db`` (VAERS, SME1)
* LLaMA-4 predictions:
  ``publication/results/llama4_runs_VAERS/llama4_raw.xlsx``

Default output:
    publication/manuscripts/Tables/table4_vaers_annotations.csv
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from collections import Counter
from pathlib import Path

import pandas as pd


TABLE_CATEGORIES = (
    "pDx",
    "sDx",
    "R/O",
    "SYM",
    "CoD",
    "Lab",
    "FHx",
    "MHx",
    "STATUS",
    "TX",
    "VAX",
)

# The two sources use slightly different spellings for rule-out annotations.
# These mappings contain taxonomy only; all displayed values are counted from
# the database or raw prediction workbook at runtime.
HUMAN_LABELS = {
    "pDx": frozenset({"pdx"}),
    "sDx": frozenset({"sdx"}),
    "R/O": frozenset({"r/o", "ro"}),
    "SYM": frozenset({"sym"}),
    "CoD": frozenset({"cod", "cause of death"}),
    "Lab": frozenset({"lab"}),
    "FHx": frozenset({"fhx", "family history"}),
    "MHx": frozenset({"mhx", "medical history"}),
    "STATUS": frozenset({"status"}),
    "TX": frozenset({"tx"}),
    "VAX": frozenset({"vax"}),
}

LLM_LABELS = {
    "pDx": frozenset({"pdx"}),
    "sDx": frozenset({"sdx"}),
    "R/O": frozenset({"ro", "r/o"}),
    "SYM": frozenset({"sym"}),
    "CoD": frozenset({"cod", "cause of death"}),
    "Lab": frozenset({"lab"}),
    "FHx": frozenset({"fhx", "family history"}),
    "MHx": frozenset({"mhx", "medical history"}),
    "STATUS": frozenset({"status"}),
    "TX": frozenset({"tx"}),
    "VAX": frozenset({"vax"}),
}


def canonical_label(value: object) -> str:
    return "" if value is None else str(value).strip().lower()


def grouped_counts(
    raw_counts: Counter[str],
    label_groups: dict[str, frozenset[str]],
) -> dict[str, int]:
    return {
        category: sum(raw_counts[label] for label in labels)
        for category, labels in label_groups.items()
    }


def human_annotation_counts(database_path: Path) -> Counter[str]:
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
    if not rows:
        raise ValueError("No VAERS SME1 annotations found in the database")
    return Counter({canonical_label(label): int(count) for label, count in rows})


def llm_prediction_counts(raw_path: Path) -> Counter[str]:
    if not raw_path.is_file():
        raise FileNotFoundError(f"Raw prediction workbook not found: {raw_path}")

    frame = pd.read_excel(raw_path, sheet_name="Raw_Results")
    required = {"match_type", "label_pred"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{raw_path} is missing required columns: {sorted(missing)}")

    unknown_match_types = set(frame["match_type"].dropna().unique()).difference(
        {"M", "C", "S", "N"}
    )
    if unknown_match_types:
        raise ValueError(
            f"{raw_path} has unknown match types: {sorted(unknown_match_types)}"
        )

    prediction_rows = frame.loc[
        frame["match_type"].isin({"M", "C", "S"})
        & frame["label_pred"].notna(),
        "label_pred",
    ]
    if prediction_rows.empty:
        raise ValueError(f"No prediction entities found in {raw_path}")
    return Counter(canonical_label(label) for label in prediction_rows)


def validate_taxonomy(
    raw_counts: Counter[str],
    label_groups: dict[str, frozenset[str]],
    source_name: str,
) -> None:
    mapped_labels = set().union(*label_groups.values())
    unknown_labels = set(raw_counts).difference(mapped_labels)
    if unknown_labels:
        raise ValueError(
            f"Unmapped {source_name} labels would be omitted: {sorted(unknown_labels)}"
        )


def table_rows(human: dict[str, int], llama: dict[str, int]) -> list[list[str]]:
    rows = [["Category", "Human", "LLM (LLaMA-4)"]]
    rows.extend(
        [category, f"{human[category]:,}", f"{llama[category]:,}"]
        for category in TABLE_CATEGORIES
    )
    rows.append(
        [
            "TOTAL",
            f"{sum(human.values()):,}",
            f"{sum(llama.values()):,}",
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
        "--llama-raw",
        type=Path,
        default=(
            repo_root
            / "publication"
            / "results"
            / "llama4_runs_VAERS"
            / "llama4_raw.xlsx"
        ),
        help="LLaMA-4 VAERS raw prediction workbook.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            repo_root
            / "publication"
            / "manuscripts"
            / "Tables"
            / "table4_vaers_annotations.csv"
        ),
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    human_raw = human_annotation_counts(args.database.resolve())
    llama_raw = llm_prediction_counts(args.llama_raw.resolve())

    validate_taxonomy(human_raw, HUMAN_LABELS, "human")
    validate_taxonomy(llama_raw, LLM_LABELS, "LLaMA-4")
    human = grouped_counts(human_raw, HUMAN_LABELS)
    llama = grouped_counts(llama_raw, LLM_LABELS)

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(table_rows(human, llama))

    print(f"Generated updated manuscript Table 4: {output_path}")
    print(
        f"Totals from current sources: Human={sum(human.values()):,}, "
        f"LLaMA-4={sum(llama.values()):,}"
    )


if __name__ == "__main__":
    main()
