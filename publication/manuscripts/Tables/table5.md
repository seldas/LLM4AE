# Table 5: Leave-One-Drug-Event-Pair-Out Cross-Validation Performance Across Four FAERS Case Series (N = 829 Reports Total)

Supervised BioBERT model generalization evaluated under a 4-fold Leave-One-Drug-Event-Pair-Out cross-validation protocol on the 17 clinical concept categories. For each case series, the model was trained on the remaining 3 case series and evaluated on the held-out target series across 5 independent random initialization seeds.

| Drug–Event Case Series | Validation Cohort Size | Primary Tier: Strict Exact F1 | Secondary Tier: Adapted ADE F1 |
| :--- | :---: | :---: | :---: |
| Azacitidine – QT Prolongation | N = 200 reports | 0.6002 ± 0.0114 | 0.7733 ± 0.0092 |
| Baricitinib – Hypersensitivity | N = 200 reports | 0.6367 ± 0.0201 | 0.7751 ± 0.0128 |
| Tramadol – Hypoglycemia | N = 229 reports | 0.5289 ± 0.0093 | 0.7242 ± 0.0036 |
| Erenumab – Stroke | N = 200 reports | 0.5084 ± 0.0122 | 0.7126 ± 0.0077 |
| **Macro-Average (All 4 Folds)** | N = 829 reports total | **0.5685 ± 0.0080** | **0.7463 ± 0.0075** |

---

### Footnotes & Methodological Notes:
1. **Validation Design:** In each fold, all cases of a specific drug-event pair were completely held out from training to simulate real-world pharmacovigilance surveillance for emerging adverse drug reactions.
2. **Evaluation Metrics:** Evaluated across the full 17 clinical concept categories. Mean $\pm$ SD reflects variance across 5 independent training runs per case series ($N = 20$ total model runs).
3. **Consistency with Master Benchmark:** The overall 4-fold macro-average strictly aligns with Table 3 and Table 6 ($0.5685 \pm 0.0080$ Strict F1, $0.7463 \pm 0.0076$ Adapted ADE F1).
