# SCAT Transition: JSON-Based to Database-Oriented Architecture

This document summarizes the progress and remaining tasks for migrating the SCAT application from a file-based (JSON) analysis workflow to a real-time, database-driven (SQLite) system.

## 1. Accomplished (Completed Tasks)

### **Backend Infrastructure**
- [x] **Database Schema Normalization:** Added explicit columns to the `cases` table for `llm_status`, `bert_status`, and `review_status` to replace JSON blob parsing.
- [x] **SQLite WAL Mode:** Enabled Write-Ahead Logging to support concurrent read/write operations, resolving "Database is locked" errors during background AI tasks.
- [x] **Incremental CRUD API:** Implemented specific REST endpoints (`POST`, `PATCH`, `DELETE`) for annotations to allow atomic database updates without overwriting full case files.
- [x] **AI User Logic:** Integrated automatic mapping of AI providers (vLLM/Elsa) to specific database users to maintain provenance.

### **Frontend & State Management**
- [x] **Case-Centric Reducer:** Refactored `doc-reducer.ts` to reflect the database record structure. The state now tracks a `caseId` and a normalized `status` object.
- [x] **Asynchronous Handlers:** Refactored UI actions (`handleAdd`, `handleRemove`, `handleVerify`) to be fully asynchronous, performing "Optimistic UI" updates synced with backend confirmations.
- [x] **Real-time Status Polling:** Implemented an ID-based polling mechanism that checks database status columns directly to refresh AI results.
- [x] **Unified Annotation Tool:** Migrated the legacy `annotate/` tool to the incremental CRUD model and consolidated it with the ICSR integration logic.

### **Integration (AskMyFAERS)**
- [x] **Integrated Intake Workflow:** Created a dedicated `/api/annotate_icsr_intake/` endpoint that handles inbound case data and automatically redirects to the unified annotation tool.
- [x] **Temporary Mode:** Implemented a lightweight UI mode for direct integrations that hides user info and uses a default "tempo" project context.
- [x] **Project Prefixing:** Implemented automatic project namespacing (e.g., `AskMyFAERS_Case-1`) for better organizational structure of integrated cases.

## 2. In Progress / Pending Tasks

### **Functional Cleanup**
- [x] **Adjudication Module:** Move adjudication decisions into a dedicated table or more structured format in the DB instead of a serialized JSON field in the annotations table.
- [x] **Audit Trail:** Create a `history_log` table in the database to track every incremental change (who changed what and when) for regulatory compliance.

### **Performance & Scalability**
- [x] **Lazy Loading:** For very long narratives, implement offset-based loading for annotations to keep the UI responsive.
- [x] **Websockets:** Replace 3-second polling with Websockets (Socket.io) for "Done" notifications from AI workers to provide instant UI refreshes.

### **Data Quality**
- [x] **Relationship Validation:** Add backend constraints to ensure that relationships (e.g., latency to drug) always point to existing annotation IDs.
- [x] **Conflict Resolution:** Implement a UI warning if two users are editing the same case simultaneously (now possible with the DB refactor).


logging.info(f"DEBUG: Full LLM Response from {annotated_text}:\n{spans}")

annotator-backend   | [2026-04-26 01:26:41 +0000] [7] [INFO] DEBUG: Full LLM Response from Case 2019FE07533 is a serious spontaneous case received from a pharmacist in Turkey. 
annotator-backend   | 
annotator-backend   | This report concerns a <Age>47-year-old</Age> <Sex>female</Sex> who experienced <AE>hypotension</AE> and <AE>fainting</AE> during treatment with oral <SDrug>PICOPREP (sodium picosulfate, mgo, citric acid) powder for oral solution</SDrug>, unknown concentration, <Dose>2 x 16.1 g</Dose> for <IND>bowel preparation</IND> on <Date>07-Nov-2019</Date>.
annotator-backend   |  
annotator-backend   | A pharmacist from a hospital reported 6 events in relation to a colon cleansing protocol at the gastroenterology unit which was using <SDrug>PICOPREP</SDrug> and <CDrug>Bekunis</CDrug> at the same time. <SDrug>PICOPREP</SDrug> was used according to label and additionally patients received <CDrug>Bekunis (content is Sennoside 3mg/bisakodil 5mg)</CDrug>.
annotator-backend   | On <Date>07-Nov-2019</Date>, the patient experienced <AE>hypotension</AE> and <AE>fainting</AE> and went to the emergency unit at a hospital. 
annotator-backend   |  
annotator-backend   | Action taken to <SDrug>PICOPREP</SDrug> was not applicable. 
annotator-backend   | On <Date>07-Nov-2019</Date>, the outcome of <AE>hypotension</AE> and <AE>fainting</AE> was <Status>recovered</Status>.
annotator-backend   |  
annotator-backend   | The following concomitant medication was reported: <CDrug>Bekunis</CDrug> (on <Date>07-Nov-2019</Date>).
annotator-backend   |  
annotator-backend   | The events in the case were reported as serious (<Status>hospitalisation</Status>).
annotator-backend   | 
annotator-backend   | At the time of reporting the case outcome was <Status>recovered</Status>.
annotator-backend   |  
annotator-backend   | Overall listedness (core label) is unlisted.
annotator-backend   | Reporter Causality: Related
annotator-backend   | Company Causality: Related
annotator-backend   |  
annotator-backend   | Other case numbers:
annotator-backend   | Link: same reporter = 2019FE07532. 
annotator-backend   | Link: same reporter = 2019FE07507. 
annotator-backend   | Link: same reporter = 2019FE07531. 
annotator-backend   | Link: same reporter = 2019FE07536. 
annotator-backend   | Link: same reporter = 2019FE07534. 
annotator-backend   | Internal # - Affiliate = SAR-2019-17.:
annotator-backend   | [{'label': 'Age', 'text': '47-year-old'}, {'label': 'Sex', 'text': 'female'}, {'label': 'AE', 'text': 'hypotension'}, {'label': 'AE', 'text': 'fainting'}, {'label': 'SDrug', 'text': 'PICOPREP (sodium picosulfate, mgo, citric acid) powder for oral solution'}, {'label': 'Dose', 'text': '2 x 16.1 g'}, {'label': 'IND', 'text': 'bowel preparation'}, {'label': 'Date', 'text': '07-Nov-2019'}, {'label': 'SDrug', 'text': 'PICOPREP'}, {'label': 'CDrug', 'text': 'Bekunis'}, {'label': 'SDrug', 'text': 'PICOPREP'}, {'label': 'CDrug', 'text': 'Bekunis (content is Sennoside 3mg/bisakodil 5mg)'}, {'label': 'Date', 'text': '07-Nov-2019'}, {'label': 'AE', 'text': 'hypotension'}, {'label': 'AE', 'text': 'fainting'}, {'label': 'SDrug', 'text': 'PICOPREP'}, {'label': 'Date', 'text': '07-Nov-2019'}, {'label': 'AE', 'text': 'hypotension'}, {'label': 'AE', 'text': 'fainting'}, {'label': 'Status', 'text': 'recovered'}, {'label': 'CDrug', 'text': 'Bekunis'}, {'label': 'Date', 'text': '07-Nov-2019'}, {'label': 'Status', 'text': 'hospitalisation'}, {'label': 'Status', 'text': 'recovered'}]