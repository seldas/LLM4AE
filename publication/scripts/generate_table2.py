#!/usr/bin/env python3
"""Generate manuscript Table 2 from canonical database and raw predictions.

The output reproduces Table 2 ("FAERS annotations, categorized by Human,
ETHER and LLM") in ``publication/manuscripts/LLM4AE_rev1.docx``.

Data lineage:
  * Human and ETHER counts: ``publication/dataset.db``
  * LLaMA-4 counts: ``publication/results/llama4_runs_FAERS/llama4_raw.xlsx``
  * Sonnet counts: ``publication/results/sonnet_runs_FAERS/sonnet_raw.xlsx``

Default output:
    publication/manuscripts/Tables/table2_faers_annotations.csv
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from collections import Counter
from pathlib import Path

import pandas as pd


TABLE_CATEGORIES = (
    "SDrug",
    "CDrug",
    "ODrug",
    "Dose",
    "Indication",
    "Treatment",
    "AE",
    "mAE",
    "Dx",
    "Lab",
    "Status",
    "R/O",
    "CoD",
    "MHx",
    "FHx",
    "Age",
    "Sex",
)

# Raw-label groups define how each source taxonomy maps to the manuscript's
# 17 clinical categories. Values are never embedded here; they are counted
# from the source database/workbooks at runtime.
HUMAN_LABELS = {
    "SDrug": frozenset({"sdrug"}),
    "CDrug": frozenset({"cdrug"}),
    "ODrug": frozenset({"drug", "odrug"}),
    "Dose": frozenset({"dose"}),
    "Indication": frozenset({"indication"}),
    "Treatment": frozenset({"treatment"}),
    "AE": frozenset({"ae"}),
    "mAE": frozenset({"mae"}),
    # Table 2 reports baseline symptoms under the harmonized Dx category.
    "Dx": frozenset({"diagnostic", "dx", "bsym", "baseline symptom"}),
    "Lab": frozenset({"lab"}),
    "Status": frozenset({"status"}),
    "R/O": frozenset({"r/o", "ro"}),
    "CoD": frozenset({"cause of death", "cod"}),
    "MHx": frozenset({"mhx", "medical history"}),
    "FHx": frozenset({"fhx", "family history"}),
    "Age": frozenset({"age"}),
    "Sex": frozenset({"sex"}),
}

LLM_LABELS = {
    "SDrug": frozenset({"sdrug"}),
    "CDrug": frozenset({"cdrug"}),
    "ODrug": frozenset({"odrug", "drug"}),
    "Dose": frozenset({"dose"}),
    "Indication": frozenset({"indication"}),
    "Treatment": frozenset({"treatment"}),
    "AE": frozenset({"ae"}),
    "mAE": frozenset({"mae"}),
    "Dx": frozenset({"diagnostic", "dx", "bsym"}),
    "Lab": frozenset({"lab"}),
    "Status": frozenset({"status"}),
    "R/O": frozenset({"ro", "r/o"}),
    "CoD": frozenset({"cod", "cause of death"}),
    "MHx": frozenset({"mhx", "medical history"}),
    "FHx": frozenset({"fhx", "family history"}),
    "Age": frozenset({"age"}),
    "Sex": frozenset({"sex"}),
}

# ETHER does not distinguish the three drug roles or AE severity. The shared
# aggregate is intentionally repeated in those manuscript rows and marked '*'.
ETHER_SHARED_LABELS = {
    "Drug": frozenset({"drug", "vaccine"}),
    "AE": frozenset({"symptom"}),
}
ETHER_LABELS = {
    "Dx": frozenset({"diagnosis", "second_level_diagnosis"}),
    "R/O": frozenset({"rule_out"}),
    "CoD": frozenset({"cause_of_death"}),
    "MHx": frozenset({"medical_history"}),
    "FHx": frozenset({"family_history"}),
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


def database_label_counts(
    connection: sqlite3.Connection,
    note: str,
) -> Counter[str]:
    rows = connection.execute(
        """
        SELECT lower(trim(a.label)), count(*)
        FROM annotations AS a
        JOIN documents AS d ON d.doc_id = a.doc_id
        WHERE d.dataset = 'FAERS' AND a.note = ?
        GROUP BY lower(trim(a.label))
        """,
        (note,),
    ).fetchall()
    if not rows:
        raise ValueError(f"No FAERS annotations found for note={note!r}")
    return Counter({canonical_label(label): int(count) for label, count in rows})


def llm_prediction_counts(path: Path) -> Counter[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Raw prediction workbook not found: {path}")

    frame = pd.read_excel(path, sheet_name="Raw_Results")
    required = {"match_type", "label_pred"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    prediction_rows = frame.loc[
        frame["match_type"].isin({"M", "C", "S"}) & frame["label_pred"].notna(),
        "label_pred",
    ]
    if prediction_rows.empty:
        raise ValueError(f"No prediction entities found in {path}")
    return Counter(canonical_label(label) for label in prediction_rows)


def ether_display_counts(raw_counts: Counter[str]) -> dict[str, str]:
    shared = grouped_counts(raw_counts, ETHER_SHARED_LABELS)
    distinct = grouped_counts(raw_counts, ETHER_LABELS)
    values = {category: "n/a" for category in TABLE_CATEGORIES}
    for category in ("SDrug", "CDrug", "ODrug"):
        values[category] = f"{shared['Drug']:,}*"
    for category in ("AE", "mAE"):
        values[category] = f"{shared['AE']:,}*"
    for category, count in distinct.items():
        values[category] = f"{count:,}"
    return values


def numeric_display_counts(
    raw_counts: Counter[str],
    label_groups: dict[str, frozenset[str]],
) -> dict[str, str]:
    counts = grouped_counts(raw_counts, label_groups)
    return {category: f"{counts[category]:,}" for category in TABLE_CATEGORIES}


def table_rows(
    human: dict[str, str],
    ether: dict[str, str],
    llama: dict[str, str],
    sonnet: dict[str, str],
) -> list[list[str]]:
    rows = [["Category", "Human", "ETHER", "LLM (LLaMA-4)", "LLM (Sonnet 4.6)"]]
    rows.extend(
        [category, human[category], ether[category], llama[category], sonnet[category]]
        for category in TABLE_CATEGORIES
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
            / "llama4_runs_FAERS"
            / "llama4_raw.xlsx"
        ),
        help="LLaMA-4 FAERS raw prediction workbook.",
    )
    parser.add_argument(
        "--sonnet-raw",
        type=Path,
        default=(
            repo_root
            / "publication"
            / "results"
            / "sonnet_runs_FAERS"
            / "sonnet_raw.xlsx"
        ),
        help="Sonnet FAERS raw prediction workbook.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            repo_root
            / "publication"
            / "manuscripts"
            / "Tables"
            / "table2_faers_annotations.csv"
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
        human_raw = database_label_counts(connection, "SME1")
        ether_raw = database_label_counts(connection, "ETHER")

    human = numeric_display_counts(human_raw, HUMAN_LABELS)
    ether = ether_display_counts(ether_raw)
    llama = numeric_display_counts(llm_prediction_counts(args.llama_raw.resolve()), LLM_LABELS)
    sonnet = numeric_display_counts(llm_prediction_counts(args.sonnet_raw.resolve()), LLM_LABELS)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(
            table_rows(human, ether, llama, sonnet)
        )

    print(f"Generated manuscript Table 2: {output_path}")


if __name__ == "__main__":
    main()
