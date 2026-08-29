#!/usr/bin/env python3
"""
Convert FAERS_D1_clean and VAERS JSON datasets into a single SQLite database.

Keeps:
  - Raw narrative text (pages[0])
  - ETHER annotations  (note == "ETHER")
  - SME   annotations  (note starts with "SME")

Drops:
  - annotated_pages (HTML markup)
  - LLM annotations
  - BERT annotations
  - Any other non-SME / non-ETHER annotator
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE     = Path("/compute001/lwu/projects/LLM4AE/LLM4AE-dev/publication")
FAERS_DIR = BASE / "Datasets" / "FAERS_D1_clean"
VAERS_DIR = BASE / "Datasets" / "VAERS"
DB_PATH   = BASE / "dataset.db"


# ── Annotator filter ───────────────────────────────────────────────────────────
def _keep_annotation(note: str) -> bool:
    """Keep only SME* and ETHER annotations; drop LLM, BERT, etc."""
    n = (note or "").strip()
    return n.startswith("SME") or n == "ETHER"


# ── Schema ─────────────────────────────────────────────────────────────────────
SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS documents (
    doc_id      TEXT    PRIMARY KEY,   -- e.g. '10064257-1' or 'VAERS_133422-1'
    dataset     TEXT    NOT NULL,      -- 'FAERS' or 'VAERS'
    base_id     TEXT    NOT NULL,      -- numeric part of the filename stem
    suffix      INTEGER NOT NULL,      -- version/annotator index
    page_text   TEXT    NOT NULL       -- raw narrative text (pages[0])
);

CREATE INDEX IF NOT EXISTS idx_docs_dataset ON documents(dataset);
CREATE INDEX IF NOT EXISTS idx_docs_base_id ON documents(base_id);

CREATE TABLE IF NOT EXISTS annotations (
    annotation_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id          TEXT    NOT NULL REFERENCES documents(doc_id),
    label           TEXT    NOT NULL,   -- raw label as stored in JSON
    note            TEXT    NOT NULL,   -- annotator tag: 'SME1', 'SME1,EXT', 'ETHER', …
    used            TEXT,               -- 'Yes'/'No' (FAERS only; NULL for VAERS)
    -- textContext fields
    tc_page         INTEGER,            -- page index; NULL when absent (some ETHER records)
    tc_start        INTEGER NOT NULL,
    tc_end          INTEGER NOT NULL,
    tc_text         TEXT    NOT NULL,   -- surface form as annotated
    tc_text_raw     TEXT,               -- normalised/lowercased form (NULL when absent)
    tc_disputed     INTEGER,            -- 0/1 boolean; SME1,EXT only; NULL otherwise
    -- relationship presence flags (relationship text values are always ""; store as 0/1)
    rel_date            INTEGER NOT NULL DEFAULT 0,
    rel_frequency       INTEGER NOT NULL DEFAULT 0,
    rel_relatives       INTEGER NOT NULL DEFAULT 0,
    rel_span            INTEGER NOT NULL DEFAULT 0,
    rel_time            INTEGER NOT NULL DEFAULT 0,
    rel_latency         INTEGER NOT NULL DEFAULT 0,   -- FAERS SME1,EXT only
    rel_temporal_seq    INTEGER NOT NULL DEFAULT 0    -- FAERS SME1,EXT only
);

CREATE INDEX IF NOT EXISTS idx_ann_doc_id    ON annotations(doc_id);
CREATE INDEX IF NOT EXISTS idx_ann_note      ON annotations(note);
CREATE INDEX IF NOT EXISTS idx_ann_label     ON annotations(label);
CREATE INDEX IF NOT EXISTS idx_ann_doc_label ON annotations(doc_id, label);
"""


# ── Filename parsers ───────────────────────────────────────────────────────────
def parse_faers_filename(stem: str):
    """'10064257-1'  →  base_id='10064257', suffix=1"""
    m = re.fullmatch(r"(.+)-(\d+)", stem)
    if not m:
        raise ValueError(f"Unexpected FAERS filename stem: {stem!r}")
    return m.group(1), int(m.group(2))


def parse_vaers_filename(stem: str):
    """'VAERS_133422-1'  →  base_id='133422', suffix=1"""
    m = re.fullmatch(r"VAERS_(\d+)-(\d+)", stem)
    if not m:
        raise ValueError(f"Unexpected VAERS filename stem: {stem!r}")
    return m.group(1), int(m.group(2))


# ── Annotation row builder ─────────────────────────────────────────────────────
def extract_annotation_row(doc_id: str, ann: dict):
    """
    Flatten one annotation dict into a DB row.
    Returns None if the annotator should be excluded.
    """
    note = (ann.get("note") or "").strip()
    if not _keep_annotation(note):
        return None

    tc   = ann.get("textContext", {})
    rels = ann.get("relationships", {})

    disputed_raw = tc.get("disputed")
    tc_disputed  = None if disputed_raw is None else (1 if disputed_raw else 0)

    return dict(
        doc_id       = doc_id,
        label        = ann.get("label", ""),
        note         = note,
        used         = ann.get("used"),          # None for VAERS
        tc_page      = tc.get("page"),           # None for some ETHER records
        tc_start     = tc["start"],
        tc_end       = tc["end"],
        tc_text      = tc.get("text", ""),
        tc_text_raw  = tc.get("text_raw"),
        tc_disputed  = tc_disputed,
        rel_date         = 1 if "date"             in rels else 0,
        rel_frequency    = 1 if "frequency"        in rels else 0,
        rel_relatives    = 1 if "relatives"        in rels else 0,
        rel_span         = 1 if "span"             in rels else 0,
        rel_time         = 1 if "time"             in rels else 0,
        rel_latency      = 1 if "latency"          in rels else 0,
        rel_temporal_seq = 1 if "temporal_sequence" in rels else 0,
    )


# ── Core ingest ────────────────────────────────────────────────────────────────
def ingest_dataset(
    cursor: sqlite3.Cursor,
    directory: Path,
    dataset_name: str,
    filename_parser,
):
    files = sorted(f for f in directory.glob("*.json") if not f.name.startswith("."))
    doc_rows  = []
    ann_rows  = []
    skipped   = 0
    ann_kept  = 0
    ann_total = 0

    for path in files:
        try:
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  [WARN] Cannot read {path.name}: {exc}", file=sys.stderr)
            skipped += 1
            continue

        pages = data.get("pages", [])
        if not pages:
            print(f"  [WARN] No pages[] in {path.name}", file=sys.stderr)
            skipped += 1
            continue

        try:
            base_id, suffix = filename_parser(path.stem)
        except ValueError as exc:
            print(f"  [WARN] {exc}", file=sys.stderr)
            skipped += 1
            continue

        doc_id = path.stem
        doc_rows.append((doc_id, dataset_name, base_id, suffix, pages[0]))

        for ann in data.get("annotations", []):
            ann_total += 1
            row = extract_annotation_row(doc_id, ann)
            if row is not None:
                ann_rows.append(row)
                ann_kept += 1

    # Bulk insert
    cursor.executemany(
        "INSERT OR IGNORE INTO documents (doc_id, dataset, base_id, suffix, page_text) "
        "VALUES (?, ?, ?, ?, ?)",
        doc_rows,
    )
    cursor.executemany(
        """INSERT INTO annotations
               (doc_id, label, note, used,
                tc_page, tc_start, tc_end, tc_text, tc_text_raw, tc_disputed,
                rel_date, rel_frequency, rel_relatives, rel_span, rel_time,
                rel_latency, rel_temporal_seq)
           VALUES
               (:doc_id, :label, :note, :used,
                :tc_page, :tc_start, :tc_end, :tc_text, :tc_text_raw, :tc_disputed,
                :rel_date, :rel_frequency, :rel_relatives, :rel_span, :rel_time,
                :rel_latency, :rel_temporal_seq)""",
        ann_rows,
    )

    n_docs = len(doc_rows) - skipped
    print(f"  {dataset_name:6s}: {n_docs:5,} documents | "
          f"{ann_kept:6,} / {ann_total:6,} annotations kept "
          f"({ann_total - ann_kept:,} filtered out)")
    return n_docs, ann_kept


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing database: {DB_PATH}")

    print(f"Creating database: {DB_PATH}\n")
    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()
    cur.executescript(SCHEMA)
    con.commit()

    total_docs = 0
    total_anns = 0

    print("Ingesting FAERS_D1_clean …")
    d, a = ingest_dataset(cur, FAERS_DIR, "FAERS", parse_faers_filename)
    total_docs += d; total_anns += a
    con.commit()

    print("\nIngesting VAERS …")
    d, a = ingest_dataset(cur, VAERS_DIR, "VAERS", parse_vaers_filename)
    total_docs += d; total_anns += a
    con.commit()

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'─' * 55}")
    print(f"Total documents        : {total_docs:,}")
    print(f"Total annotations kept : {total_anns:,}")
    print(f"Database size          : {DB_PATH.stat().st_size / 1_048_576:.1f} MB")
    print(f"Output                 : {DB_PATH}")

    print("\nPer-dataset document counts:")
    for row in cur.execute("SELECT dataset, COUNT(*) FROM documents GROUP BY dataset"):
        print(f"  {row[0]}: {row[1]:,}")

    print("\nAnnotation counts by annotator (note):")
    for row in cur.execute(
        "SELECT note, COUNT(*) n FROM annotations GROUP BY note ORDER BY n DESC"
    ):
        print(f"  {row[0]:<20} {row[1]:,}")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
