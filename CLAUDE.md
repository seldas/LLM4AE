# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**LLM4AE** is a full-stack pharmacovigilance annotation tool for assessing Individual Case Safety Reports (ICSRs). It uses LLMs and BioBERT NER models to assist medical annotators in identifying adverse events and drug mentions in case narratives.

## Commands

### Frontend (`client/`)
```bash
npm run dev          # Start Next.js dev server on port 8861
npm run dev:server   # Start Flask backend via Node shim
npm run dev:all      # Run frontend + backend concurrently
npm run build        # Production build
npm run lint         # ESLint
```

### Backend (`server/`)
```bash
python app.py                  # Start Flask dev server on port 8862
python database_manager.py     # Initialize SQLite schema
python db_init_update.py       # Run DB migrations
```

### Docker (project root)
```bash
docker compose -f docker-compose.dev.yml up --build   # Dev (ports 8861/8862)
docker compose -f docker-compose.yml up --build -d    # Production (NGINX routes)
```

> There is no automated test suite.

## Architecture

The project is split into two top-level directories:

### `client/` — Next.js 16 App Router (React 19, TypeScript, Tailwind CSS v4)
- **`app/lib/api.ts`** — Single Axios instance; all backend calls centralized here. The base URL comes from `NEXT_PUBLIC_API_BASE`.
- **`app/lib/interfaces.ts`** — All shared TypeScript types.
- **`app/lib/doc-reducer.ts`** — Custom reducer managing annotation tool state (no Redux/Zustand).
- **`app/lib/terms.ts`** — NER label definitions (e.g., `SDRUG`, `AE`, `DOSE`).
- **`app/lib/util.ts`** — Helpers including `API_BASE` and label color mapping.
- **`app/annotate/`** — Main annotation workflow (`AnnoToolClient.tsx`).
- **`app/adjudicate/`** — Adjudication view for resolving annotator disagreements.
- **`app/assess/`** and **`app/causality/`** — Post-annotation assessment views.
- **`app/components/`** — Shared UI (annotation panel, brat-style text display, context menus).

### `server/` — Flask (Python), SQLite
- **`app.py`** — All REST API routes. Background threads handle async LLM/BERT jobs.
- **`database_manager.py`** — SQLite schema definition and all DB helper functions. Run directly to initialize the DB. Schema migrations are handled inline using `PRAGMA table_info`.
- **`ai_client.py`** — Universal AI provider client supporting `vllm`, `gemini`, and `elsa` (FDA internal).
- **`llm_prompts.py`** — All LLM system prompts for annotation tasks.
- **`project_management.py`** — Flask blueprint for ingesting cases from RxLogix/InfoVIP Excel exports.
- **`text_processing.py`** — Generates HTML for demographics, products, and outcomes sections.
- **`ner_client.py`** — BioBERT NER inference client.

### `development/`
- **`NER/`** — BioBERT model training and batch annotation scripts. `batch_annotate.py` runs multi-GPU annotation over the full DB.

## Key Patterns

### API Proxy
In dev, the frontend calls `http://localhost:8862/api` directly. In production, Next.js rewrites `/annotator_api/:path*` to the backend. Configured in `client/next.config.ts`.

### Database
SQLite at `server/database/llm4ae.db`. Key tables: `users`, `projects`, `cases`, `project_cases`, `annotations`, `adjudications`, `history_log`. Cases are keyed by `(case_number, version_number)`. Annotations store character offsets into narrative text; relationships are stored as JSON in the `relationships` column.

### Async LLM/BERT Jobs
Annotation jobs run in daemon threads (`threading.Thread(daemon=True)`). The frontend polls for completion via a 3-second interval checking `llm_status`/`bert_status` columns in the DB.

### User Roles
`Admin`, `Annotator` (SME1/SME2), `Adjudicator`, `AI` (LLM/BERT system users). Auth is simple username/password — no JWT.

### State Management
The annotation tool uses a custom reducer in `doc-reducer.ts`. UI state is updated optimistically, then synced to the backend.

## Configuration

Copy templates before running locally:
- `server/.env.template` → `server/.env` (AI API keys: `LLM_URL`, `LLM_KEY`, `GEMINI_API_KEY`, `ELSA_*`)
- `client/env.local.template` → `client/env.local` (`NEXT_PUBLIC_BACKEND_HOST`, `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_BASE_PATH`)

`NEXT_PUBLIC_BASE_PATH` controls sub-path deployment (e.g., `/annotator`).