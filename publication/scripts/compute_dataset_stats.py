#!/usr/bin/env python3
"""
compute_dataset_stats.py

Compute descriptive statistics for the FAERS (D1) and VAERS annotated corpora
and write raw numbers to results/dataset_stats_raw.json.

Usage:
    python scripts/compute_dataset_stats.py
"""

import json
import glob
import os
import re
from collections import Counter, defaultdict

# ── paths ────────────────────────────────────────────────────────────────────
BASE        = "/compute001/lwu/projects/LLM4AE"
FAERS_DIR   = os.path.join(BASE, "Datasets", "FAERS_D1_clean")
VAERS_DIR   = os.path.join(BASE, "Datasets", "VAERS")
RESULTS_DIR = os.path.join(BASE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── label normalisation maps ─────────────────────────────────────────────────
# Map raw SME1 labels → canonical category names for both datasets

FAERS_LABEL_MAP = {
    # Adverse events
    "AE": "Adverse Event", "mAE": "Adverse Event (minor)",
    "MAE": "Adverse Event (minor)",
    # Drugs
    "DRUG": "Drug", "Drug": "Drug", "CDRUG": "Drug (concomitant)",
    "cDrug": "Drug (concomitant)", "SDRUG": "Drug (suspect)",
    "sDrug": "Drug (suspect)",
    # Dose
    "DOSE": "Dose", "Dose": "Dose",
    # Medical / baseline
    "MEDICAL HISTORY": "Medical History", "MHx": "Medical History",
    "BASELINE SYMPTOM": "Baseline Symptom", "bSYM": "Baseline Symptom",
    "FAMILY HISTORY": "Family History", "FHx": "Family History",
    # Diagnostics
    "DIAGNOSTIC": "Diagnostic", "Dx": "Diagnostic",
    "LAB": "Lab Finding", "Lab": "Lab Finding",
    # Other clinical
    "INDICATION": "Indication",
    "TREATMENT": "Treatment", "Treatment": "Treatment",
    "STATUS": "Status", "Status": "Status",
    "CAUSE OF DEATH": "Cause of Death",
    "R/O": "Rule-Out", "RO": "Rule-Out",
    "SEX": "Sex/Demographics", "Sex": "Sex/Demographics",
    "AGE": "Age/Demographics", "Age": "Age/Demographics",
    "TEMPO": "Temporal",
}

VAERS_LABEL_MAP = {
    "SYM": "Symptom/AE",
    "VAX": "Vaccine",
    "Tx": "Treatment",
    "MHx": "Medical History",
    "FHx": "Family History",
    "Lab": "Lab Finding",
    "Status": "Status",
    "pDx": "Primary Diagnosis",
    "sDx": "Secondary Diagnosis",
    "CoD": "Cause of Death",
    "R/O": "Rule-Out",
}

# ── tokeniser (whitespace + punctuation split, matching typical NLP practice) ─
_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)

def tokenise(text):
    return _TOKEN_RE.findall(text)

def split_sentences(text):
    """
    Sentence splitter that handles:
    - Standard punctuation (. ! ?) followed by whitespace
    - FAERS-style ↵ line-break markers and real newlines
    """
    return [s.strip() for s in re.split(r"[↵\n]+|(?<=[.!?])\s+", text) if s.strip()]

# ── per-file processing ───────────────────────────────────────────────────────
def process_files(directory, label_map, sme_note="SME1"):
    """Return a dict of aggregate stats for all JSON files in directory."""
    files = sorted(glob.glob(os.path.join(directory, "*.json")))
    n_docs = len(files)

    token_counts   = []
    sentence_counts = []
    char_counts    = []
    label_counter  = Counter()   # canonical label → count
    raw_ae_terms   = Counter()   # normalised AE/SYM text → count
    raw_drug_terms = Counter()   # normalised drug text   → count
    ann_per_doc    = []

    # which canonical categories are "adverse event / symptom / diagnosis"
    AE_CATS = {"Adverse Event", "Adverse Event (minor)", "Symptom/AE",
                "Primary Diagnosis", "Secondary Diagnosis"}
    DRUG_CATS = {"Drug", "Drug (concomitant)", "Drug (suspect)", "Vaccine"}

    for fpath in files:
        with open(fpath, encoding="utf-8") as fh:
            doc = json.load(fh)

        # --- text --
        pages = doc.get("pages", [])
        full_text = " ".join(pages)
        toks = tokenise(full_text)
        sents = split_sentences(full_text)
        token_counts.append(len(toks))
        sentence_counts.append(len(sents))
        char_counts.append(len(full_text))

        # --- annotations (SME1 only) --
        ann = [a for a in doc.get("annotations", []) if a.get("note") == sme_note]
        ann_per_doc.append(len(ann))

        for a in ann:
            raw_label = a.get("label", "")
            canon = label_map.get(raw_label, raw_label)
            label_counter[canon] += 1

            entity_text = (a.get("textContext") or {}).get("text_raw", "").strip().lower()
            if not entity_text:
                entity_text = (a.get("textContext") or {}).get("text", "").strip().lower()

            if canon in AE_CATS and entity_text:
                raw_ae_terms[entity_text] += 1
            if canon in DRUG_CATS and entity_text:
                raw_drug_terms[entity_text] += 1

    import statistics as st
    stats = {
        "n_documents": n_docs,
        "total_tokens": sum(token_counts),
        "total_sentences": sum(sentence_counts),
        "total_chars": sum(char_counts),
        "avg_tokens_per_doc": round(st.mean(token_counts), 2) if token_counts else 0,
        "median_tokens_per_doc": round(st.median(token_counts), 2) if token_counts else 0,
        "stdev_tokens_per_doc": round(st.stdev(token_counts), 2) if len(token_counts) > 1 else 0,
        "min_tokens_per_doc": min(token_counts) if token_counts else 0,
        "max_tokens_per_doc": max(token_counts) if token_counts else 0,
        "avg_sentences_per_doc": round(st.mean(sentence_counts), 2) if sentence_counts else 0,
        "total_sme_annotations": sum(ann_per_doc),
        "avg_annotations_per_doc": round(st.mean(ann_per_doc), 2) if ann_per_doc else 0,
        "label_distribution": dict(label_counter.most_common()),
        "n_unique_ae_terms": len(raw_ae_terms),
        "top50_ae_terms": dict(raw_ae_terms.most_common(50)),
        "n_unique_drug_terms": len(raw_drug_terms),
        "top50_drug_terms": dict(raw_drug_terms.most_common(50)),
    }
    return stats

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print("Processing FAERS D1 …")
    faers_stats = process_files(FAERS_DIR, FAERS_LABEL_MAP, sme_note="SME1")

    print("Processing VAERS …")
    vaers_stats = process_files(VAERS_DIR, VAERS_LABEL_MAP, sme_note="SME1")

    # combined totals
    combined = {
        "n_documents": faers_stats["n_documents"] + vaers_stats["n_documents"],
        "total_tokens": faers_stats["total_tokens"] + vaers_stats["total_tokens"],
        "total_sentences": faers_stats["total_sentences"] + vaers_stats["total_sentences"],
        "total_sme_annotations": faers_stats["total_sme_annotations"] + vaers_stats["total_sme_annotations"],
    }

    output = {
        "FAERS_D1": faers_stats,
        "VAERS":    vaers_stats,
        "COMBINED": combined,
    }

    out_path = os.path.join(RESULTS_DIR, "dataset_stats_raw.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)
    print(f"\nRaw stats saved to: {out_path}")

    # pretty-print key numbers to stdout
    for ds, st in [("FAERS D1", faers_stats), ("VAERS", vaers_stats)]:
        print(f"\n{'='*50}")
        print(f"  {ds}")
        print(f"{'='*50}")
        print(f"  Documents             : {st['n_documents']:,}")
        print(f"  Total tokens          : {st['total_tokens']:,}")
        print(f"  Total sentences       : {st['total_sentences']:,}")
        print(f"  Avg tokens / doc      : {st['avg_tokens_per_doc']:,.1f}")
        print(f"  Median tokens / doc   : {st['median_tokens_per_doc']:,.1f}")
        print(f"  Stdev tokens / doc    : {st['stdev_tokens_per_doc']:,.1f}")
        print(f"  Min / Max tokens      : {st['min_tokens_per_doc']:,} / {st['max_tokens_per_doc']:,}")
        print(f"  Avg sentences / doc   : {st['avg_sentences_per_doc']:,.1f}")
        print(f"  Total SME annotations : {st['total_sme_annotations']:,}")
        print(f"  Avg annotations / doc : {st['avg_annotations_per_doc']:,.1f}")
        print(f"  Unique AE/SYM terms   : {st['n_unique_ae_terms']:,}")
        print(f"  Unique Drug terms     : {st['n_unique_drug_terms']:,}")
        print(f"  Label distribution:")
        for lbl, cnt in st["label_distribution"].items():
            print(f"    {lbl:<35} {cnt:>5}")

    print(f"\n{'='*50}")
    print("  COMBINED")
    print(f"{'='*50}")
    for k, v in combined.items():
        print(f"  {k:<35} {v:,}")

if __name__ == "__main__":
    main()
