# Reviewer Response Materials & Evidence Mapping Document

**Manuscript Title:** Benchmarking Fine-Tuned Transformers and Frontier Large Language Models for Adverse Event Information Extraction from Spontaneous Reporting Narratives (LLM4AE)  
**Target Manuscript:** `publication/manuscripts/LLM4AE_rev1.docx`  
**Companion Document:** [`publication/manuscripts/manuscript_revision_plan.md`](manuscript_revision_plan.md)  
**Primary Result Assets:**
- [`publication/results/dataset_stats.md`](../results/dataset_stats.md)
- [`publication/results/comparison_three_schemes/three_schemes_summary.xlsx`](../results/comparison_three_schemes/three_schemes_summary.xlsx)
- [`publication/results/error_analysis/error_breakdown_summary.xlsx`](../results/error_analysis/error_breakdown_summary.xlsx)
- [`publication/scripts/evaluate_three_schemes.py`](../scripts/evaluate_three_schemes.py)
- [`publication/scripts/compare_output_formats.py`](../scripts/compare_output_formats.py)
- [`publication/scripts/analyze_error_breakdown.py`](../scripts/analyze_error_breakdown.py)
- [`publication/dataset.db`](../dataset.db)

---

## Overview

This document provides complete, rigorous, and point-by-point response materials for every comment raised by Reviewer #2, Reviewer #3, and the Editorial Team. Each comment is paired with:
1. **The Exact Reviewer / Editor Comment**.
2. **Detailed Author Response & Academic Rationale**.
3. **Exact Supporting Quantitative Data & Empirical Evidence**.
4. **Target Section for Manuscript Modification** (cross-referenced with `manuscript_revision_plan.md`).
5. **Source Scripts / Result Files Utilized**.

---

# Part 1: Reviewer #2 Comments & Point-by-Point Responses

### Reviewer #2: Overall Weaknesses & General Appraisal

#### Comment 2.W1 (Single Annotator Concern)
> *Weakness: "The corpus was annotated by only one person; therefore, the quality of the annotation could be compromised in some contexts (the authors acknowledge this aspect in the limitations section)."*

- **Author Response:**
  We fully agree with the reviewer that independent dual-annotation with standard inter-annotator agreement (IAA) represents the methodological ideal. In our study, annotation was conducted by a qualified clinical research fellow holding an RN/BSN license with 4 years of acute care experience, calibrated under the supervision of senior pharmacovigilance faculty. Due to severe institutional resource constraints regarding specialist clinical personnel, independent double-annotation of the 1,829 reports was not feasible.
  
  To maximize annotation validity and transparency without relying on circular validation:
  1. **Comprehensive Operational Taxonomy (Supplement S1):** We formalized explicit inclusion, exclusion, boundary, and disambiguation rules for overlapping clinical categories (e.g., `AE` vs. `DX`, `DX` vs. `MHX`, `LAB` vs. `AE`).
  2. **Multi-Pass Internal Verification:** A multi-pass auditing workflow was enforced, demonstrating high internal consistency particularly on closed-vocabulary structural entities (`AGE`, `SEX`, `DOSE`).
  3. **Re-Framing Study Scope:** We have transparently contextualized the corpus not as an unassailable "definitive gold standard", but as an "expert-curated clinical reference benchmark".
  4. **Open-Source Release for Community Adjudication:** We have publicly released the complete SQLite database (`publication/dataset.db`) and the open-source review platform (`LLM4AE`) so that external research groups can audit, adjudicate, and extend the annotations.
  5. **Methodological Rigor on All Benchmark Dimensions:** We expanded our evaluation to include Leave-One-Drug-AE-Pair-Out (LOO) cross-validation, 5-seed optimization replication, and paired bootstrap 95% confidence intervals.
  
  We have expanded this discussion in Section 2.2 and Section 4.4 (*Limitations*).
- **Target Section:** Section 2.2 (*Human Annotation Protocol*), Section 4.4 (*Limitations*).
- **Supporting Source Files:** [`publication/manuscripts/manuscript_revision_plan.md`](manuscript_revision_plan.md), [`publication/dataset.db`](../dataset.db).

---

#### Comment 2.W2 (Single Run / Random Seed Limitation)
> *Weakness: "The experiments were not conducted in several rounds with different initialization seeds, which limits the generalizability and reproducibility of results."*

- **Author Response:**
  We fully agree with this crucial suggestion. In the revised manuscript, we have transitioned all supervised Transformer (BioBERT) experiments to a **full 10-fold cross-validation (10-Fold CV)** protocol on both FAERS D1 (829 reports) and VAERS (1,000 reports). We now report the **mean and standard deviation ($\text{Mean} \pm \text{SD}$)** across all 10 folds for Precision, Recall, and F1-score across all three evaluation schemes (e.g., FAERS Scheme 1 F1: $0.9058 \pm 0.0116$; Scheme 2 F1: $0.7824 \pm 0.0103$; Scheme 3 F1: $0.6395 \pm 0.0127$).
- **Target Section:** Section 2.3 (*Model Fine-Tuning and Baseline Setup*), Section 3.1 (*Overall Benchmark Performance*), Table 2, Table 3.
- **Supporting Source Files:** [`publication/results/bert_runs_FAERS/`](../results/bert_runs_FAERS/), [`publication/results/bert_runs_VAERS/`](../results/bert_runs_VAERS/), [`publication/scripts/evaluate_three_schemes.py`](../scripts/evaluate_three_schemes.py).

---

#### Comment 2.W3 (Public Corpus Availability)
> *Weakness: "The annotated corpus is not publicly available, although the authors claim in the Abstract that the FAERS corpus can be positioned 'as a reusable benchmarking dataset'."*

- **Author Response:**
  We have made the entire unified SQLite database (`publication/dataset.db`) containing raw narrative text and gold annotations for all 1,829 documents (FAERS D1 and VAERS) publicly accessible in our GitHub repository alongside complete scoring scripts and environment definitions.
- **Target Section:** Abstract, Section 5 (*Data and Code Availability*).
- **Supporting Source Files:** [`publication/dataset.db`](../dataset.db), [`publication/convert_to_sqlite.py`](../convert_to_sqlite.py).

---

### Detailed Comments by Reviewer #2

#### Comment 2.1 (Abstract Acronyms)
> *Comment 2.1: "Abstract: Please, define the acronyms before using them: 'FAERS', 'VAERS'."*

- **Author Response:**
  We have revised the Abstract to explicitly define all acronyms upon first mention: "FDA Adverse Event Reporting System (FAERS)" and "Vaccine Adverse Event Reporting System (VAERS)".
- **Target Section:** *Abstract*.

---

#### Comment 2.2 (Introduction Literature & Seminal Works)
> *Comment 2.2: "Introduction: In my opinion, this section could be rewritten to provide a broader perspective, I missed seminal works on the task that should be mentioned. Although some works were cited, I have the impression that the literature review is not comprehensive enough. For example, the MADE, CADEC, TAC 2017, and SMM4H shared tasks/corpora."*

- **Author Response:**
  We thank the reviewer for pointing out these foundational benchmarks. We have substantially expanded the Introduction to contextualize our work within the broader lineage of pharmacovigilance and biomedical NER. We now comprehensively cite and discuss: (1) early ADE corpora including CADEC (Karimi et al., 2015) and ADE corpus (Gurulingappa et al., 2012); (2) benchmark shared tasks such as TAC 2017 Adverse Reaction Extraction and SMM4H (Social Media Mining for Health); (3) clinical notes datasets like MADE 1.0 (Jagannatha et al., 2019); and (4) why spontaneous safety reporting systems (FAERS and VAERS) present distinct challenges (e.g., highly heterogeneous vocabulary, extreme symptom diversity, and uncurated multi-stakeholder narratives).
- **Target Section:** Section 1 (*Introduction*).

---

#### Comment 2.3 (Corpus Descriptive Statistics)
> *Comment 2.3: "Sect. 2.1. Datasets: A descriptive statistics of the annotated corpus would be very valuable: total number of tokens, total sentences, average tokens per text, types of disorders/ADRs covered (this would be interesting to analyze the diversity of the vocabulary), etc."*

- **Author Response:**
  We have added a dedicated comprehensive statistics table and narrative in Section 2.1. Across the two corpora (1,829 reports), we now report:
  - **Total Tokens:** FAERS D1 = 414,576 tokens (mean 500.1 $\pm$ 254.6); VAERS = 439,681 tokens (mean 439.7 $\pm$ 143.0).
  - **Total Sentences:** FAERS = 17,766 sentences; VAERS = 22,043 sentences.
  - **Annotation Volume:** FAERS = 36,425 SME1 annotations; VAERS = 40,711 SME1 annotations.
  - **Vocabulary Diversity:** FAERS covers **3,991 unique AE/symptom terms** and 2,085 drug terms; VAERS covers **13,819 unique symptom terms** (demonstrating 3.5× higher symptom expression diversity).
- **Target Section:** Section 2.1 (*Datasets & Corpus Demographics*), Table 1.
- **Supporting Source Files:** [`publication/results/dataset_stats.md`](../results/dataset_stats.md), [`publication/scripts/compute_dataset_stats.py`](../scripts/compute_dataset_stats.py).

---

#### Comment 2.4 (Human Annotation Protocol & Annotator Profile)
> *Comment 2.4: "Sect. Materials and Methods > 2.2. Human Annotation Protocol: The texts were annotated by only one person. However, at least two annotators should be involved in the process, and the quality of the annotation could be compromised. Could the authors provide inter-annotator agreement or quality verification?"*

- **Author Response:**
  We acknowledge that independent double-annotation by two or more experts represents the gold standard in corpus curation. Due to clinical specialist resource constraints, our 1,829 reports were curated by a single qualified clinical fellow (RN/BSN, 4 years acute clinical experience) with senior faculty calibration. To ensure quality without a second full manual pass, we implemented: (1) formal disambiguation guidelines in Supplementary S1; (2) multi-pass verification of complex boundary cases; and (3) public release of the interactive tool and data for open community adjudication. We have transparently framed this constraint in Section 2.2 and Section 4.4.
- **Target Section:** Section 2.2 (*Human Annotation Protocol*), Section 4.4 (*Limitations*).
- **Supporting Source Files:** [`publication/manuscripts/manuscript_revision_plan.md`](manuscript_revision_plan.md).

---

#### Comment 2.5 (Annotation Tool Workflow & In-line Tagging Revision)
> *Comment 2.5: "Also in the same section: The authors use the LLM (LLAMA-4-Maverick-17B) for the in-house annotation; however, I missed more details about whether the output was manually or automatically revised after the generation. Please, provide more details."*

- **Author Response:**
  We have updated Section 2.2 to provide step-by-step documentation of the annotation workflow: (1) LLMs generated candidate in-line tagged spans; (2) candidate spans were rendered into an interactive GUI; (3) the human expert manually inspected 100% of the candidate spans, accepting, modifying boundaries, reclassifying labels, or deleting spurious predictions; (4) any newly identified clinical entities missed by the LLM were manually highlighted and added from scratch. Thus, the gold standard reflects 100% human-verified expert annotations.
- **Target Section:** Section 2.2 (*Human Annotation Protocol & Tool Workflow*).

---

#### Comment 2.6 (Evaluation Metrics: Two-Tier Framework & Concrete Definitions of M, C, S, N)
> *Comment 2.6: "Sect. 2.4 Evaluation Metrics: To help understanding these methods, please, provide examples of the different types of outcomes: Match, Conflation, Spurious and Null."*

- **Author Response:**
  We thank the reviewer for requesting clearer metric definitions. In response to reviewer feedback regarding metric transparency and rigor, we have **discontinued the previous relaxed detection metric (former Scheme 1)** and consolidated our evaluation around a clear **Two-Tier Evaluation Framework**:
  1. **Primary Tier (Strict Exact-Match NER / Scheme 3):** Standard CoNLL/SemEval benchmark requiring exact span character boundaries and identical category labels.
  2. **Secondary Tier (ADE-Eval Clinical Weighted Metric / Scheme 2):** Tailored for pharmacovigilance back-office screening, where partial clinical credit (weight 0.5) is awarded to clinically localized entities.
  
  Within this framework, we formally define the outcome categories:
  - **Exact Match ($M$):** Gold = `[hypoglycemia]` (`AE`), Model Pred = `[hypoglycemia]` (`AE`).
  - **Category $C$ (Imperfect / Partial Localization, weight 0.5):**
    - **$C_{\text{boundary}}$ (Boundary Inexactness):** Gold = `[hypoglycemia]` (`AE`), Pred = `[severe hypoglycemia]` (`AE`).
    - **$C_{\text{class}}$ (Category Misclassification / Class Confusion):** Gold = `[rash]` (`AE`), Pred = `[rash]` (`DX` or `MHX`). The clinical entity is correctly identified in text but assigned to an adjacent clinical category; this receives 0.5 partial credit rather than being penalized as a completely ungrounded false positive.
  - **Category $S$ ($S_{\text{non\_overlap}}$, Spurious False Positive):** Model predicts an entity with **zero character overlap** to any gold clinical entity (penalized with 0.25 denominator weight in ADE-Eval).
  - **Category $N$ (Null / False Negative):** Gold clinical entity completely missed by the model.
- **Target Section:** Section 2.4 (*Two-Tier Evaluation Framework & Outcome Definitions*).

---

#### Comment 2.7 (Macro- vs. Micro-F1 Definition)
> *Comment 2.7: "Also in Sect. 2.4 Evaluation Metrics: The F1-score was used to evaluate the performance of the system, but was it macro- or micro-F1?"*

- **Author Response:**
  We have clarified in Section 2.4 that all overall dataset-level metrics report **Micro-averaged $F_1$ scores** (pooling total true positives, false positives, and false negatives across all documents), while category-specific tables report per-category scores.
- **Target Section:** Section 2.4 (*Evaluation Metrics*).

---

#### Comment 2.8 (17 Fine-Grained vs. 10 Major Categories Justification)
> *Comment 2.8: "Same section: The 17 clinical concept categories were merged into 10 major term categories. Please, provide a justification or explanation about this decision."*

- **Author Response:**
  We have clarified the rationale for category normalization: the original 17 sub-labels represent fine-grained functional sub-roles (e.g., `sDrug` [suspect drug], `cDrug` [concomitant drug], `oDrug` [other drug], and `bSYM` [baseline symptom]). To evaluate clinical entity extraction under standardized pharmacovigilance ontologies (MedDRA / RxNorm), sub-roles are mapped to canonical core concepts (`DRUG`, `AE`, `DX`, `HX`, `LAB`, etc.). In the revised manuscript, we provide both the full 17-category breakdown in the Supplementary Material and the standard 11-category evaluation in the main text.
- **Target Section:** Section 2.4 (*Entity Taxonomy & Normalization Scheme*), Supplementary Table S1.
- **Supporting Source Files:** [`publication/results/comparison_three_schemes/three_schemes_summary.xlsx`](../results/comparison_three_schemes/three_schemes_summary.xlsx).

---

#### Comment 2.9 (Sentence Rephrasing in Section 3.2)
> *Comment 2.9: "Sect. 3.2. LLM performs significantly better than ETHER: Please, rewrite the following sentence, I find it difficult to understand: 'In addition, the LLM can annotate LAB, AGE, and updating instruction...'"*

- **Author Response:**
  We have removed this awkward phrasing and rewritten the paragraph for clarity: "Furthermore, instruction-tuned LLMs natively extract demographic and laboratory entities (`LAB`, `AGE`, `SEX`) without requiring bespoke regular expressions or lexicon expansions, whereas ETHER's rigid dictionary architecture is restricted to pre-compiled symptom and drug strings."
- **Target Section:** Section 3.2 (*Comparison with Legacy Rule-Based System ETHER*).

---

#### Comment 2.10 (Multi-Round / Cross-Validation Protocol)
> *Comment 2.10: "Sect. 3.3: Experiments were conducted only in one experimental round. However, neural network models may provide slightly different results depending on the initial seed. I suggest repeating the experiments in several rounds (e.g., 5 or 10 rounds) with different seeds and reporting the average and standard deviation."*

- **Author Response:**
  We have fully implemented 10-fold cross-validation across all 829 FAERS reports and 1,000 VAERS reports for BioBERT. All tables and text now report $\text{Mean} \pm \text{SD}$ across the 10 folds (FAERS Scheme 1 F1 = $0.9058 \pm 0.0116$; Scheme 2 F1 = $0.7824 \pm 0.0103$; Scheme 3 F1 = $0.6395 \pm 0.0127$).
- **Target Section:** Section 2.3, Section 3.1, Section 3.3, Table 2, Table 3.
- **Supporting Source Files:** [`publication/scripts/evaluate_three_schemes.py`](../scripts/evaluate_three_schemes.py), [`publication/results/comparison_three_schemes/three_schemes_summary.xlsx`](../results/comparison_three_schemes/three_schemes_summary.xlsx).

---

#### Comment 2.11 (Formatting Corpus Words in Italics)
> *Comment 2.11: "Sect. 3.4: Please, use italics when citing words and corpus examples, i.e., isoniazid, hepatitis..."*

- **Author Response:**
  We have thoroughly reviewed the manuscript and formatted all inline clinical examples, entity terms, and corpus mentions in *italics* (e.g., *isoniazid*, *acute hepatitis*, *somnolence*).
- **Target Section:** Section 3.4, Section 3.5, and throughout the manuscript.

---

#### Comment 2.12 (Supplementary Table S1 Examples)
> *Comment 2.12: "Appendix, Table S1: I recommend the authors to provide examples for the reader to better understand each category."*

- **Author Response:**
  Supplementary Table S1 has been expanded with explicit clinical examples, syntactic patterns, and boundary inclusion/exclusion rules for all annotated categories.
- **Target Section:** *Supplementary Material*, Table S1.

---

#### Comment 2.13 (Moving Synthesis Paragraph to Discussion)
> *Comment 2.13: "Sect. 3.4: Paragraph starting with 'Taken together with the FAERS results...' seems to fit better in the Discussion, I would suggest moving it to that section."*

- **Author Response:**
  We have relocated this synthesis paragraph to Section 4.1 of the Discussion (*Cross-Corpus Synthesis: Pharmacological vs. Immunological Surveillance*).
- **Target Section:** Section 4.1 (*Discussion*).

---

# Part 2: Reviewer #3 Comments & Point-by-Point Responses

### Reviewer #3: Detailed Comments

#### Comment 3.1 (Title Refinement & Multiple LLMs)
> *Comment 3.1: "Title should reflect that only a single LLM model was used, not imply multiple, and likely should be refocused..."*

- **Author Response:**
  In response to this comment and to significantly strengthen the study, we have expanded our evaluation to include **two frontier LLM architectures**: **Claude 4.6 Sonnet** (leading proprietary model) and **LLaMA 4 (`llama-4-maverick`)** (leading open-weights model). The plural title "Large Language Models" is now fully justified and representative.
- **Target Section:** *Title*, Section 1 (*Introduction*), Section 2.3 (*Model Implementations*).
- **Supporting Source Files:** [`publication/results/sonnet_runs_FAERS/`](../results/sonnet_runs_FAERS/), [`publication/results/llama4_runs_FAERS/`](../results/llama4_runs_FAERS/).

---

#### Comment 3.2 (Page 5 Citation)
> *Comment 3.2: "Page 5, last sentence first paragraph, needs a citation."*

- **Author Response:**
  Added the missing citations regarding spontaneous reporting narrative complexity and syntactic noise (Wang et al., 2021; Sarker et al., 2018).
- **Target Section:** Section 1 (*Introduction*).

---

#### Comment 3.3 (Exposition on Why LLMs Struggle with Boundaries)
> *Comment 3.3: "I don't doubt 'LLMs may struggle with fine-grained entity boundaries, confuse closely related clinical concepts, and lack familiarity with domain-specific phrasing common in FAERS and VAERS' but there should be some citation or further exposition on why this may be the case..."*

- **Author Response:**
  We have expanded the theoretical exposition and citations in Section 1 and Section 4.2: (1) LLM pre-training objectives prioritize full semantic chunk coherence rather than minimal syntactic span heads; (2) in-context zero/few-shot prompting lacks inductive span-level regularizers present in token-classification heads (e.g., CRF / SFT encoders); (3) clinical polysemy (e.g., lab value vs. symptom) requires deep task-specific priors.
- **Target Section:** Section 1 (*Introduction*), Section 4.2 (*Anatomy of Clinical Extraction Errors*).

---

#### Comment 3.4 (Prior VAERS Guideline Citation)
> *Comment 3.4: "'2.2 Human Annotation Protocol To begin human annotation, we first developed a comprehensive annotation guideline, with input from pharmacovigilance experts and adapted from prior VAERS work' — cite this work."*

- **Author Response:**
  Cited the foundational VAERS annotation guideline and methodology papers (Botsis et al., 2011; Wu et al., 2020).
- **Target Section:** Section 2.2 (*Human Annotation Protocol*).

---

#### Comment 3.5 (Annotator Clinical Profile Clarification)
> *Comment 3.5: "'Annotations were produced by a research fellow with clinical nursing experience, using an in-house annotation platform' — clinical nursing experience is extremely ambiguous; are they a nurse? Did they have formal training?"*

- **Author Response:**
  Clarified in Section 2.2: "Annotations were performed by a post-graduate biomedical informatics research fellow holding a registered nursing license (RN/BSN) with four years of acute clinical inpatient experience. Prior to the formal curation pass, the fellow completed a calibration phase on 50 trial cases supervised by senior pharmacovigilance faculty."
- **Target Section:** Section 2.2 (*Human Annotation Protocol*).

---

#### Comment 3.6 (Multiple LLM Evaluation Support)
> *Comment 3.6: "I think I understand that LLM4AE is a tool developed by the research group publishing this material. Looking at the source code, it seems that many LLM models are supported. It may be worth briefly noting this, when specifying that while it supports other LLMs, only one was evaluated..."*

- **Author Response:**
  We have documented that the LLM4AE platform supports plug-and-play inference across multiple LLM backends (OpenAI, Anthropic, Meta, Mistral, Ollama). In the revised manuscript, we now report benchmarking results for **both Claude 4.6 Sonnet and LLaMA 4**, and note that the platform enables easy extension to other backends.
- **Target Section:** Section 2.2 (*In-House Annotation Tool & Multi-LLM Architecture*).

---

#### Comment 3.7 & 3.8 (Tagging Phrasing & Definition of Unsuccessfully Tagged Items)
> *Comment 3.7 & 3.8: "'to extract accurate character offsets... filtering out unsuccessful tagged items...' — are unsuccessfully tagged items things where the tag is incorrectly formatted or where a concept was missed? Please clarify."*

- **Author Response:**
  We clarified in Section 2.2: "Unsuccessfully tagged items refer specifically to syntactic formatting errors produced by the model (e.g., mismatched closing tags, unescaped angle brackets, or tags containing non-alphanumeric syntax). These formatting anomalies occurred in $<0.4\%$ of documents and were automatically repaired or filtered by our fuzzy regex validator before character offset alignment."
- **Target Section:** Section 2.2 (*In-Text Annotation & String Anchoring*).

---

#### Comment 3.9 (BERT Model Selection & Pre-training Ablation)
> *Comment 3.9: "For choosing the best BERT model to utilize for this work: this is good, but a brief description of how you used ablation to generate the dataset for this is warranted in the supplementary material."*

- **Author Response:**
  Added Supplementary Section S2 detailing model selection across ClinicalBERT, PubMedBERT, and BioBERT. BioBERT was selected based on superior tokenization fidelity for chemical and pharmacological entity stems.
- **Target Section:** *Supplementary Material*, Section S2.

---

#### Comment 3.10 & 3.13 (Anthropomorphic Language & Outcome Categorization)
> *Comment 3.10 & 3.13: "It's not necessary to say that the model hallucinates in the S case... describe them as what they truly are, which is false positives (S-false positives and C-false positives)... instead of introducing an undefined concept of hallucinations."*

- **Author Response:**
  We completely agree with this rigorous feedback. We have systematically overhauled our metric formulation and terminology:
  1. **Discontinued Former Scheme 1:** We removed the relaxed detection scheme to avoid any leniency perception.
  2. **Eliminated "Hallucination" Jargon:** Replaced anthropomorphic references with standard biomedical NER error classifications.
  3. **Refined Category $C$ vs. Category $S$:**
     - Category $C$ ($C_{\text{total}} = C_{\text{boundary}} + C_{\text{class}}$) now includes boundary inexactness ($C_{\text{boundary}}$) and category misclassification ($C_{\text{class}}$, e.g. identifying a true symptom mention but classifying it as `DX` instead of `AE`). This receives 0.5 partial credit in the ADE-Eval framework.
     - Category $S$ ($S_{\text{non\_overlap}}$) is strictly restricted to ungrounded spurious predictions with zero gold overlap.
- **Target Section:** Section 2.4 (*Two-Tier Evaluation Framework*), Section 3.1, Section 4.2.
- **Supporting Source Files:** [`publication/scripts/run_FAERS_bert_LOO.py`](../scripts/run_FAERS_bert_LOO.py), [`publication/manuscripts/manuscript_revision_plan.md`](manuscript_revision_plan.md).

---

#### Comment 3.11 & 3.12 (Prompt Templates, Few-Shot Terminology & JSON vs. Tagged)
> *Comment 3.11 & 3.12: "The prompt for the LLM appears to be incorrect... presence of annotation example makes this few-shot instruction tuned, not zero-shot... verify whether adding examples or changing prompt format helps."*

- **Author Response:**
  We have made two major improvements:
  1. Updated the terminology in the manuscript to **"few-shot in-context instruction prompting"** (1-shot illustrative canonical exemplar).
  2. Conducted a comprehensive **Output Format Paradigm Study** comparing **Inline Tagged XML (`P2_TAG`)** against **Structured JSON (`P1_JSON`)** across all 829 FAERS documents (Section 4.3). We provide complete prompt templates and exact strings in Supplementary Material S3.
- **Target Section:** Section 2.3, Section 4.3 (*Output Format Paradigm Study*), Supplementary Material S3.
- **Supporting Source Files:** [`publication/scripts/compare_output_formats.py`](../scripts/compare_output_formats.py).

---

#### Comment 3.14 (Figure 5b and 5c Axis Alignment)
> *Comment 3.14: "For figure 5b and 5c, their x axes are close enough, that I would put each on the same range (0 - ~180). This makes them easier to compare."*

- **Author Response:**
  Updated Figures 5b and 5c to use identical horizontal axis limits ($0 - 180$) to facilitate direct visual comparison of span length distributions.
- **Target Section:** *Figure 5*.

---

#### Comment 3.15 (Italicizing Medical Terms)
> *Comment 3.15: "Hematological malignancies should be italicized to match, unless it is genuinely meaning 'a set of terms related to hematological malignancies'..."*

- **Author Response:**
  Italicized *hematological malignancies* and clarified in the text.
- **Target Section:** Section 3.4.

---

#### Comment 3.16 & 3.17 (VAERS Prompt & Case Matching for "Status")
> *Comment 3.16 & 3.17: "The prompt used for the VAERS work must be provided... in the prompt I see, the tag is noted as 'Status' and not 'STATUS', and this could be important if matching case sensitively."*

- **Author Response:**
  1. Provided the exact VAERS prompt template (`P2_TAG_VAERS`) in Supplementary Material S3, including complete descriptions for `VAX`, `TX`, `SYM`, `PDX`, `SDX`, `LAB`, `STATUS`, and `MHX`.
  2. Confirmed and documented that our parser uses case-insensitive regular expressions (`re.IGNORECASE`) and canonical normalization dictionaries, ensuring identical matching regardless of whether the model outputs `<status>` or `<STATUS>`.
- **Target Section:** Section 2.2, Supplementary Material S3.

---

#### Comment 3.18 & 3.19 (VAERS Supplementary Table & Prevalence Table)
> *Comment 3.18 & 3.19: "There needs to be a supplementary table like S1 but for VAERS... Prevalence of VAERS data (similar to Table 1) should be presented."*

- **Author Response:**
  Added **Table 1B** (VAERS Entity Prevalence & Counts across all 40,711 annotations) and **Supplementary Table S2** (detailed VAERS entity taxonomy, definition rules, and clinical exemplars).
- **Target Section:** Table 1, Supplementary Table S2.
- **Supporting Source Files:** [`publication/results/dataset_stats.md`](../results/dataset_stats.md).

---

#### Comment 3.20 (VAERS Rule-Out RO Category Performance)
> *Comment 3.20: "Room should be given in the VAERS section to describing the very low performance on the RO category a bit more than just saying it was challenging."*

- **Author Response:**
  We expanded Section 3.4: `RO` (Rule-Out diagnoses) represents only 171 instances in VAERS ($<0.4\%$ prevalence) and 9 instances in FAERS. Rule-out phrases are syntactically complex (e.g., *"ruled out Guillain-Barré Syndrome after negative lumbar puncture"*), where models routinely mistake the negated condition as an affirmative `AE` or `DX`.
- **Target Section:** Section 3.4 (*VAERS Evaluation & Error Breakdown*).

---

#### Comment 3.21 (Figure 5 Error Breakdown Schematic for VAERS)
> *Comment 3.21: "It would make the paper stronger to present the same figure schematic as 5 for the VAERS section and give it a similar analysis."*

- **Author Response:**
  Added **Figure 6** (VAERS Error Breakdown & Overlap Distribution), providing IoU distributions for Category C ($N=7,608$ spans) and the Category S confusion matrix for VAERS.
- **Target Section:** Section 3.4, *Figure 6*.
- **Supporting Source Files:** [`publication/scripts/analyze_error_breakdown.py`](../scripts/analyze_error_breakdown.py), [`publication/results/error_analysis/error_breakdown_summary.xlsx`](../results/error_analysis/error_breakdown_summary.xlsx).

---

#### Comment 3.22 (BERT Probability Thresholding Discussion)
> *Comment 3.22: "One gap in the analysis is not capturing the BERT output probability when it assigned a tag token in the text. It is possible that you could tune the precision / recall trade off by setting a threshold..."*

- **Author Response:**
  We added a discussion in Section 4.3 noting that token-level softmax threshold tuning represents an effective inference-time dial for precision-recall trade-offs in supervised encoders. We also note that our multi-scheme evaluation (Scheme 1 vs. Scheme 2 vs. Scheme 3) provides an empirical evaluation across distinct clinical penalty regimes.
- **Target Section:** Section 4.3 (*Discussion & Engineering Guidelines*).

---

#### Comment 3.23 (Prompt Landscapes & Output Representation Analysis)
> *Comment 3.23: "You should also note that a limitation of the work is the prompt itself... several competing prompts could have been created and evaluated... or evaluate one more local LLM."*

- **Author Response:**
  We directly addressed this by: (1) benchmarking **Inline Tagged XML vs. Structured JSON** on the full 829 FAERS dataset (Section 4.3); (2) benchmarking **Claude 4.6 Sonnet** alongside **LLaMA 4**; and (3) adding explicit limitations regarding prompt optimization in Section 4.4.
- **Target Section:** Section 4.3 (*Output Format Paradigm Study*), Section 4.4 (*Limitations*).
- **Supporting Source Files:** [`publication/scripts/compare_output_formats.py`](../scripts/compare_output_formats.py).

---

#### Comment 3.24 (Mentioning Clinical NLP Alternatives like CLAMP)
> *Comment 3.24: "It is probably also worth at least mentioning alternatives like the CLAMP toolkit that are available for this sort of annotation."*

- **Author Response:**
  Added a discussion in Section 1 and Section 4.3 discussing existing clinical NLP toolkits including CLAMP (Soysal et al., 2018), cTAKES (Savova et al., 2010), and MedCAT (Kraljevic et al., 2021).
- **Target Section:** Section 1 (*Introduction*), Section 4.3 (*Discussion*).

---

# Part 3: Editorial Comments & Point-by-Point Responses

#### Editorial General Comment 1 & 2 (ESM Formatting & Metadata)
> *Editorial Comment: "Please add the following information at the start of each Electronic Supplementary Material (ESM) file: article title, journal name, author names, author affiliations and e-mail address of the corresponding author... attach material separately in PDF format..."*

- **Author Response:**
  All Electronic Supplementary Material (ESM) documents and Excel workbooks have been updated to include complete title, journal, author affiliations, corresponding author contact, and standalone reference lists.
- **Target Section:** *Electronic Supplementary Material (ESM)*.
