#!/usr/bin/env python3
"""
generate_supplementary_files_2_3.py

Generates publication-quality Supplementary Excel Files:
- Supplementary File 2: FAERS Clinical Concept Annotation Guidance (17 Categories)
- Supplementary File 3: VAERS Vaccine Adverse Event Annotation Guidance (14 Categories)

Each workbook contains:
1. Cover Sheet: Metadata, Study Context, and Category Summary
2. Annotation Schema: Comprehensive category-level definitions, rules, trigger words, and examples
3. General Annotation Principles: Operational guidelines and edge-case resolution rules
"""

from __future__ import annotations

from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ==============================================================================
# STYLING HELPER FUNCTIONS
# ==============================================================================

def get_header_fill():
    return PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")  # Navy Blue

def get_accent_fill():
    return PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")  # Soft Ice Blue

def get_zebra_fill():
    return PatternFill(start_color="FBFBFB", end_color="FBFBFB", fill_type="solid")

def get_white_fill():
    return PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

def get_thin_border():
    thin = Side(border_style="thin", color="D0D5DD")
    return Border(left=thin, right=thin, top=thin, bottom=thin)

def style_cover_sheet(ws, title: str, subtitle: str, metadata_rows: list[tuple[str, str]]):
    ws.views.sheetView[0].showGridLines = True
    
    # Title Banner
    ws.merge_cells("B2:G2")
    ws["B2"] = title
    ws["B2"].font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    ws["B2"].fill = get_header_fill()
    ws["B2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 36

    # Subtitle
    ws.merge_cells("B3:G3")
    ws["B3"] = subtitle
    ws["B3"].font = Font(name="Calibri", size=11, italic=True, color="4A5568")
    ws["B3"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[3].height = 24

    # Metadata Table
    start_row = 5
    for idx, (label, val) in enumerate(metadata_rows):
        row = start_row + idx
        ws.row_dimensions[row].height = 22
        
        c_label = ws.cell(row=row, column=2, value=label)
        c_label.font = Font(name="Calibri", size=10.5, bold=True, color="1B365D")
        c_label.fill = get_accent_fill()
        c_label.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        c_label.border = get_thin_border()

        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=7)
        c_val = ws.cell(row=row, column=3, value=val)
        c_val.font = Font(name="Calibri", size=10, color="2D3748")
        c_val.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
        
        for col in range(3, 8):
            ws.cell(row=row, column=col).border = get_thin_border()

    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 26
    for col in ["C", "D", "E", "F", "G"]:
        ws.column_dimensions[col].width = 16


def create_schema_sheet(ws, title: str, headers: list[str], data: list[list[str]], col_widths: list[float]):
    ws.views.sheetView[0].showGridLines = True
    
    # Title
    ws.merge_cells(start_row=2, start_column=2, end_row=2, end_column=len(headers) + 1)
    ws["B2"] = title
    ws["B2"].font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    ws["B2"].fill = get_header_fill()
    ws["B2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 30

    # Header Row
    ws.row_dimensions[4].height = 26
    for c_idx, h in enumerate(headers, start=2):
        cell = ws.cell(row=4, column=c_idx, value=h)
        cell.font = Font(name="Calibri", size=10.5, bold=True, color="FFFFFF")
        cell.fill = get_header_fill()
        cell.alignment = Alignment(horizontal="center" if c_idx in [2, 4] else "left", vertical="center", wrap_text=True)
        cell.border = get_thin_border()

    # Data Rows
    for r_idx, row_values in enumerate(data, start=5):
        ws.row_dimensions[r_idx].height = 65  # Room for multi-line description
        fill = get_zebra_fill() if r_idx % 2 == 1 else get_white_fill()
        
        for c_idx, val in enumerate(row_values, start=2):
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.font = Font(name="Calibri", size=9.5, bold=(c_idx in [2, 3]))
            cell.fill = fill
            cell.border = get_thin_border()
            cell.alignment = Alignment(
                horizontal="center" if c_idx in [2, 4] else "left",
                vertical="top",
                wrap_text=True
            )

    # Column Widths
    ws.column_dimensions["A"].width = 3
    for c_idx, width in enumerate(col_widths, start=2):
        col_letter = get_column_letter(c_idx)
        ws.column_dimensions[col_letter].width = width


def create_rules_sheet(ws, title: str, rules: list[tuple[str, str, str]], col_widths: list[float]):
    ws.views.sheetView[0].showGridLines = True
    
    # Title
    ws.merge_cells(start_row=2, start_column=2, end_row=2, end_column=4)
    ws["B2"] = title
    ws["B2"].font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    ws["B2"].fill = get_header_fill()
    ws["B2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 30

    # Headers
    headers = ["Rule # & Principle", "Operational Annotation Rule & Clinical Rationale", "Illustrative Case Examples"]
    ws.row_dimensions[4].height = 26
    for c_idx, h in enumerate(headers, start=2):
        cell = ws.cell(row=4, column=c_idx, value=h)
        cell.font = Font(name="Calibri", size=10.5, bold=True, color="FFFFFF")
        cell.fill = get_header_fill()
        cell.alignment = Alignment(horizontal="center" if c_idx == 2 else "left", vertical="center", wrap_text=True)
        cell.border = get_thin_border()

    # Data Rows
    for r_idx, (r_name, r_desc, r_ex) in enumerate(rules, start=5):
        ws.row_dimensions[r_idx].height = 55
        fill = get_zebra_fill() if r_idx % 2 == 1 else get_white_fill()
        
        c2 = ws.cell(row=r_idx, column=2, value=r_name)
        c2.font = Font(name="Calibri", size=9.5, bold=True, color="1B365D")
        c2.fill = fill
        c2.border = get_thin_border()
        c2.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

        c3 = ws.cell(row=r_idx, column=3, value=r_desc)
        c3.font = Font(name="Calibri", size=9.5)
        c3.fill = fill
        c3.border = get_thin_border()
        c3.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

        c4 = ws.cell(row=r_idx, column=4, value=r_ex)
        c4.font = Font(name="Calibri", size=9.0, italic=True)
        c4.fill = fill
        c4.border = get_thin_border()
        c4.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    ws.column_dimensions["A"].width = 3
    for c_idx, width in enumerate(col_widths, start=2):
        col_letter = get_column_letter(c_idx)
        ws.column_dimensions[col_letter].width = width


# ==============================================================================
# FAERS DATA (17 CATEGORIES)
# ==============================================================================

FAERS_SCHEMA_DATA = [
    [
        "sDrug",
        "Suspect Drug Products",
        "<SDRUG>",
        "A drug or biological product believed to have caused, contributed to, or been associated with the reported adverse event. Often discontinued, modified, interrupted, or rechallenged. May have explicit causal language linking it to the AE.",
        "Annotate a drug as sDrug when it is explicitly or strongly linked to the AE through causal, temporal, or attribution language. Clinical dechallenge (stopping/reducing drug) or rechallenge actions supporting causality also qualify.",
        "suspected, suspect, implicated, caused, linked to, attributed to, associated with, following administration of, after starting, induced by, resolved after stopping, dechallenge, rechallenge",
        "• '...patient experienced severe rash after starting azacitidine [sDrug]'\n• '...hypoglycemia suspected to be caused by tramadol [sDrug]'",
        "Do not annotate concomitant chronic medications as sDrug unless explicitly implicated in causing the current AE."
    ],
    [
        "cDrug",
        "Concomitant Drug Products",
        "<CDRUG>",
        "Drugs that were concurrently administered with other drugs (e.g., suspect drugs), as part of the patient's ongoing or routine regimen. May include chronic medications, maintenance therapy, or background treatments.",
        "Annotate a drug as cDrug when described as taken concurrently with the suspect drug or as part of ongoing regimen, without sufficient evidence to classify as suspect drug or rescue treatment.",
        "concomitant, concomitant medication, background therapy, chronic therapy, maintenance therapy, maintained on, patient's usual medications, home medications, taken concurrently",
        "• 'Concomitant medications included lisinopril [cDrug] and atorvastatin [cDrug]'\n• '...maintained on background metformin [cDrug]'",
        "If a drug was initiated specifically to treat an AE, annotate as Treatment, not cDrug."
    ],
    [
        "oDrug",
        "Other Drug Products",
        "<ODRUG>",
        "Drugs mentioned but not clearly linked to the current adverse event, concomitant therapy, or an explicit treatment purpose. Includes illicit substances, prior historical drug use, or drug class references without a specified current clinical role.",
        "Annotate a drug or substance as oDrug when mentioned but cannot be reliably classified as sDrug, cDrug, or Treatment. Include historical drug exposure, general drug class references, and recreational/illicit substances.",
        "illicit substances, recreational drug, substance use, past medications, previous medication, drug history, prior drug use, drug class, general drug reference, investigational drug",
        "• 'The patient had a history of cocaine [oDrug] use'\n• '...previously received multiple NSAIDs [oDrug] in childhood'",
        "Do not use oDrug if the drug's role as suspect, concomitant, or treatment is explicitly stated."
    ],
    [
        "Dose",
        "Dose Administered",
        "<DOSE>",
        "Explicitly stated dosage information, strength, quantity, frequency, administration regimen, or stated dose adjustment associated with a drug product.",
        "Annotate the dosage information itself, not the drug name. Capture strength, unit, route descriptor, frequency, and dose modification descriptors when expressed together.",
        "mg, mcg, g, mL, units, dose, dosage, once daily, twice daily, BID, TID, weekly, increased to, decreased to, reduced, titrated",
        "• '...started on azacitidine 75 mg/m2 daily [Dose] for 7 days'\n• '...tramadol 50 mg every 6 hours [Dose]'",
        "Do not include the drug name inside the Dose tag; keep drug name under sDrug/cDrug/Treatment."
    ],
    [
        "IND",
        "Indication",
        "<IND>",
        "The disease, condition, symptom, or intended medical purpose for which a drug, treatment, or procedure was prescribed, administered, or indicated.",
        "Annotate the condition, symptom, disease, or stated reason for which a drug or treatment was given. Include explicitly stated unknown or unspecified indications when clearly identified.",
        "used for, given for, prescribed for, indicated for, to treat, for treatment of, for the management of, for prevention of, indication, reason for use",
        "• 'Baricitinib was prescribed for rheumatoid arthritis [IND]'\n• '...erenumab indicated for migraine prophylaxis [IND]'",
        "IND is the reason for medication; do not confuse with AE (the unwanted outcome) or Treatment (the therapy)."
    ],
    [
        "Treatment",
        "Drug Used for Treatment",
        "<TREATMENT>",
        "Drug products or medications explicitly described as treatments administered therapeutically to manage a disease, adverse event, complication, or symptom.",
        "Annotate a drug as Treatment only when explicitly administered or used therapeutically to manage a condition or rescue from an AE. Do not classify a drug as Treatment merely because it appears in a general medication list.",
        "treated with, treatment with, therapy with, was given, administered for, managed with, received, started on, prescribed to treat, rescue medication, supportive therapy",
        "• 'The patient was treated with intravenous methylprednisolone [Treatment] for acute hypersensitivity'\n• '...received dextrose [Treatment] for severe hypoglycemia'",
        "Pre-existing background medications belong to cDrug; only drugs given therapeutically to manage conditions/events are Treatment."
    ],
    [
        "AE",
        "Adverse Event",
        "<AE>",
        "Any untoward medical occurrence, negative health outcome, condition, sign, or symptom that represents a reported adverse event, regardless of proven causality.",
        "Annotate clinically relevant negative health outcomes, diagnosed conditions, signs, or patient-reported symptoms representing an adverse event. Proven drug causality is not required.",
        "adverse event, developed, experienced, complained of, reports, diagnosed with, presented with, onset of, occurred, after starting, suffered, toxicity",
        "• '...patient developed QT prolongation [AE] and syncope [AE]'\n• '...experienced an acute anaphylactic reaction [AE]'",
        "Pre-existing conditions described as medical history belong to MHx, not AE."
    ],
    [
        "mAE",
        "AE Manifestations / Sequelae",
        "<MAE>",
        "Immediate signs or symptoms occurring as explicit clinical manifestations of an identified AE, or secondary consequences, complications, and persistent sequelae resulting from an AE.",
        "Annotate a sign, symptom, clinical finding, or complication as mAE only when the narrative explicitly establishes it as a manifestation, complication, consequence, or sequela of another identified AE.",
        "manifested as, symptoms included, characterized by, accompanied by, resulted in, complicated by, complication of, led to, secondary to, sequela, persistent",
        "• '...developed severe hypoglycemia [AE] manifested by diaphoresis [mAE] and tremors [mAE]'\n• '...suffered a stroke [AE] resulting in hemiparesis [mAE]'",
        "Do not infer mAE solely from medical intuition; explicit narrative link (e.g. 'manifested by', 'resulting in') is required."
    ],
    [
        "Dx",
        "Diagnostic Procedure",
        "<DX>",
        "The name of a diagnostic imaging, endoscopic, electrophysiologic, biopsy, or exploratory procedure performed to evaluate or confirm a medical condition.",
        "Annotate the diagnostic procedure itself. Do not annotate its resulting diagnosis or interpretation as Dx. Laboratory blood/urine tests belong under Lab.",
        "CT, CT scan, MRI, ultrasound, X-ray, radiograph, biopsy, histopathology, colonoscopy, endoscopy, echocardiogram, ECG, EKG, PET scan, angiography",
        "• 'An emergency ECG [Dx] revealed prolonged QTc interval'\n• '...underwent brain MRI [Dx] confirming acute ischemia'",
        "ECG/MRI/Biopsy are Dx; quantitative test values (e.g., QTc 520 ms) belong to Lab; the diagnosis (stroke) belongs to AE/sDx."
    ],
    [
        "Lab",
        "Laboratory Finding",
        "<LAB>",
        "Laboratory tests, clinical measurements, or quantitative/qualitative findings indicating objective clinical measurements (blood, urine, vitals, biomarkers, BMI, height, weight).",
        "Annotate laboratory test names and explicitly reported laboratory measurements/results, including normal, abnormal, elevated, positive, or negative findings.",
        "result, level, value, measurement, elevated, increased, decreased, high, low, abnormal, normal, positive, negative, hemoglobin, platelet count, WBC, ALT, AST, creatinine, glucose, QTc",
        "• 'Serum glucose was 32 mg/dL [Lab]'\n• '...platelet count dropped to 18,000/mcL [Lab]'\n• '...ALT elevated at 450 U/L [Lab]'",
        "Diagnostic imaging procedures (CT, MRI) belong to Dx; quantitative lab tests and numeric values belong to Lab."
    ],
    [
        "Status",
        "Patient Status / Outcome",
        "<STATUS>",
        "Statements describing progression, clinical course, disposition, or outcome of the patient's overall clinical condition or adverse event following intervention.",
        "Annotate clinical course, recovery, deterioration, stability, persistence, hospitalization, admission, or discharge. Status describes what happened to the patient/event over time.",
        "recovered, resolved, improved, worsened, deteriorated, stable, unchanged, persistent, ongoing, outcome, admitted, discharged, hospitalized, asymptomatic, in remission",
        "• 'Symptoms completely resolved [Status] within 48 hours'\n• '...the patient was admitted to the ICU [Status] in critical condition [Status]'",
        "Do not label the underlying disease name as Status; annotate the recovery/outcome descriptor itself."
    ],
    [
        "R/O",
        "Rule-out Diagnosis",
        "<RO>",
        "Conditions, diseases, or differential diagnoses explicitly considered by clinicians but ultimately ruled out, excluded, or determined unsupported by findings.",
        "Annotate the condition or diagnosis that is explicitly ruled out or excluded. Do not classify a condition as R/O merely because a test is negative unless explicitly stated as excluded.",
        "ruled out, rule out, R/O, excluded, no evidence of, was considered but excluded, unlikely, not consistent with, negative for",
        "• 'Infectious etiology was ruled out [R/O: infectious etiology]'\n• '...CT showed no evidence of intracranial hemorrhage [R/O: intracranial hemorrhage]'",
        "Annotate the excluded disease concept, not the trigger phrase 'ruled out'."
    ],
    [
        "CoD",
        "Cause of Death",
        "<COD>",
        "A specific disease, condition, event, or clinical mechanism explicitly identified as causing or contributing to the patient's death.",
        "Annotate the stated cause or contributing cause of death. Do not annotate the single word 'death' alone unless it represents the stated causal concept.",
        "cause of death, died from, died of, death due to, death secondary to, succumbed to, resulted in death, fatal outcome attributed to",
        "• 'The patient died from refractory cardiogenic shock [CoD]'\n• '...autopsy revealed massive pulmonary embolism [CoD] as the cause of death'",
        "The fact of death/mortality status belongs to Status ('died'); the specific etiologic disease causing death is CoD."
    ],
    [
        "MHx",
        "Medical History",
        "<MHX>",
        "Symptoms, conditions, diseases, or medical findings that pre-existed before the current adverse event and were not caused by the suspect medication.",
        "Annotate the pre-existing or historical clinical condition itself. Do not include contextual phrases such as 'history of' when the condition can be captured separately.",
        "past medical history, medical history, PMH, history of, baseline, chronic, prior diagnosis, pre-existing, underlying condition, known condition, longstanding",
        "• 'Past medical history was notable for type 2 diabetes [MHx] and hypertension [MHx]'\n• '...a known history of severe asthma [MHx]'",
        "Acute events occurring after drug initiation belong to AE; baseline pre-existing diseases belong to MHx."
    ],
    [
        "FHx",
        "Family History",
        "<FHX>",
        "Medical conditions, genetic disorders, or clinically relevant findings explicitly attributed to the patient's family members or family pedigree.",
        "Annotate the disease, condition, or relevant finding attributed to family history. Do not classify the patient's own medical history as FHx.",
        "family history, FHx, mother had, father had, sibling had, family pedigree, familial, inherited, hereditary, genetic predisposition",
        "• 'Family history was significant for early myocardial infarction [FHx] in father'\n• '...maternal aunt had breast cancer [FHx]'",
        "Only diseases in family members qualify as FHx; the patient's own history is MHx."
    ],
    [
        "Age",
        "Patient Age",
        "<AGE>",
        "The age or age category of the patient during the described adverse event episode.",
        "Annotate explicit references to the patient's exact age, age in years/months/days, or age category (pediatric, elderly). Annotate only references clearly applying to the patient.",
        "year-old, years old, aged, age, adult, elderly, adolescent, child, pediatric, infant, newborn, neonate, octogenarian",
        "• 'A 64-year-old [Age] male presented with...'\n• '...in an elderly [Age] patient with renal failure'",
        "Do not annotate age mentions of relatives or other non-patient individuals."
    ],
    [
        "Sex",
        "Patient Sex",
        "<SEX>",
        "The biological sex or gender designation of the patient as explicitly described in the clinical narrative.",
        "Annotate explicit references to the patient's biological sex. Annotate only when the reference clearly applies to the patient.",
        "male, female, man, woman, boy, girl, gentleman, lady",
        "• 'A 45-year-old female [Sex] was admitted...'\n• '...the gentleman [Sex] experienced severe dizziness'",
        "Do not annotate gender words referring to clinicians, family members, or bystanders."
    ]
]

FAERS_GENERAL_RULES = [
    ("1. Contextual Role over Keyword Matching", "Trigger words and phrases serve as contextual clues only; they do not automatically dictate an entity category. The annotator must evaluate the semantic and clinical role of each word in its specific narrative sentence.", "Example: 'Rash' is an AE when occurring after medication, an IND when stated as the reason for treatment, and an MHx when reported in baseline history."),
    ("2. Minimal Clinically Meaningful Span", "Annotate the smallest complete clinically informative span. Exclude unnecessary surrounding articles, conjunctions, prepositions, and contextual verbs.", "Correct: 'treated with <TREATMENT>prednisone</TREATMENT>'\nIncorrect: '<TREATMENT>treated with prednisone</TREATMENT>'"),
    ("3. Verbatim Exact Offsets", "Every annotated span must match the source text character-by-character without spelling normalization, punctuation alteration, case folding, or lemmatization.", "Preserve exact narrative characters: 'azacitidine 75mg/m2' must not be expanded or corrected."),
    ("4. Non-Overlapping & Non-Nested Policy", "No text span may be assigned multiple overlapping or nested entity tags. If a phrase contains multiple concepts, choose the most specific primary role or segment into adjacent distinct spans.", "In 'atenolol 25 mg', segment as '<CDRUG>atenolol</CDRUG> <DOSE>25 mg</DOSE>' rather than one nested tag."),
    ("5. Drug Precedence Hierarchy", "Every drug mention must be resolved into exactly one of four mutually exclusive roles: (a) sDrug if suspect/implicated, (b) Treatment if administered to treat a condition/AE, (c) cDrug if concurrent/background regimen, or (d) oDrug if role is unspecified or historical.", "A drug given in emergency for anaphylaxis is Treatment; the cancer chemotherapy suspected of causing anaphylaxis is sDrug."),
    ("6. AE vs. mAE Causality Constraint", "Classify as mAE only when the narrative explicitly articulates a direct manifestation, secondary complication, or sequela relationship to a parent AE (e.g., 'manifested by', 'complicated by').", "Do not infer mAE based solely on pathophysiology without textual linkage."),
    ("7. Temporal Separation: AE vs. MHx", "A condition described as baseline, chronic, longstanding, or pre-existing prior to suspect medication initiation must be classified as MHx, whereas acute onset conditions post-administration are AE.", "Baseline 'chronic kidney disease' = MHx; acute post-dose 'renal failure' = AE."),
    ("8. Indication (IND) vs. Treatment Disambiguation", "IND is the underlying pathology or clinical purpose motivating medication use, whereas Treatment is the therapeutic agent or intervention applied.", "In 'prednisone for eczema', 'prednisone' is Treatment and 'eczema' is IND."),
    ("9. Diagnostic Procedure (Dx) vs. Laboratory Finding (Lab)", "Dx refers to imaging, exploratory procedures, endoscopies, and biopsies. Lab refers to clinical measurements, serum/urine tests, vital signs, quantitative values, and laboratory interpretation.", "ECG is Dx; QTc interval 510 ms is Lab."),
    ("10. Patient Status vs. Underlying Disease", "Status captures recovery trajectory, clinical course, admission, and discharge disposition. Do not annotate the disease name itself as Status.", "In 'the patient fully recovered from hepatitis', 'recovered' is Status; 'hepatitis' is AE.")
]


# ==============================================================================
# VAERS DATA (14 CATEGORIES)
# ==============================================================================

VAERS_SCHEMA_DATA = [
    [
        "SYM",
        "Symptom / AE Sign",
        "<SYM>",
        "A patient-reported symptom, physical sign, complaint, or clinical manifestation occurring post-vaccination that is not presented as a formal diagnosed disease entity.",
        "Annotate the symptom or sign itself when described as experienced, observed, reported, or developed in the post-vaccine adverse event context. Prefer SYM for manifestations such as pain, fever, dizziness, swelling, or nausea.",
        "symptom, symptoms, complained of, reported, experienced, developed, presented with, pain, fever, dizziness, rash, swelling, weakness, nausea, headache, fatigue, chills",
        "• 'Developed severe injection-site pain [SYM] and high fever [SYM]'\n• '...complained of headache [SYM], fatigue [SYM], and nausea [SYM]'",
        "If a formal clinical diagnosis is confirmed by a physician (e.g. myocarditis), annotate as sDx, not SYM."
    ],
    [
        "sDx",
        "Confirmed AE Diagnosis",
        "<SDX>",
        "A formal medical diagnosis or diagnosed clinical condition explicitly confirmed and identified as an adverse event in the vaccination-related episode.",
        "Annotate a diagnosed condition as sDx when the narrative presents it as an established, confirmed, or final diagnosis resulting from the post-vaccination episode.",
        "diagnosed with, diagnosis of, confirmed, final diagnosis, determined to have, diagnosed as, assessment was, impression was, discharge diagnosis",
        "• 'The cardiologist confirmed a diagnosis of acute myocarditis [sDx]'\n• '...hospitalized and diagnosed with Guillain-Barré syndrome [sDx]'",
        "Pre-existing baseline diagnoses belong to MHx; diagnoses not presented as AEs belong to DX."
    ],
    [
        "pDx",
        "Provisional AE Diagnosis",
        "<PDX>",
        "A tentative, suspected, possible, probable, or differential diagnosis considered during medical evaluation of the adverse event episode but not confirmed as final.",
        "Annotate a condition as pDx when the narrative explicitly frames it with clinical uncertainty, suspicion, or provisional differential status during adverse event workup.",
        "possible, probable, suspected, concern for, concerning for, provisional, differential diagnosis, may have, might have, could represent, likely, presumed, rule out",
        "• 'Emergency physician documented concern for possible pericarditis [pDx]'\n• '...admitted for suspected transverse myelitis [pDx]'",
        "Uncertainty must be explicitly stated in the narrative; do not assign pDx based on reader skepticism."
    ],
    [
        "DX",
        "Diagnosis (Non-AE Context)",
        "<DX>",
        "A current or contextual medical diagnosis mentioned in the narrative that is not functioning as the reported post-vaccine adverse event, provisional AE, medical history, or family history.",
        "Annotate a diagnosis as DX when it is a current or incidental clinical diagnosis but not described as an adverse event resulting from the vaccination.",
        "diagnosis, diagnosed, condition, disease, disorder, assessment, impression, incidental diagnosis",
        "• 'Incidental chest X-ray finding of cardiomegaly [DX]'\n• '...patient also had concurrent osteoarthritis [DX]'",
        "Do not use DX for pre-existing history (MHx), confirmed AEs (sDx), or provisional AEs (pDx)."
    ],
    [
        "VAX",
        "Vaccine Product",
        "<VAX>",
        "A vaccine product name, immunization, biological vaccine, or specific vaccine brand described as the administered or potentially causative exposure.",
        "Annotate the vaccine product entity itself. Do not include administration verbs ('injected with') or dose numbers ('dose 2') inside the VAX tag.",
        "vaccine, vaccination, immunization, COVID-19 vaccine, influenza vaccine, flu shot, Pfizer, Moderna, Janssen, Comirnaty, Spikevax, Shingrix, MMR",
        "• 'Received the Moderna COVID-19 vaccine [VAX] in left deltoid'\n• '...administered annual influenza vaccine [VAX]'",
        "Keep ordinal dose descriptors ('first dose') under DOSE; annotate vaccine brand under VAX."
    ],
    [
        "MHx",
        "Medical History",
        "<MHX>",
        "A disease, symptom, allergy, or clinical condition that pre-existed prior to the vaccination episode or is explicitly described as past/chronic medical history.",
        "Annotate the historical/pre-existing condition itself. Exclude contextual trigger phrases such as 'history of' when the condition can be captured separately.",
        "past medical history, medical history, PMH, history of, baseline, chronic, pre-existing, underlying condition, known condition, longstanding, prior diagnosis",
        "• 'Medical history was significant for allergic rhinitis [MHx] and asthma [MHx]'\n• '...patient had a history of hypertension [MHx]'",
        "Acute post-vaccination reactions belong to SYM/sDx; pre-existing baseline diseases belong to MHx."
    ],
    [
        "FHx",
        "Family History",
        "<FHX>",
        "A disease, medical condition, or clinically relevant finding explicitly attributed to the patient's family members or pedigree.",
        "Annotate the disease or finding attributed to family history. Do not classify the patient's own medical history as FHx.",
        "family history, FHx, mother had, father had, sibling had, familial, hereditary, inherited, genetic predisposition",
        "• 'Family history of autoimmune thyroid disease [FHx] in mother'\n• '...brother had sudden cardiac death [FHx]'",
        "Only family members' health events belong to FHx; patient's own history is MHx."
    ],
    [
        "Lab",
        "Laboratory Finding / Vital Sign",
        "<LAB>",
        "Laboratory tests, laboratory results, vital signs, physiologic measurements, or objective physical findings (blood tests, vitals, temperature, heart rate, BP, O2 sat).",
        "Annotate the test name, vital sign, and reported quantitative/qualitative result when expressed together as a clinically meaningful span.",
        "laboratory, lab, level, result, value, positive, negative, elevated, decreased, normal, abnormal, CBC, WBC, troponin, creatinine, temperature, blood pressure, heart rate, SpO2",
        "• 'Troponin I was elevated at 4.2 ng/mL [Lab]'\n• '...temperature was 39.4 C [Lab] and heart rate was 120 bpm [Lab]'",
        "Diagnostic interpretations (e.g. 'myocarditis') belong to sDx/pDx; numerical vitals and lab numbers belong to Lab."
    ],
    [
        "TEMPO",
        "Temporal Expression",
        "<TEMPO>",
        "A date, time, duration, interval, latency, relative-time phrase, or temporal marker locating an event or clinical change in time.",
        "Annotate the temporal expression itself. Capture relative time post-vaccination, duration of symptoms, and onset dates.",
        "on, at, after, before, later, same day, next day, hours later, days later, weeks later, for 3 days, since vaccination, shortly after, immediately after, date, time",
        "• 'Symptoms started 4 hours after vaccination [TEMPO]'\n• '...fever persisted for 5 days [TEMPO]'\n• '...on October 12, 2021 [TEMPO]'",
        "Annotate the timing expression only; do not absorb the clinical symptom into the TEMPO tag."
    ],
    [
        "DOSE",
        "Dose / Lot Information",
        "<DOSE>",
        "Vaccine dose number, sequence, ordinal descriptor, booster indicator, amount, volume, or manufacturer lot/batch number.",
        "Annotate explicit dose numbers (dose 1, dose 2, booster), amount (0.5 mL), and lot/batch strings.",
        "first dose, second dose, third dose, booster, dose 1, dose 2, dose, dosage, lot, lot number, batch, batch number, 0.5 mL, 0.3 mL",
        "• 'Administered the second dose [DOSE] from lot #EW0182 [DOSE]'\n• '...received a 0.5 mL booster dose [DOSE]'",
        "Vaccine product name belongs to VAX; dose number and lot code belong to DOSE."
    ],
    [
        "STATUS",
        "Patient Status / Outcome",
        "<STATUS>",
        "Statements describing the patient's clinical progression, disposition, recovery, persistence, worsening, hospitalization, emergency room visit, disability, or death.",
        "Annotate the status or outcome expression itself. STATUS describes what happened to the patient over time.",
        "recovered, recovering, resolved, improved, worsened, stable, persistent, ongoing, hospitalized, admitted, discharged, emergency room, disability, life-threatening, died",
        "• 'The patient was admitted to the hospital [STATUS] and later fully recovered [STATUS]'\n• '...symptoms remain persistent [STATUS] at 6-month follow-up'",
        "Annotate the outcome/disposition words; the symptom names belong to SYM."
    ],
    [
        "TX",
        "Treatment / Intervention / Provider",
        "<TX>",
        "Therapeutic interventions, medical procedures, rescue medications, clinical management actions, or mentioned treating healthcare provider services.",
        "Annotate the treatment entity, drug given for therapy, intervention, or treating healthcare provider service.",
        "treated with, treatment, therapy, given, administered, prescribed, managed with, IV fluids, acetaminophen, steroids, epinephrine, intubated, physician, emergency department",
        "• 'Treated in the emergency department [TX] with diphenhydramine [TX] and dexamethasone [TX]'\n• '...received epinephrine auto-injector [TX]'",
        "The reason for treatment is not TX; the therapy, drug, or provider service is TX."
    ],
    [
        "AGE",
        "Patient Age",
        "<AGE>",
        "The patient's exact or approximate age, age in years/months/days, or age category during the vaccination episode.",
        "Annotate explicit references to patient age or pediatric/geriatric category.",
        "year-old, years old, aged, age, infant, child, adolescent, adult, elderly, 6 months old, neonate",
        "• 'A 17-year-old [AGE] male developed...'\n• '...administered to a 6-month-old [AGE] infant [AGE]'",
        "Annotate patient age only; exclude ages of relatives or providers."
    ],
    [
        "SEX",
        "Patient Sex",
        "<SEX>",
        "The biological sex of the patient as explicitly reported in the VAERS narrative.",
        "Annotate explicit biological sex references applying to the patient.",
        "male, female, man, woman, boy, girl, male infant, female adolescent",
        "• 'A 28-year-old female [SEX] presented with...'\n• '...the young boy [SEX] experienced swelling'",
        "Annotate patient sex only; exclude sex references to clinicians or family members."
    ]
]

VAERS_GENERAL_RULES = [
    ("1. Symptom (SYM) vs. Diagnosis (sDx / pDx / DX)", "Preserve the clinical hierarchy: patient-reported manifestations without diagnostic confirmation are SYM; confirmed physician diagnoses for the AE episode are sDx; provisional/differential diagnoses are pDx; incidental non-AE diagnoses are DX.", "Chest pain = SYM; physician confirmed myocarditis = sDx; suspected pericarditis = pDx."),
    ("2. Diagnostic Certainty Attribution", "Assign pDx only when explicit markers of uncertainty (possible, suspected, probable, rule out) appear in the narrative text. Do not downgrade an established diagnosis to pDx without textual uncertainty.", "'Impression: confirmed anaphylaxis' = sDx; 'Impression: probable anaphylaxis' = pDx."),
    ("3. Vaccine (VAX) vs. Dose (DOSE) Disaggregation", "Decompose compound vaccination phrases into distinct product (VAX) and sequence/lot (DOSE) entities.", "In 'second dose of Pfizer COVID-19 vaccine lot #301', 'Pfizer COVID-19 vaccine' is VAX; 'second dose' and 'lot #301' are DOSE."),
    ("4. Temporal Anchor Isolation (TEMPO)", "Extract onset latency, relative post-vaccine time, and duration as pure temporal markers without absorbing surrounding clinical entities.", "'3 days after vaccination' = TEMPO; the vaccine itself remains VAX."),
    ("5. Laboratory Tests and Vital Signs (Lab)", "Capture test names, numerical values, and vital signs together when forming a single cohesive measurement phrase.", "'temperature 102.4 F' and 'platelets 22,000' are single Lab spans."),
    ("6. Treatment & Intervention Scope (TX)", "Include medications given therapeutically to manage adverse events, medical procedures, and hospital provider services under TX.", "In 'given oral diphenhydramine by EMS', 'oral diphenhydramine' and 'EMS' are TX."),
    ("7. Pre-existing Conditions (MHx) Precedence", "Medical conditions explicitly documented as existing before the vaccination date must be tagged as MHx, even if identical symptoms flare post-vaccine.", "Past history of asthma = MHx; acute asthma exacerbation post-vaccine = SYM / sDx."),
    ("8. Outcome and Disposition (STATUS)", "STATUS describes the evolution of the case (recovered, ongoing, hospitalized, expired). Annotate the recovery or disposition descriptor itself.", "In 'admitted to hospital and improved', 'admitted to hospital' and 'improved' are STATUS.")
]


# ==============================================================================
# MAIN WORKBOOK GENERATION
# ==============================================================================

def generate_faers_workbook(out_path: Path):
    wb = openpyxl.Workbook()
    
    # Sheet 1: Cover Sheet
    ws_cover = wb.active
    ws_cover.title = "Cover_Sheet"
    metadata = [
        ("Supplementary File:", "Supplementary File 2"),
        ("Document Title:", "FAERS Clinical Concept Annotation Guidance & Category Schema"),
        ("Associated Manuscript:", "Benchmarking Large Language Models and Fine-Tuned Encoders for Clinical Concept Extraction from Pharmacovigilance and Vaccine Adverse Event Narratives"),
        ("Target Corpus:", "FDA Adverse Event Reporting System (FAERS) Case Series Benchmark (N = 829 Narratives)"),
        ("Total Concept Categories:", "17 Primary Clinical Concept Categories"),
        ("Category Breakdown:", "sDrug, cDrug, oDrug, Dose, IND, Treatment, AE, mAE, Dx, Lab, Status, R/O, CoD, MHx, FHx, Age, Sex"),
        ("Evaluation Metric Tiers:", "Tier 1: Strict Exact-Match NER (CoNLL exact boundary + exact label)\nTier 2: Adapted ADE-Eval (Clinical partial overlap + cross-class weighted credit)\nTier 3: Relaxed Boundary (Token-level category agreement)"),
        ("Version & Date:", "Revision 1 (August 2026)")
    ]
    style_cover_sheet(ws_cover, "Supplementary File 2: FAERS Clinical Concept Annotation Guidance",
                      "Complete 17-Category Schema, Operational Annotation Rules, Trigger Phrases, and Clinical Exemplars", metadata)

    # Sheet 2: Category Guidance Schema
    ws_schema = wb.create_sheet(title="FAERS_17_Category_Schema")
    headers = [
        "Concept Code",
        "Category Name",
        "XML Tag",
        "Clinical Definition",
        "Annotation Rule & Scope",
        "Trigger Words / Contextual Clues",
        "Prototypical Clinical Examples",
        "Classification Caveats & Boundaries"
    ]
    col_widths = [14, 24, 14, 38, 42, 32, 38, 32]
    create_schema_sheet(ws_schema, "FAERS 17 Clinical Concept Category Annotation Schema", headers, FAERS_SCHEMA_DATA, col_widths)

    # Sheet 3: General Annotation Rules
    ws_rules = wb.create_sheet(title="General_Annotation_Rules")
    create_rules_sheet(ws_rules, "FAERS General Annotation Principles & Operational Guidelines", FAERS_GENERAL_RULES, [28, 48, 42])

    wb.save(str(out_path))
    print(f"Saved FAERS Guidance Excel to {out_path}")


def generate_vaers_workbook(out_path: Path):
    wb = openpyxl.Workbook()
    
    # Sheet 1: Cover Sheet
    ws_cover = wb.active
    ws_cover.title = "Cover_Sheet"
    metadata = [
        ("Supplementary File:", "Supplementary File 3"),
        ("Document Title:", "VAERS Vaccine Adverse Event Annotation Guidance & Category Schema"),
        ("Associated Manuscript:", "Benchmarking Large Language Models and Fine-Tuned Encoders for Clinical Concept Extraction from Pharmacovigilance and Vaccine Adverse Event Narratives"),
        ("Target Corpus:", "Vaccine Adverse Event Reporting System (VAERS) Benchmark (N = 1,000 Narratives)"),
        ("Total Concept Categories:", "14 Clinical and Contextual Concept Categories"),
        ("Category Breakdown:", "SYM, sDx, pDx, DX, VAX, MHx, FHx, Lab, TEMPO, DOSE, STATUS, TX, AGE, SEX"),
        ("Evaluation Protocol:", "10-Fold Cross-Validation on Fine-Tuned BioBERT vs. Zero-Shot/1-Shot Instruction-Tuned LLMs"),
        ("Version & Date:", "Revision 1 (August 2026)")
    ]
    style_cover_sheet(ws_cover, "Supplementary File 3: VAERS Vaccine Adverse Event Annotation Guidance",
                      "Complete 14-Category Schema, Operational Annotation Rules, Trigger Phrases, and Clinical Exemplars", metadata)

    # Sheet 2: Category Guidance Schema
    ws_schema = wb.create_sheet(title="VAERS_14_Category_Schema")
    headers = [
        "Concept Code",
        "Category Name",
        "XML Tag",
        "Clinical Definition",
        "Annotation Rule & Scope",
        "Trigger Words / Contextual Clues",
        "Prototypical Clinical Examples",
        "Classification Caveats & Boundaries"
    ]
    col_widths = [14, 24, 14, 38, 42, 32, 38, 32]
    create_schema_sheet(ws_schema, "VAERS 14 Clinical Concept Category Annotation Schema", headers, VAERS_SCHEMA_DATA, col_widths)

    # Sheet 3: General Annotation Rules
    ws_rules = wb.create_sheet(title="General_Annotation_Rules")
    create_rules_sheet(ws_rules, "VAERS General Annotation Principles & Operational Guidelines", VAERS_GENERAL_RULES, [28, 48, 42])

    wb.save(str(out_path))
    print(f"Saved VAERS Guidance Excel to {out_path}")


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    supp_dir = repo_root / "publication" / "supplementary"
    tables_dir = repo_root / "publication" / "results" / "tables"
    manuscript_dir = repo_root / "publication" / "manuscripts"
    
    supp_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    faers_out1 = supp_dir / "Supplementary_File_2_FAERS_Annotation_Guidance.xlsx"
    faers_out2 = manuscript_dir / "Supplementary_File_2_FAERS_Annotation_Guidance.xlsx"
    faers_out3 = tables_dir / "Supplementary_File_2_FAERS_Annotation_Guidance.xlsx"

    vaers_out1 = supp_dir / "Supplementary_File_3_VAERS_Annotation_Guidance.xlsx"
    vaers_out2 = manuscript_dir / "Supplementary_File_3_VAERS_Annotation_Guidance.xlsx"
    vaers_out3 = tables_dir / "Supplementary_File_3_VAERS_Annotation_Guidance.xlsx"

    generate_faers_workbook(faers_out1)
    generate_faers_workbook(faers_out2)
    generate_faers_workbook(faers_out3)

    generate_vaers_workbook(vaers_out1)
    generate_vaers_workbook(vaers_out2)
    generate_vaers_workbook(vaers_out3)


if __name__ == "__main__":
    main()
