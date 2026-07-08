# LedgerFlow

LedgerFlow turns spreadsheet-based general-ledger handling into a controlled workflow from upload to approval, audit, and reporting.

It helps finance teams replace email threads, ad hoc spreadsheets, and manual follow-up with a shared process that is trackable, reviewable, and easier to manage.

## Why It Matters

- One workflow for employees, managers, and admins.
- One system of record for uploads, approvals, alerts, and audit logs.
- Live status updates through WebSockets.
- Optional agentic processing for messy or unstructured source data.

## What It Does

- Employees upload `.xlsx` or `.csv` ledger files.
- The backend validates, parses, and stores submission data and transaction rows.
- Users review parsed data and transaction previews in the UI.
- Managers approve, reject, or request a re-upload with optional feedback.
- Alerts, audit logs, and analytics update from the same backend state.
- The optional agent pipeline can extract and repair data before normal processing finishes.

## Project Layout

- `frontend/` - React app for the user-facing workflow.
- `backend/` - FastAPI API, auth, review workflow, persistence, analytics, and WebSocket broadcasting.
- `ledgerflow_agent/` and `agents/` - optional LangGraph-based extraction and repair pipeline.
- `docs/` - architecture and deployment references.
- `tests/` - automated test coverage.

## Core Workflow

1. An employee uploads a spreadsheet.
2. The backend validates the file and creates a submission.
3. Parsed transactions are stored and shown in the UI.
4. A manager reviews the submission and adds a decision.
5. Audit logs, alerts, and analytics reflect the result.

## Main Areas

### Frontend

React single-page app for presentation, routing, and user interaction. It stays in sync with backend events and covers:

- Landing and authentication
- Upload center
- Submissions history and transaction detail views
- Manager review dashboard
- Alerts, settings, admin, and audit pages

### Backend

The backend is the system of record. It owns authentication, role-based access, upload processing, approval decisions, comments, analytics, and notifications.

It is responsible for:

- Registering and authenticating users
- Storing submission metadata and transaction rows
- Enforcing manager and admin access rules
- Tracking review state, alerts, and audit logs
- Broadcasting live updates to the UI

### Agentic Pipeline

The optional agentic pipeline helps process messy inputs, repair problematic data, and produce verified structured output when deterministic parsing is not enough.

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
