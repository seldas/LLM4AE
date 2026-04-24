# SCAT App Integration Specification

This document provides technical instructions for the SCAT application to integrate with AskMyFAERS.

## 1. Intake Function (Inbound from AskMyFAERS)

The "Go to SCAT" button in AskMyFAERS performs a standard HTTP POST request to the SCAT endpoint.

- **Method:** `POST`
- **Content-Type:** `application/x-www-form-urlencoded`
- **Payload:** A single form field named `case_data` containing a JSON-stringified object.

### Inbound JSON Structure (`case_data`)

```json
{
    "id": 123,
    "safety_report_id": "US-FDA-2023-0001",
    "case_id": "CASE12345",
    "narrative": "The patient experienced...",
    "annotations": {
        "drugs": ["Drug A", "Drug B"],
        "events": ["Nausea"],
        "edges": []
    }
}
```

### SCAT Implementation Requirements:
1. **Endpoint:** SCAT must expose a public URL that can handle this POST request.
2. **Session Handling:** SCAT should parse the `case_data`, load the narrative into its workspace, and allow the user to perform term and relationship annotation.

---

## 2. Export Function (Outbound to AskMyFAERS)

After completing the analysis in SCAT, the user will export a JSON file to be uploaded back into AskMyFAERS via the "Import Annotations" button.

- **File Format:** `.json`
- **Validation Rule:** The `narraives` field MUST match the original narrative sent in the inbound request character-for-character. Any mismatch will result in an "Import Failed" error in AskMyFAERS.

### Expected Outbound JSON Structure

```json
{
    "narraives": "The patient experienced...", 
    "terms": {
        "drugs": ["Drug A", "Drug B"],
        "events": ["Nausea", "Vomiting"],
        "time": ["2023-01-01"],
        "demographics": ["75yo Male"]
    },
    "relationships": [
        {
            "source": "Drug A",
            "target": "Nausea",
            "type": "related_to",
            "label": "suspected cause"
        }
    ]
}
```

### Field Definitions:
- **`narraives`**: (String) The exact narrative text from the original case.
- **`terms`**: (Object) A dictionary where keys are category names (e.g., `drugs`, `events`, `time`, `demographics`) and values are arrays of strings (the extracted terms).
- **`relationships`**: (Array) A list of edge objects.
    - `source`: (String) The label of the source term.
    - `target`: (String) The label of the target term.
    - `type`: (String) One of: `related_to`, `temporal`, `latency`, `relative`.
    - `label`: (String) Human-readable description of the link.

## 3. Workflow Summary
1. **AskMyFAERS** --(POST case_data)--> **SCAT App**
2. **User** performs annotation in **SCAT**.
3. **SCAT App** --(Download JSON)--> **User's Local Machine**
4. **User** --(Upload JSON)--> **AskMyFAERS** (Stage 2: Import Annotations)
