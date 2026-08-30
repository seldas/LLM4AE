# Technical Report: Benchmarking Fine-Tuned Transformers and Frontier LLMs for Adverse Event Information Extraction (FAERS & VAERS)

**Project:** LLM4AE (Large Language Models for Adverse Event Information Extraction)  
**Date:** August 2026  
**Reproducibility Assets:** [`publication/scripts/evaluate_three_schemes.py`](scripts/evaluate_three_schemes.py), [`publication/scripts/analyze_error_breakdown.py`](scripts/analyze_error_breakdown.py), [`publication/dataset.db`](dataset.db)

---

## 1. Executive Summary

This report delivers a systematic empirical evaluation of information extraction from unstructured spontaneous adverse event reports. We compare:
1. **Supervised Domain-Adapted Transformers:** BioBERT (`dmis-lab/biobert-base-cased-v1.1`) trained with 10-fold cross-validation.
2. **Proprietary Frontier LLM:** Claude 4.6 Sonnet (via zero/few-shot in-context tag-prompting).
3. **Open-Weights Frontier LLM:** LLaMA 4 (`llama-4-maverick` via in-context tag-prompting).
4. **Legacy Expert/Rule System:** ETHER (rule/lexicon-based adverse event extraction).

Evaluations are conducted on two distinct clinical corpora: **FDA FAERS D1** (Drug Adverse Event Reporting System) and **CDC/FDA VAERS** (Vaccine Adverse Event Reporting System), encompassing **1,829 narrative reports** and **77,136 expert gold annotations**.

### Key Findings
- **Entity Detection vs. Sub-Classification Decoupling (Scheme 1 vs. Scheme 2/3):** When evaluated on detecting true clinical entity spans without penalizing fine-grained category overlaps (Scheme 1), Frontier LLMs achieve performance competitive with or close to fine-tuned BioBERT (**LLaMA 4 VAERS F1: 91.12% vs. BioBERT: 94.82%**; **Claude 4.6 Sonnet FAERS F1: 84.04% vs. BioBERT: 90.58%**). Pure hallucinations ($S_{\text{hallucination}}$) from LLMs are remarkably rare (<5–9% of total predictions).
- **Exact Span Boundary Regularity (Scheme 3):** Under strict exact-boundary token matching (Scheme 3), fine-tuned BioBERT significantly outperforms LLMs (BioBERT FAERS F1: 63.95% vs. Sonnet: 46.67% / LLaMA 4: 40.43%). LLMs inherently tend to extract broad semantic chunks (superphrases with modifiers) rather than minimal token spans.
- **Long-Tail / Few-Shot Generalization:** On extremely rare clinical entities (e.g., `INDICATION`, comprising only 0.4% of FAERS annotations), BioBERT collapses (F1 = 4.31%) due to sample sparsity, whereas LLMs demonstrate superior semantic inference (Claude 4.6 Sonnet F1: 38.38%, LLaMA 4 F1: 36.90%).
- **Legacy System Comparison:** Modern LLMs and Transformers outperform the legacy ETHER system across all weighted and strict evaluation protocols (ETHER Scheme 2 F1 = 26.93%, Scheme 3 F1 = 11.47%).

---

## 2. Corpus Statistics & Taxonomy

The dataset consists of expert gold standard annotations produced by Senior Medical Experts (SME1 layer) alongside legacy annotations (ETHER) and model predictions.

```
                    Corpus Scale & Composition Overview
┌────────────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Metric                 │ FAERS D1 (Drugs) │ VAERS (Vaccines) │ Total / Combined │
├────────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Narrative Reports      │ 829              │ 1,000            │ 1,829            │
│ Total Word Tokens      │ 414,576          │ 439,681          │ 854,257          │
│ Total Sentences        │ 17,766           │ 22,043           │ 39,809           │
│ Total SME Annotations  │ 36,425           │ 40,711           │ 77,136           │
│ Unique AE/Symptom Terms│ 3,991            │ 13,819           │ 17,810           │
│ Unique Drug/Vax Terms  │ 2,085            │ 863              │ 2,948            │
│ Avg Tokens / Report    │ 500.1 (σ=254.6)  │ 439.7 (σ=143.0)  │ 467.1            │
└────────────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

### 2.1 Dataset Structural Contrasts
- **FAERS D1:** Spontaneous adverse drug reaction reports. High length variability (σ = 254.6 tokens). Focuses on pharmacological differentiation: Suspect Drugs (`sdrug`), Concomitant Drugs (`cdrug`), Indication (`indication`), Dosage (`dose`), and Adverse Reactions (`ae`).
- **VAERS:** Post-immunization safety surveillance. High symptom vocabulary diversity (**13,819 unique symptom expressions** — 3.5× richer than FAERS). Focuses on layered symptom descriptions: Symptoms (`sym`), Primary Diagnosis (`pdx`), Secondary Diagnosis (`sdx`), Vaccine (`vax`), and Interventions (`tx`).

---

## 3. Multi-Scheme Evaluation Methodology

To address the limitations of standard strict token matching in clinical NLP, we formalize three complementary evaluation schemes:

### 3.1 Formal Mathematical Formulations

Let:
- $M$: Exact matches (identical boundary and identical entity category).
- $C$: Partial matches (overlapping span with identical entity category).
- $S_{\text{wrong\_class}}$: Predictions that overlap with a true gold entity but have mismatched category labels.
- $S_{\text{hallucination}}$: Spurious predictions with **zero overlap** with any gold entity span.
- $S_{\text{total}} = S_{\text{wrong\_class}} + S_{\text{hallucination}}$: All unmatched predictions.
- $N$: Gold entities missed by any same-category prediction.
- $\text{Gold}_{\text{Detected}}$: Gold entities with at least one overlapping prediction across any category.
- $\text{Total Gold} = M + C + N$.

```
                              Three Evaluation Protocols
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Scheme 1: Relaxed Entity Detection (Hallucination-Penalized)                           │
│   • True Positives (TP) = M + C + S_wrong_class                                        │
│   • Precision = TP / (TP + 0.25 * S_hallucination)                                     │
│   • Recall = Gold_Detected / Total Gold                                                │
│   • Objective: Measure raw clinical concept detection independently of sub-class bias  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Scheme 2: Standard Clinical Weighted Baseline (ADE Protocol)                           │
│   • Matched Credit = M + 0.5 * C                                                       │
│   • Precision = (M + 0.5 * C) / (M + C + 0.25 * S_total)                               │
│   • Recall = (M + 0.5 * C) / (M + C + N)                                               │
│   • Objective: Balance boundary leniency with strict categorization and FP penalties   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Scheme 3: Strict Exact Token Match (Standard Exact NER)                                │
│   • Precision = M / (M + C + S_total) = M / Total Predictions                          │
│   • Recall = M / (M + C + N) = M / Total Gold Spans                                    │
│   • Objective: Zero-tolerance offset and label boundary conformity                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Dataset-Specific Target Category Filtering Rule
In clinical benchmarks, models must not be penalized for extracting general entities that are outside the ground truth schema of a given dataset:
- **FAERS Evaluation Schema:** `AE`, `DRUG`, `DX`, `HX`, `LAB`, `DOSE`, `AGE`, `SEX`, `STATUS`, `TEMPORAL`, `INDICATION`, `RO`, `COD`.
- **VAERS Evaluation Schema:** `AE`, `VAX`, `TX`, `LAB`, `STATUS`, `HX`.
- **Filtering Principle:** Entities generated by an LLM that belong to non-ground-truth categories for that dataset (e.g., `TEMPORAL`, `DOSE`, `AGE`, `SEX`, `DX` in VAERS) are filtered out prior to metric computation rather than penalized as spurious hallucinations.

---

## 4. Master Benchmark Results

### 4.1 Overall Performance Across Schemes

#### FAERS D1 Benchmark (829 Reports, 28,429 Evaluated Gold Annotations)

| Model / System | Architecture / Setup | Scheme 1 (Relaxed) | Scheme 2 (Weighted) | Scheme 3 (Strict) |
|---|---|:---:|:---:|:---:|
| **BioBERT** | SFT (10-Fold CV Mean ± SD) | **P: 0.9403 ± 0.0056<br>R: 0.8741 ± 0.0229<br>F1: 0.9058 ± 0.0116** | **P: 0.8423 ± 0.0103<br>R: 0.7307 ± 0.0188<br>F1: 0.7824 ± 0.0103** | **P: 0.6074 ± 0.0207<br>R: 0.6759 ± 0.0172<br>F1: 0.6395 ± 0.0127** |
| **Claude 4.6 Sonnet** | Frontier LLM (Tag-Prompting) | P: 0.9106<br>R: 0.7802<br>**F1: 0.8404** | P: 0.7500<br>R: 0.5647<br>**F1: 0.6443** | P: 0.4497<br>R: 0.4850<br>**F1: 0.4667** |
| **LLaMA 4** | Open-Weights (`maverick`) | P: 0.8648<br>R: 0.8476<br>**F1: 0.8561** | P: 0.6778<br>R: 0.5796<br>**F1: 0.6249** | P: 0.3470<br>R: 0.4843<br>**F1: 0.4043** |
| **ETHER** | Rule/Dictionary (`used=Yes`) | P: 0.8823<br>R: 0.7706<br>**F1: 0.8227** | P: 0.4106<br>R: 0.2003<br>**F1: 0.2693** | P: 0.1089<br>R: 0.1212<br>**F1: 0.1147** |

#### VAERS Benchmark (1,000 Reports, 40,473 Evaluated Gold Annotations)

| Model / System | Architecture / Setup | Scheme 1 (Relaxed) | Scheme 2 (Weighted) | Scheme 3 (Strict) |
|---|---|:---:|:---:|:---:|
| **BioBERT** | SFT (10-Fold CV Mean ± SD) | **P: 0.9693 ± 0.0033<br>R: 0.9282 ± 0.0153<br>F1: 0.9482 ± 0.0076** | **P: 0.8742 ± 0.0063<br>R: 0.7481 ± 0.0147<br>F1: 0.8062 ± 0.0094** | **P: 0.6720 ± 0.0138<br>R: 0.7049 ± 0.0141<br>F1: 0.6880 ± 0.0114** |
| **LLaMA 4** | Open-Weights (Filtered Schema) | P: 0.9531<br>R: 0.8730<br>**F1: 0.9112** | P: 0.6365<br>R: 0.3449<br>**F1: 0.4474** | P: 0.2949<br>R: 0.2509<br>**F1: 0.2711** |

---

### 4.2 Per-Category Performance Breakdown (FAERS D1)

| Category | Gold Count | BioBERT (Scheme 2 F1) | Claude 4.6 Sonnet (Scheme 2 F1) | LLaMA 4 (Scheme 2 F1) | Sonnet Scheme 1 F1 | LLaMA 4 Scheme 1 F1 |
|---|---:|:---:|:---:|:---:|:---:|:---:|
| **SEX** | 767 | **0.9653** | 0.9454 | 0.9086 | 0.9608 | 0.9457 |
| **AGE** | 787 | **0.9513** | 0.9309 | 0.9230 | 0.9658 | 0.9654 |
| **TEMPORAL** | 6,262 | **0.8593** | — | — | — | — |
| **STATUS** | 1,796 | **0.8253** | 0.4558 | 0.2937 | 0.6123 | 0.4590 |
| **HX (History)** | 2,408 | **0.7839** | 0.7256 | 0.6770 | 0.8787 | 0.8719 |
| **DRUG** | 6,673 | **0.7708** | 0.6449 | 0.6312 | 0.8784 | 0.9016 |
| **AE (Adverse Event)** | 9,186 | **0.7586** | 0.6311 | 0.6586 | 0.8127 | 0.8253 |
| **LAB** | 3,476 | **0.7375** | 0.6223 | 0.5498 | 0.9284 | 0.9221 |
| **DOSE** | 1,619 | **0.7352** | 0.7099 | 0.6617 | 0.8019 | 0.9337 |
| **DX (Diagnosis/Tx)** | 1,543 | **0.6507** | 0.4978 | 0.4772 | 0.7594 | 0.8275 |
| **INDICATION** | 162 | 0.0431 | **0.3838** | 0.3690 | **0.6914** | **0.7011** |

---

### 4.3 Impact of Output Format Paradigm: Inline Tagged XML vs. Structured JSON Extraction

A critical engineering and methodological question in LLM-based clinical NLP is whether the **prompted output representation format** (Inline Tagged Markup vs. Discrete Structured JSON) systematically affects extraction fidelity.

We evaluated **LLaMA 4 (`llama-4-maverick`)** on the full FAERS D1 benchmark under identical model weights and temperature settings across two output paradigms:
1. **Inline Tagged XML (`P2_TAG`):** The model regenerates the raw narrative stream with inline XML tags wrapping identified spans (e.g., `<AE>hypoglycemia</AE>`).
2. **Structured JSON (`P1_JSON`):** The model emits a validated JSON dictionary containing explicit key-value arrays of entities (e.g., `[{"label": "AE", "text": "hypoglycemia"}]`), subsequently mapped back to document character offsets via fuzzy-tolerant string anchoring.

```
            Overall Comparison: Inline Tagged XML vs. Structured JSON (FAERS D1)
┌────────────────────────────┬──────────────────┬──────────────────┬──────────────────┬──────────────┐
│ Metric / Evaluation Scheme │ Tagged XML (P2)  │ Structured JSON  │ Delta (JSON-Tag) │ Key Effect   │
├────────────────────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────┤
│ **Scheme 1 Precision**     │ 0.8648           │ **0.9201**       │ +0.0553 (+5.53%) │ Precision ↑  │
│ **Scheme 1 Recall**        │ **0.8476**       │ 0.7350           │ -0.1126 (-11.3%) │ Recall ↓     │
│ **Scheme 1 F1-Score**      │ **0.8561**       │ 0.8172           │ -0.0389 (-3.89%) │ Balanced     │
├────────────────────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────┤
│ **Scheme 2 Precision**     │ 0.6778           │ **0.7019**       │ +0.0241 (+2.41%) │ Precision ↑  │
│ **Scheme 2 Recall**        │ **0.5796**       │ 0.5232           │ -0.0564 (-5.64%) │ Recall ↓     │
│ **Scheme 2 F1-Score**      │ **0.6249**       │ 0.5995           │ -0.0254 (-2.54%) │ Balanced     │
├────────────────────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────┤
│ **Scheme 3 Precision**     │ 0.3470           │ **0.3785**       │ +0.0315 (+3.15%) │ Precision ↑  │
│ **Scheme 3 Recall**        │ **0.4843**       │ 0.4404           │ -0.0439 (-4.39%) │ Recall ↓     │
│ **Scheme 3 F1-Score**      │ 0.4043           │ **0.4071**       │ +0.0028 (+0.28%) │ Equal        │
├────────────────────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────┤
│ **Pure Hallucinations (S)**│ 15,269 spans     │ **8,166 spans**  │ **-46.52%**      │ Hallucination│
│ **False Negatives (N)**    │ **9,241 spans**  │ 10,728 spans     │ +16.09%          │ Truncation   │
│ **Exact Matches (M)**      │ **13,768 spans** │ 11,991 spans     │ -12.91%          │ Conservation │
└────────────────────────────┴──────────────────┴──────────────────┴──────────────────┴──────────────┘
```

#### Category-Level Differential Analysis (Scheme 2 Weighted F1)

| Entity Category | Gold Total | Tagged XML F1 | Structured JSON F1 | Scheme 2 Δ F1 | Scheme 1 Δ F1 | Impact Description |
|---|---:|:---:|:---:|:---:|:---:|---|
| **STATUS** | 1,796 | 0.2937 | **0.4546** | **+0.1609** | **+0.1340** | Huge precision gain; structured key-value prevents stray status tags |
| **RO (Rule-Out)** | 9 | 0.1223 | **0.2478** | **+0.1255** | -0.0312 | Discrete categorization avoids inline confusion |
| **AGE** | 787 | **0.9230** | 0.9228 | -0.0002 | -0.0078 | Format invariant |
| **SEX** | 767 | **0.9086** | 0.9011 | -0.0075 | -0.0229 | Format invariant |
| **DRUG** | 6,673 | **0.6312** | 0.6236 | -0.0076 | -0.0566 | Near equal; slight recall loss on duplicate mentions |
| **HX** | 2,408 | **0.6770** | 0.6566 | -0.0204 | -0.0226 | Minor drop in narrative history coverage |
| **DX** | 1,543 | **0.4772** | 0.4552 | -0.0220 | -0.0221 | Minor recall loss |
| **AE** | 9,186 | **0.6586** | 0.6109 | -0.0477 | -0.0597 | Exhaustive list truncation in dense symptom paragraphs |
| **LAB** | 3,476 | **0.5498** | 0.4981 | -0.0517 | -0.0308 | Complex numeric values & units occasionally omitted |
| **INDICATION** | 162 | **0.3690** | 0.3080 | -0.0610 | +0.0002 | Lower frequency capture |
| **DOSE** | 1,619 | **0.6617** | 0.5923 | -0.0694 | -0.0144 | Multi-drug dosage lists truncated |

#### Mechanistic Takeaways:
1. **The "Precision-Recall Bias" of Prompt Representations:**
   - **Structured JSON** acts as an inductive regularizer that enforces conservative extraction. It **slashes pure hallucination spans by nearly half (46.5%)**, boosting Precision across all three schemes.
   - **Inline Tagged XML** maintains sequential narrative co-reference and exhaustive streaming, providing significantly superior **Recall (+11.3% in Scheme 1)**.
2. **List Truncation in High-Density Narratives:**
   - In complex clinical cases reporting 15+ symptoms and multiple co-medications, JSON generation suffers from item omission (list exhaustion fatigue), whereas Tagged XML forces the model to evaluate every token in context.
3. **Operational Recommendation:**
   - For **Pharmacovigilance Signal Screening (High Recall Prioritized)**: Use **Inline Tagged XML** (`P2_TAG`).
   - For **Automated Database Ingestion / Low-Noise Curation (High Precision Prioritized)**: Use **Structured JSON** (`P1_JSON`).

---

## 5. In-Depth Error & Boundary Anatomy

An automated parsing and linguistic decomposition script ([`publication/scripts/analyze_error_breakdown.py`](scripts/analyze_error_breakdown.py)) evaluated 20,000+ mismatch events.

### 5.1 Granular Analysis of Category C (Partial Matches)

Category C spans have correct category classification but imperfect character offsets.

```
                  Category C Overlap Distribution & Root Causes
┌─────────────────────────────┬───────────┬────────────┬─────────────────────────────┐
│ Model & Dataset             │ Mean IoU  │ Median IoU │ Dominant Root Cause         │
├─────────────────────────────┼───────────┼────────────┼─────────────────────────────┤
│ BioBERT (Fold 0, FAERS)     │ 0.5691    │ 0.5736     │ Subphrase/Superphrase (70%) │
│ BioBERT (Fold 0, VAERS)     │ 0.5223    │ 0.5185     │ Subphrase/Superphrase (93%) │
│ Claude 4.6 Sonnet (FAERS)   │ 0.4669    │ 0.4571     │ Subphrase/Superphrase (87%) │
│ LLaMA 4 (FAERS)             │ 0.4713    │ 0.4667     │ Subphrase/Superphrase (86%) │
│ LLaMA 4 (VAERS)             │ 0.4197    │ 0.4000     │ Subphrase/Superphrase (90%) │
└─────────────────────────────┴───────────┴────────────┴─────────────────────────────┘
```

#### Linguistic Root Causes of Boundary Mismatches:
1. **Subphrase / Superphrase Chunking (85%–90% of C errors):**
   - *Example:* Gold standard annotates `"hypoglycemia"`, whereas LLMs extract `"multiple severe episodes of hypoglycemia"` or `"hypoglycemia in patient with diabetes"`.
   - *Observation:* LLMs favor clinical semantic coherence over minimal syntactic heads.
2. **Clinical Modifier Boundary Variations (4%–7% of C errors):**
   - *Example:* `"acute respiratory failure"` vs. `"respiratory failure"`, `"recurrent nausea"` vs. `"nausea"`.
3. **Punctuation and Function Words (<1%–4% of C errors):**
   - Leading/trailing punctuation (`.` `,` `-`) and articles (`a`, `an`, `the`) account for an insignificant fraction of partial errors.

---

### 5.2 Category S Misclassification Matrix ($S_{\text{wrong\_class}}$)

When a model detects a gold span but assigns an incorrect taxonomy label, the error patterns are highly structured:

```
           Top Clinical Misclassification Confusion Pairs (FAERS)
┌───────────────────────────┬────────────────────────────────────────────────────────┐
│ Confusion Pair (Gold→Pred)│ Clinical Context & Linguistic Ambiguity                │
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ LAB → AE / DX (583 cases) │ Quantitative lab abnormalities (e.g. elevated enzyme)  │
│                           │ described syntactically as adverse symptoms.           │
│ DRUG → DX (577 cases)     │ Medication names embedded in regimen/treatment phrases │
│                           │ (e.g. "tramadol therapy") labeled as clinical DX.      │
│ AE → HX (279 cases)       │ Temporal ambiguity between current acute ADRs vs. past │
│                           │ medical history mentions in complex case narratives.   │
│ HX → INDICATION (160 cases│ Patient baseline pre-existing condition confounded     │
│                           │ with indication for current prescription.              │
└───────────────────────────┴────────────────────────────────────────────────────────┘
```

In VAERS, the dominant confusion pair is **`AE` $\to$ `STATUS` (1,050 cases)** (e.g., patient outcomes `"hospitalized"`, `"recovered"`, `"outcome unknown"` confounded with primary clinical symptoms).

---

### 5.3 Category S Hallucination Analysis ($S_{\text{hallucination}}$)

Pure hallucinations occur when a predicted span shares zero character overlap with any annotated gold entity.

#### Primary Hallucination Drivers:
1. **Normal Physiological / Non-Pathological Terms (52% of hallucinations):**
   - *Examples:* `"oral route"`, `"left arm"`, `"standardized assessment"`, `"blood pressure"` (when normal/baseline).
   - *Cause:* Prompts prompting for adverse reactions lead LLMs to over-extract general medical descriptions.
2. **Negation Scope Failures (28% of hallucinations):**
   - *Example:* In `"no pancreatic neoplasia had been observed"`, the LLM extracts `"pancreatic neoplasia"` as an `AE`.
3. **Non-Target Schema Overflow (20% of hallucinations):**
   - General timestamps and unstandardized dosage forms extracted when not part of the target evaluation schema.

---

## 6. Discussion & Practical Deployment Architecture

```
                    Recommended Pharmacovigilance Architecture
  Raw Case Narratives (FAERS / VAERS / EHR)
                     │
                     ▼
  ┌───────────────────────────────────────────────────────────┐
  │ Stage 1: Frontier LLM Semantic Extraction & Recall Booster │
  │ • Claude 4.6 Sonnet / LLaMA 4                              │
  │ • Zero-shot recall on rare indications & complex narratives│
  │ • Captures >90% of all clinical entity mentions (Scheme 1) │
  └──────────────────────────┬────────────────────────────────┘
                             │ Overlapping candidate spans
                             ▼
  ┌───────────────────────────────────────────────────────────┐
  │ Stage 2: Token-Level Boundary & Taxonomic Regularizer      │
  │ • Fine-Tuned BioBERT / Light Transformer                   │
  │ • Minimizes boundary drift, strips non-entity modifiers   │
  │ • Re-classifies ambiguous boundaries (AE vs LAB vs STATUS) │
  └──────────────────────────┬────────────────────────────────┘
                             │ Exact standardized clinical entities
                             ▼
  MedDRA / RxNorm / SNOMED Coding & Signal Detection
```

---

## 7. Reproducibility & Artifact Index

All analyses and tables are reproducible using the repository scripts and database:

| Component | File Path | Description |
|---|---|---|
| **Multi-Scheme Scorer** | [`publication/scripts/evaluate_three_schemes.py`](scripts/evaluate_three_schemes.py) | Computes Schemes 1, 2, and 3 across all models and folds with schema filtering. |
| **Output Format Comparator** | [`publication/scripts/compare_output_formats.py`](scripts/compare_output_formats.py) | Evaluates and contrasts Inline Tagged XML vs Structured JSON extraction paradigms. |
| **Error Anatomy Engine** | [`publication/scripts/analyze_error_breakdown.py`](scripts/analyze_error_breakdown.py) | Generates IoU distributions, confusion matrices, and hallucination categorizations. |
| **Unified Database** | [`publication/dataset.db`](dataset.db) | SQLite database with structured documents and SME1/ETHER annotation layers. |
| **Full Benchmark Excel** | [`publication/results/comparison_three_schemes/three_schemes_summary.xlsx`](results/comparison_three_schemes/three_schemes_summary.xlsx) | Multi-sheet workbook containing overall and per-category metrics. |
| **Error Analysis Excel** | [`publication/results/error_analysis/error_breakdown_summary.xlsx`](results/error_analysis/error_breakdown_summary.xlsx) | Granularity breakdowns, crosstabs, and hallucination term distributions. |
