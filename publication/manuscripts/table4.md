# Table 4: Per-Category Performance Breakdown on FAERS Across All 17 Clinical Concept Categories (N = 829 Reports)

Fine-grained concept extraction performance across all 17 clinical concept categories on the FAERS benchmark corpus under the Two-Tier Evaluation Framework.

| Clinical Category | Gold Mentions (N) | BioBERT (Strict F1) | LLaMA 4 (Strict F1) | Claude Sonnet (Strict F1) | BioBERT (Adapted F1) | LLaMA 4 (Adapted F1) | Claude Sonnet (Adapted F1) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| sDrug | 4,665 | 0.6025 | 0.3181 | 0.4006 | 0.7376 | 0.5463 | 0.5619 |
| cDrug | 2,995 | 0.7433 | 0.3443 | 0.5689 | 0.8451 | 0.6013 | 0.7130 |
| oDrug | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.4804 | 0.4848 |
| Dose | 1,668 | 0.6100 | 0.2752 | 0.4300 | 0.7427 | 0.5783 | 0.6826 |
| Indication | 202 | 0.1335 | 0.0690 | 0.1042 | 0.5021 | 0.4913 | 0.5194 |
| Treatment | 1,490 | 0.6260 | 0.1832 | 0.3189 | 0.7775 | 0.4647 | 0.5355 |
| AE | 12,010 | 0.5931 | 0.3582 | 0.4401 | 0.7066 | 0.5635 | 0.5678 |
| mAE | 113 | 0.0480 | 0.0405 | 0.0594 | 0.0507 | 0.4604 | 0.4574 |
| Dx | 64 | 0.0670 | 0.0016 | 0.0000 | 0.4536 | 0.4016 | 0.3704 |
| Lab | 3,482 | 0.5964 | 0.1575 | 0.3742 | 0.7637 | 0.4912 | 0.6105 |
| Status | 1,910 | 0.7169 | 0.1304 | 0.2741 | 0.8386 | 0.2676 | 0.4547 |
| R/O | 9 | 0.0000 | 0.0073 | 0.0094 | 0.0000 | 0.4444 | 0.4539 |
| CoD | 3 | 0.0000 | 0.0052 | 0.0165 | 0.0000 | 0.4610 | 0.4686 |
| MHx | 2,370 | 0.4621 | 0.3474 | 0.4896 | 0.7138 | 0.6121 | 0.6888 |
| FHx | 105 | 0.0727 | 0.0606 | 0.1395 | 0.0818 | 0.1736 | 0.2130 |
| Age | 787 | 0.9009 | 0.7335 | 0.8752 | 0.9525 | 0.8590 | 0.9238 |
| Sex | 777 | 0.9037 | 0.7551 | 0.8829 | 0.9570 | 0.8575 | 0.9376 |
| **OVERALL** | 32,650 | **0.6032** | **0.2982** | **0.4189** | **0.7477** | **0.5515** | **0.6060** |

---

### Category Definitions & Footnotes:
- **Drug-Related:** `sDrug` (Suspect Drug), `cDrug` (Concomitant Drug), `oDrug` (Other Drug), `Dose` (Dosage), `Indication` (Drug Indication), `Treatment` (Drug used for treatment).
- **Adverse Event / Clinical Finding:** `AE` (Adverse Event), `mAE` (AE Manifestations/Sequelae), `Dx` (Diagnostic Test Results), `Lab` (Laboratory Findings), `Status` (Patient Status), `R/O` (Rule-Out Diagnosis), `CoD` (Cause of Death).
- **Medical / Family History:** `MHx` (Medical History), `FHx` (Family History).
- **Demographics:** `Age` (Patient Age), `Sex` (Patient Sex).
- **Primary Tier (Strict Exact-Match NER F1):** Requires identical character span boundaries and category assignment.
- **Secondary Tier (Adapted ADE-Eval Clinical Weighted F1):** Grants 0.5 partial credit to boundary shifts and adjacent category confusions, applying a 0.25 penalty to ungrounded false positives.
