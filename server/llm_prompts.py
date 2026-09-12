"""
LLM Prompts and Guidelines for LLM4AE

Synchronized with publication/scripts/annotation_prompts.py
Supports:
- FAERS 17-category schema (P2_TAG in-text XML tags and P1_JSON structured output)
- VAERS 14-category schema (P2_TAG_VAERS in-text XML tags and P1_JSON_VAERS structured output)
- Tag-to-label and raw-to-canonical normalizers
"""

# ============================================================
# FAERS Shared Annotation Schema (17 categories)
# ============================================================

ANNOTATION_GUIDE = r'''
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
'''

# ============================================================
# FAERS Tagged XML Prompt (P2_TAG)
# ============================================================

P2_TAG = r'''
You are an expert medical annotator analyzing a FAERS
(FDA Adverse Event Reporting System) case report narrative.

Your task is to identify clinical entities according to the annotation
schema below and insert XML-style annotation tags directly into the
original narrative.

''' + ANNOTATION_GUIDE + r'''

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
'''

# ============================================================
# FAERS Structured JSON Prompt (P1_JSON)
# ============================================================

P1_JSON = r'''
You are an expert medical annotator analyzing a FAERS
(FDA Adverse Event Reporting System) case report narrative.

Your task is to identify clinical entities in the narrative according to
the annotation schema below and return the annotations as structured JSON.

''' + ANNOTATION_GUIDE + r'''

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
  "end": 0
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
'''

# ============================================================
# VAERS Shared Annotation Schema (11 categories)
# ============================================================

ANNOTATION_GUIDE_VAERS = r'''
### Annotation Schema

Annotate ONLY the following 11 VAERS clinical feature categories:

| Clinical Concept | Definition | Annotation Rule | Trigger Words / Phrases |
|---|---|---|---|
| **pDx: Primary Diagnosis** | Medical terms representing formal diagnoses or established diagnostic clinical concepts identified in the post-vaccination evaluation. | Annotate a medical condition as **pDx** when it appears next to trigger words indicating a formal diagnosis. Under the hierarchy rule, if a feature is first tagged as pDx, subsequent mentions keep the pDx tag even without trigger words. | diagnosed with, diagnosis of, diagnosed, DX, final diagnosis, determined to have, impression was |
| **sDx: Secondary Diagnosis (Second Level)** | Medical terms describing adverse-event conditions that developed, were experienced, or were stated/suggested during the clinical episode. | Annotate a condition as **sDx** when it appears next to trigger words indicating development, occurrence, or suggestion. Trigger words for sDx override the narrative use of the word "symptoms". | develop, developed, developing, experience, experienced, state, stated, suggest, suggested, presented with |
| **RO: Rule-out Diagnosis** | Medical conditions or diagnoses considered during evaluation but explicitly ruled out, excluded, or unsupported. | Annotate the condition or diagnosis that is explicitly ruled out or excluded. Do not annotate normal findings as RO unless an explicit rule-out statement is made. | r/o, ruled out, rule out, no evidence of, was considered but excluded, excluded |
| **SYM: Symptom / Adverse-Event Sign** | Any patient-reported symptom, sign, or adverse event manifestation that does not fall under diagnosis (pDx/sDx), rule-out, or medical history. | Annotate the symptom/sign itself when it describes clinical manifestations (e.g., pain, fever, dizziness, rash, unresponsiveness, swelling). The resolution of specific symptoms is tagged SYM, while general outcome phrases belong to STATUS. | symptom, symptoms, complained of, reported, felt, sudden drop, rash, fever, dizziness, headache, nausea, pain, swelling, weakness |
| **CoD: Cause of Death** | A specific medical disease, condition, or event explicitly identified as causing or directly contributing to the patient's death. | Annotate the stated cause of death condition (e.g., "myocardial infarction"). Do not tag the word "death" alone as CoD; general death statements are tagged STATUS. | cause of death, COD, died of, died from, death due to, fatal event |
| **Lab: Laboratory Finding** | Phrases describing the name of or denoting the qualitative/directional results of a laboratory, diagnostic instrument, or general test. | Annotate the test name and directional result modifier (e.g., "elevated creatine phosphokinase", "blood work"). Specific numeric values (e.g., "WBC: 114") are excluded from annotation. Diagnostic instruments (e.g., "campimetry", "CT scan") are tagged as Lab. | laboratory, lab, blood work, physical exam, level, elevated, decreased, positive, negative, normal, abnormal, campimetry, CT, MRI, EKG |
| **STATUS: Patient Status / Outcome** | Phrases describing a patient's overall clinical condition, hospital admission, discharge, recovery, deterioration, or death statement. | Annotate statements describing clinical course, outcome, or hospitalization (e.g., "admitted to pediatric ER", "symptoms resolved", "recovered without sequelae", "condition deteriorated", "death"). | recovered, recovering, resolved, improved, worsened, deteriorated, stable, hospitalized, admitted, discharged, ER, outcome, death, died |
| **FHx: Family History** | Medical terms, conditions, or clinically relevant findings explicitly attributed to the patient's family members or family medical history. | Annotate medical conditions associated with family members, including the specific family member designation when provided (e.g., "hypertension father", "coronary artery disease mother"). | family history, FHx, father had, mother had, sister, brother, familial, maternal, paternal |
| **MHx: Medical History** | Symptoms, conditions, diagnoses, or medical findings that pre-existed the vaccination episode or are explicitly described as past/chronic medical history. | Annotate historical/pre-existing conditions (e.g., "asthma", "depression", "high blood pressure"). Also annotate explicit statements reporting the absence of medical history (e.g., "no medical history"). | past medical history, medical history, PMH, history of, baseline, chronic, pre-existing, longstanding, prior diagnosis, no medical history |
| **TX: Drug Product / Treatment** | Any non-vaccine drug name, therapeutic substance class, or medication acronym appearing in the narrative. | Annotate any drug name or class (e.g., "atenolol", "ibuprofen", "steroid shot", "penicillin"). If both brand and generic names appear, annotate each separately. If a drug appears in an allergy phrase (e.g., SYM: "allergy to penicillin"), tag the drug name additionally as TX. Also annotate explicit statements of absence ("no other concomitant medications"). Exclude dose, manufacturer, and route. | treated with, treatment, therapy, given, administered, prescribed, atenolol, ibuprofen, prednisone, acetaminophen, penicillin, antibiotic, medication |
| **VAX: Vaccine Product** | Any vaccine product name, immunization, or vaccine strain associated with the report. | Annotate the vaccine name or specific strain (e.g., "PREVENAR 13", "INFLUVAC", "ACAM2000", "anthrax vaccine", "COVID-19 vaccine"). Include modifiers such as "vaccine", "live", or "recombinant". If a vaccine appears in an allergy phrase, tag it additionally as VAX. Exclude manufacturer, lot/batch numbers, dose number, and administration site. | vaccine, vaccination, immunization, COVID-19 vaccine, influenza vaccine, flu vaccine, PREVENAR, INFLUVAC, ACAM2000, Pfizer, Moderna, shot |

### General Annotation Rules

1. **Tag Hierarchy Precedence:**
   When assigning tags, adhere to the strict hierarchy:
   MHx / FHx > CoD > RO > pDx > sDx > SYM
   A higher-level classification always supersedes a lower-level one.

2. **Directionality & Tag Persistence:**
   Keep tag types moving forward, but not backward, in text. If a feature is first tagged as pDx, subsequent mentions retain the pDx tag even without trigger words. If first tagged as SYM and later promoted to pDx by a trigger word, the subsequent mention is tagged pDx while the earlier mention remains SYM.

3. **Punctuation Rules:**
   Do not include trailing periods, quotation marks, or surrounding parentheses in entity tags. Hyphens that form integral parts of noun phrases (e.g., "poison-ivy", "QT-interval") must be retained.

4. **Articles and Pronouns:**
   Omit noun markers ("a", "an", "the") and personal pronouns ("he", "she", "him", "her", "the patient") from entity spans.

5. **Auxiliary Verbs:**
   Exclude auxiliary verbs ("can", "could", "will", "would", "had", "was", "were", "been") unless essential for clarity in negated spans (e.g., in "did not experience anaphylaxis", include "did").

6. **Hypothetical and Conditional Statements:**
   Do not annotate hypothetical, conditional, or precautionary phrases (e.g., do not annotate "if heart palpitations worsen return to ER").

7. **Parenthetical Text:**
   - If parenthetical text contains relevant clinical concepts or acronyms (e.g., "computed tomography (CAT) scan", "Good Syndrome (GS)"), tag each entity separately without parentheses.
   - If parenthetical text contains irrelevant metadata (e.g., manufacturer name, batch numbers), do not annotate it.

8. **Inclusive Clinical Concept Spans:**
   Include all essential clinical adjectives, anatomical modifiers, negations, and syntactic modifiers within a single entity span (e.g., "coronary heart disease", "severe asthma", "no nausea", "inflammatory myopathy without inclusive bodies").

9. **Clinical Modifiers:**
   - Include modifiers indicating onset, continuation, or conclusion ("started", "began", "continued", "resolved", "became").
   - Include subjective feeling inflections ("felt tired", "feeling sick").
   - Include clinical severity descriptors ("clinically significant", "disabling").
   - Include uncertainty modifiers ("possible anaphylaxis").
   - Exclude overly general non-clinical modifiers (e.g., "routine").

10. **Associated Features:**
    In structures such as "Medical condition with [feature 1] and [feature 2]", annotate each distinct associated feature separately with the parent condition's tag type.

11. **Trigger Words:**
    Trigger words (e.g., "diagnosed", "experienced", "developed") should not be included at the beginning of an annotation, but must be preserved if they occur in the middle of a concept or in explicit statements of absence (e.g., "no medical history reported").

12. **Annotating Lists:**
    Annotate each item in a list separately while propagating shared modifiers before or after the list (e.g., "decreased muscle tone", "pallor", "altered consciousness", "drowsiness").

13. **Strict 11-Category Boundary:**
    Annotate ONLY the 11 categories defined above. Do not invent or add extraneous categories.
'''

# ============================================================
# VAERS Tagged XML Prompt (P2_TAG_VAERS)
# ============================================================

P2_TAG_VAERS = r'''
You are an expert medical annotator analyzing a VAERS
(Vaccine Adverse Event Reporting System) case report narrative.

Your task is to identify clinical entities according to the
annotation schema below and insert XML-style annotation tags directly into
the original narrative.

''' + ANNOTATION_GUIDE_VAERS + r'''

### Allowed Tags

Use ONLY these tags:

<PDX>...</PDX>
<SDX>...</SDX>
<RO>...</RO>
<SYM>...</SYM>
<COD>...</COD>
<LAB>...</LAB>
<STATUS>...</STATUS>
<FHX>...</FHX>
<MHX>...</MHX>
<TX>...</TX>
<VAX>...</VAX>

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
A 45-year-old female received the second dose of <VAX>Pfizer COVID-19 vaccine</VAX> and developed <SYM>fever</SYM> and <SYM>headache</SYM> the next day.

Original:
She was diagnosed with myocarditis and treated with ibuprofen.

Correct:
She was diagnosed with <PDX>myocarditis</PDX> and treated with <TX>ibuprofen</TX>.

Original:
The patient developed pneumonia aspiration and arrhythmia.

Correct:
The patient developed <SDX>pneumonia aspiration</SDX> and <SDX>arrhythmia</SDX>.

Original:
Final diagnoses were left thigh DVT, Pulmonary embolism ruled out.

Correct:
Final diagnoses were <PDX>left thigh DVT</PDX>, <RO>Pulmonary embolism</RO> ruled out.

Original:
Past medical history included asthma and depression.

Correct:
Past medical history included <MHX>asthma</MHX> and <MHX>depression</MHX>.

Original:
Family history included hypertension father.

Correct:
Family history included <FHX>hypertension father</FHX>.

Original:
Elevated muscle enzyme levels suggested a myopathy.

Correct:
<LAB>Elevated muscle enzyme levels</LAB> suggested a <SDX>myopathy</SDX>.

Original:
The ultimate cause of the subject's death was due to myocardial infarction.

Correct:
The ultimate cause of the subject's <STATUS>death</STATUS> was due to <COD>myocardial infarction</COD>.

Original:
Symptoms resolved after two days and the patient was discharged home.

Correct:
Symptoms <STATUS>resolved</STATUS> after two days and the patient was <STATUS>discharged home</STATUS>.

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
'''

# ============================================================
# VAERS Structured JSON Prompt (P1_JSON_VAERS)
# ============================================================

P1_JSON_VAERS = r'''
You are an expert medical annotator analyzing a VAERS
(Vaccine Adverse Event Reporting System) case report narrative.

Your task is to identify clinical entities in the narrative
according to the annotation schema below and return the annotations as
structured JSON.

''' + ANNOTATION_GUIDE_VAERS + r'''

### JSON Output Schema

Return exactly one JSON object containing all 11 keys below:

{
  "pdx": [],
  "sdx": [],
  "ro": [],
  "sym": [],
  "cod": [],
  "lab": [],
  "status": [],
  "fhx": [],
  "mhx": [],
  "tx": [],
  "vax": []
}

Each detected entity must be represented as:

{
  "text": "exact substring from narrative",
  "start": 0,
  "end": 0
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

### Completeness and Ordering Rules

- Include every supported entity occurrence found in the narrative.
- Repeated occurrences must be returned as separate objects.
- Do not collapse repeated mentions into a single object.
- If a category has no entities, return an empty list.
- Return all 11 keys, even when their values are empty lists.
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
'''

# ============================================================
# Canonical Dictionaries & Label Sets
# ============================================================

FAERS_TAGS = {
    "SDRUG", "CDRUG", "ODRUG", "DOSE", "IND", "TREATMENT", "AE", "MAE",
    "DX", "LAB", "STATUS", "RO", "COD", "MHX", "FHX", "AGE", "SEX"
}

VAERS_TAGS = {
    "PDX", "SDX", "RO", "SYM", "COD", "LAB", "STATUS", "FHX", "MHX", "TX", "VAX"
}

TAG_TO_LABEL = {
    # FAERS
    "SDRUG": "sDrug",
    "CDRUG": "cDrug",
    "ODRUG": "oDrug",
    "DOSE": "Dose",
    "IND": "IND",
    "TREATMENT": "Treatment",
    "AE": "AE",
    "MAE": "mAE",
    "DX": "Dx",
    "LAB": "Lab",
    "STATUS": "Status",
    "RO": "RO",
    "COD": "CoD",
    "MHX": "MHx",
    "FHX": "FHx",
    "AGE": "Age",
    "SEX": "Sex",
    # VAERS specific
    "PDX": "pDx",
    "SDX": "sDx",
    "SYM": "SYM",
    "VAX": "VAX",
    "TX": "TX",
}

RAW_TO_LABEL = {
    "sdrug": "sDrug", "sDrug": "sDrug", "SDRUG": "sDrug",
    "cdrug": "cDrug", "cDrug": "cDrug", "CDRUG": "cDrug",
    "odrug": "oDrug", "oDrug": "oDrug", "ODRUG": "oDrug", "drug": "oDrug", "DRUG": "oDrug",
    "dose": "Dose", "Dose": "Dose", "DOSE": "Dose",
    "ind": "IND", "IND": "IND", "Indication": "IND",
    "treatment": "Treatment", "Treatment": "Treatment", "TREATMENT": "Treatment",
    "ae": "AE", "AE": "AE",
    "mae": "mAE", "mAE": "mAE", "MAE": "mAE",
    "dx": "Dx", "Dx": "Dx", "DX": "Dx",
    "lab": "Lab", "Lab": "Lab", "LAB": "Lab",
    "status": "Status", "Status": "Status", "STATUS": "Status",
    "ro": "RO", "RO": "RO", "r/o": "RO", "R/O": "RO",
    "cod": "CoD", "CoD": "CoD", "COD": "CoD",
    "mhx": "MHx", "MHx": "MHx", "MHX": "MHx", "hx": "MHx", "HX": "MHx",
    "fhx": "FHx", "FHx": "FHx", "FHX": "FHx",
    "age": "Age", "Age": "Age", "AGE": "Age",
    "sex": "Sex", "Sex": "Sex", "SEX": "Sex",
    # VAERS
    "pdx": "pDx", "pDx": "pDx", "PDX": "pDx",
    "sdx": "sDx", "sDx": "sDx", "SDX": "sDx",
    "sym": "SYM", "SYM": "SYM", "symptom": "SYM",
    "vax": "VAX", "VAX": "VAX", "vaccine": "VAX",
    "tx": "TX", "TX": "TX",
}

# Backward compatibility aliases
annotation_guideline = ANNOTATION_GUIDE
prompt_ner_html = P2_TAG
prompt_ner_tag = P2_TAG
prompt_ner_json = P1_JSON

