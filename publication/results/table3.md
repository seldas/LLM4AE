# Table 3: Master Performance Benchmark on the VAERS Dataset (N = 1,000 Reports)

Overall performance of evaluated model families across the Two-Tier Evaluation Framework on the Vaccine Adverse Event Reporting System (VAERS) benchmark corpus. Micro-averaged precision (P), recall (R), and F1 scores are reported.

| Model Family | Model & Configuration | Input Paradigm | Primary Tier: Strict Exact-Match NER ||| Secondary Tier: Adapted ADE-Eval Weighted Metric |||
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| | | | **P** | **R** | **F1** | **P** | **R** | **F1** |
| **Fine-Tuned Encoder** | BioBERT (10-Fold CV, Seed 42 Default)$^\dagger$ | Sentence Token Classification | $0.6956 \pm 0.0199$ | $0.6268 \pm 0.0203$ | **$0.6594 \pm 0.0196$** | $0.8619 \pm 0.0095$ | $0.7205 \pm 0.0153$ | **$0.7848 \pm 0.0127$** |
|  | BioBERT (10-Fold CV, 5-Seed Pooled)$^\ddagger$ | Sentence Token Classification | $0.6892 \pm 0.0195$ | $0.6324 \pm 0.0183$ | **$0.6595 \pm 0.0177$** | $0.8594 \pm 0.0092$ | $0.7279 \pm 0.0139$ | **$0.7882 \pm 0.0112$** |
| **Open-Weight LLM** | LLaMA 4 (1-shot, Target Filtered) | Inline Tagged XML (`P2_TAG_VAERS`) | 0.3418 | 0.2368 | **0.2797** | 0.6714 | 0.4129 | **0.5113** |

---

### Footnotes & Methodological Notes:
- **Primary Tier (Strict Exact-Match NER / Scheme 3):** Standard exact character-boundary and exact-category match. $\text{Precision} = M / (M + C_{\text{total}} + S_{\text{non\_overlap}})$, $\text{Recall} = M / (M + C_{\text{total}} + N)$, $\text{F1} = 2PR / (P+R)$, where $M$ is exact match, $C_{\text{total}} = C_{\text{boundary}} + C_{\text{class}}$ represents boundary inexactness and category misclassification, $S_{\text{non\_overlap}}$ represents ungrounded false positives with zero gold overlap, and $N$ represents false negatives.
- **Secondary Tier (Adapted ADE-Eval Clinical Weighted Metric / Scheme 2):** Grants partial credit (0.5 weight) to partially localized/misclassified clinical mentions ($C_{\text{total}}$) and applies a 0.25 denominator weight to non-overlapping false positives ($S_{\text{non\_overlap}}$). $\text{Precision} = (M + 0.5 C_{\text{total}}) / (M + C_{\text{total}} + 0.25 S_{\text{non\_overlap}})$, $\text{Recall} = (M + 0.5 C_{\text{total}}) / (M + C_{\text{total}} + N)$.
- $^\dagger$ **BioBERT (Seed 42 Default):** Primary in-distribution 10-fold cross-validation on the 1,000 VAERS reports using random initialization seed 42. Mean $\pm$ SD reflects variance across the 10 test folds.
- $^\ddagger$ **BioBERT (5-Seed Pooled):** 10-fold cross-validation repeated across 5 independent random initialization seeds (`42, 123, 456, 789, 1011`), summarizing cross-fold variance and optimization stability ($N = 50$ total training runs).
- **Target Schema Filtering:** Performance is evaluated against the 6 core VAERS gold target categories (`AE`, `HX`, `LAB`, `STATUS`, `TX`, `VAX`). Non-gold categories extracted by the LLM (e.g., `DOSE`, `AGE`, `SEX`) are filtered prior to scoring to prevent artificial false positive penalties.
