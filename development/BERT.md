# BERT NER Implementation Plan for Pharmacovigilance

This document outlines the strategy for implementing a BERT-based Named Entity Recognition (NER) pipeline within the LLM4AE platform. The goal is to provide a specialized, local alternative to LLM-based annotation by fine-tuning a transformer model on ICSR datasets.

---

## 🎯 Objective
Create a self-contained training and evaluation environment in `./development/` that converts annotated JSON files from the `history/` folder into a fine-tuned BioBERT model capable of identifying medical entities (Drugs, Events, etc.).

## 🏗️ Phase 1: Environment Setup
Since the current environment is focused on Flask and LLM APIs, we need to establish a deep learning stack.
- **Location**: All scripts and models will reside in `./development/`.
- **Dependencies**: 
  - `torch`: For the underlying tensor computations.
  - `transformers`: For BioBERT/ClinicalBERT access and fine-tuning.
  - `datasets`: For efficient data handling.
  - `seqeval`: For NER-specific metrics (F1, Precision, Recall).
- **Foundation Model**: Default to `dmis-lab/biobert-base-cased-v1.2` (optimized for biomedical text).

## 📊 Phase 2: Data Engineering
Transforming character-level annotations into token-level BIO (Begin, Inside, Outside) tags.
1. **Data Discovery**: A script to recursively scan selected folders in `./server/history/` for `.json` files.
2. **Preprocessing**:
   - Tokenize the `pages` text.
   - Map character offsets (`start`, `end`) from the `annotations` array to tokens.
   - Generate BIO labels (e.g., `B-DRUG`, `I-DRUG`, `O`).
3. **Automated Splitting**: 
   - Implement a random shuffle and split (e.g., 80% training, 20% validation).
   - Ensure case-level integrity (don't split pages from the same case across sets).

## 🚀 Phase 3: Training Pipeline
A dedicated script `./development/train_bert.py` will handle the fine-tuning process.
- **Configuration**:
  - Max sequence length: 512 tokens (standard for BERT).
  - Learning rate: 2e-5 to 5e-5.
  - Batch size: 8-16 (depending on available VRAM/RAM).
- **Checkpoints**: Save the best-performing model to `./development/models/bert_ner_latest/`.

## 🧪 Phase 4: Evaluation & Results
- **Metrics**: Standard NER metrics using `seqeval` at the entity level (not just token level).
- **Outputs**:
  - `./development/results/classification_report.txt`
  - `./development/results/loss_curves.png`
- **Validation**: Use the 20% validation set to report final performance benchmarks.

## 🛠️ Phase 5: Inference Integration
Create a standalone inference script `./development/predict.py` to:
1. Load the fine-tuned model from `./development/models/`.
2. Accept raw text as input.
3. Output entities in the same JSON format used by the frontend.

---

## 📝 Guidelines
- **Isolation**: Do not modify files in `client/`, `server/`, or `nginx/` during this phase.
- **Resource Management**: The training script should check for CUDA availability but fallback to CPU if necessary.
- **Data Privacy**: Ensure that training logs do not leak raw ICSR narratives if they contain PII.
