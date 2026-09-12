# LLM4AE: Named Entity Recognition of Clinical Concepts in Safety Reports using Large Language Models and BERT

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/next.js-15-black.svg)](https://nextjs.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Official code and reproduction repository for the manuscript:
> **Named Entity Recognition of Clinical Concepts in Safety Reports using Large Language Models and BERT**

---

## 🌟 Overview

**LLM4AE** is an open-source clinical NLP platform and evaluation suite tailored for pharmacovigilance (PV) and clinical safety surveillance. It integrates deep biomedical transformer models (**BioBERT**) and state-of-the-art instruction-tuned Large Language Models (**LLMs**, including Claude 4.6 Sonnet and LLaMA 4) with an interactive, enterprise-grade web application for clinical concept extraction from **Individual Case Safety Reports (ICSRs)**.

### Key Capabilities:
- **Interactive Annotation Web-App**: Dual-panel viewer supporting AI pre-labeling, independent SME annotations (SME1, SME2), consensus adjudication, entity relation mapping, and ICSR causality scoring.
- **Two-Tier Evaluation Framework**: Advanced evaluation protocol handling exact matches, boundary inexactness, class confusions, and spurious hallucinated predictions.
- **Reproducible Publication Suite**: Standalone, deterministic scripts reproducing all 7 tables and Figures 2–6 in the manuscript.
- **Standardized Schema**: Canonical database structure accommodating multi-annotator workflows and structured case series evaluation.

---

## 📁 Repository Structure

```text
LLM4AE/
├── client/                     # Next.js interactive web annotation application
│   ├── app/                    # Next.js App Router (Annotate, Adjudicate, Causality)
│   ├── components/             # Annotation panels, BRAT-style viewer, context menus
│   ├── lib/                    # API client, interfaces, state reducers
│   └── package.json            # Frontend dependencies
├── server/                     # Flask RESTful backend API & AI pipeline service
│   ├── ai_client.py            # Multi-provider LLM API orchestrator
│   ├── app.py                  # API endpoints for annotation, adjudication, and auth
│   ├── database_manager.py     # SQLite session and document management
│   ├── llm_annotation.py       # In-text tagging and structured extraction logic
│   ├── llm_prompts.py          # Verbatim prompts and schema injectables
│   ├── Dockerfile
│   ├── requirements.txt        # Backend dependencies
│   └── .env.template           # Environment variables template
├── publication/
│   ├── DATASET_SCHEMA.md       # Canonical SQLite database schema specification
│   ├── code/
│   │   └── custom_scorer_v5.py # Canonical Two-Tier Evaluation Framework scorer
│   ├── manuscripts/
│   │   ├── Figures/            # High-resolution publication figures (Figure 2 - 6)
│   │   ├── Tables/             # Tables 1 through 7 (CSV format)
│   │   └── supplementary/      # Supplementary Files 1 through 4
│   ├── results/                # Aggregated summary metrics and ablation results
│   │   ├── bert_replim_VAERS/  # Model ablation summaries (BERT vs BioBERT vs ClinicalBERT)
│   │   ├── bert_runs_FAERS_LOO/# FAERS leave-one-out cross-validation metrics
│   │   └── bert_runs_VAERS/    # VAERS k-fold cross-validation metrics
│   └── scripts/                # Source code to generate all figures, tables, and reports
│       ├── generate_figure2.py ... generate_figure6.py
│       ├── generate_table1.py  ... generate_table7.py
│       ├── generate_supplementary_file_1.py
│       ├── generate_supplementary_files_2_3.py
│       ├── analyze_bert_ablation.py
│       ├── analyze_inter_annotator_agreement.py
│       └── run_*.py (Evaluation & inference runners)
├── requirements.txt            # Top-level Python environment requirements
├── .gitignore
└── README.md
```

---

## 🔒 Data Availability & Compliance Statement

> [!IMPORTANT]
> In strict compliance with patient privacy protections (including HIPAA Safe Harbor regulations), institutional research governance, and FDA/CDC data use constraints, **raw clinical narratives (`page_text`), verbatim safety transcripts, and unmasked patient identifiers are intentionally omitted from this public repository**.

- **Aggregated Results**: All evaluation summaries, confusion matrices, and publication tables are provided in `publication/manuscripts/Tables/` and `publication/results/`.
- **Database Schema**: Full DDL, schema definitions, and table relationships are documented in [**`publication/DATASET_SCHEMA.md`**](publication/DATASET_SCHEMA.md). Researchers can construct a local SQLite database adhering to this schema to test and execute the reproduction pipeline.

---

## 🚀 Quickstart: Web Annotation Application

The LLM4AE web platform consists of a **Next.js** frontend (`client/`) and a **Flask** backend (`server/`).

### 1. Backend API Service

```bash
cd server

# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.template .env
# Edit .env to set AI API keys (OpenAI / Google Gemini / local endpoints)

# Launch Flask server
python app.py
```
The backend API service will start on `http://localhost:5000`.

### 2. Frontend Web Client

```bash
cd client

# Install dependencies
npm install

# Start development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser to access the annotation and adjudication interface.

---

## 📊 Generating Manuscript Figures & Tables

All figure and table generation scripts are located in `publication/scripts/`. Every script deterministically generates exactly **one** designated target file:

### Manuscript Figures (Outputs to `publication/manuscripts/Figures/`):
```bash
# Figure 2: Example of LLM in-text annotation & fuzzy string anchoring
python publication/scripts/generate_figure2.py

# Figure 3: Overall Performance Comparison on FAERS (Panel a & b)
python publication/scripts/generate_figure3.py

# Figure 4: Comparative Concept Extraction Performance across 17 Categories
python publication/scripts/generate_figure4.py

# Figure 5: Comprehensive Error Taxonomy Analysis
python publication/scripts/generate_figure5.py

# Figure 6: Cross-Validation Reproducibility on VAERS
python publication/scripts/generate_figure6.py
```

### Manuscript Tables (Outputs to `publication/manuscripts/Tables/`):
```bash
# Table 1: Descriptive statistics of the annotated corpora
python publication/scripts/generate_table1.py

# Table 2: FAERS clinical concept annotation distributions
python publication/scripts/generate_table2.py

# Table 3: Performance comparison on FAERS corpus
python publication/scripts/generate_table3.py

# Table 4: VAERS concept annotation performance
python publication/scripts/generate_table4.py

# Table 5: Leave-one-out cross-validation across case series cohorts
python publication/scripts/generate_table5.py

# Table 6: Multi-seed model reproducibility evaluation
python publication/scripts/generate_table6.py

# Table 7: In-text tagging vs. JSON schema output comparison
python publication/scripts/generate_table7.py
```

### Supplementary Files (Outputs to `publication/manuscripts/supplementary/`):
```bash
# Supplementary File 1: Full LLM Prompt Templates (.docx)
python publication/scripts/generate_supplementary_file_1.py

# Supplementary Files 2 & 3: FAERS & VAERS Annotation Guidelines (.xlsx)
python publication/scripts/generate_supplementary_files_2_3.py

# Supplementary File 4: Inter-Annotator Agreement (IAA) Analysis
python publication/scripts/analyze_inter_annotator_agreement.py
```

---

## 📄 License

This repository is distributed under the **Apache License 2.0**. See `LICENSE` for details.
