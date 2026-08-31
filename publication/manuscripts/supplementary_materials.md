# Electronic Supplementary Material

**Article Title:** Benchmarking Fine-Tuned Encoders and Instruction-Tuned Large Language Models for Adverse Event Clinical Concept Extraction from Spontaneous Reporting Narratives
**Journal:** Drug Safety
**Authors:** [Author Names]
**Affiliations:** [Affiliations]
**Corresponding Author:** [Email]

---

## Table S1: FAERS Operational Annotation Guidelines (17 Categories)

### Annotation Schema

Annotate ONLY the following 17 clinical concept categories:

| Clinical Concept | Definition | Annotation Rule | Trigger Words / Phrases |
|---|---|---|---|
| **sDrug: Suspect Drug Products** | A drug or biological product believed to have caused, contributed to, or been associated with the adverse event. Often discontinued, changed, or adjusted after the AE. May have explicit causal language linking it to the AE. | Annotate a drug as **sDrug** when it is explicitly or strongly linked to the AE through causal, temporal, or attribution language. A clinical action taken because of the suspected relationship, such as discontinuation, dose reduction, dose increase, interruption, or rechallenge, can also support classification as sDrug. | suspected, suspect, implicated, caused, linked to, attributed to, associated with, related to, following administration of, after starting, after receiving, induced by, resolved after stopping, improved after discontinuation, symptoms worsened after increasing dose, dechallenge, rechallenge |
| **cDrug: Concomitant Drug Products** | Drugs that were concurrently administered with other drugs (e.g., suspect drugs), as part of the patient's ongoing or routine regimen. May include chronic medications, maintenance therapy, or background treatments. Some may have a potential or implicit causal relationship with the AE, as per applicant report. | Annotate a drug as **cDrug** when it is described as being taken concurrently with the suspect drug or as part of the patient's ongoing medication regimen, without sufficient evidence to classify it as the suspect drug or as treatment for the reported event. | concomitant, concomitant medication, concomitant drug, background therapy, chronic therapy, maintenance therapy, maintained on, patient's usual medications, current medications, home medications, taken concurrently, other medications included, medication regimen |
| **oDrug: Other Drug Products** | Drugs mentioned but not clearly linked to the current adverse event, concomitant drugs or therapy, or an explicit treatment purpose. Illicit substances should also be included when mentioned. Typically includes historical drug use or drug references without a specified current clinical role. | Annotate a drug or substance as **oDrug** when it is mentioned but cannot be reliably classified as sDrug, cDrug, or Treatment. Include historical drug exposure, general drug references, investigational drugs without a defined role in the current event, and illicit/non-medical substances. | illicit substances, recreational drug, substance use, past medications, previous medication, drug history, prior drug use, drug class, general drug reference, drug under investigation, investigational drug, historical use |
| **Dose: Dose Administered** | Explicitly stated dosage information associated with a drug. | Annotate explicit dosage quantity, strength, frequency, regimen, or stated dose adjustment. Annotate the dosage information itself, not the drug name. | mg, mcg, g, mL, units, dose, dosage, once daily, twice daily, BID, TID, weekly, increased, decreased, adjusted, reduced, titrated |
| **IND: Indication** | The reason or intended medical purpose for which a drug, treatment, or procedure is used. | Annotate the condition, symptom, disease, or stated reason for which a drug, treatment, or procedure was given or intended. Include explicitly stated unknown or unspecified indications when clearly identified as the indication. | used for, given for, prescribed for, indicated for, to treat, for treatment of, for the management of, for prevention of, indication, reason for use, unknown indication |
| **Treatment: Drug used for treatment** | Drug products or drug administration explicitly described as treatments addressing disease, adverse events, complications, or symptoms. | Annotate a drug as **Treatment** only when it is explicitly administered or used therapeutically to manage a disease, AE, complication, or symptom. Do not classify a drug as Treatment merely because it appears in a medication list. | treated with, treatment with, therapy with, was given, administered for, managed with, received, started on, prescribed to treat, supportive treatment, rescue medication |
| **AE: Adverse Event** | Any negative health outcome, condition, sign, or symptom that could represent an adverse event, regardless of proven relation to a drug. | Annotate clinically relevant negative health outcomes, diagnosed conditions, signs, or patient-reported symptoms representing an adverse event. Do not require proven drug causality. | adverse event, developed, experienced, complained of, reports, diagnosed with, presented with, onset of, occurred, after starting, unwell, discomfort |
| **mAE: AE Manifestations/Sequelae** | Manifestations are immediate signs or symptoms occurring as part of an identified AE. Sequelae are consequences, complications, or persistent secondary effects resulting from an AE. | Annotate a sign, symptom, clinical finding, consequence, or complication as **mAE** only when the narrative explicitly establishes it as a manifestation, consequence, complication, or sequela of another identified AE. Do not infer this relationship solely from medical knowledge. | manifested as, symptoms included, characterized by, accompanied by, resulted in, complicated by, complication of, led to, secondary to, sequela, persistent, residual, long-term effects |
| **Dx: Diagnostic Procedure** | The name of a diagnostic procedure performed to evaluate or confirm a medical condition or diagnosis. | Annotate the diagnostic procedure itself. Do not annotate its resulting diagnosis or interpretation as Dx. Laboratory tests and laboratory findings belong under Lab. | CT, CT scan, MRI, ultrasound, X-ray, radiograph, biopsy, histopathology, colonoscopy, endoscopy, echocardiogram, ECG, EKG, PET scan |
| **Lab: Laboratory Finding** | Laboratory tests, measurements, or results indicating quantitative or qualitative clinical findings. | Annotate laboratory test names and explicitly reported laboratory measurements/results, including normal, abnormal, positive, or negative findings. Objective measurements such as height, weight, and BMI may also be included when reported as clinical measurements. | result, level, value, measurement, elevated, increased, decreased, high, low, abnormal, normal, positive, negative, hemoglobin, platelet count, WBC, ALT, AST, bilirubin, creatinine, urinalysis, serum, height, weight, BMI |
| **Status: Patient Status** | Statements describing progression or outcome of the patient's overall clinical condition or an adverse event after treatment or intervention. | Annotate the clinical course, progression, outcome, recovery, deterioration, stability, persistence, or resolution. Status describes what happened to the patient or event rather than naming the underlying event itself. | recovered, resolved, improved, worsened, deteriorated, stable, unchanged, persistent, ongoing, outcome, admitted, discharged, hospitalized, asymptomatic, returned to baseline |
| **R/O: Rule-out Diagnosis** | Conditions considered but ultimately ruled out as explanations for symptoms or adverse events. | Annotate the condition or diagnosis that is explicitly ruled out, excluded, or determined unsupported. Do not automatically classify a condition as R/O solely because a test is negative. | ruled out, rule out, R/O, excluded, no evidence of, was considered but excluded, unlikely, not consistent with |
| **CoD: Cause of Death** | A specific disease, condition, event, or reason explicitly identified as causing or contributing to the patient's death. | Annotate the stated cause or contributing cause of death. Do not annotate the word "death" alone unless it itself represents the stated causal concept. | cause of death, died from, died of, death due to, death secondary to, succumbed to, resulted in death, contributing cause of death |
| **MHx: Medical History** | Symptoms, conditions, diagnoses, or medical findings that pre-existed before the current adverse event and were not caused by it. | Annotate the pre-existing or historical clinical condition itself. Do not include contextual phrases such as "history of" when the actual condition can be separately captured. | past medical history, medical history, PMH, history of, baseline, chronic, prior diagnosis, pre-existing, underlying condition, known condition, longstanding |
| **FHx: Family History** | Medical conditions or clinically relevant findings attributed to the patient's family members or family history. | Annotate the disease, condition, or relevant finding attributed to family history. Do not classify the patient's own medical history as FHx. | family history, FHx, mother had, father had, sibling had, familial, inherited, hereditary, genetic predisposition |
| **Age: Age** | The age or age category of the patient during the described event. | Annotate explicit references to the patient's exact or approximate age or age category. Annotate only references that clearly refer to the patient. | year-old, years old, aged, age, adult, elderly, adolescent, child, pediatric, infant, newborn, neonate |
| **Sex: Sex** | The biological sex of the patient as explicitly described in the clinical narrative. | Annotate explicit references to the patient's biological sex. Annotate only when the reference clearly applies to the patient. | male, female, man, woman, boy, girl |

### General Annotation Rules

1. **Use narrative context, not keyword matching.**
   Trigger words and phrases are contextual clues only. A trigger word does not automatically determine an annotation.

2. **Annotate the clinical entity, not the contextual trigger phrase.**
   For example:
   - "treated with prednisone" -> annotate "prednisone" as Treatment.
   - "history of hypertension" -> annotate "hypertension" as MHx.
   - "CT showed..." -> annotate "CT" as Dx when appropriate.

3. **Use exact text spans.**
   Every annotated span must occur verbatim in the source narrative. Do not normalize spelling, capitalization, abbreviations, numbers, or units.

4. **Prefer the smallest complete clinically meaningful span.**
   Do not include unnecessary surrounding words, punctuation, conjunctions, or trigger phrases.

5. **Do not infer unsupported clinical relationships.**
   Use only information expressed or clearly established in the narrative. Do not infer causality, chronology, indication, manifestation, or treatment role solely from medical knowledge.

6. **Do not annotate the same text span with multiple categories.**
   Choose the category that best represents the role of that span in its local narrative context.

7. **Do not create overlapping or nested annotations.**

8. **Drug-role precedence must be contextual.**
   For each drug mention, determine its role in that specific context:
   - sDrug = suspected or implicated in causing/contributing to an AE.
   - cDrug = concurrent/background medication.
   - Treatment = explicitly administered to treat a disease, AE, complication, or symptom.
   - oDrug = drug mentioned without sufficient evidence for the above roles.

9. **AE versus mAE must be based on an explicit relationship.**
   - AE = the adverse health event/condition/symptom itself.
   - mAE = a manifestation, complication, consequence, or sequela explicitly linked to another AE.
   If that relationship is not established in the narrative, do not infer mAE.

10. **AE versus MHx is determined by temporal/contextual role.**
    A condition explicitly described as pre-existing, chronic, baseline, or historical should be MHx rather than AE in that occurrence.

11. **IND is the reason for treatment, not the treatment itself.**
    Example:
    "prednisone for rash"
    - "prednisone" -> Treatment when explicitly being used therapeutically.
    - "rash" -> IND when explicitly stated as the reason for prednisone.

12. **Dx versus Lab:**
    - Dx = diagnostic procedure.
    - Lab = laboratory test, measurement, or laboratory finding/result.

13. **Status describes clinical course or outcome.**
    Do not label the underlying disease or AE as Status merely because its outcome is discussed.

14. **Repeated mentions may be annotated separately.**
    If the same clinical concept appears multiple times in the narrative, annotate each explicit occurrence according to its local context.

15. **Annotate only the 17 categories defined above.**
    Do not invent or add additional categories.

---

## Table S2: VAERS Operational Annotation Guidelines (14 Categories)

### Annotation Schema

Annotate ONLY the following 14 VAERS clinical/contextual concept categories:

| Clinical Concept | Definition | Annotation Rule | Trigger Words / Phrases |
|---|---|---|---|
| **SYM: Symptom / Adverse-Event Sign** | A patient-reported symptom, sign, complaint, or other clinical manifestation occurring as part of the post-vaccination adverse-event narrative. | Annotate the symptom/sign itself when it is described as experienced, observed, reported, or developed in the adverse-event context and is not presented as a formal diagnosis. Prefer SYM for manifestations such as pain, fever, dizziness, rash, weakness, swelling, nausea, or other signs/symptoms when no diagnostic label is being assigned. | symptom, symptoms, complained of, reported, experienced, developed, presented with, pain, fever, dizziness, rash, swelling, weakness, nausea, vomiting, headache, fatigue |
| **sDx: Confirmed AE Diagnosis** | A formal diagnosis or diagnosed clinical condition explicitly identified as an adverse event in the vaccination-related episode. | Annotate a diagnosed condition as **sDx** when the narrative presents it as a confirmed/established diagnosis belonging to the adverse-event episode. Use sDx rather than SYM when the text names a diagnosis rather than a symptom, and rather than DX when the diagnosis itself is part of the adverse-event outcome being reported. | diagnosed with, diagnosis of, confirmed, final diagnosis, determined to have, diagnosed as, assessment was, impression was |
| **pDx: Provisional AE Diagnosis** | A tentative, suspected, possible, or provisional diagnosis considered during evaluation of the adverse-event episode but not established as final. | Annotate a condition as **pDx** when the narrative explicitly frames it as suspected, possible, probable, provisional, differential, or otherwise uncertain during the adverse-event evaluation. Do not use pDx merely because the annotator is uncertain; uncertainty must be present in the narrative. | possible, probable, suspected, concern for, concerning for, provisional, differential diagnosis, may have, might have, could represent, likely, presumed |
| **DX: Diagnosis (Non-AE Context)** | A diagnosis or clinical condition mentioned in a diagnostic or clinical context that is not functioning as the reported adverse event, provisional AE diagnosis, medical history, or family history. | Annotate a diagnosis as **DX** when it is a current or contextual diagnosis but the narrative does not present it as the adverse event itself. Do not use DX for pre-existing conditions (MHx), family history (FHx), confirmed AEs (sDx), provisional AEs (pDx), symptoms (SYM), or diagnostic procedures. | diagnosis, diagnosed, condition, disease, disorder, assessment, impression, clinical diagnosis |
| **VAX: Vaccine** | A vaccine product, vaccination, immunization, or vaccine dose described as the administered or potentially causative exposure in the VAERS narrative. | Annotate the vaccine product/name or explicit vaccine reference when it identifies the immunization associated with the report. Annotate the vaccine entity itself, not surrounding administration verbs or temporal phrases. | vaccine, vaccination, immunization, immunized, COVID-19 vaccine, influenza vaccine, flu vaccine, Pfizer, Moderna, Janssen, dose of vaccine, shot |
| **MHx: Medical History** | A symptom, diagnosis, condition, or medical finding that pre-existed the vaccination/adverse-event episode or is explicitly described as part of the patient's past or chronic medical history. | Annotate the historical/pre-existing clinical condition itself. Do not include contextual phrases such as "history of" when the underlying condition can be separately captured. | past medical history, medical history, PMH, history of, baseline, chronic, pre-existing, underlying condition, known condition, longstanding, prior diagnosis |
| **FHx: Family History** | A disease, condition, or clinically relevant finding explicitly attributed to the patient's family members or family medical history. | Annotate the condition/finding attributed to family history. Do not classify the patient's own condition as FHx. | family history, FHx, mother had, father had, sibling had, familial, hereditary, inherited, genetic predisposition |
| **Lab: Laboratory Finding / Vital Sign** | A laboratory test, laboratory result, vital sign, physiologic measurement, or other objective measured clinical finding. | Annotate the test/measurement and its reported result when expressed as one clinically meaningful span when practical. Include normal, abnormal, positive, negative, quantitative, and qualitative findings. Include vital signs and objective measurements when they are reported as clinical findings. | laboratory, lab, level, result, value, positive, negative, elevated, decreased, normal, abnormal, CBC, WBC, hemoglobin, platelet, creatinine, glucose, temperature, blood pressure, heart rate, oxygen saturation |
| **TEMPO: Temporal Expression** | A date, time, duration, interval, relative-time phrase, latency, or other expression locating an event in time. | Annotate the temporal expression itself. Include absolute dates/times and relative expressions such as time since vaccination, onset latency, duration, or sequence timing. Do not include the clinical event unless it is inseparable from the temporal phrase. | on, at, after, before, later, same day, next day, hours later, days later, weeks later, for 3 days, since vaccination, shortly after, immediately after, date, time |
| **DOSE: Dose / Lot Information** | Vaccine dose information, dose number, amount, sequence, administration-dose descriptor, or vaccine lot/batch number. | Annotate explicit vaccine dose or lot information, including ordinal dose number and lot/batch identifier. Keep vaccine product name under VAX rather than DOSE. | first dose, second dose, third dose, booster, dose 1, dose 2, dose, dosage, lot, lot number, batch, batch number, 0.5 mL |
| **STATUS: Patient Status / Outcome** | A statement describing the patient's clinical course, disposition, recovery, persistence, worsening, hospitalization status, disability, death status, or other outcome. | Annotate the status/outcome expression itself. STATUS describes what happened to the patient or event over time, not the underlying symptom/diagnosis. | recovered, recovering, resolved, improved, worsened, stable, persistent, ongoing, hospitalized, admitted, discharged, emergency room, disability, life-threatening, outcome, died, death |
| **TX: Treatment / Provider / Intervention** | A treatment, therapeutic intervention, clinical management action, procedure used for treatment, or explicitly mentioned treating/provider service associated with management of the patient. | Annotate the treatment/intervention/provider entity or therapeutic action used to manage the patient or adverse event. Do not annotate the indication as TX. Drug names used as treatment may be included as TX when explicitly administered therapeutically. | treated with, treatment, therapy, given, administered, prescribed, managed with, IV fluids, acetaminophen, antihistamine, steroids, epinephrine, surgery, physician, provider, emergency department |
| **AGE: Patient Age** | The patient's exact or approximate age or age category during the reported vaccination/adverse-event episode. | Annotate explicit references to the patient's age or age category only when they clearly refer to the patient. | year-old, years old, aged, age, infant, child, adolescent, adult, elderly, older adult |
| **SEX: Patient Sex** | The biological sex of the patient as explicitly described in the VAERS narrative. | Annotate explicit references to the patient's biological sex only when they clearly refer to the patient. | male, female, man, woman, boy, girl |

### General Annotation Rules

1. **Use narrative context, not keyword matching.**
   Trigger words and phrases are contextual clues only. A trigger word does not automatically determine an annotation.

2. **Annotate the clinical entity, not the contextual trigger phrase.**
   Examples:
   - "history of asthma" -> annotate "asthma" as MHx.
   - "treated with acetaminophen" -> annotate "acetaminophen" as TX.
   - "two days after vaccination" -> annotate "two days after vaccination" or the smallest complete temporal expression as TEMPO, while the vaccine itself remains VAX when separately expressed.

3. **Use exact text spans.**
   Every annotated span must occur verbatim in the source narrative. Do not normalize spelling, capitalization, abbreviations, numbers, or units.

4. **Prefer the smallest complete clinically meaningful span.**
   Do not include unnecessary surrounding words, punctuation, conjunctions, or trigger phrases.

5. **Do not infer unsupported clinical relationships.**
   Use only information expressed or clearly established in the narrative. Do not infer causality, chronology, diagnosis certainty, medical history, or treatment role solely from medical knowledge.

6. **Do not annotate the same text span with multiple categories.**
   Choose the category that best represents the role of that occurrence in its local narrative context.

7. **Do not create overlapping or nested annotations.**

8. **SYM vs sDx vs pDx vs DX must follow the narrative role.**
   - SYM = symptom/sign/complaint without a formal diagnostic role.
   - sDx = established/confirmed diagnosis functioning as an adverse event in the reported episode.
   - pDx = tentative/suspected/provisional diagnosis in the adverse-event episode.
   - DX = diagnosis in a current/contextual non-AE role.
   Do not convert a symptom into a diagnosis based only on medical knowledge.

9. **sDx vs pDx is determined by diagnostic certainty expressed in the text.**
   A diagnosis is pDx only when the narrative itself indicates uncertainty, suspicion, possibility, probability, or provisional status.

10. **MHx and FHx take precedence when history is explicit.**
    - MHx = patient's own pre-existing/historical condition.
    - FHx = condition attributed to family members/family history.
    Do not relabel these occurrences as SYM, sDx, pDx, or DX solely because the same condition could be clinically relevant to the current event.

11. **VAX identifies the vaccine exposure, not the timing or dose descriptor.**
    Example: "second dose of Pfizer vaccine"
    - "second dose" -> DOSE
    - "Pfizer vaccine" -> VAX

12. **DOSE includes vaccine sequence and lot information.**
    Dose number, amount, booster designation, and lot/batch identifiers belong to DOSE when explicitly stated.

13. **TEMPO captures temporal information only.**
    Dates, times, durations, latency, and relative temporal phrases belong to TEMPO. Do not absorb the associated symptom, diagnosis, vaccine, or treatment into the temporal span unless the phrase cannot be separated without losing its meaning.

14. **Lab includes objective laboratory findings and vital signs.**
    Diagnostic labels inferred from those findings should not be added unless explicitly stated elsewhere in the narrative.

15. **STATUS describes course, disposition, or outcome.**
    Do not label the underlying symptom or diagnosis as STATUS merely because its course or outcome is discussed.

16. **TX includes therapeutic management/intervention.**
    Annotate what was done to treat or manage the patient. Do not label the condition being treated as TX.

17. **Repeated mentions may be annotated separately.**
    If the same concept appears multiple times, annotate each explicit occurrence according to its local context.

18. **Annotate only the 14 VAERS categories defined above.**
    Do not invent or add additional categories.

---

## Section S2: Model Selection & Pre-training Ablation Rationale

Prior to adopting BioBERT as the supervised encoder baseline, we conducted pre-training domain ablation studies comparing generic BERT, ClinicalBERT (Alsentzer et al., trained on MIMIC-III EHRs), PubMedBERT (Gu et al., trained on PubMed full-text), and BioBERT (Lee et al., trained on PubMed abstracts).

BioBERT was ultimately selected for pharmacovigilance benchmarking due to its superior subword tokenization fidelity for chemical stems and pharmacological entities. While ClinicalBERT excels on EHR-specific abbreviations (e.g., ICU shorthand), spontaneous reporting narratives lack standardized hospital syntax. Instead, they contain high densities of complex chemical compound names (e.g., *pembrolizumab*, *azacitidine*) and rare pathophysiological symptom clusters. Because BioBERT was extensively pre-trained on biomedical literature abstracts, its WordPiece vocabulary minimizes out-of-vocabulary (OOV) fragmentation for long drug names, providing the most structurally coherent token representations for the sequence tagging head.

---

## Section S3: Verbatim Prompt Templates

### S3.1 FAERS In-Line Tagged XML Prompt (P2_TAG)

`	ext
You are an expert medical annotator analyzing a FAERS
(FDA Adverse Event Reporting System) case report narrative.

Your task is to identify clinical entities according to the annotation
schema below and insert XML-style annotation tags directly into the
original narrative.


### Annotation Schema

Annotate ONLY the following 17 clinical concept categories:

| Clinical Concept | Definition | Annotation Rule | Trigger Words / Phrases |
|---|---|---|---|
| **sDrug: Suspect Drug Products** | A drug or biological product believed to have caused, contributed to, or been associated with the adverse event. Often discontinued, changed, or adjusted after the AE. May have explicit causal language linking it to the AE. | Annotate a drug as **sDrug** when it is explicitly or strongly linked to the AE through causal, temporal, or attribution language. A clinical action taken because of the suspected relationship, such as discontinuation, dose reduction, dose increase, interruption, or rechallenge, can also support classification as sDrug. | suspected, suspect, implicated, caused, linked to, attributed to, associated with, related to, following administration of, after starting, after receiving, induced by, resolved after stopping, improved after discontinuation, symptoms worsened after increasing dose, dechallenge, rechallenge |
| **cDrug: Concomitant Drug Products** | Drugs that were concurrently administered with other drugs (e.g., suspect drugs), as part of the patient's ongoing or routine regimen. May include chronic medications, maintenance therapy, or background treatments. Some may have a potential or implicit causal relationship with the AE, as per applicant report. | Annotate a drug as **cDrug** when it is described as being taken concurrently with the suspect drug or as part of the patient's ongoing medication regimen, without sufficient evidence to classify it as the suspect drug or as treatment for the reported event. | concomitant, concomitant medication, concomitant drug, background therapy, chronic therapy, maintenance therapy, maintained on, patient's usual medications, current medications, home medications, taken concurrently, other medications included, medication regimen |
| **oDrug: Other Drug Products** | Drugs mentioned but not clearly linked to the current adverse event, concomitant drugs or therapy, or an explicit treatment purpose. Illicit substances should also be included when mentioned. Typically includes historical drug use or drug references without a specified current clinical role. | Annotate a drug or substance as **oDrug** when it is mentioned but cannot be reliably classified as sDrug, cDrug, or Treatment. Include historical drug exposure, general drug references, investigational drugs without a defined role in the current event, and illicit/non-medical substances. | illicit substances, recreational drug, substance use, past medications, previous medication, drug history, prior drug use, drug class, general drug reference, drug under investigation, investigational drug, historical use |
| **Dose: Dose Administered** | Explicitly stated dosage information associated with a drug. | Annotate explicit dosage quantity, strength, frequency, regimen, or stated dose adjustment. Annotate the dosage information itself, not the drug name. | mg, mcg, g, mL, units, dose, dosage, once daily, twice daily, BID, TID, weekly, increased, decreased, adjusted, reduced, titrated |
| **IND: Indication** | The reason or intended medical purpose for which a drug, treatment, or procedure is used. | Annotate the condition, symptom, disease, or stated reason for which a drug, treatment, or procedure was given or intended. Include explicitly stated unknown or unspecified indications when clearly identified as the indication. | used for, given for, prescribed for, indicated for, to treat, for treatment of, for the management of, for prevention of, indication, reason for use, unknown indication |
| **Treatment: Drug used for treatment** | Drug products or drug administration explicitly described as treatments addressing disease, adverse events, complications, or symptoms. | Annotate a drug as **Treatment** only when it is explicitly administered or used therapeutically to manage a disease, AE, complication, or symptom. Do not classify a drug as Treatment merely because it appears in a medication list. | treated with, treatment with, therapy with, was given, administered for, managed with, received, started on, prescribed to treat, supportive treatment, rescue medication |
| **AE: Adverse Event** | Any negative health outcome, condition, sign, or symptom that could represent an adverse event, regardless of proven relation to a drug. | Annotate clinically relevant negative health outcomes, diagnosed conditions, signs, or patient-reported symptoms representing an adverse event. Do not require proven drug causality. | adverse event, developed, experienced, complained of, reports, diagnosed with, presented with, onset of, occurred, after starting, unwell, discomfort |
| **mAE: AE Manifestations/Sequelae** | Manifestations are immediate signs or symptoms occurring as part of an identified AE. Sequelae are consequences, complications, or persistent secondary effects resulting from an AE. | Annotate a sign, symptom, clinical finding, consequence, or complication as **mAE** only when the narrative explicitly establishes it as a manifestation, consequence, complication, or sequela of another identified AE. Do not infer this relationship solely from medical knowledge. | manifested as, symptoms included, characterized by, accompanied by, resulted in, complicated by, complication of, led to, secondary to, sequela, persistent, residual, long-term effects |
| **Dx: Diagnostic Procedure** | The name of a diagnostic procedure performed to evaluate or confirm a medical condition or diagnosis. | Annotate the diagnostic procedure itself. Do not annotate its resulting diagnosis or interpretation as Dx. Laboratory tests and laboratory findings belong under Lab. | CT, CT scan, MRI, ultrasound, X-ray, radiograph, biopsy, histopathology, colonoscopy, endoscopy, echocardiogram, ECG, EKG, PET scan |
| **Lab: Laboratory Finding** | Laboratory tests, measurements, or results indicating quantitative or qualitative clinical findings. | Annotate laboratory test names and explicitly reported laboratory measurements/results, including normal, abnormal, positive, or negative findings. Objective measurements such as height, weight, and BMI may also be included when reported as clinical measurements. | result, level, value, measurement, elevated, increased, decreased, high, low, abnormal, normal, positive, negative, hemoglobin, platelet count, WBC, ALT, AST, bilirubin, creatinine, urinalysis, serum, height, weight, BMI |
| **Status: Patient Status** | Statements describing progression or outcome of the patient's overall clinical condition or an adverse event after treatment or intervention. | Annotate the clinical course, progression, outcome, recovery, deterioration, stability, persistence, or resolution. Status describes what happened to the patient or event rather than naming the underlying event itself. | recovered, resolved, improved, worsened, deteriorated, stable, unchanged, persistent, ongoing, outcome, admitted, discharged, hospitalized, asymptomatic, returned to baseline |
| **R/O: Rule-out Diagnosis** | Conditions considered but ultimately ruled out as explanations for symptoms or adverse events. | Annotate the condition or diagnosis that is explicitly ruled out, excluded, or determined unsupported. Do not automatically classify a condition as R/O solely because a test is negative. | ruled out, rule out, R/O, excluded, no evidence of, was considered but excluded, unlikely, not consistent with |
| **CoD: Cause of Death** | A specific disease, condition, event, or reason explicitly identified as causing or contributing to the patient's death. | Annotate the stated cause or contributing cause of death. Do not annotate the word "death" alone unless it itself represents the stated causal concept. | cause of death, died from, died of, death due to, death secondary to, succumbed to, resulted in death, contributing cause of death |
| **MHx: Medical History** | Symptoms, conditions, diagnoses, or medical findings that pre-existed before the current adverse event and were not caused by it. | Annotate the pre-existing or historical clinical condition itself. Do not include contextual phrases such as "history of" when the actual condition can be separately captured. | past medical history, medical history, PMH, history of, baseline, chronic, prior diagnosis, pre-existing, underlying condition, known condition, longstanding |
| **FHx: Family History** | Medical conditions or clinically relevant findings attributed to the patient's family members or family history. | Annotate the disease, condition, or relevant finding attributed to family history. Do not classify the patient's own medical history as FHx. | family history, FHx, mother had, father had, sibling had, familial, inherited, hereditary, genetic predisposition |
| **Age: Age** | The age or age category of the patient during the described event. | Annotate explicit references to the patient's exact or approximate age or age category. Annotate only references that clearly refer to the patient. | year-old, years old, aged, age, adult, elderly, adolescent, child, pediatric, infant, newborn, neonate |
| **Sex: Sex** | The biological sex of the patient as explicitly described in the clinical narrative. | Annotate explicit references to the patient's biological sex. Annotate only when the reference clearly applies to the patient. | male, female, man, woman, boy, girl |

### General Annotation Rules

1. **Use narrative context, not keyword matching.**
   Trigger words and phrases are contextual clues only. A trigger word does not automatically determine an annotation.

2. **Annotate the clinical entity, not the contextual trigger phrase.**
   For example:
   - "treated with prednisone" -> annotate "prednisone" as Treatment.
   - "history of hypertension" -> annotate "hypertension" as MHx.
   - "CT showed..." -> annotate "CT" as Dx when appropriate.

3. **Use exact text spans.**
   Every annotated span must occur verbatim in the source narrative. Do not normalize spelling, capitalization, abbreviations, numbers, or units.

4. **Prefer the smallest complete clinically meaningful span.**
   Do not include unnecessary surrounding words, punctuation, conjunctions, or trigger phrases.

5. **Do not infer unsupported clinical relationships.**
   Use only information expressed or clearly established in the narrative. Do not infer causality, chronology, indication, manifestation, or treatment role solely from medical knowledge.

6. **Do not annotate the same text span with multiple categories.**
   Choose the category that best represents the role of that span in its local narrative context.

7. **Do not create overlapping or nested annotations.**

8. **Drug-role precedence must be contextual.**
   For each drug mention, determine its role in that specific context:
   - sDrug = suspected or implicated in causing/contributing to an AE.
   - cDrug = concurrent/background medication.
   - Treatment = explicitly administered to treat a disease, AE, complication, or symptom.
   - oDrug = drug mentioned without sufficient evidence for the above roles.

9. **AE versus mAE must be based on an explicit relationship.**
   - AE = the adverse health event/condition/symptom itself.
   - mAE = a manifestation, complication, consequence, or sequela explicitly linked to another AE.
   If that relationship is not established in the narrative, do not infer mAE.

10. **AE versus MHx is determined by temporal/contextual role.**
    A condition explicitly described as pre-existing, chronic, baseline, or historical should be MHx rather than AE in that occurrence.

11. **IND is the reason for treatment, not the treatment itself.**
    Example:
    "prednisone for rash"
    - "prednisone" -> Treatment when explicitly being used therapeutically.
    - "rash" -> IND when explicitly stated as the reason for prednisone.

12. **Dx versus Lab:**
    - Dx = diagnostic procedure.
    - Lab = laboratory test, measurement, or laboratory finding/result.

13. **Status describes clinical course or outcome.**
    Do not label the underlying disease or AE as Status merely because its outcome is discussed.

14. **Repeated mentions may be annotated separately.**
    If the same clinical concept appears multiple times in the narrative, annotate each explicit occurrence according to its local context.

15. **Annotate only the 17 categories defined above.**
    Do not invent or add additional categories.


### Allowed Tags

Use ONLY these tags:

<SDRUG>...</SDRUG>
<CDRUG>...</CDRUG>
<ODRUG>...</ODRUG>
<DOSE>...</DOSE>
<IND>...</IND>
<TREATMENT>...</TREATMENT>
<AE>...</AE>
<MAE>...</MAE>
<DX>...</DX>
<LAB>...</LAB>
<STATUS>...</STATUS>
<RO>...</RO>
<COD>...</COD>
<MHX>...</MHX>
<FHX>...</FHX>
<AGE>...</AGE>
<SEX>...</SEX>

Do NOT create any other tag.

### In-Text Annotation Rules

1. Insert tags around the exact entity span in the original narrative.

2. Do NOT alter the original narrative in any way other than inserting
   annotation tags.

3. Preserve exactly:
   - wording
   - spelling
   - capitalization
   - punctuation
   - numbers
   - whitespace
   - paragraph structure

4. Every opening tag must have the corresponding closing tag.

5. Tags must NOT overlap or nest.

6. Annotate only the smallest complete clinically meaningful span.

7. Contextual or trigger phrases should normally remain outside the tag.

Example:

Original:
The patient was treated with prednisone for rash.

Correct:
The patient was treated with <TREATMENT>prednisone</TREATMENT> for <IND>rash</IND>.

Incorrect:
The patient was <TREATMENT>treated with prednisone</TREATMENT> for rash.

### Additional Examples

Original:
Concomitant medications included atenolol 25 mg twice daily.

Correct:
Concomitant medications included <CDRUG>atenolol</CDRUG> <DOSE>25 mg twice daily</DOSE>.

Original:
Her medical history included hypertension.

Correct:
Her medical history included <MHX>hypertension</MHX>.

Original:
CT demonstrated no acute intracranial abnormality.

Correct:
<DX>CT</DX> demonstrated no acute intracranial abnormality.

### Narrative

{text}

### CRITICAL OUTPUT REQUIREMENTS

1. Return ONLY the fully annotated narrative.
2. Do NOT add an introductory sentence such as
   "The annotated text is shown as below:".
3. Do NOT use Markdown code fences.
4. Do NOT provide explanations, comments, summaries, or lists.
5. Apart from the inserted annotation tags, every character of the
   original narrative must remain unchanged.
`

### S3.2 FAERS Structured JSON Prompt (P1_JSON)

`	ext
You are an expert medical annotator analyzing a FAERS
(FDA Adverse Event Reporting System) case report narrative.

Your task is to identify clinical entities in the narrative according to
the annotation schema below and return the annotations as structured JSON.


### Annotation Schema

Annotate ONLY the following 17 clinical concept categories:

| Clinical Concept | Definition | Annotation Rule | Trigger Words / Phrases |
|---|---|---|---|
| **sDrug: Suspect Drug Products** | A drug or biological product believed to have caused, contributed to, or been associated with the adverse event. Often discontinued, changed, or adjusted after the AE. May have explicit causal language linking it to the AE. | Annotate a drug as **sDrug** when it is explicitly or strongly linked to the AE through causal, temporal, or attribution language. A clinical action taken because of the suspected relationship, such as discontinuation, dose reduction, dose increase, interruption, or rechallenge, can also support classification as sDrug. | suspected, suspect, implicated, caused, linked to, attributed to, associated with, related to, following administration of, after starting, after receiving, induced by, resolved after stopping, improved after discontinuation, symptoms worsened after increasing dose, dechallenge, rechallenge |
| **cDrug: Concomitant Drug Products** | Drugs that were concurrently administered with other drugs (e.g., suspect drugs), as part of the patient's ongoing or routine regimen. May include chronic medications, maintenance therapy, or background treatments. Some may have a potential or implicit causal relationship with the AE, as per applicant report. | Annotate a drug as **cDrug** when it is described as being taken concurrently with the suspect drug or as part of the patient's ongoing medication regimen, without sufficient evidence to classify it as the suspect drug or as treatment for the reported event. | concomitant, concomitant medication, concomitant drug, background therapy, chronic therapy, maintenance therapy, maintained on, patient's usual medications, current medications, home medications, taken concurrently, other medications included, medication regimen |
| **oDrug: Other Drug Products** | Drugs mentioned but not clearly linked to the current adverse event, concomitant drugs or therapy, or an explicit treatment purpose. Illicit substances should also be included when mentioned. Typically includes historical drug use or drug references without a specified current clinical role. | Annotate a drug or substance as **oDrug** when it is mentioned but cannot be reliably classified as sDrug, cDrug, or Treatment. Include historical drug exposure, general drug references, investigational drugs without a defined role in the current event, and illicit/non-medical substances. | illicit substances, recreational drug, substance use, past medications, previous medication, drug history, prior drug use, drug class, general drug reference, drug under investigation, investigational drug, historical use |
| **Dose: Dose Administered** | Explicitly stated dosage information associated with a drug. | Annotate explicit dosage quantity, strength, frequency, regimen, or stated dose adjustment. Annotate the dosage information itself, not the drug name. | mg, mcg, g, mL, units, dose, dosage, once daily, twice daily, BID, TID, weekly, increased, decreased, adjusted, reduced, titrated |
| **IND: Indication** | The reason or intended medical purpose for which a drug, treatment, or procedure is used. | Annotate the condition, symptom, disease, or stated reason for which a drug, treatment, or procedure was given or intended. Include explicitly stated unknown or unspecified indications when clearly identified as the indication. | used for, given for, prescribed for, indicated for, to treat, for treatment of, for the management of, for prevention of, indication, reason for use, unknown indication |
| **Treatment: Drug used for treatment** | Drug products or drug administration explicitly described as treatments addressing disease, adverse events, complications, or symptoms. | Annotate a drug as **Treatment** only when it is explicitly administered or used therapeutically to manage a disease, AE, complication, or symptom. Do not classify a drug as Treatment merely because it appears in a medication list. | treated with, treatment with, therapy with, was given, administered for, managed with, received, started on, prescribed to treat, supportive treatment, rescue medication |
| **AE: Adverse Event** | Any negative health outcome, condition, sign, or symptom that could represent an adverse event, regardless of proven relation to a drug. | Annotate clinically relevant negative health outcomes, diagnosed conditions, signs, or patient-reported symptoms representing an adverse event. Do not require proven drug causality. | adverse event, developed, experienced, complained of, reports, diagnosed with, presented with, onset of, occurred, after starting, unwell, discomfort |
| **mAE: AE Manifestations/Sequelae** | Manifestations are immediate signs or symptoms occurring as part of an identified AE. Sequelae are consequences, complications, or persistent secondary effects resulting from an AE. | Annotate a sign, symptom, clinical finding, consequence, or complication as **mAE** only when the narrative explicitly establishes it as a manifestation, consequence, complication, or sequela of another identified AE. Do not infer this relationship solely from medical knowledge. | manifested as, symptoms included, characterized by, accompanied by, resulted in, complicated by, complication of, led to, secondary to, sequela, persistent, residual, long-term effects |
| **Dx: Diagnostic Procedure** | The name of a diagnostic procedure performed to evaluate or confirm a medical condition or diagnosis. | Annotate the diagnostic procedure itself. Do not annotate its resulting diagnosis or interpretation as Dx. Laboratory tests and laboratory findings belong under Lab. | CT, CT scan, MRI, ultrasound, X-ray, radiograph, biopsy, histopathology, colonoscopy, endoscopy, echocardiogram, ECG, EKG, PET scan |
| **Lab: Laboratory Finding** | Laboratory tests, measurements, or results indicating quantitative or qualitative clinical findings. | Annotate laboratory test names and explicitly reported laboratory measurements/results, including normal, abnormal, positive, or negative findings. Objective measurements such as height, weight, and BMI may also be included when reported as clinical measurements. | result, level, value, measurement, elevated, increased, decreased, high, low, abnormal, normal, positive, negative, hemoglobin, platelet count, WBC, ALT, AST, bilirubin, creatinine, urinalysis, serum, height, weight, BMI |
| **Status: Patient Status** | Statements describing progression or outcome of the patient's overall clinical condition or an adverse event after treatment or intervention. | Annotate the clinical course, progression, outcome, recovery, deterioration, stability, persistence, or resolution. Status describes what happened to the patient or event rather than naming the underlying event itself. | recovered, resolved, improved, worsened, deteriorated, stable, unchanged, persistent, ongoing, outcome, admitted, discharged, hospitalized, asymptomatic, returned to baseline |
| **R/O: Rule-out Diagnosis** | Conditions considered but ultimately ruled out as explanations for symptoms or adverse events. | Annotate the condition or diagnosis that is explicitly ruled out, excluded, or determined unsupported. Do not automatically classify a condition as R/O solely because a test is negative. | ruled out, rule out, R/O, excluded, no evidence of, was considered but excluded, unlikely, not consistent with |
| **CoD: Cause of Death** | A specific disease, condition, event, or reason explicitly identified as causing or contributing to the patient's death. | Annotate the stated cause or contributing cause of death. Do not annotate the word "death" alone unless it itself represents the stated causal concept. | cause of death, died from, died of, death due to, death secondary to, succumbed to, resulted in death, contributing cause of death |
| **MHx: Medical History** | Symptoms, conditions, diagnoses, or medical findings that pre-existed before the current adverse event and were not caused by it. | Annotate the pre-existing or historical clinical condition itself. Do not include contextual phrases such as "history of" when the actual condition can be separately captured. | past medical history, medical history, PMH, history of, baseline, chronic, prior diagnosis, pre-existing, underlying condition, known condition, longstanding |
| **FHx: Family History** | Medical conditions or clinically relevant findings attributed to the patient's family members or family history. | Annotate the disease, condition, or relevant finding attributed to family history. Do not classify the patient's own medical history as FHx. | family history, FHx, mother had, father had, sibling had, familial, inherited, hereditary, genetic predisposition |
| **Age: Age** | The age or age category of the patient during the described event. | Annotate explicit references to the patient's exact or approximate age or age category. Annotate only references that clearly refer to the patient. | year-old, years old, aged, age, adult, elderly, adolescent, child, pediatric, infant, newborn, neonate |
| **Sex: Sex** | The biological sex of the patient as explicitly described in the clinical narrative. | Annotate explicit references to the patient's biological sex. Annotate only when the reference clearly applies to the patient. | male, female, man, woman, boy, girl |

### General Annotation Rules

1. **Use narrative context, not keyword matching.**
   Trigger words and phrases are contextual clues only. A trigger word does not automatically determine an annotation.

2. **Annotate the clinical entity, not the contextual trigger phrase.**
   For example:
   - "treated with prednisone" -> annotate "prednisone" as Treatment.
   - "history of hypertension" -> annotate "hypertension" as MHx.
   - "CT showed..." -> annotate "CT" as Dx when appropriate.

3. **Use exact text spans.**
   Every annotated span must occur verbatim in the source narrative. Do not normalize spelling, capitalization, abbreviations, numbers, or units.

4. **Prefer the smallest complete clinically meaningful span.**
   Do not include unnecessary surrounding words, punctuation, conjunctions, or trigger phrases.

5. **Do not infer unsupported clinical relationships.**
   Use only information expressed or clearly established in the narrative. Do not infer causality, chronology, indication, manifestation, or treatment role solely from medical knowledge.

6. **Do not annotate the same text span with multiple categories.**
   Choose the category that best represents the role of that span in its local narrative context.

7. **Do not create overlapping or nested annotations.**

8. **Drug-role precedence must be contextual.**
   For each drug mention, determine its role in that specific context:
   - sDrug = suspected or implicated in causing/contributing to an AE.
   - cDrug = concurrent/background medication.
   - Treatment = explicitly administered to treat a disease, AE, complication, or symptom.
   - oDrug = drug mentioned without sufficient evidence for the above roles.

9. **AE versus mAE must be based on an explicit relationship.**
   - AE = the adverse health event/condition/symptom itself.
   - mAE = a manifestation, complication, consequence, or sequela explicitly linked to another AE.
   If that relationship is not established in the narrative, do not infer mAE.

10. **AE versus MHx is determined by temporal/contextual role.**
    A condition explicitly described as pre-existing, chronic, baseline, or historical should be MHx rather than AE in that occurrence.

11. **IND is the reason for treatment, not the treatment itself.**
    Example:
    "prednisone for rash"
    - "prednisone" -> Treatment when explicitly being used therapeutically.
    - "rash" -> IND when explicitly stated as the reason for prednisone.

12. **Dx versus Lab:**
    - Dx = diagnostic procedure.
    - Lab = laboratory test, measurement, or laboratory finding/result.

13. **Status describes clinical course or outcome.**
    Do not label the underlying disease or AE as Status merely because its outcome is discussed.

14. **Repeated mentions may be annotated separately.**
    If the same clinical concept appears multiple times in the narrative, annotate each explicit occurrence according to its local context.

15. **Annotate only the 17 categories defined above.**
    Do not invent or add additional categories.


### Reported FAERS Context

The following structured FAERS fields are provided only to determine
"is_reported" and "mapped_term". They must NOT be used to invent an
annotation that is absent from the narrative.

Reported Suspect Drugs:
{suspect_drugs}

Reported Events (Preferred Terms):
{primary_events}

### JSON Output Schema

Return exactly one JSON object containing all 17 keys below:

{
  "sdrug": [],
  "cdrug": [],
  "odrug": [],
  "dose": [],
  "ind": [],
  "treatment": [],
  "ae": [],
  "mae": [],
  "dx": [],
  "lab": [],
  "status": [],
  "ro": [],
  "cod": [],
  "mhx": [],
  "fhx": [],
  "age": [],
  "sex": []
}

Each detected entity must be represented as:

{
  "text": "exact substring from narrative",
  "start": 0,
  "end": 0,
  "is_reported": false,
  "mapped_term": null
}

### Rules for "text", "start", and "end"

- "text" MUST be copied verbatim from the narrative.
- "start" MUST be the 0-based character offset of the first character of "text" in the supplied narrative.
- "end" MUST be the 0-based exclusive character offset immediately after the last character of "text".
- The intended relationship is: narrative[start:end] == text.
- Count every character exactly as it appears in the supplied narrative, including spaces, punctuation, and newline characters.
- Do not normalize, rewrite, expand, abbreviate, or correct the text.
- Do not include unnecessary contextual words around the entity.
- If the same entity text occurs multiple times, use the offsets of the specific occurrence being annotated.
- Each explicit occurrence must be represented separately.
- Within each category, order entities by ascending "start", then ascending "end".

### Rules for "is_reported"

For **sdrug**:
- true if the annotated drug corresponds to a Reported Suspect Drug,
  either by exact match or a clearly equivalent synonym/name.
- false otherwise.

For **ae** and **mae**:
- true if the annotated clinical event corresponds to a Reported Event (PT),
  either by exact match or a clearly equivalent synonym/description.
- false otherwise.

For all other categories:
- use false.

The Reported FAERS fields are reference metadata only.
They must NOT determine whether an entity is annotated.

### Rules for "mapped_term"

- If "is_reported" is false, use null.
- If the narrative text exactly matches the corresponding Reported term,
  use null.
- If the narrative uses a synonym, abbreviation, or descriptive expression
  corresponding to a Reported term, set "mapped_term" to that exact
  Reported term.
- Do not create a mapped term that is not present in the supplied
  Reported Suspect Drugs or Reported Events.

### Completeness and Ordering Rules

- Include every supported entity occurrence found in the narrative.
- Repeated occurrences must be returned as separate objects.
- Do not collapse repeated mentions into a single object.
- If a category has no entities, return an empty list.
- Return all 17 keys, even when their values are empty lists.
- Do not return duplicate objects for the same occurrence.
- Within each category list, order annotations by ascending "start", then ascending "end".

### Narrative

{text}

### CRITICAL OUTPUT REQUIREMENTS

1. Return ONLY valid JSON.
2. Do NOT use Markdown code fences.
3. Do NOT include ```json or ```.
4. Do NOT include explanations, headings, comments, or conversational text.
5. The first character of the response must be "{".
6. The final character of the response must be "}".
`

### S3.3 VAERS In-Line Tagged XML Prompt (P2_TAG_VAERS)

`	ext
You are an expert medical annotator analyzing a VAERS
(Vaccine Adverse Event Reporting System) case report narrative.

Your task is to identify clinical and contextual entities according to the
annotation schema below and insert XML-style annotation tags directly into
the original narrative.


### Annotation Schema

Annotate ONLY the following 14 VAERS clinical/contextual concept categories:

| Clinical Concept | Definition | Annotation Rule | Trigger Words / Phrases |
|---|---|---|---|
| **SYM: Symptom / Adverse-Event Sign** | A patient-reported symptom, sign, complaint, or other clinical manifestation occurring as part of the post-vaccination adverse-event narrative. | Annotate the symptom/sign itself when it is described as experienced, observed, reported, or developed in the adverse-event context and is not presented as a formal diagnosis. Prefer SYM for manifestations such as pain, fever, dizziness, rash, weakness, swelling, nausea, or other signs/symptoms when no diagnostic label is being assigned. | symptom, symptoms, complained of, reported, experienced, developed, presented with, pain, fever, dizziness, rash, swelling, weakness, nausea, vomiting, headache, fatigue |
| **sDx: Confirmed AE Diagnosis** | A formal diagnosis or diagnosed clinical condition explicitly identified as an adverse event in the vaccination-related episode. | Annotate a diagnosed condition as **sDx** when the narrative presents it as a confirmed/established diagnosis belonging to the adverse-event episode. Use sDx rather than SYM when the text names a diagnosis rather than a symptom, and rather than DX when the diagnosis itself is part of the adverse-event outcome being reported. | diagnosed with, diagnosis of, confirmed, final diagnosis, determined to have, diagnosed as, assessment was, impression was |
| **pDx: Provisional AE Diagnosis** | A tentative, suspected, possible, or provisional diagnosis considered during evaluation of the adverse-event episode but not established as final. | Annotate a condition as **pDx** when the narrative explicitly frames it as suspected, possible, probable, provisional, differential, or otherwise uncertain during the adverse-event evaluation. Do not use pDx merely because the annotator is uncertain; uncertainty must be present in the narrative. | possible, probable, suspected, concern for, concerning for, provisional, differential diagnosis, may have, might have, could represent, likely, presumed |
| **DX: Diagnosis (Non-AE Context)** | A diagnosis or clinical condition mentioned in a diagnostic or clinical context that is not functioning as the reported adverse event, provisional AE diagnosis, medical history, or family history. | Annotate a diagnosis as **DX** when it is a current or contextual diagnosis but the narrative does not present it as the adverse event itself. Do not use DX for pre-existing conditions (MHx), family history (FHx), confirmed AEs (sDx), provisional AEs (pDx), symptoms (SYM), or diagnostic procedures. | diagnosis, diagnosed, condition, disease, disorder, assessment, impression, clinical diagnosis |
| **VAX: Vaccine** | A vaccine product, vaccination, immunization, or vaccine dose described as the administered or potentially causative exposure in the VAERS narrative. | Annotate the vaccine product/name or explicit vaccine reference when it identifies the immunization associated with the report. Annotate the vaccine entity itself, not surrounding administration verbs or temporal phrases. | vaccine, vaccination, immunization, immunized, COVID-19 vaccine, influenza vaccine, flu vaccine, Pfizer, Moderna, Janssen, dose of vaccine, shot |
| **MHx: Medical History** | A symptom, diagnosis, condition, or medical finding that pre-existed the vaccination/adverse-event episode or is explicitly described as part of the patient's past or chronic medical history. | Annotate the historical/pre-existing clinical condition itself. Do not include contextual phrases such as "history of" when the underlying condition can be separately captured. | past medical history, medical history, PMH, history of, baseline, chronic, pre-existing, underlying condition, known condition, longstanding, prior diagnosis |
| **FHx: Family History** | A disease, condition, or clinically relevant finding explicitly attributed to the patient's family members or family medical history. | Annotate the condition/finding attributed to family history. Do not classify the patient's own condition as FHx. | family history, FHx, mother had, father had, sibling had, familial, hereditary, inherited, genetic predisposition |
| **Lab: Laboratory Finding / Vital Sign** | A laboratory test, laboratory result, vital sign, physiologic measurement, or other objective measured clinical finding. | Annotate the test/measurement and its reported result when expressed as one clinically meaningful span when practical. Include normal, abnormal, positive, negative, quantitative, and qualitative findings. Include vital signs and objective measurements when they are reported as clinical findings. | laboratory, lab, level, result, value, positive, negative, elevated, decreased, normal, abnormal, CBC, WBC, hemoglobin, platelet, creatinine, glucose, temperature, blood pressure, heart rate, oxygen saturation |
| **TEMPO: Temporal Expression** | A date, time, duration, interval, relative-time phrase, latency, or other expression locating an event in time. | Annotate the temporal expression itself. Include absolute dates/times and relative expressions such as time since vaccination, onset latency, duration, or sequence timing. Do not include the clinical event unless it is inseparable from the temporal phrase. | on, at, after, before, later, same day, next day, hours later, days later, weeks later, for 3 days, since vaccination, shortly after, immediately after, date, time |
| **DOSE: Dose / Lot Information** | Vaccine dose information, dose number, amount, sequence, administration-dose descriptor, or vaccine lot/batch number. | Annotate explicit vaccine dose or lot information, including ordinal dose number and lot/batch identifier. Keep vaccine product name under VAX rather than DOSE. | first dose, second dose, third dose, booster, dose 1, dose 2, dose, dosage, lot, lot number, batch, batch number, 0.5 mL |
| **STATUS: Patient Status / Outcome** | A statement describing the patient's clinical course, disposition, recovery, persistence, worsening, hospitalization status, disability, death status, or other outcome. | Annotate the status/outcome expression itself. STATUS describes what happened to the patient or event over time, not the underlying symptom/diagnosis. | recovered, recovering, resolved, improved, worsened, stable, persistent, ongoing, hospitalized, admitted, discharged, emergency room, disability, life-threatening, outcome, died, death |
| **TX: Treatment / Provider / Intervention** | A treatment, therapeutic intervention, clinical management action, procedure used for treatment, or explicitly mentioned treating/provider service associated with management of the patient. | Annotate the treatment/intervention/provider entity or therapeutic action used to manage the patient or adverse event. Do not annotate the indication as TX. Drug names used as treatment may be included as TX when explicitly administered therapeutically. | treated with, treatment, therapy, given, administered, prescribed, managed with, IV fluids, acetaminophen, antihistamine, steroids, epinephrine, surgery, physician, provider, emergency department |
| **AGE: Patient Age** | The patient's exact or approximate age or age category during the reported vaccination/adverse-event episode. | Annotate explicit references to the patient's age or age category only when they clearly refer to the patient. | year-old, years old, aged, age, infant, child, adolescent, adult, elderly, older adult |
| **SEX: Patient Sex** | The biological sex of the patient as explicitly described in the VAERS narrative. | Annotate explicit references to the patient's biological sex only when they clearly refer to the patient. | male, female, man, woman, boy, girl |

### General Annotation Rules

1. **Use narrative context, not keyword matching.**
   Trigger words and phrases are contextual clues only. A trigger word does not automatically determine an annotation.

2. **Annotate the clinical entity, not the contextual trigger phrase.**
   Examples:
   - "history of asthma" -> annotate "asthma" as MHx.
   - "treated with acetaminophen" -> annotate "acetaminophen" as TX.
   - "two days after vaccination" -> annotate "two days after vaccination" or the smallest complete temporal expression as TEMPO, while the vaccine itself remains VAX when separately expressed.

3. **Use exact text spans.**
   Every annotated span must occur verbatim in the source narrative. Do not normalize spelling, capitalization, abbreviations, numbers, or units.

4. **Prefer the smallest complete clinically meaningful span.**
   Do not include unnecessary surrounding words, punctuation, conjunctions, or trigger phrases.

5. **Do not infer unsupported clinical relationships.**
   Use only information expressed or clearly established in the narrative. Do not infer causality, chronology, diagnosis certainty, medical history, or treatment role solely from medical knowledge.

6. **Do not annotate the same text span with multiple categories.**
   Choose the category that best represents the role of that occurrence in its local narrative context.

7. **Do not create overlapping or nested annotations.**

8. **SYM vs sDx vs pDx vs DX must follow the narrative role.**
   - SYM = symptom/sign/complaint without a formal diagnostic role.
   - sDx = established/confirmed diagnosis functioning as an adverse event in the reported episode.
   - pDx = tentative/suspected/provisional diagnosis in the adverse-event episode.
   - DX = diagnosis in a current/contextual non-AE role.
   Do not convert a symptom into a diagnosis based only on medical knowledge.

9. **sDx vs pDx is determined by diagnostic certainty expressed in the text.**
   A diagnosis is pDx only when the narrative itself indicates uncertainty, suspicion, possibility, probability, or provisional status.

10. **MHx and FHx take precedence when history is explicit.**
    - MHx = patient's own pre-existing/historical condition.
    - FHx = condition attributed to family members/family history.
    Do not relabel these occurrences as SYM, sDx, pDx, or DX solely because the same condition could be clinically relevant to the current event.

11. **VAX identifies the vaccine exposure, not the timing or dose descriptor.**
    Example: "second dose of Pfizer vaccine"
    - "second dose" -> DOSE
    - "Pfizer vaccine" -> VAX

12. **DOSE includes vaccine sequence and lot information.**
    Dose number, amount, booster designation, and lot/batch identifiers belong to DOSE when explicitly stated.

13. **TEMPO captures temporal information only.**
    Dates, times, durations, latency, and relative temporal phrases belong to TEMPO. Do not absorb the associated symptom, diagnosis, vaccine, or treatment into the temporal span unless the phrase cannot be separated without losing its meaning.

14. **Lab includes objective laboratory findings and vital signs.**
    Diagnostic labels inferred from those findings should not be added unless explicitly stated elsewhere in the narrative.

15. **STATUS describes course, disposition, or outcome.**
    Do not label the underlying symptom or diagnosis as STATUS merely because its course or outcome is discussed.

16. **TX includes therapeutic management/intervention.**
    Annotate what was done to treat or manage the patient. Do not label the condition being treated as TX.

17. **Repeated mentions may be annotated separately.**
    If the same concept appears multiple times, annotate each explicit occurrence according to its local context.

18. **Annotate only the 14 VAERS categories defined above.**
    Do not invent or add additional categories.


### Allowed Tags

Use ONLY these tags:

<SYM>...</SYM>
<SDX>...</SDX>
<PDX>...</PDX>
<DX>...</DX>
<VAX>...</VAX>
<MHX>...</MHX>
<FHX>...</FHX>
<LAB>...</LAB>
<TEMPO>...</TEMPO>
<DOSE>...</DOSE>
<STATUS>...</STATUS>
<TX>...</TX>
<AGE>...</AGE>
<SEX>...</SEX>

Do NOT create any other tag.

### In-Text Annotation Rules

1. Insert tags around the exact entity span in the original narrative.

2. Do NOT alter the original narrative in any way other than inserting
   annotation tags.

3. Preserve exactly:
   - wording
   - spelling
   - capitalization
   - punctuation
   - numbers
   - whitespace
   - paragraph structure

4. Every opening tag must have the corresponding closing tag.

5. Tags must NOT overlap or nest.

6. Annotate only the smallest complete clinically meaningful span.

7. Contextual or trigger phrases should normally remain outside the tag.

### Examples

Original:
A 45-year-old female received the second dose of Pfizer COVID-19 vaccine and developed fever and headache the next day.

Correct:
A <AGE>45-year-old</AGE> <SEX>female</SEX> received the <DOSE>second dose</DOSE> of <VAX>Pfizer COVID-19 vaccine</VAX> and developed <SYM>fever</SYM> and <SYM>headache</SYM> <TEMPO>the next day</TEMPO>.

Original:
She was diagnosed with myocarditis and treated with ibuprofen.

Correct:
She was diagnosed with <SDX>myocarditis</SDX> and treated with <TX>ibuprofen</TX>.

Original:
The emergency physician was concerned for possible myocarditis.

Correct:
The emergency physician was concerned for possible <PDX>myocarditis</PDX>.

Original:
Past medical history included asthma.

Correct:
Past medical history included <MHX>asthma</MHX>.

Original:
Temperature was 39.1 C and heart rate was 112 bpm.

Correct:
<LAB>Temperature was 39.1 C</LAB> and <LAB>heart rate was 112 bpm</LAB>.

Original:
Symptoms resolved after two days and the patient was discharged home.

Correct:
Symptoms <STATUS>resolved</STATUS> <TEMPO>after two days</TEMPO> and the patient was <STATUS>discharged home</STATUS>.

### Narrative

{text}

### CRITICAL OUTPUT REQUIREMENTS

1. Return ONLY the fully annotated narrative.
2. Do NOT add an introductory sentence such as
   "The annotated text is shown as below:".
3. Do NOT use Markdown code fences.
4. Do NOT provide explanations, comments, summaries, or lists.
5. Apart from the inserted annotation tags, every character of the
   original narrative must remain unchanged.
`
