# LedgerFlow

LedgerFlow turns messy general-ledger spreadsheets into structured, reviewable workflows through its extraction pipeline.

It is built for teams that need to upload XLSX or CSV files, extract usable ledger data from inconsistent inputs, route it through manager review, and keep a clear audit trail without relying on ad hoc spreadsheets or email threads.

## What It Solves

  - Removes manual follow-up from spreadsheet-based financial submissions.
  - Extracts structured ledger data from inconsistent file layouts without forcing every upload into the same rigid template.
  - Keeps uploads, approvals, alerts, and audit logs in one place.
  - Supports live status updates instead of manual refresh.
  - Provides an extraction pipeline for messy or unstructured source data.

## Key Features

  - Spreadsheet uploads with validation and parsing
  - Extraction pipeline for messy or inconsistent source files
  - Column grounding and structured data extraction
  - Ambiguity handling and repair when input is incomplete
  - Submission preview and transaction detail views
  - Manager approve, reject, and re-upload workflow
  - Comments, alerts, audit logs, and analytics
  - Role-based access for employees, managers, and admins

## Project Layers

  - `frontend/` - React app for uploads, submissions, dashboards, alerts, settings, and admin screens.
  - `backend/` - FastAPI API, authentication, persistence, approvals, analytics, and WebSocket updates.
  - `ledgerflow_agent/` and `agents/` - extraction, grounding, repair, and execution pipeline.
  - `docs/` - architecture and deployment references.
  - `tests/` - automated test coverage.

## Architecture Overview

```mermaid
flowchart LR
  U[User] --> F[Frontend<br/>React + Vite]
  F -->|REST /api| B[Backend<br/>FastAPI]
  F -->|WebSocket /ws/*| WS[Live updates]
  B --> DB[(PostgreSQL)]
  B --> M[(Uploaded files)]
  B --> E[Email / notifications]
  B --> A[Extraction pipeline]
  A --> B

  subgraph Frontend["Frontend"]
    F1[Landing / Auth]
    F2[Upload Center]
    F3[Submissions]
    F4[Manager / Admin / Audit]
  end

  subgraph Backend["Backend"]
    B1[Auth + roles]
    B2[Uploads + parsing]
    B3[Approvals + comments]
    B4[Alerts + analytics]
    B5[WebSockets]
  end

  F --- F1
  F --- F2
  F --- F3
  F --- F4
  B --- B1
  B --- B2
  B --- B3
  B --- B4
  B --- B5
```

The important separation is:

- Frontend = presentation and user interaction.
- Backend = system of record and business rules.
- Extraction pipeline = the differentiator that converts messy files into structured ledger data.

```mermaid
sequenceDiagram
  participant E as Employee
  participant F as Frontend
  participant B as Backend
  participant D as Database
  participant M as Manager
  participant A as Agentic pipeline

  E->>F: Upload spreadsheet
  F->>B: POST /api/uploads
  B->>D: Store submission metadata
  B->>A: Optional extraction / repair
  A-->>B: Verified structured output
  B->>D: Store transaction rows
  B-->>F: Preview and status
  M->>F: Review submission
  F->>B: Approve / reject / request re-upload
  B->>D: Store review decision
  B-->>F: WebSocket update
```

```mermaid
flowchart TB
  subgraph UI["Frontend pages"]
    UI1["Landing / Auth"]
    UI2["Upload Center"]
    UI3["Submissions"]
    UI4["Manager Dashboard"]
    UI5["Alerts / Settings / Admin / Audit"]
  end

  subgraph API["Backend routes"]
    API1["Auth"]
    API2["Uploads"]
    API3["Approvals"]
    API4["Comments"]
    API5["Analytics"]
    API6["Alerts"]
    API7["Admin"]
    API8["WebSockets"]
  end

  subgraph DATA["Data and services"]
    D1[(PostgreSQL)]
    D2[(Uploaded files)]
    D3[Email / notifications]
    D4[Agentic pipeline]
  end

  UI1 --> API1
  UI2 --> API2
  UI3 --> API2
  UI4 --> API3
  UI4 --> API4
  UI5 --> API5
  UI5 --> API6
  UI5 --> API7
  API1 --> D1
  API2 --> D1
  API2 --> D2
  API2 --> D4
  D4 --> API2
  API3 --> D1
  API3 --> D3
  API4 --> D1
  API4 --> D3
  API5 --> D1
  API6 --> D1
  API7 --> D1
  API8 --> UI1
```

## How The Product Works

1. An employee uploads a spreadsheet.
2. The backend validates the file and creates a submission.
3. Parsed transactions are stored and shown in the UI.
4. A manager reviews the submission and leaves a decision.
5. Alerts, audit logs, and analytics update from the same backend state.

## Frontend

The frontend is a React single-page app. It handles presentation, routing, and user interaction, and it stays in sync with backend events.

Main screens:

- Landing and authentication
- Upload center
- Submissions history and transaction detail views
- Manager review dashboard
- Alerts, settings, admin, and audit pages

## Backend

The backend is the system of record. It owns authentication, role-based access, upload processing, approval decisions, comments, analytics, and notifications.

Main responsibilities:

- Registering and authenticating users
- Storing submission metadata and transaction rows
- Enforcing manager and admin access rules
- Tracking review state, alerts, and audit logs
- Broadcasting live updates to the UI

## Extraction Pipeline

The extraction pipeline is the core differentiator. It helps process messy inputs, ground columns against the sheet, repair problematic data, and produce verified structured output when deterministic parsing is not enough.

## Quick Start

### Docker Compose

```powershell
docker compose up --build
```

### Backend Only

```powershell
Copy-Item backend\.env.example backend\.env
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Only

```powershell
cd frontend
npm install
npm run dev
```

### Optional Agent Run

```powershell
py -3 main.py
```

## Configuration

Start with `backend/.env.example`. Common settings include:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `CORS_ORIGINS`
- `FRONTEND_BASE_URL`
- `DEFAULT_ADMIN_EMAIL`
- `DEFAULT_ADMIN_PASSWORD`
- `EMAILS_ENABLED`
- `UPLOAD_DIR`

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Railway deployment](docs/RAILWAY_DEPLOYMENT.md)
- [Testing guide](TESTING_GUIDE.md)
- [Agent notes](agent.md)
