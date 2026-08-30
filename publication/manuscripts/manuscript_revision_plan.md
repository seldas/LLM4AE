# Manuscript Revision Plan & Section-by-Section Modification Guide

**Target Document:** `publication/manuscripts/LLM4AE_rev1.docx`  
**Companion Document:** [`publication/manuscripts/reviewer_response_materials.md`](reviewer_response_materials.md)  
**Supporting Result Files:**
- [`publication/results/dataset_stats.md`](../results/dataset_stats.md)
- [`publication/results/comparison_three_schemes/three_schemes_summary.xlsx`](../results/comparison_three_schemes/three_schemes_summary.xlsx)
- [`publication/results/error_analysis/error_breakdown_summary.xlsx`](../results/error_analysis/error_breakdown_summary.xlsx)
- [`publication/technical_reports.md`](../technical_reports.md)

---

## 1. Executive Roadmap of Manuscript Updates

```
                        Manuscript Revision Architecture
┌───────────────────────────┬────────────────────────────────────────────────────────┐
│ Manuscript Section        │ Summary of Updates & Reviewer Mappings                 │
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ Title & Abstract          │ • Reflect multiple LLMs (Sonnet + LLaMA 4) [R#3 C3.1]  │
│                           │ • Define acronyms (FAERS, VAERS) [R#2 C2.1]            │
│                           │ • Update 10-fold CV & new benchmark numbers [R#2 W2]   │
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ 1. Introduction           │ • Add foundational ADE/NER citations [R#2 C2.2]        │
│                           │ • Theoretical exposition on LLM boundary bias [R#3 C3.3│
│                           │ • Mention clinical NLP toolkits (CLAMP, cTAKES) [R#3 C24│
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ 2. Materials and Methods  │ • 2.1: Add full corpus statistics (Table 1) [R#2 C2.3] │
│                           │ • 2.2: Clarify annotator clinical background [R#3 C3.5]│
│                           │ • 2.2: Document multi-LLM tool architecture [R#3 C3.6] │
│                           │ • 2.3: BioBERT 10-fold CV setup [R#2 C2.10]            │
│                           │ • 2.3: Few-shot prompt specification [R#3 C3.11, C3.12]│
│                           │ • 2.4: Formalize 3 Evaluation Schemes [R#3 C3.10, C3.13│
│                           │ • 2.4: Micro-F1 & M/C/S/N examples [R#2 C2.6, C2.7]    │
│                           │ • 2.4: Target category schema filtering rule           │
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ 3. Results                │ • 3.1: FAERS Benchmark (BioBERT 10-fold, Sonnet, LLaMA4│
│                           │ • 3.2: VAERS Benchmark with Filtered Schema [R#3 C3.19]│
│                           │ • 3.3: Category breakdown (Long-tail Indication) [R#2 C8│
│                           │ • 3.4: In-depth Error Anatomy (C IoU, S confusion) [R#3│
│                           │ • 3.5: Output Format Study (Tagged XML vs JSON) [R#3 23│
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ 4. Discussion             │ • 4.1: Cross-corpus synthesis (moved from 3.4) [R#2 C13│
│                           │ • 4.2: Precision-Recall tradeoff & boundary mechanics  │
│                           │ • 4.3: Hybrid Clinical PV Pipeline (LLM + SFT Encoder) │
│                           │ • 4.4: Limitations (Single annotator, prompt bounds)   │
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ Figures & Tables          │ • Table 1: Corpus Demographics (FAERS & VAERS)         │
│                           │ • Table 2: FAERS Master Benchmark (3 Schemes)          │
│                           │ • Table 3: VAERS Master Benchmark (3 Schemes)          │
│                           │ • Table 4: Output Format Comparison (Tagged vs JSON)   │
│                           │ • Figure 5: FAERS Error Anatomy (aligned x-axis 0-180) │
│                           │ • Figure 6: VAERS Error Anatomy (new figure) [R#3 C3.21│
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ Supplementary Material    │ • Table S1 & S2: FAERS & VAERS Taxonomy with examples  │
│                           │ • Section S2: BERT Selection Ablation Details [R#3 C3.9│
│                           │ • Section S3: Complete Prompt Text Files [R#3 C3.11,16]│
│                           │ • ESM Metadata Headers (Title, Authors, Contact) [Ed 1]│
└───────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 2. Section-by-Section Revision Specification

### Title & Abstract
- **Title Update:** Change title to explicitly include multiple LLMs:  
  *"Benchmarking Fine-Tuned Transformers and Frontier Large Language Models for Adverse Event Information Extraction from Spontaneous Reporting Narratives"*
- **Abstract Modifications:**
  - Define `FAERS` as "FDA Adverse Event Reporting System" and `VAERS` as "Vaccine Adverse Event Reporting System" on first use (*Reviewer #2, Comment 2.1*).
  - Update numerical results to report BioBERT 10-fold CV mean ($F_1 = 0.9058 \pm 0.0116$ Scheme 1, $0.7824 \pm 0.0103$ Scheme 2), Claude 4.6 Sonnet ($F_1 = 0.8404$ Scheme 1, $0.6443$ Scheme 2), and LLaMA 4 ($F_1 = 0.8561$ Scheme 1, $0.6249$ Scheme 2).
  - State clearly that the annotated SQLite corpus (`dataset.db`) and scoring scripts are publicly released (*Reviewer #2, Weakness 3*).

---

### Section 1: Introduction
- **Literature Broadening (*Reviewer #2, Comment 2.2*):**
  - Integrate seminal ADE/NER benchmarks: CADEC (Karimi et al., 2015), ADE Corpus (Gurulingappa et al., 2012), TAC 2017 Track 1 ADR extraction, SMM4H shared tasks, and MADE 1.0 (Jagannatha et al., 2019).
  - Highlight the unique challenges of spontaneous reporting post-market narratives (FAERS/VAERS) compared to curated electronic health records.
- **LLM Theoretical Boundary Bias (*Reviewer #3, Comment 3.3*):**
  - Insert exposition explaining why generative LLMs exhibit superphrase/subphrase boundary dilation: autoregressive pre-training optimizes for fluent semantic units rather than minimal syntactic entity spans.
- **Clinical NLP Toolkits (*Reviewer #3, Comment 3.24*):**
  - Mention existing specialized clinical information extraction toolkits (CLAMP, cTAKES, MedCAT).

---

### Section 2: Materials and Methods

#### 2.1 Datasets & Corpus Demographics (*Reviewer #2, Comment 2.3; Reviewer #3, Comment 3.19*)
- Insert **Table 1: Corpus Scale, Demographic, and Vocabulary Statistics**:
  - FAERS D1: 829 documents, 414,576 tokens (mean $500.1 \pm 254.6$), 17,766 sentences, 36,425 annotations, 3,991 unique AE/symptom terms, 2,085 unique drug terms.
  - VAERS: 1,000 documents, 439,681 tokens (mean $439.7 \pm 143.0$), 22,043 sentences, 40,711 annotations, 13,819 unique symptom terms (3.5× richer vocabulary), 863 vaccine terms.

#### 2.2 Human Annotation Protocol & Tooling (*Reviewer #2, Comments 2.4, 2.5; Reviewer #3, Comments 3.4, 3.5, 3.6, 3.7, 3.8*)
- **Annotator Profile:** Specify that annotations were curated by a biomedical research fellow holding an RN/BSN license with 4 years of acute clinical experience, calibrated on 50 trial cases supervised by senior pharmacovigilance faculty (*Reviewer #3, Comment 3.5*).
- **Guidelines:** Cite foundational VAERS and FAERS annotation protocols (Botsis et al., 2011; Wu et al., 2020) (*Reviewer #3, Comment 3.4*).
- **LLM4AE Platform:** Clarify multi-LLM backend support (Anthropic, Meta, OpenAI, Ollama) and describe the interactive review workflow (*Reviewer #3, Comment 3.6*).
- **Unsuccessfully Tagged Items:** Define as syntax formatting errors (e.g., unclosed tags, non-alphanumeric tag corruptions) occurring in $<0.4\%$ of outputs, resolved by regex validation (*Reviewer #3, Comments 3.7, 3.8*).
- **Special Strategy for Single-Annotator Constraint (*Reviewer #2, Comments 2.W1, 2.4*):**
  - *Context & Constraint:* Independent full-corpus dual annotation (SME2) was precluded due to severe institutional resource constraints regarding specialist clinical personnel. Rather than attempting circular validation (e.g., comparing human annotations against the evaluated models), we explicitly acknowledge this constraint and establish a 4-pillar quality assurance framework:
    1. **Expert Qualification & Calibration:** Single-annotator curation by a licensed clinical specialist with 4 years of acute care experience and faculty calibration.
    2. **Formal Operational Taxonomy (Supplement S1):** Detailed boundary, inclusion, exclusion, and disambiguation rules for complex overlapping clinical concepts (e.g., `AE` vs. `DX`, `DX` vs. `MHX`, `LAB` vs. `AE`).
    3. **Deterministic Multi-Pass Verification:** Multi-pass internal auditing with verified high consistency on closed-vocabulary entities (`AGE`, `SEX`, `DOSE`).
    4. **Community Adjudication via Open Source:** Full public release of `publication/dataset.db` and the interactive platform to enable external community adjudication and benchmark evolution.
    5. **Empirical Methodological Compensation:** Supplemented with extensive out-of-distribution validation (Leave-One-Pair-Out LOO 4-fold CV), 5-seed optimization replication, and paired bootstrap 95% CIs.

#### 2.3 Model Implementations & Baselines (*Reviewer #2, Comment 2.10; Reviewer #3, Comments 3.1, 3.11, 3.12*)
- **BioBERT Setup:** Detail the 10-fold cross-validation configuration (80% train, 10% validation, 10% test split per fold) using `dmis-lab/biobert-base-cased-v1.1`.
- **Frontier LLM Setup:** Detail execution for **Claude 4.6 Sonnet** (via Anthropic API) and **LLaMA 4 (`llama-4-maverick`)** under few-shot in-context tag-prompting (1 canonical exemplar).
- **Output Format Paradigm:** Introduce the comparative setup between Inline Tagged XML (`P2_TAG`) and Structured JSON (`P1_JSON`).

#### 2.4 Multi-Scheme Evaluation Framework (*Reviewer #2, Comments 2.6, 2.7, 2.8; Reviewer #3, Comments 3.10, 3.13, 3.17*)
- Formally define the three evaluation protocols:
  1. **Scheme 1 (Relaxed Entity Detection / Hallucination-Penalized):** $\text{TP} = M + C + S_{\text{wrong\_class}}$, $\text{Precision} = \frac{\text{TP}}{\text{TP} + 0.25 S_{\text{hallucination}}}$, $\text{Recall} = \frac{\text{Gold}_{\text{Detected}}}{\text{Total Gold}}$.
  2. **Scheme 2 (Weighted Clinical Baseline / ADE Protocol):** $\text{Precision} = \frac{M + 0.5C}{M + C + 0.25 S_{\text{total}}}$, $\text{Recall} = \frac{M + 0.5C}{M + C + N}$.
  3. **Scheme 3 (Strict Exact Match NER):** $\text{Precision} = \frac{M}{M + C + S_{\text{total}}}$, $\text{Recall} = \frac{M}{M + C + N}$.
- Clarify Micro-averaged aggregation across all documents (*Reviewer #2, Comment 2.7*).
- Provide clinical examples for $M$, $C$, $S_{\text{wrong\_class}}$, $S_{\text{hallucination}}$, and $N$ (*Reviewer #2, Comment 2.6; Reviewer #3, Comments 3.10, 3.13*).
- State the **Target Category Schema Filtering Rule**: non-gold categories (e.g., `TEMPORAL`, `DOSE`, `AGE`, `SEX` in VAERS) are filtered out prior to scoring rather than penalized as false positives.

---

### Section 3: Results

#### 3.1 Master Benchmark Performance (FAERS & VAERS)
- Present **Table 2 (FAERS Master Benchmark)** and **Table 3 (VAERS Master Benchmark)**:
  - BioBERT FAERS 10-Fold CV: Scheme 1 F1 = **$0.9058 \pm 0.0116$**, Scheme 2 F1 = **$0.7824 \pm 0.0103$**, Scheme 3 F1 = **$0.6395 \pm 0.0127$**.
  - Claude 4.6 Sonnet FAERS: Scheme 1 F1 = **0.8404**, Scheme 2 F1 = **0.6443**, Scheme 3 F1 = **0.4667**.
  - LLaMA 4 FAERS: Scheme 1 F1 = **0.8561**, Scheme 2 F1 = **0.6249**, Scheme 3 F1 = **0.4043**.
  - ETHER FAERS: Scheme 1 F1 = 0.8227, Scheme 2 F1 = 0.2693, Scheme 3 F1 = 0.1147.
  - BioBERT VAERS 10-Fold CV: Scheme 1 F1 = **$0.9482 \pm 0.0076$**, Scheme 2 F1 = **$0.8062 \pm 0.0094$**, Scheme 3 F1 = **$0.6880 \pm 0.0114$**.
  - LLaMA 4 VAERS (Filtered): Scheme 1 F1 = **0.9112**, Scheme 2 F1 = **0.4474**, Scheme 3 F1 = **0.2711**.

#### 3.2 Category-Level Breakdown & Long-Tail Generalization
- Present **Table 4 (FAERS 11-Category Evaluation Table)**:
  - Contrast frequent categories (`AE`, `DRUG`, `LAB`, `AGE`, `SEX`) vs. rare long-tail entities.
  - Highlight the `INDICATION` category (162 gold instances): BioBERT collapses due to extreme sparsity (F1 = **0.0431**), while Claude 4.6 Sonnet (F1 = **0.3838**) and LLaMA 4 (F1 = **0.3690**) maintain strong semantic few-shot capture.

#### 3.3 In-Depth Error Anatomy (*Reviewer #3, Comments 3.10, 3.14, 3.21*)
- **Category C Granularity:** Mean IoU (BioBERT 0.57, LLMs 0.47). Show that 85%–90% of C mismatches are superphrase context extensions (*Figure 5a*).
- **Category S Misclassification Matrix:** Document top confusing pairs (LAB $\to$ AE/DX [583 cases], DRUG $\to$ DX [577 cases], AE $\to$ HX [279 cases], AE $\to$ STATUS [1,050 cases in VAERS]).
- **Pure Hallucinations ($S_{\text{hallucination}}$):** Group into normal physiological terms (52%), negation scope errors (28%), and non-target schema overflow (20%).
- **Axis Alignment:** Align Figure 5b and 5c horizontal axes to identical range ($0 - 180$) (*Reviewer #3, Comment 3.14*).
- **VAERS Error Breakdown:** Add **Figure 6** presenting Category C IoU distribution and S confusion matrix for VAERS (*Reviewer #3, Comment 3.21*).

#### 3.4 Impact of Output Format Paradigm (Tagged XML vs. JSON) (*Reviewer #3, Comment 3.23*)
- Present **Table 5: LLaMA 4 FAERS Tagged XML (`P2_TAG`) vs. Structured JSON (`P1_JSON`)**:
  - Show that JSON output reduces pure hallucinations by **46.52%** (from 15,269 to 8,166 spans), boosting Scheme 1 Precision from 0.8648 to **0.9201**.
  - Show that Tagged XML maintains superior narrative co-reference, yielding **+11.26% higher Recall** in Scheme 1 (0.8476 vs. 0.7350).

---

### Section 4: Discussion & Limitations
- **4.1 Cross-Corpus Synthesis:** Relocate synthesis paragraph from Section 3.4 to Section 4.1 (*Reviewer #2, Comment 2.13*).
- **4.2 The Semantic vs. Boundary Decoupling:** Discuss why LLMs achieve $\ge 85\% - 91\%$ raw entity detection while trailing supervised models on exact token boundaries.
- **4.3 Hybrid Pharmacovigilance Pipeline:** Propose the two-stage architecture: Stage 1 Frontier LLM Semantic Recall Filter $\to$ Stage 2 Fine-Tuned Small Encoder Boundary & Taxonomy Regularizer.
- **4.4 Limitations:**
  - *Single-Annotator Constraint & Transparent Framing:* Formally acknowledge single-expert annotation (SME1) as a study limitation; reframe the dataset from a "definitive gold standard" to an "expert-curated clinical reference benchmark"; highlight the multi-pass calibration, detailed operational guidelines (Supplementary S1), and open-source platform release as enablers for community adjudication (*Reviewer #2, Weakness 1, Comment 2.4*).
  - *Case Series Scope:* Discuss the 4 drug-AE series in FAERS and contextualize the Leave-One-Pair-Out out-of-distribution findings.
  - *Prompt & Architecture Boundaries:* Note prompt sensitivity across zero/few-shot regimes (*Reviewer #3, Comment 3.23*) and discuss span confidence threshold tuning (*Reviewer #3, Comment 3.22*).

---

### Supplementary Material & ESM Artifacts
- **Table S1 & Table S2:** Complete annotation guidelines, inclusion/exclusion rules, and clinical exemplars for FAERS (17 categories) and VAERS (11 categories) (*Reviewer #2, Comment 2.12; Reviewer #3, Comment 3.18*).
- **Section S2:** Model Selection & Pre-training Ablation Details (BioBERT vs. PubMedBERT vs. ClinicalBERT) (*Reviewer #3, Comment 3.9*).
- **Section S3:** Verbatim Prompt Templates for FAERS Tagged, FAERS JSON, and VAERS Tagged (*Reviewer #3, Comments 3.11, 3.16*).
- **ESM Compliance:** Ensure all supplementary workbooks include the required title, journal, author affiliations, and corresponding author metadata sheet (*Editorial Comment 1*).

---

## 3. Key Source Result Files Mapping

| File Path | Used In Manuscript Revision | Purpose / Content |
|---|---|---|
| [`publication/results/dataset_stats.md`](../results/dataset_stats.md) | Section 2.1, Table 1 | Full corpus scale, sentence/token counts, unique vocabulary stats. |
| [`publication/results/comparison_three_schemes/three_schemes_summary.xlsx`](../results/comparison_three_schemes/three_schemes_summary.xlsx) | Section 3.1, 3.2, Tables 2, 3, 4 | Multi-scheme benchmark results for BioBERT 10-fold, Sonnet, LLaMA 4, ETHER. |
| [`publication/results/error_analysis/error_breakdown_summary.xlsx`](../results/error_analysis/error_breakdown_summary.xlsx) | Section 3.3, Figures 5, 6 | Category C IoU distributions, S confusion matrices, hallucination counts. |
| [`publication/scripts/compare_output_formats.py`](../scripts/compare_output_formats.py) | Section 3.4, Table 5 | Output format study metrics (Tagged XML vs Structured JSON). |
| [`publication/dataset.db`](../dataset.db) | Abstract, Section 5 | Public SQLite database containing 1,829 reports and all annotations. |
