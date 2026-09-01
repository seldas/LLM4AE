#!/usr/bin/env python3
"""Re-align saved FAERS BERT/LLM outputs under the formal bSYM -> Dx taxonomy.

This script performs no inference and no training. It reconstructs the saved
prediction spans from BERT ``raw.xlsx`` and LLaMA ``predictions.jsonl``, then
aligns them with the original SME1 annotations after normalizing baseline
symptoms to ``diagnostic``. The standard result workbooks are overwritten only
when ``--write`` is supplied.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

import pandas as pd

from run_FAERS_bert_LOO import align_and_classify_spans, summarize_evaluation


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
BSYM_TO_DX = {"bsym": "diagnostic"}
LLAMA_RAW_COLUMNS = [
    "document", "match_type", "label_gold", "gold_start", "gold_end", "gold_text",
    "label_pred", "pred_start", "pred_end", "pred_text",
]
LLAMA_EVAL_LABEL_POOL = {
    "ae": "AE", "mae": "AE", "sdrug": "DRUG", "cdrug": "DRUG", "odrug": "DRUG",
    "mhx": "HX", "fhx": "HX", "diagnostic": "DX", "treatment": "DX", "lab": "LAB",
    "dose": "DOSE", "status": "STATUS", "ro": "RO", "cod": "COD", "age": "AGE",
    "sex": "SEX", "indication": "INDICATION",
}
RAW_LABELS = {
    "ae": "ae", "mae": "mae", "sdrug": "sdrug", "cdrug": "cdrug", "odrug": "odrug",
    "drug": "odrug", "dose": "dose", "ind": "indication", "indication": "indication",
    "treatment": "treatment", "dx": "diagnostic", "diagnostic": "diagnostic", "lab": "lab",
    "status": "status", "r/o": "ro", "ro": "ro", "cod": "cod", "cause of death": "cod",
    "mhx": "mhx", "medical history": "mhx", "fhx": "fhx", "family history": "fhx",
    "age": "age", "sex": "sex", "bsym": "diagnostic", "baseline symptom": "diagnostic",
}


def normalize_label(value: object) -> str | None:
    if pd.isna(value):
        return None
    label = str(value).strip().lower()
    return BSYM_TO_DX.get(label, label)


def overlaps(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 == b0 or a1 == b1 or a0 < b0 < a1 or a0 < b1 < a1 or b0 < a0 < b1


def align_llama_entities(text: str, gold_ents: list[tuple], pred_ents: list[tuple]) -> list[dict]:
    """Match the legacy LLaMA M/C/S/N evaluator (same-label partial matches only)."""
    rows, used = [], [False] * len(pred_ents)
    for g0, g1, glab in sorted(gold_ents, key=lambda value: (value[0], value[1], value[2])):
        exact = partial = None
        best_overlap = 0
        for index, (p0, p1, plab) in enumerate(pred_ents):
            if used[index]:
                continue
            if (p0, p1, plab) == (g0, g1, glab):
                exact = index
                break
            if plab == glab and overlaps(g0, g1, p0, p1):
                overlap = max(0, min(g1, p1) - max(g0, p0))
                if overlap > best_overlap:
                    best_overlap, partial = overlap, index
        if exact is not None or partial is not None:
            index = exact if exact is not None else partial
            p0, p1, plab = pred_ents[index]
            used[index] = True
            rows.append({
                "match_type": "M" if exact is not None else "C", "label_gold": glab,
                "gold_start": g0, "gold_end": g1, "gold_text": text[g0:g1], "label_pred": plab,
                "pred_start": p0, "pred_end": p1, "pred_text": text[p0:p1],
            })
        else:
            rows.append({
                "match_type": "N", "label_gold": glab, "gold_start": g0, "gold_end": g1,
                "gold_text": text[g0:g1], "label_pred": None, "pred_start": None,
                "pred_end": None, "pred_text": None,
            })
    for index, (p0, p1, plab) in enumerate(pred_ents):
        if not used[index]:
            rows.append({
                "match_type": "S", "label_gold": None, "gold_start": None, "gold_end": None,
                "gold_text": None, "label_pred": plab, "pred_start": p0, "pred_end": p1,
                "pred_text": text[p0:p1],
            })
    return rows


def load_prediction_cache(path: Path) -> dict[str, dict]:
    cache = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("status") == "ok" and row.get("document"):
                cache[str(row["document"])] = row
    return cache


def load_llama_records(db_path: Path) -> tuple[list[dict], dict[str, list[dict]]]:
    """Load FAERS narratives and SME1 annotations from the canonical SQLite database."""
    with sqlite3.connect(db_path) as connection:
        documents = connection.execute(
            "SELECT doc_id, page_text FROM documents WHERE dataset = 'FAERS' ORDER BY doc_id"
        ).fetchall()
        annotations = connection.execute(
            "SELECT doc_id, label, tc_start, tc_end FROM annotations WHERE note = 'SME1'"
        ).fetchall()
    by_document: dict[str, list[dict]] = defaultdict(list)
    for doc_id, label, start, end in annotations:
        by_document[str(doc_id)].append({"label": label, "start": start, "end": end})
    return (
        [{"document": f"{doc_id}.json", "doc_id": str(doc_id), "text": str(text)} for doc_id, text in documents],
        by_document,
    )


def load_llama_gold(annotations: list[dict], text: str) -> list[tuple]:
    gold = []
    for annotation in annotations:
        label = RAW_LABELS.get(str(annotation.get("label", "")).strip().casefold())
        if label is None:
            continue
        try:
            start, end = int(annotation["start"]), int(annotation["end"])
        except (KeyError, TypeError, ValueError):
            continue
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if 0 <= start < end <= len(text):
            gold.append((start, end, label))
    return gold


def llama_weighted_prf(M: int, C: int, S: int, N: int) -> tuple[float, float, float]:
    credit = M + 0.5 * C
    precision = credit / (credit + 0.5 * C + 0.25 * S) if credit + 0.5 * C + 0.25 * S else 0.0
    recall = credit / (credit + 0.5 * C + N) if credit + 0.5 * C + N else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return round(precision, 4), round(recall, 4), round(f1, 4)


def compute_llama_metrics(raw: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    counts = raw["match_type"].value_counts().to_dict()
    M, C, S, N = (int(counts.get(kind, 0)) for kind in ("M", "C", "S", "N"))
    precision, recall, f1 = llama_weighted_prf(M, C, S, N)
    overall = {"M": M, "C": C, "S": S, "N": N, "precision": precision, "recall": recall, "f1": f1}
    labels = set(raw.loc[raw["match_type"].isin(["M", "C", "N"]), "label_gold"].dropna())
    labels.update(raw.loc[raw["match_type"] == "S", "label_pred"].dropna())
    rows = []
    for label in sorted(labels):
        values = [int(((raw["match_type"] == kind) & (raw["label_gold" if kind != "S" else "label_pred"] == label)).sum()) for kind in ("M", "C", "S", "N")]
        p, r, score = llama_weighted_prf(*values)
        rows.append({"label": label, "eval_category": LLAMA_EVAL_LABEL_POOL.get(label, label.upper()),
                     "M": values[0], "C": values[1], "S": values[2], "N": values[3],
                     "precision": p, "recall": r, "f1": score})
    return overall, pd.DataFrame(rows)


def build_collapsed_category_summary(per_label: pd.DataFrame) -> pd.DataFrame:
    grouped = per_label.groupby("eval_category", as_index=False).agg(M=("M", "sum"), C=("C", "sum"), S=("S", "sum"), N=("N", "sum"))
    grouped[["precision", "recall", "f1"]] = grouped.apply(
        lambda row: pd.Series(llama_weighted_prf(int(row.M), int(row.C), int(row.S), int(row.N))), axis=1
    )
    return grouped


def _unique_spans(rows: pd.DataFrame, prefix: str) -> list[tuple]:
    spans = []
    seen = set()
    for row in rows.itertuples(index=False):
        start, end = getattr(row, f"{prefix}_start"), getattr(row, f"{prefix}_end")
        label = normalize_label(getattr(row, f"label_{'gold' if prefix == 'gold' else 'pred'}"))
        if pd.isna(start) or pd.isna(end) or label is None:
            continue
        key = (int(start), int(end), label)
        if key not in seen:
            seen.add(key)
            spans.append(key)
    return spans


def reconcile_bert(bert_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Relabel BERT spans and re-align only bSYM/Dx collision documents."""
    source = pd.read_excel(bert_path, sheet_name="Raw_Results")
    required = {"label_gold", "label_pred", "match_type", "error_subtype"}
    missing = required.difference(source.columns)
    if missing:
        raise ValueError(f"{bert_path} is missing {sorted(missing)}")
    class_confusions = source[
        (source["match_type"] == "C") & (source["error_subtype"] == "class_confusion")
    ]
    gold = class_confusions["label_gold"].map(normalize_label)
    pred = class_confusions["label_pred"].map(normalize_label)
    collisions = class_confusions.loc[gold == pred, ["fold", "fold_name", "seed", "doc_idx"]].drop_duplicates()
    collision_keys = {tuple(row) for row in collisions.itertuples(index=False, name=None)}
    normalized = source.copy()
    normalized["label_gold"] = normalized["label_gold"].map(normalize_label)
    normalized["label_pred"] = normalized["label_pred"].map(normalize_label)
    rebuilt_rows = []
    for key in collision_keys:
        fold, fold_name, seed, doc_idx = key
        original = source[(source["fold"] == fold) & (source["fold_name"] == fold_name) & (source["seed"] == seed) & (source["doc_idx"] == doc_idx)]
        sentence = original["sentence"].iat[0]
        gold_spans = _unique_spans(original[original["match_type"].isin(["M", "C", "N"])], "gold")
        pred_spans = [(start, end, label, 1.0) for start, end, label in _unique_spans(original[original["match_type"].isin(["M", "C", "S"])], "pred")]
        for row in align_and_classify_spans(sentence, gold_spans, pred_spans):
            row.update({"fold": fold, "fold_name": fold_name, "seed": seed, "doc_idx": doc_idx, "sentence": sentence})
            rebuilt_rows.append(row)
    if collision_keys:
        key_frame = pd.DataFrame(list(collision_keys), columns=["fold", "fold_name", "seed", "doc_idx"])
        untouched = normalized.merge(key_frame.assign(_replace=True), on=["fold", "fold_name", "seed", "doc_idx"], how="left")
        untouched = untouched[untouched["_replace"].isna()].drop(columns="_replace")
        raw = pd.concat([untouched, pd.DataFrame(rebuilt_rows)], ignore_index=True)
    else:
        raw = normalized
    raw = raw[source.columns]

    overall_rows, category_frames = [], []
    for (fold, fold_name, seed), run in raw.groupby(["fold", "fold_name", "seed"], sort=True):
        overall, categories = summarize_evaluation(run, fold_idx=int(fold), fold_name=str(fold_name), seed=int(seed))
        overall_rows.append(overall)
        category_frames.append(categories)
    overall_df = pd.DataFrame(overall_rows).sort_values(["fold_name", "seed"]).reset_index(drop=True)
    categories = pd.concat(category_frames, ignore_index=True)
    fold_summary = overall_df.groupby(["fold_name", "test_case_series"], as_index=False).agg(
        runs=("seed", "nunique"), M=("M", "sum"), C_boundary=("C_boundary", "sum"),
        C_class=("C_class", "sum"), C_total=("C_total", "sum"), S_non_overlap=("S_non_overlap", "sum"), N=("N", "sum"),
        strict_F1_mean=("strict_F1", "mean"), strict_F1_std=("strict_F1", "std"),
        ade_F1_mean=("ade_F1", "mean"), ade_F1_std=("ade_F1", "std"),
    ).round(4)
    fold_summary[["strict_F1_std", "ade_F1_std"]] = fold_summary[["strict_F1_std", "ade_F1_std"]].fillna(0.0)
    category_summary = categories.groupby("category", as_index=False).agg(
        runs=("seed", "count"), M=("M", "sum"), C_boundary=("C_boundary", "sum"), C_class=("C_class", "sum"),
        C_total=("C_total", "sum"), S_non_overlap=("S_non_overlap", "sum"), N=("N", "sum"),
        strict_F1_mean=("strict_F1", "mean"), strict_F1_std=("strict_F1", "std"),
        ade_F1_mean=("ade_F1", "mean"), ade_F1_std=("ade_F1", "std"),
    ).round(4)
    category_summary[["strict_F1_std", "ade_F1_std"]] = category_summary[["strict_F1_std", "ade_F1_std"]].fillna(0.0)
    return raw, overall_df, fold_summary, categories, category_summary


def reconcile_llama(db_path: Path, predictions_path: Path) -> tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    cache = load_prediction_cache(predictions_path)
    all_rows, document_rows = [], []
    missing = []
    records, annotations = load_llama_records(db_path)
    for record in records:
        cached = cache.get(record["document"])
        if cached is None or cached.get("status") != "ok":
            missing.append(record["document"])
            continue
        gold = load_llama_gold(annotations.get(record["doc_id"], []), record["text"])
        predicted = [
            (int(span["start"]), int(span["end"]), normalize_label(span["label"]))
            for span in cached.get("predicted_entities", [])
        ]
        rows = align_llama_entities(record["text"], gold, predicted)
        for row in rows:
            row["document"] = record["document"]
        all_rows.extend(rows)
        counts = pd.Series([row["match_type"] for row in rows]).value_counts()
        document_rows.append({"document": record["document"], **{kind: int(counts.get(kind, 0)) for kind in ("M", "C", "S", "N")}})
    if missing:
        raise RuntimeError(f"Missing cached predictions for {len(missing)} documents; first: {missing[:5]}")
    raw = pd.DataFrame(all_rows).reindex(columns=LLAMA_RAW_COLUMNS)
    overall, per_label = compute_llama_metrics(raw)
    collapsed = build_collapsed_category_summary(per_label)
    return raw, overall, per_label, pd.DataFrame(document_rows), collapsed


def write_outputs(
    bert_dir: Path,
    bert_raw: pd.DataFrame,
    bert_overall: pd.DataFrame,
    bert_fold_summary: pd.DataFrame,
    bert_categories: pd.DataFrame,
    bert_category_summary: pd.DataFrame,
    llama_dir: Path,
    llama_raw: pd.DataFrame,
    llama_overall: dict,
    llama_per_label: pd.DataFrame,
    llama_per_document: pd.DataFrame,
    llama_collapsed: pd.DataFrame,
    sonnet_dir: Path | None = None,
    sonnet_raw: pd.DataFrame | None = None,
    sonnet_overall: dict | None = None,
    sonnet_per_label: pd.DataFrame | None = None,
    sonnet_per_document: pd.DataFrame | None = None,
    sonnet_collapsed: pd.DataFrame | None = None,
) -> None:
    with pd.ExcelWriter(bert_dir / "raw.xlsx", engine="openpyxl") as writer:
        bert_raw.to_excel(writer, sheet_name="Raw_Results", index=False)
    with pd.ExcelWriter(bert_dir / "metrics.xlsx", engine="openpyxl") as writer:
        bert_overall.to_excel(writer, sheet_name="All_Runs", index=False)
        bert_fold_summary.to_excel(writer, sheet_name="Fold_Summary", index=False)
        bert_categories.to_excel(writer, sheet_name="Per_Category", index=False)
        bert_category_summary.to_excel(writer, sheet_name="Category_Summary", index=False)
    with pd.ExcelWriter(llama_dir / "llama4_raw.xlsx", engine="openpyxl") as writer:
        llama_raw.to_excel(writer, sheet_name="Raw_Results", index=False)
    with pd.ExcelWriter(llama_dir / "llama4_metrics.xlsx", engine="openpyxl") as writer:
        pd.DataFrame([llama_overall]).to_excel(writer, sheet_name="Overall", index=False)
        llama_per_label.to_excel(writer, sheet_name="Per_Label", index=False)
        llama_collapsed.to_excel(writer, sheet_name="Collapsed_Category", index=False)
        llama_per_document.to_excel(writer, sheet_name="Per_Document", index=False)
    if sonnet_dir and sonnet_raw is not None and sonnet_overall is not None:
        with pd.ExcelWriter(sonnet_dir / "sonnet_raw.xlsx", engine="openpyxl") as writer:
            sonnet_raw.to_excel(writer, sheet_name="Raw_Results", index=False)
        with pd.ExcelWriter(sonnet_dir / "sonnet_metrics.xlsx", engine="openpyxl") as writer:
            pd.DataFrame([sonnet_overall]).to_excel(writer, sheet_name="Overall", index=False)
            if sonnet_per_label is not None:
                sonnet_per_label.to_excel(writer, sheet_name="Per_Label", index=False)
            if sonnet_collapsed is not None:
                sonnet_collapsed.to_excel(writer, sheet_name="Collapsed_Category", index=False)
            if sonnet_per_document is not None:
                sonnet_per_document.to_excel(writer, sheet_name="Per_Document", index=False)
    print("Wrote normalized BERT, LLaMA, and Sonnet result workbooks.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Overwrite standard result workbooks.")
    parser.add_argument("--db-path", type=Path, default=PROJECT_ROOT / "dataset.db")
    args = parser.parse_args()
    bert_dir = RESULTS_DIR / "bert_runs_FAERS_LOO"
    llama_dir = RESULTS_DIR / "llama4_runs_FAERS"
    sonnet_dir = RESULTS_DIR / "sonnet_runs_FAERS"
    bert_raw, bert_overall, bert_folds, bert_categories, bert_category_summary = reconcile_bert(bert_dir / "raw.xlsx")
    llama_raw, llama_overall, llama_labels, llama_docs, llama_collapsed = reconcile_llama(
        args.db_path, llama_dir / "predictions.jsonl"
    )
    sonnet_raw, sonnet_overall, sonnet_labels, sonnet_docs, sonnet_collapsed = reconcile_llama(
        args.db_path, sonnet_dir / "predictions.jsonl"
    )
    print("BERT run rows:", len(bert_raw), "| seed 42:", bert_raw[bert_raw["seed"] == 42]["match_type"].value_counts().to_dict())
    print("LLaMA rows:", len(llama_raw), "| counts:", llama_raw["match_type"].value_counts().to_dict())
    print("Sonnet rows:", len(sonnet_raw), "| counts:", sonnet_raw["match_type"].value_counts().to_dict())
    if args.write:
        write_outputs(bert_dir, bert_raw, bert_overall, bert_folds, bert_categories, bert_category_summary,
                      llama_dir, llama_raw, llama_overall, llama_labels, llama_docs, llama_collapsed,
                      sonnet_dir, sonnet_raw, sonnet_overall, sonnet_labels, sonnet_docs, sonnet_collapsed)
    else:
        print("Dry run only. Re-run with --write to overwrite result workbooks.")


if __name__ == "__main__":
    main()

