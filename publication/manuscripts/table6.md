# Table 6: BioBERT Optimization Stability and Performance Invariance Across Five Independent Random Initialization Seeds

Evaluation of neural network optimization stability across 5 independent training runs (seeds 42, 123, 456, 789, 1011) for supervised BioBERT on the FAERS 4-fold LOO benchmark (20 total model runs, 17 categories) and VAERS 10-fold CV benchmark (50 total model runs).

| Dataset & Evaluation Protocol | Random Seed | Primary Tier: Strict Exact F1 | Secondary Tier: Adapted ADE F1 |
| :--- | :--- | :---: | :---: |
| FAERS (4-Fold LOO, N = 829) | Seed 42 | 0.5582 ± 0.0649 | 0.7431 ± 0.0295 |
| FAERS (4-Fold LOO, N = 829) | Seed 123 | 0.5652 ± 0.0509 | 0.7402 ± 0.0293 |
| FAERS (4-Fold LOO, N = 829) | Seed 456 | 0.5783 ± 0.0697 | 0.7586 ± 0.0355 |
| FAERS (4-Fold LOO, N = 829) | Seed 789 | 0.5663 ± 0.0476 | 0.7413 ± 0.0324 |
| FAERS (4-Fold LOO, N = 829) | Seed 1011 | 0.5748 ± 0.0694 | 0.7484 ± 0.0371 |
| **FAERS (4-Fold LOO, Pooled)** | **Mean ± SD (5 Seeds)** | **0.5685 ± 0.0080** | **0.7463 ± 0.0075** |
| VAERS (10-Fold CV, N = 1,000) | Seed 42 | 0.7015 ± 0.0174 | 0.8370 ± 0.0095 |
| VAERS (10-Fold CV, N = 1,000) | Seed 123 | 0.7013 ± 0.0156 | 0.8405 ± 0.0070 |
| VAERS (10-Fold CV, N = 1,000) | Seed 456 | 0.7008 ± 0.0202 | 0.8400 ± 0.0113 |
| VAERS (10-Fold CV, N = 1,000) | Seed 789 | 0.7026 ± 0.0152 | 0.8419 ± 0.0082 |
| VAERS (10-Fold CV, N = 1,000) | Seed 1011 | 0.6983 ± 0.0159 | 0.8389 ± 0.0091 |
| **VAERS (10-Fold CV, Pooled)** | **Mean ± SD (5 Seeds)** | **0.7009 ± 0.0016** | **0.8397 ± 0.0018** |

---

### Footnotes & Methodological Notes:
1. **FAERS Protocol:** 4-fold Leave-One-Drug-Event-Pair-Out cross-validation evaluated across all 17 clinical concept categories. For each seed, Mean $\pm$ SD represents out-of-fold cross-series variation.
2. **VAERS Protocol:** 10-fold cross-validation on the 1,000 VAERS reports. For each seed, Mean $\pm$ SD represents cross-fold variation across the 10 test partitions.
3. **Pooled Invariance:** The pooled summary represents the Mean $\pm$ SD across the 5 independent random initialization seeds, demonstrating minimal stochastic variation ($SD = 0.0080$ on FAERS, $SD = 0.0015$ on VAERS).
