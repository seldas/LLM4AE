annotation_guideline = '''
Annotation Types and Their Descriptions:
Use the following table as your reference to annotate the provided text:

| Clinical Concept/Temporal Feature | Description | Annotation Rule | Trigger Words |
|-----------------------------------|-------------|-----------------|---------------|
| SDrug | A drug or biological product believed to have caused, contributed to, or been associated with the adverse event. | The drug is explicitly linked to the AE through temporal or causal language. A clinical action was taken on the drug (e.g., discontinuation, dose adjustment). | Suspected, implicated, caused, linked to, attributed to, associated with, following administration of, resolved after stopping, symptoms worsened after increasing dose. |
| CDrug | Drugs that were concurrently administered with other drugs (e.g., suspect drugs), as part of the patient's ongoing or routine regimen. | The drug is mentioned as part of the patient's medication list and taken concurrently. The drug is mentioned as part of the patient's medication regimen but lacks a causal link to AE. | Background therapy, chronic therapy, maintained on, patient's usual medications, taken concurrently, other medications included, concomitant drug. |
| ODrug | Include drugs mentioned but not clearly linked to current adverse event, concomitant drugs or therapy, or explicit treatment purpose. Illicit substances, whether explicitly relief, supportive care, or as a response to an adverse event. | Annotate references to specific drugs (both suspect and concomitant) as "drug" when they are listed without symptoms, adverse events, or causal indicators directly linked to them. Include any references to the disposition of drugs (e.g. "Drug discontinued," "dose adjusted"). | Illicit substances, past medications, drug history, drug class, general drug references without clinical context, drug under investigation, dosage, frequency, route, supportive care, absence of treatment. |
| Dose | Explicitly stated dosage information of any drugs. | Annotate dosage quantity, frequency, adjustments, or changes. | Mg, dose, once daily, twice daily, adjusted, increased, decreased. |
| Treatment| Capture only drug products/drug administration explicitly described as treatments addressing disease, adverse events or symptoms. | Annotate drug names when explicitly stated as treatments or therapeutic measures in the narrative. | Treatment, therapy, managed by, treatment with, intervention (when drug-based). |
| AE| Any negative health outcome, condition, or symptom that could represent an adverse event, regardless of their relation to the drug or baseline status. | Annotate as Adverse Event: Diagnosed conditions and symptoms that are explicitly described as occurring during or immediately after adverse event. | Caused by, due to, result of, associated with, linked to, following, induced by, after starting, led to, Feels, reports, experiences, complains of, sensation of, unwell, discomfort, suffers from, dx, diagnosed with, developed. |
| mAE| mAE-Manifestations: immediate signs, symptoms that appear as part of the adverse event. mAE-Sequelae: consequences or complications resulting from the adverse event. | Annotate signs and symptoms that are explicitly described as occurring during or immediately after adverse event. Annotate consequences or complications resulting from the adverse event. | After taking, developed, symptoms included, resulted in, caused by, following resolution of, long-term effects included. |
| bSYM| Symptoms, conditions, or findings that existed prior to the adverse event and are unrelated to it. | Describe pre-existing conditions unrelated to the adverse event. May be chronic conditions or ongoing symptoms before AE onset. | Prior to, pre-existing, before the onset of. |
| RO | Conditions considered but ultimately ruled out as causes of symptoms or adverse events. | Annotate as Rule-Out Diagnosis if the language indicates that a condition was ruled out as a cause. | Ruled out, R/O, no evidence of, excluded. |
| Dx | Captured only the names of diagnostic procedures performed to evaluate or confirm a medical condition or diagnosis. | Annotate the procedure name (e.g. Biopsy, CT, MRI, endoscopy, ultrasound). | Imaging test: CT, MRI, ultrasound, X-ray, radiograph. Diagnostic procedures: biopsy, histopathology, colonoscopy, endoscopy. |
| CoD | Specific cause or reason for patient death that may be related to the drug. | Annotate as Cause of Death if causative language specifically attributes the death to a condition or event potentially related to the drug. | |
| Lab | Results (test named and specific results) specifically from laboratory tests indicating quantitative measurements or biochemical markers. | Annotate as Laboratory Finding if: Test and result indicators: results, level, measurement, value, findings. Test name: include test results not included/reported. | Normal and negative indicators: normal, within range, negative, unremarkable. Abnormal and positive indicators: elevated, increased, decreased, positive for, abnormal, high, low. Specific tests: names of lab tests, hemoglobin, blood test, urine analysis, serum measurement, height, weight, BMI. |
| FHx | Patient's family medical history, often related to genetic predispositions. | Annotate as Family History if the condition is described in the context of family members and not linked to drug-related events. | Family history, FHx, inherited, genetic predisposition. |
| MHx | Symptoms, conditions, or medical findings that pre-existed before the adverse event and are not caused by it. | Annotate any medical condition or symptom clearly described as present prior to the AE. | Past medical history, history of, baseline, chronic, prior diagnosis, pre-existing, known condition, underlying, previously diagnosed, maintained on. |
| IND | The reason or intended medical purpose for which a drug, treatment, or procedure is used. | Annotate as Indication if the narrative states that a drug or treatment is used for a specific condition or symptom. | Used for, given for, prescribed for, indicated for, to treat, for the management of, for prevention of, due to, because of, unknown indication, reason for use unclear. |
| Status | Captures statements about the progression or outcome of either the patient's overall clinical condition or the adverse event status after a treatment, or intervention. | Annotate as Patient Status if: Resolution or recovery, deterioration or worsening, stability or no change, long-term effects or complications. | Admitted, discharged, recovered, deteriorated, outcome, improvement, unknown, resolved, unchanged, persistent symptoms, stable. |
| Age | The age of the patient when the AE occurred or during the described event. | The age of the patient explicitly mentioned in the text. | Exact or approximate age is mentioned. Adult, older, infant, newborn. |
| Sex | The biological sex of the patient, as described in the clinical narrative. | The biological sex of the patient explicitly mentioned in the text. | Biological sex is explicitly mentioned. Boy, girl, female, male. |
| Date | Specific or partial dates provided in the text. | Annotate as Date if the text specifies an exact or partial date. | On, in, exact dates (e.g., 15-MAR-2007, November 1991, 2005). |
| Time | Specific times of day mentioned in the report. | Annotate as Time if the text specifies a clock time. | AM, PM, morning, evening, specific times (e.g., 9pm). Minutes, hours, days, weeks, months, years. |
| Duration | Length of time over which a clinical event occurs or persists. | Annotate as Duration if the text describes a time span. | |
| Relative | Time expressions relative to other events. | Annotate as Relative if the text indicates time relative to another event. | Before, after, following, within, later. |
| Latency | Refers to the time interval that occurs between an initial event and a subsequent adverse event. | Mark expressions that specify the amount of time passing between an intervention or exposure and the occurrence of an adverse event as latency. | After, within, following. |
| Temporal | Involves annotating explicit temporal markers that show the timing of adverse events. | Annotate only those parts of the text that use explicit time-related expressions indicating when an adverse event occurs in relation to others. | Hours later, days before, next morning. |

'''

prompt_ner_html= f'''**You are an expert medical annotator tasked with identifying and tagging key clinical and contextual attributes in a FAERS (FDA Adverse Event Reporting System) case report narrative. Follow these instructions meticulously:**

### ✳️ Annotation Format and Rules
1. Perform **in-text annotation** by enclosing the relevant text with appropriate XML-style tags.
2. **Do not alter the original text in any way**. Your task is solely to insert annotation tags.
3. Use capitalized tags in this format: `<TAG>relevant text</TAG>`.
4. Ensure all tags are properly opened and closed. For example: `<SDRUG>atenolol</SDRUG>`.
5. Be precise in your tag placement. Include only the specific words that correspond to the entity being tagged.

### 🏷️ Tag Types
Include a list of all possible tags here, such as SDRUG, CDRUG, AE, DATE, DOSE, etc., with a brief description of each.

### ✅ Annotation Example  
Original text:  
Concomitant medications included on an unknown date, atenolol tablet at a dose of 25 milligrams twice a day via unknown route for unknown indication.

Correctly annotated text:  
Concomitant medications included on an unknown date, atenolol tablet at a dose of 25 milligramstwice a day via unknown route for unknown indication.

### 🚫 Common Mistakes to Avoid
1. Incomplete tags (e.g., `<SDRUG>atenolol` without a closing tag)
2. Altering the original text content
3. Inconsistent capitalization of tags
4. Overlapping or nested tags

Your task is to apply these annotation principles to the provided FAERS case report narrative. Maintain accuracy and consistency throughout your annotations.
---

{annotation_guideline}

> 🔔 *Note:* Adverse Events should be tagged as `<AE>...</AE>` only when clearly distinguishable from general diagnoses.
> 🔔 *Note:* The tag can only be chosen from the first column, which is from: [SDrug, CDrug, ODrug, Dose, Treatment, AE, mAE, bSYM, RO, Dx, CoD, Lab, FHx, MHx, IND, Status, Age, Sex, Date, Time, Duration, Relative, Latency, Temporal].
    DO NOT add other tags.
---

### 📝 Output Instructions  
- Begin your output with:  
  The annotated text is shown as below:  
- Follow this with the full narrative, inserting only the annotation tags where appropriate.
- Ensure **the original text structure and punctuation remain unchanged** aside from the added tags.

'''

prompt_ner_json = '''
You are an expert medical annotator tasked with identifying and tagging key clinical and contextual attributes in a FAERS (FDA Adverse Event Reporting System) case report narrative. Follow these instructions meticulously:**

### ✳️ Annotation Format and Rules
1. Perform **in-text annotation** by enclosing the relevant text with appropriate XML-style tags.
2. **Do not alter the original text in any way**. Your task is solely to insert annotation tags.
3. Use capitalized tags in this format: `<TAG>relevant text</TAG>`.
4. Ensure all tags are properly opened and closed. For example: `<SDRUG>atenolol</SDRUG>`.
5. Be precise in your tag placement. Include only the specific words that correspond to the entity being tagged.

### 🏷️ Tag Types
Include a list of all possible tags here, such as SDRUG, CDRUG, AE, DATE, DOSE, etc., with a brief description of each.

### ✅ Annotation Example  
Original text:  
Concomitant medications included on an unknown date, atenolol tablet at a dose of 25 milligrams twice a day via unknown route for unknown indication.

Correctly annotated text:  
Concomitant medications included on an unknown date, atenolol tablet at a dose of 25 milligramstwice a day via unknown route for unknown indication.

### 🚫 Common Mistakes to Avoid
1. Incomplete tags (e.g., `<SDRUG>atenolol` without a closing tag)
2. Altering the original text content
3. Inconsistent capitalization of tags
4. Overlapping or nested tags

Your task is to apply these annotation principles to the provided FAERS case report narrative. Maintain accuracy and consistency throughout your annotations.
---

{annotation_guideline}

> 🔔 *Note:* Adverse Events should be tagged as `<AE>...</AE>` only when clearly distinguishable from general diagnoses.
> 🔔 *Note:* The tag can only be chosen from the first column, which is from: [SDrug, CDrug, ODrug, Dose, Treatment, AE, mAE, bSYM, RO, Dx, CoD, Lab, FHx, MHx, IND, Status, Age, Sex, Date, Time, Duration, Relative, Latency, Temporal].
    DO NOT add other tags.
---

OUTPUT (STRICT):
Return ONLY valid JSON (no prose, no markdown fences) in this exact shape:
{{
  "annotated_text": "<string>"
}}
'''.format(annotation_guideline=annotation_guideline)

prompt_ner_simple_json = '''
You are an expert medical annotator for FAERS narratives.

Goal:
- Extract all clinical concepts and temporal features from the narrative.
- Return a simple list of entities found.

CRITICAL RULES:
- Return ONLY valid JSON.
- Do NOT return the original or annotated narrative text.
- Each object in the list must have "label" and "text".
- Labels must be one of:
  [SDrug, CDrug, ODrug, Dose, Treatment, AE, mAE, bSYM, RO, Dx, CoD, Lab, FHx, MHx, IND, Status, Age, Sex, Date, Time, Duration, Relative, Latency, Temporal]

{annotation_guideline}

OUTPUT (STRICT):
Return ONLY a JSON object with a key "entities" containing the list:
{{
  "entities": [
    {{"label":"AE", "text":"..."}},
    {{"label":"SDrug", "text":"..."}},
    ...
  ]
}}
'''.format(annotation_guideline=annotation_guideline)
