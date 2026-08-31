# Table 2: Master Performance Benchmark on the FAERS Dataset (N = 829 Reports)

Overall performance of evaluated model families across the Two-Tier Evaluation Framework on the FDA Adverse Event Reporting System (FAERS) benchmark corpus. Micro-averaged precision (P), recall (R), and F1 scores are reported.

| Model Family | Model & Configuration | Input Paradigm | Primary Tier: Strict Exact-Match NER ||| Secondary Tier: Adapted ADE-Eval Weighted Metric |||
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| | | | **P** | **R** | **F1** | **P** | **R** | **F1** |
| **Fine-Tuned Encoder** | BioBERT (4-Fold LOO, Seed 42 Default)$^\dagger$ | Sentence Token Classification | $0.5280 \pm 0.0883$ | $0.5958 \pm 0.0410$ | **$0.5582 \pm 0.0649$** | $0.7877 \pm 0.0484$ | $0.7038 \pm 0.0189$ | **$0.7431 \pm 0.0295$** |
| **Fine-Tuned Encoder** | BioBERT (4-Fold LOO, 5-Seed Pooled)$^\ddagger$ | Sentence Token Classification | $0.5442 \pm 0.0695$ | $0.5976 \pm 0.0450$ | **$0.5685 \pm 0.0549$** | $0.7967 \pm 0.0373$ | $0.7025 \pm 0.0316$ | **$0.7463 \pm 0.0301$** |
| **Proprietary Frontier LLM** | Claude 4.6 Sonnet (1-shot) | Inline Tagged XML (`P2_TAG`) | 0.4497 | 0.4291 | **0.4392** | 0.7405 | 0.5572 | **0.6359** |
| **Open-Weight LLM** | LLaMA 4 (1-shot, Tagged) | Inline Tagged XML (`P2_TAG`) | 0.3470 | 0.4091 | **0.3755** | 0.6763 | 0.5673 | **0.6170** |
|  | LLaMA 4 (1-shot, Structured JSON) | Structured JSON (`P1_JSON`) | 0.3785 | 0.3502 | **0.3638** | 0.6947 | 0.5184 | **0.5938** |
| **Rule-Based Baseline** | ETHER (Dictionary / Regex Baseline) | Dictionary String Match | 0.1089 | 0.1212 | **0.1147** | 0.4106 | 0.2003 | **0.2693** |

---

### Footnotes & Methodological Notes:
- **Primary Tier (Strict Exact-Match NER / Scheme 3):** Standard exact character-boundary and exact-category match. $\text{Precision} = M / (M + C_{\text{total}} + S_{\text{non\_overlap}})$, $\text{Recall} = M / (M + C_{\text{total}} + N)$, $\text{F1} = 2PR / (P+R)$, where $M$ is exact match, $C_{\text{total}} = C_{\text{boundary}} + C_{\text{class}}$ represents boundary inexactness and category misclassification, $S_{\text{non\_overlap}}$ represents ungrounded false positives with zero gold overlap, and $N$ represents false negatives.
- **Secondary Tier (Adapted ADE-Eval Clinical Weighted Metric / Scheme 2):** Grants partial credit (0.5 weight) to partially localized/misclassified clinical mentions ($C_{\text{total}}$) and applies a 0.25 denominator weight to non-overlapping false positives ($S_{\text{non\_overlap}}$). $\text{Precision} = (M + 0.5 C_{\text{total}}) / (M + C_{\text{total}} + 0.25 S_{\text{non\_overlap}})$, $\text{Recall} = (M + 0.5 C_{\text{total}}) / (M + C_{\text{total}} + N)$.
- $^\dagger$ **BioBERT (Seed 42 Default):** Evaluates cross-case-series generalization using Leave-One-Drug-AE-Pair-Out (4-Fold LOO) cross-validation with initialization random seed 42. Mean $\pm$ SD reflects variation across the 4 held-out case series.
- $^\ddagger$ **BioBERT (5-Seed Pooled):** Evaluates Leave-One-Drug-AE-Pair-Out (4-Fold LOO) cross-validation across 5 independent random initialization seeds (`42, 123, 456, 789, 1011`), summarizing cross-case-series and optimization stability.
- **Target Schema:** Standard 11 core clinical categories (`AE`, `DRUG`, `DX`, `HX`, `LAB`, `DOSE`, `AGE`, `SEX`, `STATUS`, `INDICATION`, `RO`).
