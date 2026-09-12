# LLM4AE: Named Entity Recognition of Clinical Concepts in Safety Reports using Large Language Models and BERT

Official repository for the research paper:
> **Named Entity Recognition of Clinical Concepts in Safety Reports using Large Language Models and BERT**

---

## Overview

**LLM4AE** is an open-source framework and interactive platform designed for pharmacovigilance (PV) and clinical safety research. It combines deep clinical language models (BioBERT) and instruction-tuned Large Language Models (LLMs) with an enterprise-ready dual-annotator and adjudication web application for Individual Case Safety Reports (ICSRs).

This repository provides:
1. **Interactive Annotation Platform**: Full source code for the Next.js frontend and Flask backend supporting AI pre-labeling, independent SME annotations, consensus adjudication, and causality assessment.
2. **Analysis & Reproduction Suite**: Complete source code to reproduce all 7 tables and 5 figures in the manuscript, alongside supplementary files and evaluation routines.
3. **Database Schema Specification**: Formal DDL and architectural specification for storing and evaluating annotated ICSR corpora.

---

## 📁 Repository Structure

`
.
├── client/                     # Next.js interactive web annotation application
│   ├── app/                    # React page routes (Annotate, Adjudicate, Causality)
│   ├── components/             # Annotation panels, BRAT-style viewer, context menus
│   ├── lib/                    # API client, interfaces, state reducers
│   └── package.json
├── server/                     # Flask RESTful API & AI pipeline service
│   ├── ai_client.py            # LLM API orchestrator (OpenAI / Gemini / local endpoints)
│   ├── app.py                  # API endpoints for annotation, adjudication, and auth
│   ├── llm_annotation.py       # In-text tagging and structured extraction logic
│   ├── llm_prompts.py          # Verbatim prompts and schema injectables
│   ├── Dockerfile
│   └── requirements.txt
├── publication/
│   ├── DATASET_SCHEMA.md       # Canonical SQLite database schema specification
│   ├── code/
│   │   └── custom_scorer_v5.py # Two-Tier Evaluation Framework scorer
│   ├── manuscripts/
│   │   ├── Figures/            # Publication figures (Figure 2 through Figure 6)
│   │   ├── Tables/             # Tables 1 through 7 (CSV format)
│   │   └── supplementary/      # Supplementary Files 1 through 4
│   ├── results/                # Aggregated summary metrics and ablation results
│   │   ├── bert_replim_VAERS/  # Model ablation summaries (BERT vs BioBERT vs ClinicalBERT)
│   │   ├── bert_runs_FAERS_LOO/# FAERS leave-one-out cross-validation metrics
│   │   └── bert_runs_VAERS/    # VAERS k-fold cross-validation metrics
│   └── scripts/                # Source code to generate all figures, tables, and reports
│       ├── generate_figure2.py
│       ├── generate_figure3.py
│       ├── generate_figure4.py
│       ├── generate_figure5.py
│       ├── generate_figure6.py
│       ├── generate_table1.py ... generate_table7.py
│       ├── generate_supplementary_file_1.py
│       ├── generate_supplementary_files_2_3.py
│       └── ...
├── requirements.txt            # Top-level Python dependencies
└── README.md
`

---

## 🔒 Data Availability & Compliance Statement

In accordance with patient privacy regulations (including HIPAA), institutional research ethics requirements, and individual case safety report data access governance, **raw, unmasked patient narratives and full clinical safety case reports are not publicly distributed in this repository**.

- All statistical aggregates, evaluation outputs, and summary tables presented in the manuscript are provided in publication/manuscripts/Tables/ and publication/results/.
- Researchers wishing to run the data-dependent reproduction scripts on their own clinical safety datasets can format their data according to our schema specification in [publication/DATASET_SCHEMA.md](publication/DATASET_SCHEMA.md).

---

## 🚀 Quickstart: Web Annotation Application

The LLM4AE platform consists of a Next.js frontend (client/) and a Flask backend (server/).

### 1. Backend Setup
`ash
cd server
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cp .env.template .env
# Configure your API keys or local LLM server endpoint in .env
python app.py
`
The backend will run on http://localhost:5000.

### 2. Frontend Setup
`ash
cd client
npm install
npm run dev
`
The frontend will run on http://localhost:3000.

---

## 📊 Generating Manuscript Figures & Tables

All figure and table generation scripts are located in publication/scripts/. Each script is designed to output a single, deterministic, publication-quality target file:

`ash
# Generate Figure 2 (Fuzzy String Anchoring Diagram)
python publication/scripts/generate_figure2.py

# Generate Table 1 through Table 7 (Requires local dataset.db)
python publication/scripts/generate_table1.py
python publication/scripts/generate_table2.py
python publication/scripts/generate_table3.py
python publication/scripts/generate_table4.py
python publication/scripts/generate_table5.py
python publication/scripts/generate_table6.py
python publication/scripts/generate_table7.py

# Generate Supplementary Files
python publication/scripts/generate_supplementary_file_1.py
python publication/scripts/generate_supplementary_files_2_3.py
`

---

## 📜 License

This project is licensed under the Apache 2.0 License.
