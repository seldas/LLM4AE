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

#### 2.4 Two-Tier Evaluation Framework & Metric Definitions (*Reviewer #2, Comments 2.6, 2.7, 2.8; Reviewer #3, Comments 3.10, 3.13, 3.17*)
- **Discontinuation of Former Scheme 1:** Formally state that the previous relaxed entity detection metric (Scheme 1) has been discontinued to avoid metric leniency and inflation concerns raised by Reviewer #3.
- **Two-Tier Framework Definition:**
  1. **Primary Tier — Strict Exact-Match Standard NER (Scheme 3):** Standard CoNLL/SemEval exact boundary and label match.
     $$\text{Precision} = \frac{M}{M + C_{\text{total}} + S_{\text{non\_overlap}}}, \quad \text{Recall} = \frac{M}{M + C_{\text{total}} + N}, \quad F_1 = \frac{2 \cdot P \cdot R}{P + R}$$
  2. **Secondary Tier — Refined ADE-Eval Clinical Weighted Metric (Scheme 2):**
     - **Category $C$ ($C_{\text{total}} = C_{\text{boundary}} + C_{\text{class}}$):** Unifies boundary inexactness ($C_{\text{boundary}}$) and category misclassification ($C_{\text{class}}$, e.g. `AE` vs. `DX`, `DX` vs. `MHX`, `DRUG` vs. `TREATMENT`). Receives **0.5 partial credit** in numerator and denominator, recognizing that the clinical entity was correctly localized in the narrative.
     - **Category $S$ ($S_{\text{non\_overlap}}$):** Strictly reserved for non-overlapping spurious predictions (false positives with zero gold overlap), penalized at 0.25 in the precision denominator.
     $$\text{Precision} = \frac{M + 0.5 C_{\text{total}}}{M + C_{\text{total}} + 0.25 S_{\text{non\_overlap}}}, \quad \text{Recall} = \frac{M + 0.5 C_{\text{total}}}{M + C_{\text{total}} + N}, \quad F_1 = \frac{2 \cdot P \cdot R}{P + R}$$
- Clarify Micro-averaged aggregation across all documents (*Reviewer #2, Comment 2.7*).
- Provide clinical examples for $M$, $C_{\text{boundary}}$, $C_{\text{class}}$, $S_{\text{non\_overlap}}$, and $N$ (*Reviewer #2, Comment 2.6; Reviewer #3, Comments 3.10, 3.13*).
- State the **Target Category Schema Filtering Rule**: non-gold categories (e.g., `TEMPORAL`, `DOSE`, `AGE`, `SEX` in VAERS) are filtered out prior to scoring rather than penalized as false positives.

---

### Section 3: Results

#### 3.1 Master Benchmark Performance (FAERS & VAERS)
- Present **Table 2 (FAERS Master Benchmark)** and **Table 3 (VAERS Master Benchmark)** under the Two-Tier Framework:
  - **BioBERT FAERS (10-Fold CV):** Tier 1 Strict F1 = **$0.6099 \pm 0.0133$**, Tier 2 ADE-Eval F1 = **$0.7638 \pm 0.0095$**.
  - **BioBERT FAERS (Leave-One-Pair-Out LOO 4-Fold x 5-Seed OOD):** Tier 1 Strict F1 = **$0.5930 \pm 0.0542$** (95% CI: `[0.5758, 0.5921]`), Tier 2 ADE-Eval F1 = **$0.7463 \pm 0.0298$** (95% CI: `[0.7543, 0.7649]`).
  - **Claude 4.6 Sonnet FAERS (1-shot):** Tier 1 Strict F1 = **0.4392**, Tier 2 ADE-Eval F1 = **0.6359**.
  - **LLaMA 4 FAERS (1-shot):** Tier 1 Strict F1 = **0.3755**, Tier 2 ADE-Eval F1 = **0.6170**.
  - **ETHER FAERS (Rule-based):** Tier 1 Strict F1 = **0.1147**, Tier 2 ADE-Eval F1 = **0.2693**.
  - **BioBERT VAERS (10-Fold CV):** Tier 1 Strict F1 = **$0.6441 \pm 0.0136$**, Tier 2 ADE-Eval F1 = **$0.7789 \pm 0.0099$**.
  - **LLaMA 4 VAERS (1-shot, Filtered):** Tier 1 Strict F1 = **0.2364**, Tier 2 ADE-Eval F1 = **0.4766**.

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
