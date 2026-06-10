# NER Model Development

This directory contains scripts for training and evaluating BERT-based NER models for llm4ae.

## Directory Structure
- `scripts/`: Python scripts for data prep, training, and evaluation.
- `data/`: Generated `.spacy` datasets (train.spacy, dev.spacy).
- `output/`: Model artifacts and evaluation results.

## Workflow

### 1. Prepare Data
Fetch annotations from `llm4ae.db` and convert them to spaCy format.
```bash
python scripts/prepare_data.py
```
By default, it fetches annotations from user `SME1`. You can modify `DEFAULT_USER` in the script.

### 2. Train Model
Train the NER model using BioBERT.
```bash
python scripts/train_ner.py
```
This script will:
- Create a `config.cfg` if it doesn't exist.
- Run `spacy train` using GPU 0.
- Use the custom scorer defined in `scripts/custom_scorer.py`.

### 3. Evaluate Model
Evaluate the trained model on the dev set using the custom weighted scorer.
```bash
python scripts/evaluate_ner.py
```

## Requirements
- spaCy
- spacy-transformers
- torch
- scikit-learn
- sqlite3 (standard library)

Ensure you have the BioBERT model accessible (it will be downloaded automatically by `spacy-transformers` if not present).
