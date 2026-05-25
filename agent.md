# LedgerFlow Analytics Agent Handoff

This file is a compact briefing for another LLM or coding agent working in this repository. Treat it as the first context file to read before making changes.

## Project Summary

LedgerFlow Analytics is a full-stack financial transaction upload, validation, approval, discussion, re-upload, and analytics platform.

Employees upload `.xlsx` or `.csv` files that match a fixed financial transaction schema. The backend validates the file, stores typed transaction rows in PostgreSQL, and creates a pending submission. Assigned managers review submissions, discuss corrections in a submission thread, approve, decline, or request re-upload. Employees can re-upload corrected versions when requested. Admin users assign employees to managers. The frontend shows role-specific dashboards and receives live refresh events over WebSockets.

## Tech Stack

- Frontend: React 19, Vite, React Router, Axios, Recharts, React Icons, Tailwind CSS.
- Backend: FastAPI, SQLAlchemy async, Pydantic, Pandas, OpenPyXL, Uvicorn, WebSockets.
- Database: PostgreSQL 16 with Alembic migrations.
- Local orchestration: Docker Compose.

## Important Paths

- `frontend/src/main.jsx`: React route tree and role-based home redirect.
- `frontend/src/api/client.js`: Axios API client, bearer token interceptor, refresh-token retry, WebSocket URL helper.
- `frontend/src/auth/AuthContext.jsx`: login, register, logout, session validation.
- `frontend/src/auth/ProtectedRoute.jsx`: frontend auth and role guard.
- `frontend/src/shell/AppShell.jsx`: authenticated app shell, topbar, collapsible sidebar.
- `frontend/src/components/CommentThread.jsx`: reusable submission discussion thread with WebSocket updates.
- `frontend/src/components/DataTable.jsx`: reusable preview/detail table.
- `frontend/src/components/ProgressMilestones.jsx`: submission progress/decision visual.
- `frontend/src/pages/AuthPage.jsx`: login/register UI; preserves full redirect path including query strings for email links.
- `frontend/src/pages/UploadCenter.jsx`: employee upload flow and transaction preview.
- `frontend/src/pages/SubmissionsPage.jsx`: employee upload history, comment thread access, and re-upload button.
- `frontend/src/pages/ManagerDashboard.jsx`: manager review queue, token deep links, comment thread, review actions, version tabs.
- `frontend/src/pages/AdminDashboard.jsx`: admin manager/employee assignment UI.
- `frontend/src/pages/Dashboard.jsx`: KPI and analytics dashboard.
- `backend/app/main.py`: FastAPI app, CORS, routers, startup seeded accounts.
- `backend/app/api/auth.py`: registration, login, refresh, logout, current user, account settings.
- `backend/app/api/uploads.py`: upload parsing, re-upload flow, row persistence, listing, preview, version history, access checks.
- `backend/app/api/comments.py`: submission comment APIs, WebSocket broadcast, comment email notification.
- `backend/app/api/approvals.py`: manager review actions and review-link token verification.
- `backend/app/api/admin.py`: admin manager list, employee list, assign, reassign.
- `backend/app/api/agent.py`: API surface for a posting/upload agent.
- `backend/app/api/analytics.py`: KPI aggregation.
- `backend/app/services/excel_parser.py`: spreadsheet parsing and transaction validation.
- `backend/app/services/email.py`: optional SMTP notifications and manager review links.
- `backend/app/services/websocket_manager.py`: in-memory WebSocket channel broadcaster.
- `backend/app/models.py`: SQLAlchemy models and enums.
- `backend/app/schemas.py`: Pydantic request/response contracts.
- `backend/alembic/versions/`: database migrations.
- `docs/ARCHITECTURE.md`: detailed architecture reference.
- `docs/RAILWAY_DEPLOYMENT.md`: deployment notes.

## Local Development

Copy backend environment defaults:

```powershell
Copy-Item backend\.env.example backend\.env
```

Run everything in Docker:

```powershell
docker compose up --build
```

If the browser still shows old frontend assets after changes:

```powershell
docker compose down
docker compose up --build --force-recreate
```

Then hard refresh `http://localhost:5173` with `Ctrl + F5`.

Run services separately:

```powershell
docker compose up -d postgres
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

Ports:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- PostgreSQL host port: `5433`

## Environment Settings

Backend settings live in `backend/app/core/config.py` and `backend/.env.example`.

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

- `employee`: can register/login, upload files, view own uploads, comment on own submissions, re-upload when requested, and view scoped analytics.
- `manager`: can register/login, view assigned employee uploads, comment on assigned submissions, approve/decline/request re-upload, and view scoped analytics.
- `admin`: seeded by backend startup, can assign/reassign employees to managers and view all uploads/analytics.

Public registration only accepts `employee` or `manager`. Admin users are created from environment-backed startup seeding.

Manager review access is assignment-scoped: a manager can only review/comment on submissions where `submission.user.manager_id == manager.id`.

## Auth And Deep-Link Notes

The session is stored in `localStorage` under `ledgerflow_auth`. The API also uses a refresh-token cookie.

Manager email links are generated as:

```text
{FRONTEND_BASE_URL}/manager?token=<review-token>
```

The frontend preserves query strings through login. When a manager opens a token link while a different manager is already logged in, `ManagerDashboard.jsx` verifies the token, compares the intended `manager_id` to the current user, logs out the stale user, and redirects to login while preserving the link.

## Data Model

Core tables:

- `users`: full name, email, hashed password, role, optional `manager_id`.
- `refresh_tokens`: hashed refresh tokens for cookie-based access-token refresh.
- `submissions`: upload metadata, file path, original filename, `version_number`, optional `parent_submission_id`, review status.
- `submission_comments`: discussion thread entries with `submission_id`, `user_id`, message, and timestamp.
- `reviews`: one manager decision per submission. Review feedback now lives in `submission_comments`; `reviews.comment` may be null.
- `transaction_rows`: normalized financial transaction records linked to submissions.

Versioning:

- Original upload: `version_number = 1`, `parent_submission_id = null`.
- Re-upload: `version_number = max(existing versions) + 1`, `parent_submission_id = root submission id`.
- Managers can switch between versions in the review dashboard.

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
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `PATCH /api/auth/me`
- `POST /api/auth/change-password`

Agent:

- `POST /api/agent/login`
- `POST /api/agent/upload`

Uploads:

- `POST /api/uploads`
- `POST /api/uploads/{submission_id}/reupload`
- `GET /api/uploads`
- `GET /api/uploads/{upload_id}`

Submission comments:

- `GET /api/submissions/{submission_id}/comments`
- `POST /api/submissions/{submission_id}/comments`

Approvals:

- `GET /api/approvals/verify-token?token=...`
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
- `date_from` and `date_to` filter KPI data by `transaction_rows.transaction_date`.
- `status` filters KPI data by `transaction_rows.status` values: `Initiated`, `Pending`, `Successful`, or `Failed`.
- KPI status counts are transaction-row counts, not submission review-status counts.
- `Transaction Initiated` is the umbrella KPI: it equals all scoped transaction rows and all scoped transaction amount. `Pending`, `Successful`, and `Failed` are subsets of that initiated total.
- `totals.revenue` and `totals.total_amount` are grand totals across all transaction statuses. `totals.cash` and `totals.approved_amount` represent `Successful` transaction amount.
- Role scoping still comes from submissions/users: employees see their own rows, managers see assigned employees' rows, admins see all rows.
- Latest upload and latest transactions are intentionally most recent for the role scope and are not narrowed by the KPI date filter.

Health:

- `GET /health`

## Important Workflow Rules

Upload:

- Only employees can upload through `/api/uploads`.
- Upload creates a submission, persists typed transaction rows after parsing, and moves the submission into manager review when parsing succeeds.
- If an employee has a manager and email is enabled, the manager receives a review link.

Review:

- Only the assigned manager can review a submission.
- Only pending submissions can be reviewed.
- Approve does not require thread feedback.
- Reject and Request Re-upload require the manager to have added at least one comment in the submission thread first.
- Review actions create a `reviews` row and update `submissions.review_status`.

Re-upload:

- Only the owning employee can call `/api/uploads/{submission_id}/reupload`.
- It only works when the target submission status is `reupload_requested`.
- It is blocked if a newer version already exists.
- The new version is a new `submissions` row linked to the root submission.

Comments:

- Comments are access-scoped using the same upload visibility rules.
- Manager and employee comments send best-effort email notifications to the opposite party when SMTP is enabled.
- New comments broadcast a `new_comment` WebSocket event.

## WebSockets

Endpoint:

```text
/ws/{channel}
```

Current channels:

- `uploads`
- `manager`
- `dashboard`
- `comments`
- `submissions`

Current events include:

- `upload_progress`
- `upload.complete`
- `new_upload`
- `upload.new`
- `upload_status`
- `approval.decision`
- `upload_reviewed`
- `dashboard_refresh`
- `kpi.update`
- `new_comment`

The broadcaster is process-local. Multi-instance deployments need a shared bus such as Redis Pub/Sub or PostgreSQL LISTEN/NOTIFY.

## Development Notes

- Prefer existing patterns and endpoint shapes before adding new abstractions.
- Keep backend access rules mirrored in the frontend where useful, but backend checks are authoritative.
- When changing schema, update SQLAlchemy models, Alembic migrations, and this handoff/architecture docs. If `database/schema.sql` is still used for fresh DB initialization, keep it aligned too.
- When changing upload response shape, update `schemas.py`, `uploads.py`, frontend pages/components, and docs.
- Raw uploaded files are written to local disk or the Docker `backend_uploads` volume.
- Parsing runs as a FastAPI background task after the raw file is saved; the submission is `processing` until parsing succeeds or fails.
- Email sending is best-effort and disabled unless configured.
- The current WebSocket manager is in memory and single-process only.

## Verification Commands

Backend syntax check:

```powershell
py -3 -m compileall backend\app
```

Frontend build:

```powershell
cd frontend
npm.cmd run build
```

Docker rebuild:

```powershell
docker compose down
docker compose up --build --force-recreate
```
