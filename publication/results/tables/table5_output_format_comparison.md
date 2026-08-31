# Table 5: Impact of Output Format Paradigm on LLaMA 4 Concept Extraction (FAERS D1, N = 829 Reports)

Empirical comparison between **Inline Tagged XML (`P2_TAG`)** and **Structured JSON (`P1_JSON`)** representations evaluated on the full FAERS corpus across overall metrics, error distributions, and per-category performance.

### Panel A: Overall Performance and Error Count Distribution

| Output Format Paradigm | Primary Tier: Strict Exact-Match NER ||| Secondary Tier: Adapted ADE-Eval Weighted Metric ||| Outcome Category Counts |||||
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| | **P** | **R** | **F1** | **P** | **R** | **F1** | **M** | **C_bound** | **C_class** | **S_non_overlap** | **N** |
| **Inline Tagged XML (`P2_TAG`)** | 0.3470 | 0.4091 | **0.3755** | 0.6763 | 0.5673 | **0.6170** | 13,768 | 5,420 | 5,222 | 15,269 | 9,241 |
| **Structured JSON (`P1_JSON`)** | 0.3785 | 0.3502 | **0.3638** | 0.6947 | 0.5184 | **0.5938** | 11,991 | 4,511 | 7,012 | 8,166 | 10,728 |
| *Format Delta (JSON - Tagged)* | +0.0315 | -0.0590 | -0.0117 | +0.0184 | -0.0488 | -0.0232 | -1,777 | -909 | +1,790 | -7,103 (-46.52%) | +1,487 |

---

### Panel B: Per-Category Performance Comparison

| Clinical Category | Gold Support (N) | Strict Exact-Match F1 ||| Adapted ADE-Eval Weighted F1 |||
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| | | **Tagged XML** | **Structured JSON** | **$\Delta$ (JSON - Tagged)** | **Tagged XML** | **Structured JSON** | **$\Delta$ (JSON - Tagged)** |
| **AE** | 9,186 | 0.4320 | 0.4306 | -0.0014 | 0.6508 | 0.6048 | -0.0460 |
| **AGE** | 787 | 0.8303 | 0.8281 | -0.0022 | 0.9203 | 0.9165 | -0.0038 |
| **COD** | 3 | 0.0106 | 0.0000 | -0.0106 | 0.4687 | 0.4370 | -0.0317 |
| **DOSE** | 1,619 | 0.3776 | 0.2126 | -0.1650 | 0.6492 | 0.5836 | -0.0656 |
| **DRUG** | 6,673 | 0.3816 | 0.4163 | +0.0347 | 0.6222 | 0.6141 | -0.0081 |
| **DX** | 1,543 | 0.2170 | 0.1910 | -0.0260 | 0.5073 | 0.4964 | -0.0109 |
| **HX** | 2,408 | 0.4568 | 0.4664 | +0.0096 | 0.6672 | 0.6481 | -0.0191 |
| **INDICATION** | 162 | 0.1074 | 0.0866 | -0.0208 | 0.4493 | 0.4355 | -0.0138 |
| **LAB** | 3,476 | 0.2225 | 0.2006 | -0.0219 | 0.5549 | 0.5134 | -0.0415 |
| **RO** | 9 | 0.0074 | 0.0370 | +0.0296 | 0.4466 | 0.4731 | +0.0265 |
| **SEX** | 767 | 0.8269 | 0.7928 | -0.0341 | 0.9078 | 0.8957 | -0.0121 |
| **STATUS** | 1,796 | 0.1908 | 0.2636 | +0.0728 | 0.3072 | 0.4753 | +0.1681 |

---

### Footnotes & Methodological Takeaways:
1. **Spurious False Positive Suppression:** Formatting outputs as **Structured JSON suppresses non-overlapping spurious hallucinations ($S_{\text{non\_overlap}}$) by 46.52%** (from 15,269 spans in Tagged XML down to 8,166 in JSON), resulting in higher Strict Precision (0.3785 vs. 0.3470) and higher ADE-Eval Precision (0.7019 vs. 0.6763).
2. **Narrative Token Grounding & Recall:** **Inline Tagged XML preserves narrative context alignment**, yielding fewer missed clinical entities ($N = 9,241$ in Tagged vs. $10,728$ in JSON) and higher ADE-Eval Recall (0.5673 vs. 0.5232). JSON generation occasionally experiences list truncation on long complex narratives.
3. **Category Shifts:** Structured JSON substantially improves extraction of outcome disposition phrases (`STATUS`, $+0.1681$ ADE F1), but exhibits slight sensitivity to multi-token clinical modifier phrases (`DOSE`, $-0.0656$ ADE F1; `LAB`, $-0.0415$ ADE F1) where offset boundaries are harder for the autoregressive decoder to align exactly.
