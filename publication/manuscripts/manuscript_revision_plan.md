# Manuscript Revision Plan & Section-by-Section Modification Guide

**Target Document:** `publication/manuscripts/LLM4AE_rev1.docx`  
**Companion Document:** [`publication/manuscripts/reviewer_response_materials.md`](reviewer_response_materials.md)  
**Supporting Result Files:**
- [`publication/results/dataset_stats.md`](../results/dataset_stats.md)
- [`publication/results/comparison_three_schemes/three_schemes_summary.xlsx`](../results/comparison_three_schemes/three_schemes_summary.xlsx)
- [`publication/results/bert_runs_FAERS_LOO/loo_evaluation_summary.xlsx`](../results/bert_runs_FAERS_LOO/loo_evaluation_summary.xlsx)
- [`publication/results/error_analysis/error_breakdown_summary.xlsx`](../results/error_analysis/error_breakdown_summary.xlsx)
- [`publication/dataset.db`](../dataset.db)

---

## 1. Executive Roadmap of Manuscript Updates

```
                        Manuscript Revision Architecture
┌───────────────────────────┬────────────────────────────────────────────────────────┐
│ Manuscript Section        │ Summary of Updates & Reviewer Mappings                 │
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ Title & Abstract          │ • Title: Neutral, plural ("Instruction-Tuned LLMs")    │
│                           │ • Define acronyms (FAERS, VAERS) [R#2 C2.1]            │
│                           │ • Report Two-Tier Metrics (Strict CoNLL & ADE-Eval)    │
│                           │ • Highlight LOO 4-fold OOD Generalization & Open Data  │
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ 1. Introduction           │ • Add foundational ADE/NER citations [R#2 C2.2]        │
│                           │ • Theoretical exposition on LLM boundary bias [R#3 C3.3│
│                           │ • Contextualize spontaneous reporting vs EHRs [R#2 C2.2│
│                           │ • Mention clinical NLP toolkits (CLAMP, cTAKES) [R#3 C24│
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ 2. Materials and Methods  │ • 2.1: Full corpus statistics & vocabulary [R#2 C2.3]  │
│                           │ • 2.2: Annotator clinical credentials (RN/BSN) [R#3 C35│
│                           │ • 2.2: Transparent single-annotator QA protocol [R#2 W1│
│                           │ • 2.2: Annotation workflow (LLM pre-tag + 100% audit)  │
│                           │ • 2.3: BioBERT 10-fold CV & 5 random seeds [R#2 C2.10] │
│                           │ • 2.3: Leave-One-Drug-AE-Pair-Out (LOO) setup [R#2]    │
│                           │ • 2.3: Few-shot prompt specification [R#3 C3.11, C3.12]│
│                           │ • 2.4: Discontinuation of Scheme 1; Two-Tier Framework │
│                           │ • 2.4: Redefine C (boundary + mis-class) and S (pure FP│
│                           │ • 2.4: Micro-F1 aggregation & Target Schema Filtering  │
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ 3. Results                │ • 3.1: Master Benchmark on FAERS & VAERS (Table 2, 3)  │
│                           │ • 3.2: LOO 4-Fold Generalization across 4 Case-Series  │
│                           │ • 3.3: Per-Category Breakdown (INDICATION collapse)    │
│                           │ • 3.4: In-depth Error Anatomy (C IoU, class confusion) │
│                           │ • 3.5: Output Format Study (Tagged XML vs JSON Table 5)│
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ 4. Discussion & Limits    │ • 4.1: Cross-corpus synthesis [R#2 C2.13]              │
│                           │ • 4.2: Semantic vs. Boundary Decoupling Mechanics      │
│                           │ • 4.3: Two-Stage Hybrid PV Architecture Pipeline       │
│                           │ • 4.4: Limitations (Single annotator, Case-Series scope│
├───────────────────────────┼────────────────────────────────────────────────────────┤
│ Supplementary Material    │ • Table S1 & S2: FAERS & VAERS Full Guidelines & Rules │
│                           │ • Section S2: BioBERT a priori Selection Rationale     │
│                           │ • Section S3: Complete Prompt Text Files [R#3 C3.11,16]│
│                           │ • ESM Metadata Cover Sheet (Drug Safety Compliance)    │
└───────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 2. Section-by-Section Revision Specification

### Title & Abstract
- **Title Update:** Refine title to be objective and reflect evaluated models:  
  *"Benchmarking Fine-Tuned Encoders and Instruction-Tuned Large Language Models for Adverse Event Clinical Concept Extraction from Spontaneous Reporting Narratives"*
- **Abstract Modifications:**
  - Define `FAERS` as "FDA Adverse Event Reporting System" and `VAERS` as "Vaccine Adverse Event Reporting System" on first mention (*Reviewer #2, Comment 2.1*).
  - Report Primary Tier (Strict Exact-Match NER) and Secondary Tier (ADE-Eval Clinical Weighted) metrics:
    - FAERS BioBERT (10-fold CV): Strict F1 = **$0.6099 \pm 0.0133$**, ADE-Eval F1 = **$0.7638 \pm 0.0095$**.
    - FAERS BioBERT (Leave-One-Pair-Out LOO): Strict F1 = **$0.5930 \pm 0.0542$** (95% CI: `[0.5758, 0.5921]`), ADE-Eval F1 = **$0.7463 \pm 0.0298$** (95% CI: `[0.7543, 0.7649]`), demonstrating minimal OOD decay ($\Delta \text{F1} \approx 1.75\%$).
    - FAERS Claude 4.6 Sonnet (1-shot): Strict F1 = **0.4392**, ADE-Eval F1 = **0.6359**.
    - FAERS LLaMA 4 (1-shot): Strict F1 = **0.3755**, ADE-Eval F1 = **0.6170**.
    - VAERS BioBERT (10-fold CV): Strict F1 = **$0.6441 \pm 0.0136$**, ADE-Eval F1 = **$0.7789 \pm 0.0099$**.
    - VAERS LLaMA 4 (Filtered): Strict F1 = **0.2364**, ADE-Eval F1 = **0.4766**.
  - Formally announce public release of the unified SQLite database (`publication/dataset.db`) containing 1,829 reports and scoring tools (*Reviewer #2, Weakness 3*).

---

### Section 1: Introduction
- **Comprehensive Literature Framing (*Reviewer #2, Comment 2.2*):**
  - Integrate seminal ADE and biomedical NER benchmarks: CADEC (Karimi et al., 2015), ADE Corpus (Gurulingappa et al., 2012), TAC 2017 Track 1 Adverse Reaction Extraction, SMM4H shared tasks, and MADE 1.0 (Jagannatha et al., 2019).
  - Explicitly delineate why post-market spontaneous reporting narratives (FAERS/VAERS) present distinctive extraction challenges compared to clinical EHRs (unstandardized vocabulary, extreme colloquial symptom diversity, multi-stakeholder reporters, high syntactic fragmentation).
- **LLM Theoretical Boundary Bias (*Reviewer #3, Comment 3.3*):**
  - Provide theoretical exposition explaining why autoregressive LLMs exhibit phrase dilation: next-token pre-training optimizes semantic coherence rather than minimal syntactic head spans, lacking inductive token-level transition regularizers (e.g. CRF/BIO constraints).
- **Clinical NLP Toolkits Context (*Reviewer #3, Comment 3.24*):**
  - Contextualize rule-based/hybrid clinical toolkits (cTAKES, CLAMP, MedCAT).

---

### Section 2: Materials and Methods

#### 2.1 Datasets & Corpus Demographics (*Reviewer #2, Comment 2.3; Reviewer #3, Comment 3.19*)
- Insert **Table 1: Corpus Scale, Demographic, and Vocabulary Statistics**:
  - **FAERS D1:** 829 documents, 414,576 tokens (mean $500.1 \pm 254.6$), 17,766 sentences, 36,425 SME1 annotations, 3,991 unique AE/symptom surface terms, 2,085 unique drug terms.
  - **VAERS:** 1,000 documents, 439,681 tokens (mean $439.7 \pm 143.0$), 22,043 sentences, 40,711 SME1 annotations, 13,819 unique symptom terms, 863 vaccine terms.
  - **Vocabulary Nuance:** Tone down "richer" claim to "3.5× higher surface-form symptom expression diversity under exact string matching".

#### 2.2 Human Annotation Protocol & Quality Framework (*Reviewer #2, Comments 2.W1, 2.4, 2.5; Reviewer #3, Comments 3.4, 3.5, 3.6, 3.7, 3.8*)
- **Annotator Profile:** Specify curation by a post-graduate biomedical informatics research fellow holding a registered nursing license (RN/BSN) with 4 years of acute inpatient clinical experience, calibrated on 50 trial cases supervised by senior pharmacovigilance faculty (*Reviewer #3, Comment 3.5*).
- **Guideline Lineage:** Cite foundational VAERS (Botsis et al., 2011) and FAERS (Wu et al., 2020) annotation protocols (*Reviewer #3, Comment 3.4*).
- **Annotation Workflow Provenance:** Explicitly document the two-stage interactive workflow: (1) LLM generated candidate spans in the GUI; (2) human clinical fellow inspected 100% of spans, editing boundaries, correcting labels, deleting false alarms, and manually tagging missed entities.
- **Unsuccessfully Tagged Items:** Define as syntactic formatting errors occurring in $<0.4\%$ of generations, resolved by regex validation (*Reviewer #3, Comments 3.7, 3.8*).
- **Single-Annotator Quality Assurance Framework:**
  - Independent double-annotation was precluded by specialist clinical resource constraints. We establish a 5-pillar QA framework:
    1. *Licensed Clinical Credentialing & Faculty Calibration;*
    2. *Comprehensive Operational Taxonomy with Disambiguation Rules (Supplementary Table S1/S2);*
    3. *Deterministic Multi-Pass Verification with Verified Near-Perfect Closed-Vocabulary Extraction (`AGE`, `SEX`, `DOSE`);*
    4. *Re-framing from "Definitive Gold Standard" to "Expert Reference Benchmark";*
    5. *Public Release of `dataset.db` for Open Community Adjudication.*

#### 2.3 Model Implementations & Validation Setup (*Reviewer #2, Comment 2.10; Reviewer #3, Comments 3.1, 3.11, 3.12*)
- **BioBERT In-Distribution Setup:** Stratified 10-fold cross-validation (80% train, 10% dev, 10% test per fold) repeated across 5 independent random initialization seeds (`42, 123, 456, 789, 1011`).
- **BioBERT Out-of-Distribution Setup (Leave-One-Pair-Out LOO):** 4-Fold cross-validation held out by Drug-AE Case Series (`Azacitidine-QT`, `Tramadol-Hypoglycemia`, `Baricitinib-Hypersensitivity`, `Erenumab-Stroke`) with 5 seeds per fold.
- **Frontier LLM Setup:** Claude 4.6 Sonnet and LLaMA 4 evaluated under 1-shot in-context instruction prompting.
- **Output Format Paradigm:** Inline Tagged XML (`P2_TAG`) vs. Structured JSON (`P1_JSON`).

#### 2.4 Two-Tier Evaluation Framework & Metric Definitions (*Reviewer #2, Comments 2.6, 2.7, 2.8; Reviewer #3, Comments 3.10, 3.13, 3.17*)
- **Discontinuation of Former Scheme 1:** Formally state that relaxed entity detection (Scheme 1) has been discontinued.
- **Two-Tier Framework Formulation:**
  1. **Primary Tier — Strict Exact-Match NER (Scheme 3):** Standard CoNLL/SemEval exact match.
     $$\text{Precision} = \frac{M}{M + C_{\text{total}} + S_{\text{non\_overlap}}}, \quad \text{Recall} = \frac{M}{M + C_{\text{total}} + N}, \quad F_1 = \frac{2 \cdot P \cdot R}{P + R}$$
  2. **Secondary Tier — Refined ADE-Eval Clinical Weighted Metric (Scheme 2):**
     - **Category $C$ ($C_{\text{total}} = C_{\text{boundary}} + C_{\text{class}}$):** Unifies boundary inexactness ($C_{\text{boundary}}$) and category misclassification ($C_{\text{class}}$) with **0.5 partial credit**.
     - **Category $S$ ($S_{\text{non\_overlap}}$):** Strictly reserved for non-overlapping spurious predictions (0.25 denominator penalty).
     $$\text{Precision} = \frac{M + 0.5 C_{\text{total}}}{M + C_{\text{total}} + 0.25 S_{\text{non\_overlap}}}, \quad \text{Recall} = \frac{M + 0.5 C_{\text{total}}}{M + C_{\text{total}} + N}, \quad F_1 = \frac{2 \cdot P \cdot R}{P + R}$$
- **Micro-averaging & Schema Filtering:** Clarify dataset-level micro-averaging and non-gold category filtering (e.g. ignoring `DOSE`/`AGE` on VAERS rather than penalizing as FP).

---

### Section 3: Results

#### 3.1 Master Benchmark Performance (FAERS & VAERS)
- **Table 2 (FAERS Master Benchmark):**
  - BioBERT (10-Fold CV): Strict F1 = **$0.6099 \pm 0.0133$**, ADE-Eval F1 = **$0.7638 \pm 0.0095$**.
  - Claude 4.6 Sonnet (1-shot): Strict F1 = **0.4392**, ADE-Eval F1 = **0.6359**.
  - LLaMA 4 (1-shot): Strict F1 = **0.3755**, ADE-Eval F1 = **0.6170**.
  - ETHER (Rule-based): Strict F1 = **0.1147**, ADE-Eval F1 = **0.2693**.
- **Table 3 (VAERS Master Benchmark):**
  - BioBERT (10-Fold CV): Strict F1 = **$0.6441 \pm 0.0136$**, ADE-Eval F1 = **$0.7789 \pm 0.0099$**.
  - LLaMA 4 (1-shot, Filtered): Strict F1 = **0.2364**, ADE-Eval F1 = **0.4766**.

#### 3.2 Out-of-Distribution Generalization (Leave-One-Pair-Out LOO)
- BioBERT 4-Fold LOO $\times$ 5-Seed Results:
  - `Azacitidine-QT`: Strict F1 = **$0.6280 \pm 0.0097$**, ADE F1 = **$0.7733 \pm 0.0092$**.
  - `Baricitinib-Hypersensitivity`: Strict F1 = **$0.6563 \pm 0.0178$**, ADE F1 = **$0.7751 \pm 0.0128$**.
  - `Tramadol-Hypoglycemia`: Strict F1 = **$0.5602 \pm 0.0091$**, ADE F1 = **$0.7242 \pm 0.0036$**.
  - `Erenumab-Stroke`: Strict F1 = **$0.5274 \pm 0.0105$**, ADE F1 = **$0.7126 \pm 0.0077$**.
  - **Overall LOO Mean:** Strict F1 = **$0.5930 \pm 0.0542$** (95% CI: `[0.5758, 0.5921]`), ADE F1 = **$0.7463 \pm 0.0298$** (95% CI: `[0.7543, 0.7649]`).
  - **Generalization Gap:** Out-of-distribution transfer gap is only $1.75\%$ relative to 10-fold CV.

#### 3.3 Per-Category Breakdown & Long-Tail Generalization
- **Table 4 (FAERS 11-Category Evaluation Table):**
  - High accuracy on structural entities: `SEX` (Strict 0.9213, ADE 0.9571), `AGE` (Strict 0.9173, ADE 0.9492), `TEMPORAL` (Strict 0.7398, ADE 0.8619).
  - Robust core extraction: `DRUG` (Strict 0.5280, ADE 0.7156), `AE` (Strict 0.5115, ADE 0.6966).
  - `INDICATION` Sparsity Contrast: BioBERT collapses in OOD transfer (Strict F1 = **0.0368**), while Claude 4.6 Sonnet (F1 = **0.3838**) and LLaMA 4 (F1 = **0.3690**) maintain robust semantic capture.

#### 3.4 In-Depth Error Anatomy (*Reviewer #3, Comments 3.10, 3.14, 3.21*)
- **Methodology (Technical Overview):** To conduct the in-depth error analysis, we computationally parse the raw span-level model predictions against the SME1 gold standard annotations, classifying boundary discrepancies (`Category C`) and class confusions (`S_wrong_class`) via character offset overlap logic. For Category C mismatches, we compute Intersection-over-Union (IoU) distributions and systematically categorize the root cause of the shift (e.g., punctuation, clinical modifier inclusion, or superphrase context extensions). For `S_wrong_class` misclassifications, we map the most closely overlapping gold category to the erroneous prediction to construct pairwise confusion matrices, revealing systematic model schema biases.
- **Category C Granularity:** Mean IoU (BioBERT FAERS: 0.57, BioBERT VAERS Seed 42: 0.52, LLMs: ~0.42–0.47). We demonstrate that the vast majority of LLM boundary mismatches (85%–92%) and BioBERT VAERS mismatches (91.7%) are driven by subphrase/superphrase context extensions rather than complex boundary shifts (*Figure 5a*).
- **Class Confusion Matrix ($C_{\text{class}}$):** 
  - **LLaMA 4 FAERS (Tagged XML):** Top confusing pairs include structural boundary misalignments (LAB $\to$ LAB [934 cases], DRUG $\to$ DRUG [845 cases]) and category shifts (DRUG $\to$ DX [350 cases], LAB $\to$ AE [267 cases]).
  - **LLaMA 4 FAERS (JSON):** The JSON paradigm alters the confusion profile, causing high misclassification of LAB entities into DOSE (775 cases) or AE (485 cases).
  - **LLaMA 4 VAERS:** Dominated by AE $\to$ AE boundary misalignments (6,809 cases) and high confusion of AE $\to$ STATUS (1,050 cases) and AE $\to$ LAB (919 cases).
- **Non-Overlapping Spurious Predictions ($S_{\text{non\_overlap}}$):** Grouped into physiological/anatomical terms (52%), negation scope errors (28%), and schema overflow (20%).
- **Axis Alignment:** Align Figure 5b and 5c horizontal axes to identical range ($0 - 180$) (*Reviewer #3, Comment 3.14*).
- **VAERS Error Anatomy:** Add **Figure 6** presenting Category C IoU distribution and confusion matrix for VAERS, explicitly integrating the BioBERT Seed 42 baseline metrics (*Reviewer #3, Comment 3.21*).

#### 3.5 Impact of Output Format Paradigm (Tagged XML vs. JSON) (*Reviewer #3, Comment 3.23*)
- **Table 5: LLaMA 4 FAERS Tagged XML (`P2_TAG`) vs. Structured JSON (`P1_JSON`):**
  - JSON output reduces non-overlapping spurious false positives ($S_{\text{non\_overlap}}$) by **46.52%** (from 15,269 to 8,166 spans).
  - Tagged XML preserves narrative token alignment and yields **+11.26% higher Recall** (0.8476 vs. 0.7350).

---

### Section 4: Discussion & Limitations
- **4.1 Cross-Corpus Synthesis:** Relocate synthesis paragraph from Section 3.4 to Section 4.1 (*Reviewer #2, Comment 2.13*).
- **4.2 Semantic vs. Boundary Decoupling:** Detail why LLMs achieve high clinical localization while trailing supervised models on exact boundary syntax.
- **4.3 Two-Stage Hybrid PV Architecture:** Propose the production pipeline: Frontier LLM Semantic Recall Filter $\to$ Fine-Tuned Small Encoder Boundary Regularizer.
- **4.4 Limitations:**
  - *Single-Annotator Constraint & Transparent Framing:* Acknowledge SME1 curation limitation; reframe corpus as an expert reference benchmark; highlight calibration, guidelines (Table S1/S2), and open platform release (*Reviewer #2, Weakness 1, Comment 2.4*).
  - *Case Series Scope:* Discuss 4 Drug-AE series in FAERS and contextualize LOO findings.
  - *Prompt Sensitivity & Confidence Calibration:* Note prompt variance and outline span probability threshold calibration as future work (*Reviewer #3, Comments 3.22, 3.23*).

---

### Supplementary Material & ESM Artifacts
- **Table S1 & Table S2:** Complete operational guidelines, inclusion/exclusion criteria, and clinical exemplars for FAERS (17 categories) and VAERS (11 categories) (*Reviewer #2, Comment 2.12; Reviewer #3, Comment 3.18*).
- **Section S2:** Model Selection & Pre-training Ablation Rationale (BioBERT domain match for pharmacology) (*Reviewer #3, Comment 3.9*).
- **Section S3:** Verbatim Prompt Templates for FAERS Tagged, FAERS JSON, and VAERS Tagged (*Reviewer #3, Comments 3.11, 3.16*).
- **ESM Compliance:** Full metadata header page on all electronic supplementary workbooks (*Editorial Comment 1*).
