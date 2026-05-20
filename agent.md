# LedgerFlow Analytics Agent Handoff

This file is a compact briefing for another LLM or coding agent working in this repository.

## Project Summary

LedgerFlow Analytics is a full-stack financial transaction upload, validation, approval, and analytics platform. Employees upload `.xlsx` or `.csv` files that match a fixed financial transaction schema. The backend validates the file, stores typed transaction rows in PostgreSQL, and marks the submission as pending. Assigned managers review submissions and can approve, decline, or request reupload. Admin users assign employees to managers. The frontend shows role-specific dashboards and receives live refresh events over WebSockets.

## Tech Stack

- Frontend: React 19, Vite, React Router, Axios, Recharts, React Icons, Tailwind CSS.
- Backend: FastAPI, SQLAlchemy async, Pydantic, Pandas, OpenPyXL, Uvicorn, WebSockets.
- Database: PostgreSQL 16 with Alembic migrations and a Docker initialization schema.
- Local orchestration: Docker Compose.

## Important Paths

- `frontend/src/main.jsx`: React route tree and role-based home redirect.
- `frontend/src/api/client.js`: Axios API client, bearer token interceptor, WebSocket URL helper.
- `frontend/src/auth/AuthContext.jsx`: login, register, logout, session validation.
- `frontend/src/auth/ProtectedRoute.jsx`: frontend auth and role guard.
- `frontend/src/pages/UploadCenter.jsx`: employee upload flow and preview.
- `frontend/src/pages/ManagerDashboard.jsx`: manager review queue and actions.
- `frontend/src/pages/AdminDashboard.jsx`: admin manager/employee assignment UI.
- `frontend/src/pages/Dashboard.jsx`: KPI and analytics dashboard.
- `backend/app/main.py`: FastAPI app, CORS, routers, startup seeded accounts.
- `backend/app/api/auth.py`: registration, login, current user.
- `backend/app/api/uploads.py`: upload parsing, row persistence, upload listing, preview access checks.
- `backend/app/api/approvals.py`: manager review actions.
- `backend/app/api/admin.py`: admin manager list, employee list, assign, reassign.
- `backend/app/api/agent.py`: API surface for a posting/upload agent.
- `backend/app/api/analytics.py`: KPI aggregation.
- `backend/app/services/excel_parser.py`: spreadsheet parsing and transaction validation.
- `backend/app/services/email.py`: optional SMTP notifications.
- `backend/app/services/websocket_manager.py`: in-memory WebSocket channel broadcaster.
- `backend/app/models.py`: SQLAlchemy models and enums.
- `backend/app/schemas.py`: Pydantic request/response contracts.
- `backend/alembic/versions/`: database migrations.
- `database/schema.sql`: Docker Postgres initialization schema.
- `docs/ARCHITECTURE.md`: detailed architecture reference.
- `docs/RAILWAY_DEPLOYMENT.md`: deployment notes.

## Local Development

Copy backend environment defaults:

```powershell
Copy-Item backend\.env.example backend\.env
```

Start PostgreSQL:

```powershell
docker compose up -d postgres
```

Run backend:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Run frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

Full Docker Compose defines `postgres`, `backend`, and `frontend` services. The composed frontend is served through Nginx on host port `5173`; the backend is exposed on `8000`; PostgreSQL is exposed on host port `5433`.

## Environment Settings

Backend settings are defined in `backend/app/core/config.py` and `backend/.env.example`.

Key variables:

- `DATABASE_URL`: async SQLAlchemy PostgreSQL URL. Plain `postgres://` and `postgresql://` are normalized to `postgresql+asyncpg://`.
- `UPLOAD_DIR`: local directory for raw uploaded files.
- `MAX_PREVIEW_ROWS`: preview row limit.
- `MAX_UPLOAD_SIZE_MB`: upload size limit.
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`: auth token settings.
- `CORS_ORIGINS`: comma-separated allowed frontend origins.
- `FRONTEND_BASE_URL`: used in manager review email links.
- `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD`, `DEFAULT_ADMIN_NAME`: seeded admin account.
- `AGENT_EMAIL`, `AGENT_PASSWORD`, `AGENT_NAME`: optional seeded employee account for agent uploads.
- `EMAILS_ENABLED` and `SMTP_*`: optional SMTP notification settings.

Production validation rejects unsafe default secrets, localhost database URLs, localhost CORS origins, weak default admin passwords, and partially configured agent credentials.

## Roles And Permissions

- `employee`: can register/login, upload files, view own uploads, and view scoped analytics.
- `manager`: can register/login, view uploads from assigned employees, approve/decline/request reupload, and view scoped analytics.
- `admin`: seeded by backend startup, can assign/reassign employees to managers and view all uploads/analytics.

Public registration only accepts `employee` or `manager`. Admin users are created from environment-backed startup seeding.

Manager review access is assignment-scoped: a manager can only review submissions where `submission.user.manager_id == manager.id`.

## Data Model

Core tables:

- `users`: full name, email, hashed password, role, optional `manager_id`.
- `submissions`: upload metadata, file path, original filename, version metadata, review status.
- `reviews`: one manager decision per submission, with required comments for decline/reupload.
- `transaction_rows`: normalized financial transaction records linked to submissions.

Important relationship:

- `users.manager_id` points back to `users.id`, assigning employees to managers.

## Spreadsheet Contract

Supported upload types: `.xlsx`, `.csv`.

Required columns:

- `customer_name`
- `account_number`
- `transaction_id`
- `transaction_date`
- `amount`
- `transaction_type`
- `merchant_name`
- `invoice_id`
- `payment_method`
- `status`

Accepted enum values:

- `transaction_type`: `Payment`, `Debit`, `Credit`, `Transfer`, `Refund`
- `payment_method`: `NEFT`, `UPI`, `Credit Card`, `Debit Card`, `Net Banking`
- `status`: `Initiated`, `Pending`, `Successful`, `Failed`

Validation rejects empty files, unsupported extensions, files over `MAX_UPLOAD_SIZE_MB`, missing columns, missing required values, non-positive or non-numeric amounts, unparsable dates, and invalid enum values.

## API Overview

Authentication:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

Agent:

- `POST /api/agent/login`
- `POST /api/agent/upload`

Uploads:

- `POST /api/uploads`
- `GET /api/uploads`
- `GET /api/uploads/{upload_id}`

Approvals:

- `POST /api/approvals/approve`
- `POST /api/approvals/{upload_id}/approve`
- `POST /api/approvals/reject`
- `POST /api/approvals/{upload_id}/reject`
- `POST /api/approvals/request-reupload`
- `POST /api/approvals/{upload_id}/request-reupload`

Admin:

- `GET /api/admin/managers`
- `GET /api/admin/employees`
- `POST /api/admin/assign`
- `POST /api/admin/reassign`

Analytics:

- `GET /api/analytics/kpis`

Health:

- `GET /health`

## WebSockets

Endpoint:

```text
/ws/{channel}
```

Current channels:

- `uploads`
- `manager`
- `dashboard`

Current events include `upload_progress`, `upload.complete`, `new_upload`, `upload.new`, `upload_status`, `approval.decision`, `upload_reviewed`, `dashboard_refresh`, and `kpi.update`.

The broadcaster is process-local. Multi-instance deployments need a shared bus such as Redis Pub/Sub or PostgreSQL LISTEN/NOTIFY.

## Development Notes

- Prefer existing patterns and endpoint shapes before adding new abstractions.
- Keep backend access rules mirrored in the frontend where reasonable, but treat backend role checks as authoritative.
- When changing schema, update SQLAlchemy models, Alembic migrations, and `database/schema.sql`.
- When changing upload data shape, update `excel_parser.py`, `uploads.py`, schemas, frontend preview/dashboard code, and architecture docs.
- Raw uploaded files are written to local disk or the Docker `backend_uploads` volume.
- Parsing currently runs inline inside the upload request.
- Email sending is best-effort and disabled unless configured.

## Verification Commands

Backend syntax check:

```powershell
python -m compileall backend\app
```

Frontend build:

```powershell
cd frontend
npm run build
```

Docker services:

```powershell
docker compose up --build
```
