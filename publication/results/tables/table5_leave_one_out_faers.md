# Table 5: Leave-One-Drug-Event-Pair-Out Cross-Validation Performance Across Four FAERS Case Series (N = 829 Reports Total)

Supervised BioBERT model generalization evaluated under a 4-fold Leave-One-Drug-Event-Pair-Out cross-validation protocol on all 17 clinical concept categories. For each case series, the model was trained on the remaining 3 case series and evaluated on the held-out target series across 5 independent random initialization seeds.

| Drug–Event Case Series | Validation Cohort Size | Primary Tier: Strict Exact F1 | Secondary Tier: Adapted ADE F1 |
| :--- | :---: | :---: | :---: |
| Azacitidine – QT Prolongation | N = 200 reports | 0.6002 ± 0.0113 | 0.7733 ± 0.0092 |
| Baricitinib – Hypersensitivity | N = 200 reports | 0.6367 ± 0.0201 | 0.7751 ± 0.0128 |
| Tramadol – Hypoglycemia | N = 229 reports | 0.5289 ± 0.0093 | 0.7242 ± 0.0036 |
| Erenumab – Stroke | N = 200 reports | 0.5084 ± 0.0122 | 0.7126 ± 0.0077 |
| **Total (Micro-Average Aggregated)** | **N = 829 reports total** | **0.5564 ± 0.0069** | **0.7420 ± 0.0061** |

---

### Footnotes & Methodological Notes:
1. **Validation Design:** In each fold, all cases of a specific drug-event pair were completely held out from training to simulate real-world pharmacovigilance surveillance for emerging adverse drug reactions.
2. **Evaluation Metrics:** Evaluated across the full 17 clinical concept categories. Mean $\pm$ SD reflects variance across 5 independent training runs per case series ($N = 20$ total model runs).
3. **Micro-Average Aggregation:** The overall Total row reflects micro-average aggregation pooled across all 829 reports for each random seed (0.5564 ± 0.0069 Strict Exact F1, 0.7420 ± 0.0061 Adapted ADE F1).
