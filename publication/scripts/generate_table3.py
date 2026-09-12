#!/usr/bin/env python3
"""Generate the updated manuscript Table 3 from current raw data.

The manuscript document is used only as a structural reference. All reported
metrics are recomputed at runtime from these canonical sources:

* BERT: ``publication/results/bert_runs_FAERS_LOO/raw.xlsx``
* LLaMA-4: ``publication/results/llama4_runs_FAERS/llama4_raw.xlsx``
* Sonnet: ``publication/results/sonnet_runs_FAERS/sonnet_raw.xlsx``
* ETHER and SME1 gold: ``publication/dataset.db``

Default output:
    publication/manuscripts/Tables/table3_faers_performance.csv
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


MATCH_TYPES = ("M", "C", "S", "N")
DEFAULT_SEED = 42
EXPECTED_BERT_FOLDS = {
    "Azacitidine-QT",
    "Tramadol-Hypoglycemia",
    "Baricitinib-Hypersensitivity",
    "Erenumab-Stroke",
}

GOLD_CATEGORY_MAP = {
    "ae": "AE",
    "mae": "AE",
    "sdrug": "DRUG",
    "cdrug": "DRUG",
    "odrug": "DRUG",
    "drug": "DRUG",
    "treatment": "DX",
    "bsym": "DX",
    "baseline symptom": "DX",
    "diagnostic": "DX",
    "dx": "DX",
    "mhx": "HX",
    "medical history": "HX",
    "fhx": "HX",
    "family history": "HX",
    "indication": "INDICATION",
    "lab": "LAB",
    "dose": "DOSE",
    "age": "AGE",
    "sex": "SEX",
    "status": "STATUS",
    "r/o": "RO",
    "ro": "RO",
    "cause of death": "COD",
    "cod": "COD",
}

ETHER_CATEGORY_MAP = {
    "symptom": "AE",
    "drug": "DRUG",
    "vaccine": "DRUG",
    "diagnosis": "DX",
    "second_level_diagnosis": "DX",
    "medical_history": "HX",
    "family_history": "HX",
    "rule_out": "RO",
    "cause_of_death": "COD",
}


@dataclass(frozen=True)
class Scores:
    M: int
    C: int
    S: int
    N: int
    strict_precision: float
    strict_recall: float
    strict_f1: float
    adapted_precision: float
    adapted_recall: float
    adapted_f1: float


def canonical_label(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip().lower()


def spans_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return (
        a_start == b_start
        or a_end == b_end
        or a_start < b_start < a_end
        or a_start < b_end < a_end
        or b_start < a_start < b_end
    )


def span_iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    intersection = max(0, min(a_end, b_end) - max(a_start, b_start))
    union = max(a_end, b_end) - min(a_start, b_start)
    return intersection / union if union else 0.0


def calculate_scores(M: int, C: int, S: int, N: int) -> Scores:
    strict_p_den = M + C + S
    strict_r_den = M + C + N
    strict_precision = M / strict_p_den if strict_p_den else 0.0
    strict_recall = M / strict_r_den if strict_r_den else 0.0
    strict_f1 = (
        2 * strict_precision * strict_recall / (strict_precision + strict_recall)
        if strict_precision + strict_recall
        else 0.0
    )

    matched_credit = M + 0.5 * C
    adapted_p_den = M + C + 0.25 * S
    adapted_r_den = M + C + N
    adapted_precision = matched_credit / adapted_p_den if adapted_p_den else 0.0
    adapted_recall = matched_credit / adapted_r_den if adapted_r_den else 0.0
    adapted_f1 = (
        2 * adapted_precision * adapted_recall / (adapted_precision + adapted_recall)
        if adapted_precision + adapted_recall
        else 0.0
    )
    return Scores(
        M=M,
        C=C,
        S=S,
        N=N,
        strict_precision=strict_precision,
        strict_recall=strict_recall,
        strict_f1=strict_f1,
        adapted_precision=adapted_precision,
        adapted_recall=adapted_recall,
        adapted_f1=adapted_f1,
    )


def read_raw_workbook(path: Path, required_columns: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Raw workbook not found: {path}")
    frame = pd.read_excel(path, sheet_name="Raw_Results")
    missing = required_columns.difference(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")
    unknown = set(frame["match_type"].dropna().unique()).difference(MATCH_TYPES)
    if unknown:
        raise ValueError(f"{path} has unknown match types: {sorted(unknown)}")
    return frame


def match_type_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = frame["match_type"].value_counts()
    return {kind: int(counts.get(kind, 0)) for kind in MATCH_TYPES}


def bert_scores(path: Path, seed: int) -> Scores:
    """Pool all four LOO folds for one seed and calculate micro scores."""
    required = {"fold_name", "seed", "match_type"}
    frame = read_raw_workbook(path, required)

    available_seeds = sorted(int(value) for value in frame["seed"].dropna().unique())
    if seed not in available_seeds:
        raise ValueError(
            f"BERT seed {seed} not found; available: {available_seeds}"
        )
    selected = frame.loc[frame["seed"] == seed]
    actual_folds = set(selected["fold_name"].dropna().astype(str).unique())
    if actual_folds != EXPECTED_BERT_FOLDS:
        raise ValueError(
            f"Unexpected BERT folds for seed {seed}; expected "
            f"{sorted(EXPECTED_BERT_FOLDS)}, found {sorted(actual_folds)}"
        )
    return calculate_scores(**match_type_counts(selected))


def corrected_llm_scores(path: Path) -> tuple[Scores, int]:
    """Collapse one-to-one overlapping wrong-label N/S pairs into C."""
    required = {
        "document",
        "match_type",
        "label_gold",
        "gold_start",
        "gold_end",
        "label_pred",
        "pred_start",
        "pred_end",
    }
    frame = read_raw_workbook(path, required)

    correction_count = 0
    for _, rows in frame.groupby("document", sort=False):
        unmatched_gold = []
        for row in rows.loc[rows["match_type"] == "N"].itertuples(index=False):
            if pd.notna(row.gold_start) and pd.notna(row.gold_end):
                unmatched_gold.append(
                    (int(row.gold_start), int(row.gold_end), canonical_label(row.label_gold))
                )
        unmatched_gold.sort(key=lambda span: (span[0], span[1], span[2]))

        predictions = [
            row
            for row in rows.loc[rows["match_type"] == "S"].itertuples(index=False)
            if pd.notna(row.pred_start) and pd.notna(row.pred_end)
        ]
        candidate_edges: list[list[int]] = []
        for gold_start, gold_end, gold_label in unmatched_gold:
            candidates = []
            for prediction_index, prediction in enumerate(predictions):
                pred_start = int(prediction.pred_start)
                pred_end = int(prediction.pred_end)
                pred_label = canonical_label(prediction.label_pred)
                if (
                    gold_label != pred_label
                    and spans_overlap(pred_start, pred_end, gold_start, gold_end)
                ):
                    candidates.append(prediction_index)
            candidates.sort(
                key=lambda prediction_index: (
                    -span_iou(
                        int(predictions[prediction_index].pred_start),
                        int(predictions[prediction_index].pred_end),
                        gold_start,
                        gold_end,
                    ),
                    int(predictions[prediction_index].pred_start),
                    int(predictions[prediction_index].pred_end),
                    canonical_label(predictions[prediction_index].label_pred),
                )
            )
            candidate_edges.append(candidates)

        prediction_to_gold: dict[int, int] = {}

        def augment(gold_index: int, visited: set[int]) -> bool:
            for prediction_index in candidate_edges[gold_index]:
                if prediction_index in visited:
                    continue
                visited.add(prediction_index)
                previous_gold = prediction_to_gold.get(prediction_index)
                if previous_gold is None or augment(previous_gold, visited):
                    prediction_to_gold[prediction_index] = gold_index
                    return True
            return False

        for gold_index in range(len(unmatched_gold)):
            augment(gold_index, set())
        correction_count += len(prediction_to_gold)

    counts = match_type_counts(frame)
    if correction_count > counts["S"] or correction_count > counts["N"]:
        raise ValueError("Wrong-label correction exceeds available S/N outcomes")
    counts["C"] += correction_count
    counts["S"] -= correction_count
    counts["N"] -= correction_count
    return calculate_scores(**counts), correction_count


def load_ether_inputs(
    connection: sqlite3.Connection,
) -> tuple[dict[str, list[tuple]], dict[str, list[tuple]]]:
    gold_rows = connection.execute(
        """
        SELECT a.doc_id, lower(trim(a.label)), a.tc_start, a.tc_end
        FROM annotations AS a
        JOIN documents AS d ON d.doc_id = a.doc_id
        WHERE d.dataset = 'FAERS' AND a.note = 'SME1'
        """
    ).fetchall()
    prediction_rows = connection.execute(
        """
        SELECT a.doc_id, lower(trim(a.label)), a.tc_start, a.tc_end, a.used
        FROM annotations AS a
        JOIN documents AS d ON d.doc_id = a.doc_id
        WHERE d.dataset = 'FAERS' AND a.note = 'ETHER'
        """
    ).fetchall()

    gold_by_document: dict[str, list[tuple]] = defaultdict(list)
    for document, label, start, end in gold_rows:
        category = GOLD_CATEGORY_MAP.get(str(label))
        if category is not None:
            gold_by_document[str(document)].append((int(start), int(end), category))

    pred_by_document: dict[str, list[tuple]] = defaultdict(list)
    for document, label, start, end, used in prediction_rows:
        category = ETHER_CATEGORY_MAP.get(str(label))
        if category is not None and str(used).strip().lower() == "yes":
            pred_by_document[str(document)].append((int(start), int(end), category))
    return gold_by_document, pred_by_document


def ether_scores(database_path: Path) -> Scores:
    if not database_path.is_file():
        raise FileNotFoundError(f"Database not found: {database_path}")
    with sqlite3.connect(database_path) as connection:
        gold_by_document, pred_by_document = load_ether_inputs(connection)

    M = C = S = N = 0
    for document, gold_spans in gold_by_document.items():
        predictions = pred_by_document.get(document, [])
        prediction_matched = [False] * len(predictions)

        for gold_start, gold_end, gold_category in gold_spans:
            exact_index = None
            partial_index = None
            best_overlap = 0
            for index, (pred_start, pred_end, pred_category) in enumerate(predictions):
                if prediction_matched[index]:
                    continue
                if (
                    pred_start == gold_start
                    and pred_end == gold_end
                    and pred_category == gold_category
                ):
                    exact_index = index
                    break
                if pred_category == gold_category and spans_overlap(
                    gold_start, gold_end, pred_start, pred_end
                ):
                    overlap_length = max(
                        0, min(gold_end, pred_end) - max(gold_start, pred_start)
                    )
                    if overlap_length > best_overlap:
                        best_overlap = overlap_length
                        partial_index = index

            if exact_index is not None:
                M += 1
                prediction_matched[exact_index] = True
            elif partial_index is not None:
                C += 1
                prediction_matched[partial_index] = True
            else:
                N += 1

        S += sum(not matched for matched in prediction_matched)
    return calculate_scores(M, C, S, N)


def format_score(value: float) -> str:
    return f"{value:.4f}"


def table_rows(
    bert: Scores,
    llama: Scores,
    sonnet: Scores,
    ether: Scores,
) -> list[list[str]]:
    return [
        ["Model", "Strict Exact F1", "Adapted ADE-Eval F1"],
        [
            f"BERT (seed {DEFAULT_SEED})",
            format_score(bert.strict_f1),
            format_score(bert.adapted_f1),
        ],
        ["LLaMA-4", format_score(llama.strict_f1), format_score(llama.adapted_f1)],
        [
            "Claude 4.6 Sonnet",
            format_score(sonnet.strict_f1),
            format_score(sonnet.adapted_f1),
        ],
        ["ETHER", format_score(ether.strict_f1), format_score(ether.adapted_f1)],
    ]


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    results = repo_root / "publication" / "results"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=repo_root / "publication" / "dataset.db",
    )
    parser.add_argument(
        "--bert-raw",
        type=Path,
        default=results / "bert_runs_FAERS_LOO" / "raw.xlsx",
    )
    parser.add_argument(
        "--llama-raw",
        type=Path,
        default=results / "llama4_runs_FAERS" / "llama4_raw.xlsx",
    )
    parser.add_argument(
        "--sonnet-raw",
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
            / "table3_faers_performance.csv"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bert = bert_scores(args.bert_raw.resolve(), DEFAULT_SEED)
    llama, llama_corrections = corrected_llm_scores(args.llama_raw.resolve())
    sonnet, sonnet_corrections = corrected_llm_scores(args.sonnet_raw.resolve())
    ether = ether_scores(args.database.resolve())

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(
            table_rows(bert, llama, sonnet, ether)
        )

    print(f"Generated updated manuscript Table 3: {output_path}")
    print(
        "Corrected overlapping wrong-label pairs: "
        f"LLaMA-4={llama_corrections:,}, Sonnet={sonnet_corrections:,}"
    )
    print(
        f"LLaMA-4 corrected M/C/S/N: {llama.M:,}/{llama.C:,}/{llama.S:,}/{llama.N:,}"
    )
    print(
        f"Sonnet corrected M/C/S/N: {sonnet.M:,}/{sonnet.C:,}/{sonnet.S:,}/{sonnet.N:,}"
    )
    print(f"ETHER M/C/S/N: {ether.M:,}/{ether.C:,}/{ether.S:,}/{ether.N:,}")


if __name__ == "__main__":
    main()
