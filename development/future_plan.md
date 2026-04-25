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
- [ ] **Lazy Loading:** For very long narratives, implement offset-based loading for annotations to keep the UI responsive.
- [ ] **Websockets:** Replace 3-second polling with Websockets (Socket.io) for "Done" notifications from AI workers to provide instant UI refreshes.

### **Data Quality**
- [ ] **Relationship Validation:** Add backend constraints to ensure that relationships (e.g., latency to drug) always point to existing annotation IDs.
- [ ] **Conflict Resolution:** Implement a UI warning if two users are editing the same case simultaneously (now possible with the DB refactor).
