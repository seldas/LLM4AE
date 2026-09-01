# Table 8: Pretrained Transformer Encoder Architecture Ablation on VAERS (N = 1,000 Reports)

Empirical comparison of four transformer encoder architectures evaluated across five independent random initialization seeds (seeds 42, 123, 456, 789, 1011) on the VAERS dataset under standard default hyperparameters (learning rate $1\times 10^{-4}$ with linear warmup, Adam optimizer, max length 512, batch size 32).

| Model Architecture | Pretrained Checkpoint | Pretraining Domain | Validation F1 (Mean $\pm$ SD) | Validation Precision | Validation Recall | Clinical Score | Convergence Step |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **BioBERT v1.1** | `dmis-lab/biobert-base-cased-v1.1` | Biomedical Literature (PubMed abstracts + PMC full articles) | **0.8471 ± 0.0058** | 0.8666 ± 0.0048 | 0.8285 ± 0.0089 | 0.8500 ± 0.0071 | 1800 |
| Bio_ClinicalBERT | `emilyalsentzer/Bio_ClinicalBERT` | BioBERT initialized + MIMIC-III EHR Clinical Notes | 0.8433 ± 0.0070 | 0.8610 ± 0.0078 | 0.8264 ± 0.0104 | 0.8440 ± 0.0055 | 1080 |
| BERT-Base | `bert-base-cased` | General Domain (English Wikipedia + BooksCorpus) | 0.8382 ± 0.0047 | 0.8596 ± 0.0055 | 0.8179 ± 0.0061 | 0.8420 ± 0.0045 | 2160 |
| ClinicalBERT | `medicalai/ClinicalBERT` | Hospital EHR Clinical Records (MIMIC-III) | 0.8369 ± 0.0086 | 0.8615 ± 0.0106 | 0.8140 ± 0.0167 | 0.8400 ± 0.0071 | 1640 |

---

### Key Methodological & Clinical Insights:
1. **Biomedical Pretraining Advantage:** **BioBERT achieved the top overall performance** ($F_1 = 0.8471 \pm 0.0058$, Precision $= 0.8666$, Recall $= 0.8285$), confirming that pretraining on biomedical literature (PubMed abstracts and PMC full text) provides rich semantic representations for pharmacovigilance adverse event terminology.
2. **Domain Specialization Trade-off:** **Bio_ClinicalBERT** ($F_1 = 0.8433 \pm 0.0070$) demonstrated the fastest convergence (optimal checkpoint at step $1,080$), but showed slightly lower peak recall than pure BioBERT ($82.64\%$ vs. $82.85\%$), indicating that EHR-specific hospital discharge note syntax does not fully align with spontaneous public vaccine report narratives.
3. **General-Domain Robustness:** General-domain **BERT-Base** ($F_1 = 0.8382 \pm 0.0047$) demonstrated remarkably consistent optimization with the lowest standard deviation across seeds ($SD = 0.0047$), though requiring longer training steps (step $2,160$) to adapt to clinical vocabularies.
4. **Optimization Invariance:** All four architectures maintained narrow cross-seed variance ($SD < 0.009$ across 5 seeds), reaffirming that supervised transformer fine-tuning on spontaneous reporting narratives is robust across random weight initializations.
