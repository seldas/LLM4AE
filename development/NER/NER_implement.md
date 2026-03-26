# NER Model Integration Plan

This document outlines the strategy for integrating the trained BioBERT NER model (located in `development/NER/output/model-best`) into the LLM4AE system to provide automated annotations for ICSR narratives.

## Overview
The goal is to allow users to trigger "AI Annotation" on the home page for a specific case, which will use the local BioBERT model instead of (or in addition to) external LLM APIs.

## Implementation Steps

### 1. Create a Python Inference Wrapper
Create a utility script or class in `server/ner_client.py` that loads the spaCy model and provides a clean interface for prediction.

- **Initialization**: Load the model once (lazy loading) from `development/NER/output/model-best`.
- **Inference**: A function `annotate_text(text)` that returns a list of entities in the format `(start, end, label, text)`.

### 2. Update the Backend API (`server/app.py`)
Modify the Flask backend to include an endpoint for local NER.

- **New Endpoint**: `POST /api/annotate/bert`
- **Request**: `{ "case_id": 123, "narrative": "..." }`
- **Logic**:
    1. Call the inference wrapper.
    2. Format the results to match the system's `annotations` table schema.
    3. (Optional) Auto-save these to the database under the `BioBERT` user (migration_key='BERT').

### 3. Update AI Annotation Logic (`server/llm_annotation.py`)
Integrate the BERT model into the existing AI annotation workflow.

- Currently, `llm_annotation.py` likely handles calls to OpenAI/Llama.
- Add a branch or a new function `run_bert_annotation` that utilizes the local model.
- This allows the UI to toggle between "LLM Annotation" and "BERT NER Annotation".

### 4. Frontend Integration (`client/app/components/context-menus/llm-annotation-popup.tsx`)
Modify the UI to allow users to select the BioBERT model.

- Add a "BioBERT" option to the AI annotation selection.
- When selected, call the new `/api/annotate/bert` endpoint.
- Display the returned entities in the annotation panel for user verification/editing.

### 5. Database Records
Ensure the `BioBERT` user exists in the `users` table (it is already initialized in `database_manager.py` with `migration_key='BERT'`). All automated annotations from this model should be attributed to this `user_id`.

## Technical Considerations
- **Performance**: spaCy Transformers (BioBERT) require a GPU for optimal speed. Ensure the server environment has `torch` and `cuda` configured.
- **Concurrency**: If multiple users request annotation simultaneously, the GPU memory usage must be managed.
- **Alignment**: The model was trained on 512-character chunks. The inference wrapper must handle longer narratives by splitting them (using the same logic as `prepare_data.py`) and then re-aligning the offsets to the original full narrative.
