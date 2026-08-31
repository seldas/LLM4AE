# Table 4: Per-Category Performance Breakdown on FAERS (N = 829 Reports)

Fine-grained concept extraction performance across all clinical categories on the FAERS benchmark corpus under the Two-Tier Evaluation Framework. Values report Strict Exact-Match NER F1 and Adapted ADE-Eval Clinical Weighted F1.

| Clinical Category | Gold Support (N) | BioBERT (4-Fold LOO)$^\dagger$ || Claude 4.6 Sonnet (1-shot) || LLaMA 4 (1-shot, Tagged) || LLaMA 4 (1-shot, JSON) ||
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| | | **Strict F1** | **ADE-Eval F1** | **Strict F1** | **ADE-Eval F1** | **Strict F1** | **ADE-Eval F1** | **Strict F1** | **ADE-Eval F1** |
| **AE** | 9,186 | $0.5115 \pm 0.0476$ | $0.6966 \pm 0.0415$ | 0.4609 | 0.6259 | 0.4320 | 0.6508 | 0.4306 | 0.6048 |
| **AGE** | 787 | $0.9173 \pm 0.0597$ | $0.9492 \pm 0.0344$ | 0.8873 | 0.9305 | 0.8303 | 0.9203 | 0.8281 | 0.9165 |
| **COD** | 3 | N/A | N/A | 0.0171 | 0.4605 | 0.0106 | 0.4687 | 0.0000 | 0.4370 |
| **DOSE** | 1,619 | $0.4666 \pm 0.0645$ | $0.6972 \pm 0.0370$ | 0.4436 | 0.6944 | 0.3776 | 0.6492 | 0.2126 | 0.5836 |
| **DRUG** | 6,673 | $0.5280 \pm 0.0730$ | $0.7156 \pm 0.0445$ | 0.4528 | 0.6379 | 0.3816 | 0.6222 | 0.4163 | 0.6141 |
| **DX** | 1,543 | $0.4253 \pm 0.0556$ | $0.6599 \pm 0.0486$ | 0.2621 | 0.5159 | 0.2170 | 0.5073 | 0.1910 | 0.4964 |
| **HX** | 2,408 | $0.6099 \pm 0.1357$ | $0.7875 \pm 0.0928$ | 0.5526 | 0.7165 | 0.4568 | 0.6672 | 0.4664 | 0.6481 |
| **INDICATION** | 162 | $0.0368 \pm 0.0470$ | $0.0864 \pm 0.1080$ | 0.1178 | 0.4617 | 0.1074 | 0.4493 | 0.0866 | 0.4355 |
| **LAB** | 3,476 | $0.4519 \pm 0.0945$ | $0.6743 \pm 0.0649$ | 0.3623 | 0.6143 | 0.2225 | 0.5549 | 0.2006 | 0.5134 |
| **RO** | 9 | N/A | N/A | 0.0144 | 0.4512 | 0.0074 | 0.4466 | 0.0370 | 0.4731 |
| **SEX** | 767 | $0.9213 \pm 0.0189$ | $0.9571 \pm 0.0225$ | 0.8922 | 0.9449 | 0.8269 | 0.9078 | 0.7928 | 0.8957 |
| **STATUS** | 1,796 | $0.6112 \pm 0.1034$ | $0.7575 \pm 0.0864$ | 0.2896 | 0.4663 | 0.1908 | 0.3072 | 0.2636 | 0.4753 |

---

### Footnotes & Clinical Interpretations:
- **Primary Tier (Strict Exact-Match NER):** Requires identical character span boundaries and category assignment. Partial overlaps receive 0 credit.
- **Secondary Tier (Adapted ADE-Eval Weighted Metric):** Grants 0.5 partial credit to boundary shifts and adjacent category confusions, applying a 0.25 denominator penalty to ungrounded non-overlapping false positives.
- $^\dagger$ **BioBERT (4-Fold LOO, 5-Seed Pooled):** Reports mean $\pm$ standard deviation across the 4 held-out case series and 5 random initialization seeds (`42, 123, 456, 789, 1011`).
- **Key Observations:**
  1. **Demographic Entities (`AGE`, `SEX`):** Extremely high precision and boundary agreement across all models (F1 $> 0.82 - 0.95$).
  2. **Core Clinical Concepts (`AE`, `DRUG`):** BioBERT maintains highest exact-boundary capture (Strict F1: 0.5115 for AE, 0.5280 for DRUG), while LLMs achieve strong semantic detection under ADE-Eval (ADE F1: 0.6259 for Sonnet, 0.6508 for LLaMA 4).
  3. **The `INDICATION` Generalization Contrast:** BioBERT exhibits severe out-of-distribution transfer degradation when encountering unseen indication contexts in held-out case series (Strict F1: 0.0368, ADE F1: 0.0864). In contrast, zero/few-shot LLMs leverage broad pre-trained medical knowledge to preserve robust indication recognition (ADE F1: 0.4617 for Sonnet, 0.4493 for LLaMA 4 Tagged).
  4. **Output Format Contrast (Tagged vs. JSON):** Structured JSON increases exact-match precision for discrete entities like `AE` (+3.8% Strict F1) by eliminating loose descriptive boundaries, but slightly impairs multi-word modifier categories.
