#!/usr/bin/env python3
"""Generate manuscript Table 7 directly from the current FAERS raw results.

Table 7 compares the output-format paradigms used by LLaMA-4 and Claude
4.6 Sonnet.  The manuscript document is used only as a structural reference;
all scores are recomputed at runtime from the three ``*_raw.xlsx`` files.

The scoring implementation is shared with ``generate_table3.py`` so that the
same one-to-one correction of overlapping wrong-label N/S pairs and the same
Strict/Adapted metric definitions are used in both manuscript tables.

Default output:
    publication/manuscripts/Tables/table7_llm_output_format.csv
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from generate_table3 import Scores, corrected_llm_scores


@dataclass(frozen=True)
class RawRun:
    model: str
    output_paradigm: str
    path: Path


def format_score(value: float) -> str:
    return f"{value:.4f}"


def table_rows(results: list[tuple[RawRun, Scores]]) -> list[list[str]]:
    rows = [
        [
            "Model",
            "Output Paradigm",
            "Strict Exact-Match F1",
            "Adapted ADE-Eval F1",
        ]
    ]
    rows.extend(
        [
            run.model,
            run.output_paradigm,
            format_score(scores.strict_f1),
            format_score(scores.adapted_f1),
        ]
        for run, scores in results
    )
    return rows


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    results = repo_root / "publication" / "results"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--llama-inline-raw",
        type=Path,
        default=results / "llama4_runs_FAERS" / "llama4_raw.xlsx",
    )
    parser.add_argument(
        "--llama-json-raw",
        type=Path,
        default=(
            results / "llama4_runs_FAERS_json" / "llama4_json_raw.xlsx"
        ),
    )
    parser.add_argument(
        "--sonnet-inline-raw",
        type=Path,
        default=results / "sonnet_runs_FAERS" / "sonnet_raw.xlsx",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            repo_root
            / "publication"
            / "manuscripts"
            / "Tables"
            / "table7_llm_output_format.csv"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runs = [
        RawRun("LLaMA-4", "Inline Tagged", args.llama_inline_raw.resolve()),
        RawRun("LLaMA-4", "JSON", args.llama_json_raw.resolve()),
        RawRun(
            "Claude 4.6 Sonnet",
            "Inline Tagged",
            args.sonnet_inline_raw.resolve(),
        ),
    ]

    results: list[tuple[RawRun, Scores]] = []
    corrections: dict[str, int] = {}
    for run in runs:
        scores, correction_count = corrected_llm_scores(run.path)
        results.append((run, scores))
        corrections[f"{run.model} / {run.output_paradigm}"] = correction_count

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(table_rows(results))

    print(f"Generated updated manuscript Table 7: {output_path}")
    for run, scores in results:
        key = f"{run.model} / {run.output_paradigm}"
        print(
            f"{key}: corrected pairs={corrections[key]:,}; "
            f"M/C/S/N={scores.M:,}/{scores.C:,}/{scores.S:,}/{scores.N:,}; "
            f"Strict F1={scores.strict_f1:.4f}; "
            f"Adapted F1={scores.adapted_f1:.4f}"
        )


if __name__ == "__main__":
    main()
