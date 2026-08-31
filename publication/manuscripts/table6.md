# Table 6: BioBERT Optimization Stability and Performance Invariance Across Five Independent Random Initialization Seeds

Evaluation of neural network optimization stability across 5 independent training runs (seeds 42, 123, 456, 789, 1011) for supervised BioBERT on the FAERS 4-fold LOO benchmark (20 total model runs, 17 categories) and VAERS 10-fold CV benchmark (50 total model runs, 14 categories).

| Dataset & Evaluation Protocol | Random Seed | Primary Tier: Strict Exact F1 | Secondary Tier: Adapted ADE F1 |
| :--- | :--- | :---: | :---: |
| FAERS (4-Fold LOO, N = 829) | Seed 42 | 0.5582 ± 0.0649 | 0.7431 ± 0.0295 |
| FAERS (4-Fold LOO, N = 829) | Seed 123 | 0.5652 ± 0.0509 | 0.7402 ± 0.0293 |
| FAERS (4-Fold LOO, N = 829) | Seed 456 | 0.5783 ± 0.0697 | 0.7586 ± 0.0355 |
| FAERS (4-Fold LOO, N = 829) | Seed 789 | 0.5663 ± 0.0476 | 0.7413 ± 0.0324 |
| FAERS (4-Fold LOO, N = 829) | Seed 1011 | 0.5748 ± 0.0694 | 0.7484 ± 0.0371 |
| **FAERS (4-Fold LOO, Pooled)** | **Mean ± SD (5 Seeds)** | **0.5685 ± 0.0080** | **0.7463 ± 0.0075** |
| VAERS (10-Fold CV, N = 1,000) | Seed 42 | 0.6594 ± 0.0196 | 0.7848 ± 0.0127 |
| VAERS (10-Fold CV, N = 1,000) | Seed 123 | 0.6601 ± 0.0175 | 0.7891 ± 0.0104 |
| VAERS (10-Fold CV, N = 1,000) | Seed 456 | 0.6593 ± 0.0218 | 0.7883 ± 0.0138 |
| VAERS (10-Fold CV, N = 1,000) | Seed 789 | 0.6615 ± 0.0159 | 0.7907 ± 0.0095 |
| VAERS (10-Fold CV, N = 1,000) | Seed 1011 | 0.6574 ± 0.0169 | 0.7879 ± 0.0106 |
| **VAERS (10-Fold CV, Pooled)** | **Mean ± SD (5 Seeds)** | **0.6595 ± 0.0015** | **0.7882 ± 0.0022** |

---

### Footnotes & Methodological Notes:
1. **FAERS Protocol:** 4-fold Leave-One-Drug-Event-Pair-Out cross-validation evaluated across all 17 clinical concept categories. For each seed, Mean $\pm$ SD represents out-of-fold cross-series variation.
2. **VAERS Protocol:** 10-fold cross-validation evaluated across all 14 clinical concept categories. For each seed, Mean $\pm$ SD represents cross-fold variation across the 10 test partitions.
3. **Pooled Invariance:** The pooled summary represents the Mean $\pm$ SD across the 5 independent random initialization seeds, demonstrating minimal stochastic variation ($SD = 0.0080$ on FAERS, $SD = 0.0015$ on VAERS).
