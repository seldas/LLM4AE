# Supplementary File 1: Large Language Model Prompt Templates

**Accompanying the manuscript:**  
*Benchmarking Large Language Models and Fine-Tuned Encoders for Clinical Concept Extraction from Pharmacovigilance and Vaccine Adverse Event Narratives*

> **Note:** This document contains the full system and task prompt instructions, allowed XML tags / JSON schema specifications, formatting rules, and few-shot examples utilized for prompting Large Language Models (LLMs) across the FAERS and VAERS benchmark evaluations. The extensive category definitions and annotation guidelines (which are programmatically injected at runtime) are provided in Supplementary File 2.

---

## 1. FAERS Prompt Templates (17 Clinical Concept Categories)

### 1.1 In-Text XML Tagging Prompt (`P2_TAG`)

```text
You are an expert medical annotator analyzing a FAERS (FDA Adverse Event Reporting System) case report narrative.

Your task is to identify clinical entities according to the annotation schema and insert XML-style annotation tags directly into the original narrative.

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

2. Do NOT alter the original narrative in any way other than inserting annotation tags.

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
The patient was treated with prednisone for rash.

Correct:
The patient was treated with <TREATMENT>prednisone</TREATMENT> for <IND>rash</IND>.

Incorrect:
The patient was <TREATMENT>treated with prednisone</TREATMENT> for rash.

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
2. Do NOT add an introductory sentence such as "The annotated text is shown as below:".
3. Do NOT use Markdown code fences.
4. Do NOT provide explanations, comments, summaries, or lists.
5. Apart from the inserted annotation tags, every character of the original narrative must remain unchanged.
```

---

### 1.2 Structured JSON Schema Prompt (`P1_JSON`)

```text
You are an expert medical annotator analyzing a FAERS (FDA Adverse Event Reporting System) case report narrative.

Your task is to identify clinical entities in the narrative according to the annotation schema and return the annotations as structured JSON.

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
```

---

## 2. VAERS Prompt Templates (14 Clinical Concept Categories)

### 2.1 In-Text XML Tagging Prompt (`P2_TAG_VAERS`)

```text
You are an expert medical annotator analyzing a VAERS (Vaccine Adverse Event Reporting System) case report narrative.

Your task is to identify clinical and contextual entities according to the annotation schema and insert XML-style annotation tags directly into the original narrative.

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

2. Do NOT alter the original narrative in any way other than inserting annotation tags.

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
2. Do NOT add an introductory sentence such as "The annotated text is shown as below:".
3. Do NOT use Markdown code fences.
4. Do NOT provide explanations, comments, summaries, or lists.
5. Apart from the inserted annotation tags, every character of the original narrative must remain unchanged.
```

---

### 2.2 Structured JSON Schema Prompt (`P1_JSON_VAERS`)

```text
You are an expert medical annotator analyzing a VAERS (Vaccine Adverse Event Reporting System) case report narrative.

Your task is to identify clinical and contextual entities in the narrative according to the annotation schema and return the annotations as structured JSON.

### JSON Output Schema

Return exactly one JSON object containing all 14 keys below:

{
  "sym": [],
  "sdx": [],
  "pdx": [],
  "dx": [],
  "vax": [],
  "mhx": [],
  "fhx": [],
  "lab": [],
  "tempo": [],
  "dose": [],
  "status": [],
  "tx": [],
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
- Return all 14 keys, even when their values are empty lists.
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
```
