# Database Schema Specification (dataset.db)

This document provides the formal schema specification for the canonical SQLite database (dataset.db) utilized across the LLM4AE benchmark and evaluation pipelines.

---

## Data Governance & Privacy Statement

Individual Case Safety Reports (ICSRs) collected from pharmacovigilance databases (such as FDA FAERS and CDC/FDA VAERS) often contain unstructured, free-text clinical narratives describing patient medical histories, clinical episodes, and therapeutic courses. 

To comply with patient privacy protections, institutional ethical review requirements, and medical data usage agreements, **raw clinical narratives (page_text) and unmasked verbatim patient texts are strictly excluded from this public distribution**. Researchers wishing to apply this evaluation framework to their own pharmacovigilance datasets may construct a compatible local SQLite database matching the schema detailed below.

---

## Entity-Relationship Overview

`
+-----------------------------------+
|             documents             |
+-----------------------------------+
| PK doc_id (TEXT)                  |<----+
|    dataset (TEXT)                 |     | (1:N)
|    base_id (TEXT)                 |     |
|    suffix (INTEGER)               |     |
|    page_text (TEXT)               |     |
+-----------------------------------+     |
                  |                       |
                  | (1:1)                 |
                  v                       |
+-----------------------------------+     |
|         faers_case_series         |     |
+-----------------------------------+     |
| PK doc_id (TEXT, FK -> documents) |     |
|    case_series (TEXT)             |     |
|    include_in_loo (INTEGER)       |     |
|    assignment_source (TEXT)       |     |
|    assignment_note (TEXT)         |     |
+-----------------------------------+     |
                                          |
                                          |
+-----------------------------------------+
|               annotations               |
+-----------------------------------------+
| PK annotation_id (INTEGER AUTOINCREMENT)|
| FK doc_id (TEXT -> documents)           |
|    label (TEXT)                         |
|    note (TEXT)                          |
|    used (TEXT)                          |
|    tc_page (INTEGER)                    |
|    tc_start (INTEGER)                   |
|    tc_end (INTEGER)                     |
|    tc_text (TEXT)                       |
|    tc_text_raw (TEXT)                   |
|    tc_disputed (INTEGER)                |
|    rel_* (INTEGER flags)                |
+-----------------------------------------+
`

---

## Table Definitions & Data DDL

### 1. documents Table
Stores report document-level metadata and clinical narratives.

`sql
CREATE TABLE documents (
    doc_id      TEXT    PRIMARY KEY,   -- Unique case identifier (e.g., '10064257-1', 'VAERS_133422-1')
    dataset     TEXT    NOT NULL,      -- Corpus identifier: 'FAERS' or 'VAERS'
    base_id     TEXT    NOT NULL,      -- Numeric portion of the safety report ID
    suffix      INTEGER NOT NULL,      -- Report version or narrative segment index
    page_text   TEXT    NOT NULL       -- Full unstructured clinical narrative text
);

CREATE INDEX idx_docs_dataset ON documents(dataset);
CREATE INDEX idx_docs_base_id ON documents(base_id);
`

#### Field Descriptions:
- doc_id: Unique alphanumeric key identifying each case report narrative.
- dataset: Specifies which pharmacovigilance corpus the document belongs to (FAERS or VAERS).
- ase_id: Base report identifier without suffix (e.g. FAERS ISR/Case number).
- suffix: Version suffix (e.g., 1 for primary report version).
- page_text: Unstructured text extracted from the report narrative. *(Restricted under data privacy policies)*.

---

### 2. nnotations Table
Stores entity annotations (gold-standard annotations from Subject Matter Experts, baseline rule-based extractions, and model outputs).

`sql
CREATE TABLE annotations (
    annotation_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id              TEXT    NOT NULL REFERENCES documents(doc_id),
    label               TEXT    NOT NULL,   -- Clinical concept category
    note                TEXT    NOT NULL,   -- Annotator provenance: 'SME1', 'SME2', 'Adjudication', 'ETHER'
    used                TEXT,               -- Validation flag: 'Yes' / 'No' (FAERS only)
    tc_page             INTEGER,            -- Page / segment index (default 0)
    tc_start            INTEGER NOT NULL,   -- 0-indexed character start offset in page_text
    tc_end              INTEGER NOT NULL,   -- 0-indexed character end offset in page_text
    tc_text             TEXT    NOT NULL,   -- Surface token/phrase annotated
    tc_text_raw         TEXT,               -- Normalized surface text (lowercased)
    tc_disputed         INTEGER,            -- Binary flag (1 if disputed during adjudication, 0 otherwise)
    rel_date            INTEGER NOT NULL DEFAULT 0,  -- Relation flag: temporal date
    rel_frequency       INTEGER NOT NULL DEFAULT 0,  -- Relation flag: dosing frequency
    rel_relatives       INTEGER NOT NULL DEFAULT 0,  -- Relation flag: relative temporal marker
    rel_span            INTEGER NOT NULL DEFAULT 0,  -- Relation flag: time span / duration
    rel_time            INTEGER NOT NULL DEFAULT 0,  -- Relation flag: explicit time
    rel_latency         INTEGER NOT NULL DEFAULT 0,  -- Relation flag: event onset latency
    rel_temporal_seq    INTEGER NOT NULL DEFAULT 0   -- Relation flag: sequence relationship
);

CREATE INDEX idx_ann_doc_id    ON annotations(doc_id);
CREATE INDEX idx_ann_note      ON annotations(note);
CREATE INDEX idx_ann_label     ON annotations(label);
CREATE INDEX idx_ann_doc_label ON annotations(doc_id, label);
`

#### Controlled Vocabularies for label:
- **FAERS Corpus (17 Clinical Concepts)**:
  - Suspect / Concomitant Drugs: sdrug, cdrug, odrug
  - Dosage & Treatment: dose, indication, 	reatment
  - Adverse Events: e, mae (mild adverse event)
  - Clinical Context & Diagnostics: diagnostic, lab, status, 
o (rule out), cod (cause of death)
  - Patient History: mhx (medical history), hx (family history)
  - Patient Demographics: ge, sex
- **VAERS Corpus (14 Clinical Concepts)**:
  - Vaccine: ax
  - Symptoms & Diagnosis: sym (symptom), pdx (primary diagnosis), sdx (secondary diagnosis)
  - Additional clinical context matching the VAERS annotation guideline.

#### Annotator Tags (
ote):
- SME1: Primary gold-standard annotations produced by clinical expert 1.
- SME2: Independent annotations produced by clinical expert 2 for inter-annotator agreement analysis.
- Adjudication: Consensus annotations reconciled by the clinical adjudication panel.
- ETHER: Benchmark baseline extractions produced by the rule-based clinical NLP system.

---

### 3. aers_case_series Table
Defines case series partition assignments and Leave-One-Out (LOO) cross-validation evaluation cohorts for FAERS D1 reports.

`sql
CREATE TABLE faers_case_series (
    doc_id             TEXT PRIMARY KEY REFERENCES documents(doc_id),
    case_series        TEXT,
    include_in_loo     INTEGER NOT NULL CHECK (include_in_loo IN (0, 1)),
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
);

CREATE INDEX idx_faers_case_series_name ON faers_case_series(case_series);
`

#### Case Series Drug-Event Cohorts:
1. Azacitidine-QT: Azacitidine-induced QT prolongation cases.
2. Tramadol-Hypoglycemia: Tramadol-induced hypoglycemia cases.
3. Baricitinib-Hypersensitivity: Baricitinib-induced hypersensitivity cases.
4. Erenumab-Stroke: Erenumab-associated stroke / vascular cases.

---

## Building a Local Database for Reproduction

To execute the data-driven figure and table generation scripts (publication/scripts/generate_figure*.py, generate_table*.py), create a local SQLite database at publication/dataset.db with the schema above and populate the tables with your local corpus.
