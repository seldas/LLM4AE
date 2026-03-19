# LLM4AE: LLM-Powered Annotation & Extraction for Pharmacovigilance

LLM4AE is an advanced annotation and assessment platform specifically designed for **Pharmacovigilance (PV)** professionals. It leverages Large Language Models (LLMs) to streamline the process of extracting, annotating, and assessing clinical data from **Individual Case Safety Reports (ICSRs)**.

---

## ✨ Key Features

### 📁 Smart Project Management
- **Excel Ingestion**: Create entire projects by simply uploading Excel exports from common PV systems (supports **RxLogix** and **InfoVIP** formats).
- **Automatic Case Parsing**: Automatically extracts narratives and structured metadata (Demographics, Products, Outcomes) for each case.
- **Playground Mode**: Quickly paste any text for immediate, ad-hoc annotation.

### ✍️ Advanced Annotation Tool
- **Dual-Panel Interface**: View the case narrative alongside structured case data or AI-generated annotations.
- **AI-Assisted Labeling**: Trigger background LLM processes to pre-annotate medical entities (Drugs, Adverse Events, Lab Tests, etc.).
- **Multi-Role Workflow**: Supports independent annotation by multiple SMEs (**SME1**, **SME2**) and a specialized **Adjudication** mode for reconciliation.
- **Relationship Builder**: Map complex relationships between entities, such as linking a suspected drug to an adverse event with temporal details (latency, frequency).

### 🧠 ICSR Causality Assessment
- **Automated Scoring**: Use LLMs to estimate causality judgments (Certain, Probable, Possible, Unlikely, Unassessable) based on clinical evidence.
- **Detailed Explanations**: Generate human-readable explanations for causality ratings, mapped to standard PV factors (Time Relationship, Alternative Explanations, Dechallenge, etc.).

### 📊 Reporting & Export
- **Rich Exports**: Export data to raw JSON or formatted Excel files.
- **Adjudication Reports**: Generate specialized Excel reports comparing SME findings to facilitate consensus.

---

## 🛠️ Technology Stack

- **Frontend**: [Next.js](https://nextjs.org/) (React), [Tailwind CSS v4](https://tailwindcss.com/), [TanStack Table](https://tanstack.com/table), [ExcelJS](https://github.com/exceljs/exceljs).
- **Backend**: [Flask](https://flask.palletsprojects.com/) (Python), [Pandas](https://pandas.pydata.org/) for data processing.
- **AI Integration**: [OpenAI](https://openai.com/) and [Google Gemini](https://ai.google.dev/) APIs.
- **Infrastructure**: [Docker](https://www.docker.com/) and [NGINX](https://www.nginx.com/).

---

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose installed.
- (Optional) API keys for OpenAI or Google Gemini (configured in `server/.env`).

### Development Environment
To start the development environment with live-reloading:

```bash
docker compose -f docker-compose.dev.yaml up --build
```

- **Frontend/NGINX**: [http://localhost:8862](http://localhost:8862)
- **Backend API**: [http://localhost:5000](http://localhost:5000)

### Production Deployment
For a production-ready setup:

```bash
docker compose -f docker-compose.prod.yaml up --build -d
```

- **Access URL**: [http://localhost:8861](http://localhost:8861) (or your configured port).

---

## 📁 Project Structure

| Directory | Description |
|-----------|-------------|
| `client/` | Next.js frontend application. |
| `server/` | Flask backend API, LLM logic, and document processing. |
| `nginx/` | Reverse proxy configurations. |
| `history/`| (Auto-generated) Stores project JSON files and Meta Excel files. |

---

## ⚙️ Configuration

1. Copy `server/.env.template` to `server/.env`.
2. Configure your AI model preferences and API keys in the `.env` file.
3. (Optional) Adjust NGINX ports in the `docker-compose` files if needed.
