#!/usr/bin/env python3
"""Classify FAERS reports into four drug-event case series with audit evidence.

The classifier uses only ``publication/dataset.db``. It does not enforce the
historical 200/200/229/200 cohort sizes. Each assignment includes the matched
drug/event evidence, runner-up score, confidence, and a manual-review flag.

Default output:
    publication/results/faers_case_series_classification.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PairDefinition:
    drug_patterns: tuple[tuple[str, str], ...]
    event_patterns: tuple[tuple[str, str], ...]


PAIR_DEFINITIONS = {
    "Azacitidine-QT": PairDefinition(
        drug_patterns=(
            ("azacitidine", r"\bazacitidine\b"),
            ("Vidaza", r"\bvidaza\b"),
            ("5-azacytidine", r"\b5-aza(?:cytidine)?\b"),
            ("azacytidine", r"\bazacytidine\b"),
        ),
        event_patterns=(
            ("QT prolongation", r"\bqt\s*(?:interval\s*)?prolong\w*"),
            ("long QT", r"\blong\s+qt\b"),
            ("torsade", r"\btorsade\w*\b"),
            (
                "ventricular arrhythmia",
                r"\bventricular\s+(?:tachycardia|arrhythmia)\b",
            ),
        ),
    ),
    "Tramadol-Hypoglycemia": PairDefinition(
        drug_patterns=(
            ("tramadol", r"\btramadol\b"),
            ("Ultram", r"\bultram\b"),
            ("Tramacet", r"\btramacet\b"),
            ("Ixprim", r"\bixprim\b"),
            ("Trarmadol", r"\btrarmadol\b"),
            ("Tremadol", r"\btremadol\b"),
            ("Tramal", r"\btramal\b"),
            ("Zydol", r"\bzydol\b"),
        ),
        event_patterns=(
            ("hypoglycemia", r"\bhypoglyc\w*\b"),
            (
                "low glucose",
                r"\b(?:low|decreased)\s+(?:blood\s+)?(?:glucose|sugar)\b",
            ),
        ),
    ),
    "Baricitinib-Hypersensitivity": PairDefinition(
        drug_patterns=(
            ("baricitinib", r"\bbaricitinib\b"),
            ("Olumiant", r"\bolumiant\b"),
            ("barcitinib", r"\bbarcitinib\b"),
            ("Olimiant", r"\bolimiant\b"),
        ),
        event_patterns=(
            ("hypersensitivity", r"\bhypersensitiv\w*\b"),
            ("anaphylaxis", r"\banaphylax\w*\b"),
            ("allergic reaction", r"\ballergic\s+reaction\b"),
            ("angioedema", r"\bangioedema\b"),
            ("urticaria", r"\burticaria\b"),
            ("hives", r"\bhives\b"),
        ),
    ),
    "Erenumab-Stroke": PairDefinition(
        drug_patterns=(
            ("erenumab", r"\berenumab\b"),
            ("Aimovig", r"\baimovig\b"),
        ),
        event_patterns=(
            ("stroke", r"\bstroke\b"),
            (
                "cerebrovascular accident",
                r"\bcerebrovascular\s+accident\b",
            ),
            ("cerebral infarction", r"\bcerebral\s+infarct\w*\b"),
            ("ischemic infarction", r"\bischemi\w*\s+infarct\w*\b"),
            (
                "transient ischemic attack",
                r"\btransient\s+isch(?:a)?emic\s+attack\b",
            ),
            ("TIA", r"\btia\b"),
        ),
    ),
}

DRUG_LABELS = frozenset({"sdrug", "cdrug", "odrug", "drug"})
EVENT_LABELS = frozenset({"ae", "mae", "diagnostic", "bsym"})


@dataclass(frozen=True)
class Evidence:
    series: str
    score: int
    suspect_drugs: tuple[str, ...]
    other_drugs: tuple[str, ...]
    text_drugs: tuple[str, ...]
    annotated_events: tuple[str, ...]
    text_events: tuple[str, ...]

    @property
    def has_drug(self) -> bool:
        return bool(self.suspect_drugs or self.other_drugs or self.text_drugs)

    @property
    def has_annotated_drug(self) -> bool:
        return bool(self.suspect_drugs or self.other_drugs)

    @property
    def has_event(self) -> bool:
        return bool(self.annotated_events or self.text_events)

    @property
    def has_annotated_event(self) -> bool:
        return bool(self.annotated_events)


def canonical_label(value: object) -> str:
    return "" if value is None else str(value).strip().lower()


def matched_terms(
    text: str,
    patterns: tuple[tuple[str, str], ...],
) -> tuple[str, ...]:
    return tuple(
        name for name, pattern in patterns if re.search(pattern, text, re.IGNORECASE)
    )


def capped_occurrences(
    text: str,
    patterns: tuple[tuple[str, str], ...],
    cap: int,
) -> int:
    count = sum(
        len(re.findall(pattern, text, re.IGNORECASE)) for _, pattern in patterns
    )
    return min(count, cap)


def score_pair(
    series: str,
    definition: PairDefinition,
    narrative: str,
    suspect_drug_text: str,
    other_drug_text: str,
    event_annotation_text: str,
) -> Evidence:
    suspect_drugs = matched_terms(suspect_drug_text, definition.drug_patterns)
    other_drugs = matched_terms(other_drug_text, definition.drug_patterns)
    text_drugs = matched_terms(narrative, definition.drug_patterns)
    annotated_events = matched_terms(
        event_annotation_text, definition.event_patterns
    )
    text_events = matched_terms(narrative, definition.event_patterns)

    score = 0
    score += 120 * capped_occurrences(
        suspect_drug_text, definition.drug_patterns, cap=3
    )
    score += 40 * capped_occurrences(
        other_drug_text, definition.drug_patterns, cap=3
    )
    score += 12 * capped_occurrences(narrative, definition.drug_patterns, cap=5)
    score += 90 * capped_occurrences(
        event_annotation_text, definition.event_patterns, cap=3
    )
    score += 12 * capped_occurrences(narrative, definition.event_patterns, cap=5)

    has_annotated_drug = bool(suspect_drugs or other_drugs)
    has_drug = bool(has_annotated_drug or text_drugs)
    has_annotated_event = bool(annotated_events)
    has_event = bool(has_annotated_event or text_events)
    if has_annotated_drug and has_annotated_event:
        score += 180
    elif has_drug and has_event:
        score += 90

    return Evidence(
        series=series,
        score=score,
        suspect_drugs=suspect_drugs,
        other_drugs=other_drugs,
        text_drugs=text_drugs,
        annotated_events=annotated_events,
        text_events=text_events,
    )


def determine_confidence(
    top: Evidence,
    runner_up: Evidence,
) -> tuple[str, bool, str]:
    margin = top.score - runner_up.score
    if top.score == 0:
        return "unclassified", True, "no target drug or event evidence"
    if margin == 0:
        return "ambiguous", True, "top-score tie"
    if (
        top.has_annotated_drug
        and top.has_annotated_event
        and margin >= 180
    ):
        return "high", False, "annotated drug-event pair with clear margin"
    if top.suspect_drugs and top.has_event and margin >= 120:
        return "high", False, "suspect drug plus event evidence"
    if top.has_drug and top.has_event and margin >= 70:
        return "medium", False, "drug-event evidence with positive margin"
    if top.has_annotated_drug and margin >= 80:
        return "medium", False, "annotated target drug without strong event evidence"
    return "low", True, "weak, incomplete, or competing evidence"


def join_terms(values: tuple[str, ...]) -> str:
    return "; ".join(values)


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=repo_root / "publication" / "dataset.db",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            repo_root
            / "publication"
            / "results"
            / "faers_case_series_classification.csv"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_path = args.database.resolve()
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
            SELECT a.doc_id, lower(trim(a.label)), lower(coalesce(a.tc_text, ''))
            FROM annotations AS a
            JOIN documents AS d ON d.doc_id = a.doc_id
            WHERE d.dataset = 'FAERS' AND a.note = 'SME1'
            ORDER BY a.doc_id, a.tc_start
            """
        ).fetchall()
    if not documents:
        raise ValueError("No FAERS documents found in the database")

    annotations: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for document, label, surface in annotation_rows:
        annotations[str(document)].append(
            (canonical_label(label), str(surface).lower())
        )

    header = [
        "doc_id",
        "assigned_series",
        "confidence",
        "review_required",
        "review_reason",
        "top_score",
        "runner_up_series",
        "runner_up_score",
        "score_margin",
        "suspect_drug_evidence",
        "other_drug_evidence",
        "text_drug_evidence",
        "annotated_event_evidence",
        "text_event_evidence",
        "all_series_scores",
    ]
    output_rows = []
    distribution: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()

    for document, narrative in documents:
        doc_annotations = annotations.get(str(document), [])
        suspect_drug_text = " ".join(
            text for label, text in doc_annotations if label == "sdrug"
        )
        other_drug_text = " ".join(
            text
            for label, text in doc_annotations
            if label in DRUG_LABELS and label != "sdrug"
        )
        event_annotation_text = " ".join(
            text for label, text in doc_annotations if label in EVENT_LABELS
        )

        evidence = [
            score_pair(
                series,
                definition,
                str(narrative).lower(),
                suspect_drug_text,
                other_drug_text,
                event_annotation_text,
            )
            for series, definition in PAIR_DEFINITIONS.items()
        ]
        evidence.sort(key=lambda item: (-item.score, item.series))
        top, runner_up = evidence[0], evidence[1]
        confidence, review_required, reason = determine_confidence(top, runner_up)

        assigned_series = top.series if top.score > runner_up.score else "UNRESOLVED"
        distribution[assigned_series] += 1
        confidence_counts[confidence] += 1
        output_rows.append(
            [
                document,
                assigned_series,
                confidence,
                "Yes" if review_required else "No",
                reason,
                top.score,
                runner_up.series,
                runner_up.score,
                top.score - runner_up.score,
                join_terms(top.suspect_drugs),
                join_terms(top.other_drugs),
                join_terms(top.text_drugs),
                join_terms(top.annotated_events),
                join_terms(top.text_events),
                "; ".join(f"{item.series}={item.score}" for item in evidence),
            ]
        )

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(output_rows)

    print(f"Generated trial classification: {output_path}")
    print(f"Reports classified: {len(output_rows):,}")
    print("Natural assignment distribution:")
    for series in (*PAIR_DEFINITIONS, "UNRESOLVED"):
        print(f"  {series}: {distribution[series]:,}")
    print("Confidence distribution:")
    for confidence in ("high", "medium", "low", "ambiguous", "unclassified"):
        print(f"  {confidence}: {confidence_counts[confidence]:,}")
    print(
        "Manual review required: "
        f"{sum(1 for row in output_rows if row[3] == 'Yes'):,}"
    )


if __name__ == "__main__":
    main()
