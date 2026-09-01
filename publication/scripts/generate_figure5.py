#!/usr/bin/env python3
"""Generate the reproducible FAERS error-analysis Figure 5.

All data come from current raw evaluator outputs, not a legacy aggregate:
``results/llama4_runs_FAERS/llama4_raw.xlsx`` and the requested seed from
``results/bert_runs_FAERS_LOO/raw.xlsx``. The LOO evaluator already records
class confusions as C. The legacy LLaMA evaluator instead leaves wrong-label
overlaps as one S row plus one N row, so this script deterministically collapses
each one-to-one overlapping S/N wrong-label pair into C. Panels (a)--(e) are
generated from these source-derived data.
"""

from __future__ import annotations

import json
import os
import tempfile
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Sequence

# Keep Matplotlib's cache outside the repository and avoid a locked home cache.
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "llm4ae-matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from wordcloud import WordCloud


MATCH_TYPES = ("M", "C", "S", "N")
REQUIRED_COLUMNS = {
    "match_type", "label_gold", "gold_start", "gold_end", "gold_text",
    "label_pred", "pred_start", "pred_end", "pred_text",
}
LABEL_DISPLAY = {
    "ae": "AE", "age": "Age", "bsym": "Baseline symptom", "cdrug": "cDrug",
    "cod": "CoD", "diagnostic": "Dx", "dose": "Dose", "fhx": "FHx",
    "indication": "Indication", "lab": "Lab", "mae": "mAE", "mhx": "MHx",
    "odrug": "oDrug", "ro": "R/O", "sdrug": "sDrug", "sex": "Sex",
    "status": "Status", "temporal": "Temporal", "treatment": "Treatment",
}


def canonical_label(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip().lower()


def display_label(label: str) -> str:
    return LABEL_DISPLAY.get(label, label)


def normalize_term(value: object) -> str:
    return "" if pd.isna(value) else " ".join(str(value).lower().split())


def spans_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Match the endpoint-overlap logic used by the evaluator scripts."""
    return (
        a_start == b_start or a_end == b_end or a_start < b_start < a_end
        or a_start < b_end < a_end or b_start < a_start < b_end
    )


def span_iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    intersection = max(0, min(a_end, b_end) - max(a_start, b_start))
    union = max(a_end, b_end) - min(a_start, b_start)
    return intersection / union if union else 0.0


def read_raw_workbook(path: Path, group_columns: Sequence[str]) -> pd.DataFrame:
    """Read and validate one raw-result workbook without changing it."""
    if not path.exists():
        raise FileNotFoundError(f"Missing raw result workbook: {path}")
    frame = pd.read_excel(path, sheet_name="Raw_Results")
    missing = REQUIRED_COLUMNS.union(group_columns).difference(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")
    unknown = set(frame["match_type"].dropna().unique()).difference(MATCH_TYPES)
    if unknown:
        raise ValueError(f"{path} has unknown match types: {sorted(unknown)}")
    return frame


def load_inputs(
    repo_root: Path,
    bert_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, Path]:
    results_dir = repo_root / "publication" / "results"
    llama_path = results_dir / "llama4_runs_FAERS" / "llama4_raw.xlsx"
    bert_path = results_dir / "bert_runs_FAERS_LOO" / "raw.xlsx"
    llama = read_raw_workbook(llama_path, ("document",))
    bert_all = read_raw_workbook(bert_path, ("fold_name", "seed", "doc_idx"))
    if "seed" not in bert_all.columns:
        raise ValueError(f"{bert_path} does not include the required seed column")
    bert = bert_all.loc[bert_all["seed"] == bert_seed].copy()
    if bert.empty:
        available = sorted(int(seed) for seed in bert_all["seed"].dropna().unique())
        raise ValueError(f"BERT seed {bert_seed} is absent from {bert_path}; available seeds: {available}")
    return llama, bert, bert_path


def match_type_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = frame["match_type"].value_counts()
    return {code: int(counts.get(code, 0)) for code in MATCH_TYPES}


def correct_label_mismatches(
    frame: pd.DataFrame,
    group_columns: Sequence[str],
) -> tuple[dict[str, int], pd.DataFrame]:
    """Reclassify one-to-one overlapping N/S label errors as C outcomes.

    Only unmatched gold spans (N) and unmatched predictions (S) are candidates.
    We compute a maximum-cardinality bipartite matching between N and S spans,
    so no correctable label error is left as S merely because it competed with
    another nearby span. Candidate edges are ordered by overlap quality for
    deterministic tie-breaking. Each selected pair becomes one C outcome,
    preventing double counting as both a miss and a spurious prediction.
    """
    groups: dict[tuple[object, ...], list[object]] = defaultdict(list)
    for row in frame.itertuples(index=False):
        groups[tuple(getattr(row, column) for column in group_columns)].append(row)

    records: list[dict[str, object]] = []
    for group_key, rows in groups.items():
        unmatched_gold = []
        for row in rows:
            if row.match_type == "N" and pd.notna(row.gold_start) and pd.notna(row.gold_end):
                unmatched_gold.append(
                    (int(row.gold_start), int(row.gold_end), canonical_label(row.label_gold), str(row.gold_text))
                )
        unmatched_gold.sort(key=lambda span: (span[0], span[1], span[2]))
        predictions = [
            row for row in rows
            if row.match_type == "S" and pd.notna(row.pred_start) and pd.notna(row.pred_end)
        ]
        candidate_edges: list[list[int]] = []
        for gold_start, gold_end, gold_label, _ in unmatched_gold:
            candidates = []
            for pred_index, prediction in enumerate(predictions):
                pred_start, pred_end = int(prediction.pred_start), int(prediction.pred_end)
                if gold_label != canonical_label(prediction.label_pred) and spans_overlap(pred_start, pred_end, gold_start, gold_end):
                    candidates.append(pred_index)
            candidates.sort(
                key=lambda pred_index: (
                    -span_iou(int(predictions[pred_index].pred_start), int(predictions[pred_index].pred_end), gold_start, gold_end),
                    -(min(int(predictions[pred_index].pred_end), gold_end) - max(int(predictions[pred_index].pred_start), gold_start)),
                    int(predictions[pred_index].pred_start),
                    int(predictions[pred_index].pred_end),
                    canonical_label(predictions[pred_index].label_pred),
                )
            )
            candidate_edges.append(candidates)

        prediction_to_gold: dict[int, int] = {}

        def augment(gold_index: int, visited_predictions: set[int]) -> bool:
            for pred_index in candidate_edges[gold_index]:
                if pred_index in visited_predictions:
                    continue
                visited_predictions.add(pred_index)
                matched_gold = prediction_to_gold.get(pred_index)
                if matched_gold is None or augment(matched_gold, visited_predictions):
                    prediction_to_gold[pred_index] = gold_index
                    return True
            return False

        for gold_index in range(len(unmatched_gold)):
            augment(gold_index, set())

        for pred_index, gold_index in sorted(prediction_to_gold.items(), key=lambda item: item[1]):
            gold_start, gold_end, gold_label, gold_text = unmatched_gold[gold_index]
            prediction = predictions[pred_index]
            score = span_iou(int(prediction.pred_start), int(prediction.pred_end), gold_start, gold_end)
            records.append(
                {
                    "source_group": "|".join(str(value) for value in group_key),
                    "label_gold": gold_label,
                    "label_pred": canonical_label(prediction.label_pred),
                    "gold_text": gold_text,
                    "pred_text": str(prediction.pred_text),
                    "iou": score,
                }
            )
    corrected = match_type_counts(frame)
    correction_count = len(records)
    if correction_count > corrected["S"] or correction_count > corrected["N"]:
        raise ValueError("Cannot reclassify more N/S pairs than exist in the raw results")
    corrected["C"] += correction_count
    corrected["S"] -= correction_count
    corrected["N"] -= correction_count
    expected_corrected_total = len(frame) - correction_count
    if sum(corrected.values()) != expected_corrected_total:
        raise ValueError("Corrected M/C/S/N counts do not reconcile after collapsing S/N pairs")
    return corrected, pd.DataFrame(
        records,
        columns=["source_group", "label_gold", "label_pred", "gold_text", "pred_text", "iou"],
    )


def recorded_class_confusions(
    frame: pd.DataFrame,
    group_columns: Sequence[str],
) -> pd.DataFrame:
    """Return class confusions directly recorded as C by the current evaluator."""
    columns = ["source_group", "label_gold", "label_pred", "gold_text", "pred_text", "iou"]
    if "error_subtype" not in frame.columns:
        return pd.DataFrame(columns=columns)
    rows = frame.loc[
        (frame["match_type"] == "C") & (frame["error_subtype"] == "class_confusion")
    ]
    if rows.empty:
        return pd.DataFrame(columns=columns)
    records = []
    for row in rows.itertuples(index=False):
        records.append({
            "source_group": "|".join(str(getattr(row, column)) for column in group_columns),
            "label_gold": canonical_label(row.label_gold),
            "label_pred": canonical_label(row.label_pred),
            "gold_text": str(row.gold_text),
            "pred_text": str(row.pred_text),
            "iou": span_iou(int(row.gold_start), int(row.gold_end), int(row.pred_start), int(row.pred_end)),
        })
    return pd.DataFrame(records, columns=columns)


def top_confusions(confusions: pd.DataFrame, top_k: int = 8) -> list[tuple[str, int]]:
    if confusions.empty:
        return []
    counts = confusions.groupby(["label_gold", "label_pred"]).size().sort_values(ascending=False).head(top_k)
    return [
        (f"{display_label(gold)} → {display_label(pred)}", int(count))
        for (gold, pred), count in counts.items()
    ]


def term_frequencies(confusions: pd.DataFrame, pairs: set[tuple[str, str]]) -> Counter[str]:
    if confusions.empty:
        return Counter()
    selected = confusions[
        confusions.apply(lambda row: (row["label_gold"], row["label_pred"]) in pairs, axis=1)
    ]
    return Counter(term for term in selected["gold_text"].map(normalize_term) if term)


def plot_confusion_bars(axis, pairs: list[tuple[str, int]], color: str, title: str) -> None:
    axis.set_title(title, fontsize=12.5, fontweight="bold", loc="left", pad=10)
    if not pairs:
        axis.text(0.5, 0.5, "No label confusions found", ha="center", va="center", fontsize=11)
        axis.set_axis_off()
        return
    pairs = list(reversed(pairs))
    labels, values = zip(*pairs)
    y = np.arange(len(labels))
    axis.barh(y, values, height=0.62, color=color, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    maximum = max(values)
    padding = max(1.0, maximum * 0.15)
    for position, value in zip(y, values):
        axis.text(value + padding * 0.06, position, f"{value:,}", va="center", ha="left", fontsize=9.5, fontweight="bold", color=color)
    axis.set_yticks(y)
    axis.set_yticklabels(labels, fontsize=10, fontweight="bold")
    axis.set_xlim(0, maximum + padding)
    axis.set_xlabel("Number of label confusions", fontsize=10.5, fontweight="bold")
    axis.set_ylabel("Gold → predicted", fontsize=10.5, fontweight="bold")
    axis.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)


def plot_word_cloud(axis, frequencies: Counter[str], colormap: str, title: str, max_words: int = 25) -> None:
    axis.set_title(title, fontsize=12, fontweight="bold", pad=8)
    if not frequencies:
        axis.text(0.5, 0.5, "No matching terms found", ha="center", va="center", fontsize=11)
        axis.axis("off")
        return
    cloud = WordCloud(
        width=800, height=450, background_color="white", colormap=colormap,
        random_state=42, max_words=max_words, prefer_horizontal=0.9, collocations=False,
    ).generate_from_frequencies(frequencies)
    axis.imshow(cloud, interpolation="bilinear")
    axis.axis("off")


def save_audit_data(
    output_path: Path,
    llama_path: Path,
    bert_path: Path,
    bert_seed: int,
    bert_raw_counts: dict[str, int],
    llama_raw_counts: dict[str, int],
    bert_counts: dict[str, int],
    llama_counts: dict[str, int],
    bert_top: list[tuple[str, int]],
    llama_top: list[tuple[str, int]],
    drug_terms: Counter[str],
    history_terms: Counter[str],
) -> None:
    repo_root = llama_path.parents[3]
    payload = {
        "inputs": {
            "llama4_raw": str(llama_path.relative_to(repo_root)),
            "bert_raw": str(bert_path.relative_to(repo_root)),
            "bert_seed": bert_seed,
        },
        "raw_match_type_counts": {"BERT": bert_raw_counts, "LLaMA_4": llama_raw_counts},
        "corrected_match_type_counts": {
            "BERT": bert_counts,
            "LLaMA_4": llama_counts,
        },
        "correction_rule": "Each one-to-one overlapping raw N/S pair with different labels is reclassified as C (Conflation).",
        "reclassified_N_S_pairs": {
            "BERT": bert_raw_counts["S"] - bert_counts["S"],
            "LLaMA_4": llama_raw_counts["S"] - llama_counts["S"],
        },
        "top_conflation_types": {"BERT": bert_top, "LLaMA_4": llama_top},
        "word_cloud_term_frequencies": {
            "cDrug_or_Treatment_to_sDrug": dict(drug_terms.most_common(25)),
            "MHx_Dx_AE_confusions": dict(history_terms.most_common(25)),
        },
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bert-seed", type=int, default=42,
        help="LOO BERT random seed to include in Figure 5 (default: 42).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    results_dir = repo_root / "publication" / "results"
    figures_dir = results_dir / "figures"
    manuscript_dir = repo_root / "publication" / "manuscripts"
    figures_dir.mkdir(parents=True, exist_ok=True)

    llama, bert, bert_path = load_inputs(repo_root, args.bert_seed)
    llama_path = results_dir / "llama4_runs_FAERS" / "llama4_raw.xlsx"
    bert_raw_counts = match_type_counts(bert)
    llama_raw_counts = match_type_counts(llama)
    bert_counts, _ = correct_label_mismatches(bert, ("fold_name", "seed", "doc_idx"))
    bert_confusions = recorded_class_confusions(bert, ("fold_name", "seed", "doc_idx"))
    llama_counts, llama_confusions = correct_label_mismatches(llama, ("document",))
    bert_top = top_confusions(bert_confusions)
    llama_top = top_confusions(llama_confusions)
    drug_terms = term_frequencies(llama_confusions, {("cdrug", "sdrug"), ("treatment", "sdrug")})
    history_terms = term_frequencies(
        llama_confusions,
        {("mhx", "diagnostic"), ("mhx", "ae"), ("ae", "diagnostic"), ("ae", "mhx")},
    )

    print("BERT raw M/C/S/N:", bert_raw_counts)
    print("BERT corrected M/C/S/N:", bert_counts)
    print("BERT source: LOO seed", args.bert_seed)
    print("LLaMA 4 raw M/C/S/N:", llama_raw_counts)
    print("LLaMA 4 corrected M/C/S/N:", llama_counts)
    print("BERT recorded class confusions:", len(bert_confusions))
    print("LLaMA 4 S/N-to-C corrections:", len(llama_confusions))
    print("LLaMA 4 panel (d) terms:", sum(drug_terms.values()))
    print("LLaMA 4 panel (e) terms:", sum(history_terms.values()))

    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Calibri", "DejaVu Sans", "Helvetica"]
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 0.9
    bert_color, llama_color = "#1F77B4", "#FF6F61"

    figure = plt.figure(figsize=(15, 14), dpi=300)
    grid = figure.add_gridspec(3, 2, height_ratios=[1.0, 1.1, 1.0], hspace=0.34, wspace=0.24)
    axis_a = figure.add_subplot(grid[0, :])
    error_labels = ["M: Exact Match", "C: Conflation", "S: Spurious Prediction", "N: Miss"]
    bert_values = [bert_counts[code] for code in MATCH_TYPES]
    llama_values = [llama_counts[code] for code in MATCH_TYPES]
    x, width = np.arange(len(MATCH_TYPES)), 0.35
    axis_a.bar(x - width / 2, bert_values, width, label="BERT", color=bert_color, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    axis_a.bar(x + width / 2, llama_values, width, label="LLM (LLaMA 4)", color=llama_color, alpha=0.92, edgecolor="#111", linewidth=0.7, zorder=2)
    for index, code in enumerate(MATCH_TYPES):
        axis_a.text(x[index] - width / 2, bert_values[index] + 300, f"{bert_counts[code]:,}", ha="center", va="bottom", fontsize=9.2, fontweight="bold", color="#0B3C5D")
        axis_a.text(x[index] + width / 2, llama_values[index] + 300, f"{llama_counts[code]:,}", ha="center", va="bottom", fontsize=9.2, fontweight="bold", color="#922B21")
    axis_a.set_title("(a) M/C/S/N Error Distribution for BERT vs. LLM (LLaMA 4)", fontsize=13, fontweight="bold", loc="left", pad=12)
    axis_a.set_xticks(x)
    axis_a.set_xticklabels(error_labels, fontsize=11, fontweight="bold")
    axis_a.set_ylim(0, max(max(bert_values), max(llama_values)) * 1.16)
    axis_a.set_ylabel("Number of alignment outcomes", fontsize=11, fontweight="bold")
    axis_a.set_xlabel("Error type", fontsize=11, fontweight="bold", labelpad=6)
    axis_a.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    axis_a.legend(title="Model", title_fontsize=10, loc="upper right", fontsize=10, framealpha=0.95)

    plot_confusion_bars(figure.add_subplot(grid[1, 0]), bert_top, bert_color, "(b) Top Conflation Types (Misclassification Labels) - BERT")
    plot_confusion_bars(figure.add_subplot(grid[1, 1]), llama_top, llama_color, "(c) Top Conflation Types (Misclassification Labels) - LLM")
    plot_word_cloud(figure.add_subplot(grid[2, 0]), drug_terms, "Blues", "(d) cDrug / Treatment Terms Misclassified as sDrug by LLM", max_words=25)
    plot_word_cloud(figure.add_subplot(grid[2, 1]), history_terms, "Reds", "(e) MHx ↔ Dx / AE Confusion Terms by LLM", max_words=25)
    figure.subplots_adjust(left=0.08, right=0.98, bottom=0.05, top=0.96)

    output_paths = [
        figures_dir / "figure5.png",
        manuscript_dir / "Figures" / "figure5.png",
        manuscript_dir / "figure5.png",
    ]
    primary_out = output_paths[0]
    primary_out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(primary_out, dpi=300, bbox_inches="tight")
    print(f"Saved figure: {primary_out}")
    plt.close(figure)

    import shutil
    for out_path in output_paths[1:]:
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(primary_out), str(out_path))
            print(f"Saved figure: {out_path}")
        except Exception as e:
            print(f"Warning: Could not copy figure to {out_path}: {e}")

    audit_path = figures_dir / "figure5_data.json"
    save_audit_data(
        audit_path, llama_path, bert_path, args.bert_seed,
        bert_raw_counts, llama_raw_counts, bert_counts, llama_counts,
        bert_top, llama_top, drug_terms, history_terms,
    )
    print("Saved Figure 5:")
    for path in output_paths:
        print(f"  - {path}")
    print(f"Saved audit data: {audit_path}")


if __name__ == "__main__":
    main()
