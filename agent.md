# LedgerFlow Analytics Agent Handoff

This file is a compact briefing for another LLM or coding agent working in this repository. Treat it as the first context file to read before making changes.

## Project Summary

**LedgerFlow Analytics** is an enterprise financial transaction management platform enabling employees to upload general-ledger data, managers to review and approve submissions with real-time collaboration, comprehensive audit logging, intelligent alert detection, and role-based analytics dashboards. The system provides end-to-end transaction lifecycle management with full compliance and auditability.

Employees upload `.xlsx` or `.csv` files that match a fixed general-ledger transaction schema. The backend validates the file, stores typed transaction rows in PostgreSQL, and creates a pending submission. Assigned managers review submissions, discuss corrections in a submission thread, approve, decline, or request re-upload. Employees can re-upload corrected versions when requested. Admin users assign employees to managers, track system audit logs, and manage alerts. The frontend shows role-specific dashboards and receives live refresh events over WebSockets.

## Tech Stack

- **Frontend**: React 19, Vite, React Router, Axios, Recharts, React Icons, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy async, Pydantic, Pandas, OpenPyXL, Uvicorn, WebSockets
- **Database**: PostgreSQL 16 with Alembic migrations
- **Orchestration**: Docker Compose for local development, Railway/Docker for production

## Platform Pages & Features

### Public Pages
- **Landing Page** (`/`) — Hero section with "Get Started" CTA, auto-redirects authenticated users to role-specific home

### Authenticated Pages (All Roles)
- **Dashboard** (`/dashboard`) — KPI cards, analytics charts, upload activity trends, recent transactions
- **Upload Center** (`/uploads`) — Drag-drop file upload, transaction preview with type filters, validation progress
- **Submissions** (`/submissions`) — Submission history table with row actions (View Comments, View Transactions, Re-upload)
- **Alerts** (`/alerts`) — DTCD validation alerts with searchable/filterable UI, transaction enrichment, bulk read actions
- **Settings** (`/settings`) — Profile name update, password change, session management

### Manager Pages
- **Manager Dashboard** (`/manager`) — Approval queue (left panel), KPI cards (top-right), review panel with comment thread, action buttons (Approve/Reject/Request Re-upload)

### Admin Pages
- **Admin Dashboard** (`/admin`) — Manager/employee list, drag-drop assignment UI, reassignment workflow
- **Audit Page** (`/audit`) — Searchable audit log with action type filters, user actor tracking, timestamp and detail view

## Important Paths

### Frontend
- `frontend/src/main.jsx` — React Router tree, role-based home redirect
- `frontend/src/auth/AuthContext.jsx` — Login, register, logout, token refresh
- `frontend/src/auth/ProtectedRoute.jsx` — Role-based route guard
- `frontend/src/shell/AppShell.jsx` — Authenticated app layout with topbar/sidebar
- `frontend/src/pages/AuthPage.jsx` — Login/Register UI with email + password, role selection
- `frontend/src/pages/LandingPage.jsx` — Hero landing with authenticated user redirect
- `frontend/src/pages/UploadCenter.jsx` — File upload, progress tracking, transaction preview with type filters
- `frontend/src/pages/SubmissionsPage.jsx` — Submission history table with kebab actions (comments modal, transactions modal, re-upload)
- `frontend/src/pages/ManagerDashboard.jsx` — Approval queue, review panel, comment thread, manager actions
- `frontend/src/pages/Dashboard.jsx` — KPI cards, charts, analytics
- `frontend/src/pages/AlertsPage.jsx` — Alert list with search/filter, enriched transaction details, bulk read
- `frontend/src/pages/SettingsPage.jsx` — Profile and password management
- `frontend/src/pages/AdminDashboard.jsx` — User assignment/reassignment UI
- `frontend/src/pages/AuditPage.jsx` — Searchable, filterable audit log
- `frontend/src/components/CommentThread.jsx` — Reusable submission discussion thread with WebSocket updates
- `frontend/src/components/DataTable.jsx` — Reusable spreadsheet-style table component
- `frontend/src/components/ProgressMilestones.jsx` — Visual submission status/decision indicator
- `frontend/src/api/client.js` — Axios API client, bearer token interceptor, refresh-token retry, WebSocket URL helper

### Backend
- `backend/app/main.py` — FastAPI app, CORS, routers, startup seeded accounts, health endpoint
- `backend/app/api/auth.py` — Registration, login, refresh, logout, current user, account settings, password change
- `backend/app/api/uploads.py` — Upload parsing, re-upload flow, row persistence, listing, preview, version history, access checks, and integration with the Agentic AI Pipeline via optional `use_agents` parameter
- `backend/app/api/comments.py` — Submission comment APIs, WebSocket broadcast, email notification
- `backend/app/api/approvals.py` — Manager review actions (approve/reject/request-reupload), review-link token verification
- `backend/app/api/alerts.py` — DTCD validation alerts, alert creation, read/mark-all, optional transaction enrichment
- `backend/app/api/admin.py` — Admin manager list, employee list, assign, reassign endpoints
- `backend/app/api/audit.py` — Audit log retrieval and filtering
- `backend/app/api/agent.py` — API surface for posting/upload agent interactions
- `backend/app/api/analytics.py` — KPI aggregation with date/status filtering, role scoping
- `backend/app/api/websockets.py` — WebSocket connection manager, channel broadcasting
- `backend/app/services/excel_parser.py` — Spreadsheet parsing, column name normalization, transaction validation
- `backend/app/services/email.py` — SMTP notifications and manager review links
- `backend/app/services/websocket_manager.py` — In-memory WebSocket channel broadcaster
- `backend/app/models.py` — SQLAlchemy models, enums, relationships
- `backend/app/schemas.py` — Pydantic request/response contracts
- `backend/alembic/versions/` — Database migrations

### Documentation
- `docs/ARCHITECTURE.md` — Detailed system design, data model, endpoints, WebSocket channels, deployment notes
- `docs/RAILWAY_DEPLOYMENT.md` — Production deployment instructions
- `DESIGN_SYSTEM.md` — UI design tokens, colors, typography, component patterns
- `DESIGN_QUICK_REFERENCE.md` — Quick-reference guide for UI development


## Current Features (Latest)

### Frontend
- **Landing Page** — Public hero with CTA, auto-redirects authenticated users
- **Upload Center** — Drag-drop upload with real-time progress, transaction preview with type filters, and a toggle switch to run the Agentic AI Pipeline
- **Submissions Page** — History table with kebab actions (comments modal, transactions modal, re-upload button)
- **Alerts Page** — DTCD validation alerts, searchable/filterable UI, transaction enrichment modals, bulk read actions
- **Manager Dashboard** — Approval queue left panel, KPI right panel, comment thread, review actions
- **Admin Dashboard** — Manager/employee assignment with drag-drop workflow
- **Audit Page** — Searchable audit log with user/action type filters, timestamp tracking
- **Settings Page** — Profile name update, password change, session management
- **Real-time Updates** — WebSocket-driven comment threads, approval notifications, KPI refreshes
- **Automatic Viewport Scaling** — Dynamically scales the entire application layout based on screen size for desktop viewports (>1024px) targeting a base layout width of 1536px. It utilizes a CSS transform scale applied to the `#root` element combined with dynamic width/height calculations, ensuring a seamless, responsive layout that fits the screen without leaving white margin gaps on Safari or Chrome, and maintains natural document scrolling (vertical scrollbars remain fully functional across all browsers).

### Backend
- **Audit API** — Immutable log of all actions (uploads, approvals, comments, assignments, logins)
- **Alerts API** — DTCD validation, alert creation, read/mark-all, transaction enrichment (with fallback)
- **Enhanced Comments** — WebSocket broadcast on new comments, email notifications
- **Role Scoping** — Employees see own data, managers see assigned team data, admins see all
- **Version History** — Full re-upload chain tracking with parent_submission_id
- **Token Verification** — Manager review link validation with session checks
- **Agentic AI Pipeline Integration** — Dynamic invocation of the sibling `agentic-ai-pipeline` graph during uploads using an optional `use_agents` toggle. Bypasses HTTP upload loopback and customizes output paths to prevent concurrency conflicts, storing clean/repaired transactions directly under the submission ID.

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

## Role Permissions

### Employee
- Register/login with `employee` role
- Upload `.xlsx` or `.csv` files
- View own submissions and transaction preview
- Comment on own submissions, receive manager feedback
- Re-upload when manager requests
- View personal analytics and KPI data
- View personal transaction history

### Manager
- Register/login with `manager` role
- View assigned employee submissions via dashboard
- Review submissions with approval queue
- Comment on assigned submissions with thread discussion
- Approve, reject, or request re-upload
- Receive email notifications on new submissions (SMTP enabled)
- View assigned team analytics and KPI data
- Accept token-based review links for deep-linking from emails

### Admin
- Seeded via `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD`
- Assign employees to managers (one manager per employee)
- Reassign employees to different managers
- View all uploads, submissions, transactions, and analytics
- View system-wide audit log with user/action filtering
- Manage user access and role permissions

## Auth And Deep-Link Notes

The session is stored in `localStorage` under `ledgerflow_auth`. The API also uses a refresh-token cookie.

Manager email links are generated as:

```text
{FRONTEND_BASE_URL}/manager?token=<review-token>
```

The frontend preserves query strings through login. When a manager opens a token link while a different manager is already logged in, `ManagerDashboard.jsx` verifies the token, compares the intended `manager_id` to the current user, logs out the stale user, and redirects to login while preserving the link.

## Data Model

### Core Tables
- `users` — Full name, email, hashed password, role (employee/manager/admin), optional manager_id
- `refresh_tokens` — Hashed refresh tokens for cookie-based token refresh
- `submissions` — Upload metadata, file path, original filename, version_number, optional parent_submission_id, review_status (`processing`, `initiated` (draft), `pending`, `approved`, `declined`, `parse_failed`, `reupload_requested`)
- `submission_comments` — Discussion thread entries with submission_id, user_id, message, timestamp
- `reviews` — Manager decision per submission (approve/reject/reupload_requested), timestamp
- `transaction_rows` — Parsed GL transaction records: entry_no, account_code, sub_account, debit/credit amounts, status, timestamp, dtcd_difference, validation_messages, repairs_applied
- `alerts` — DTCD validation failures: entry_no, account_code, difference, status, read_at, optional transaction_detail enrichment
- `audit_logs` — Immutable log: user_id, action, target_type, target_id, detail, timestamp

### Versioning
- Original upload: `version_number = 1`, `parent_submission_id = null`
- Re-upload: `version_number = max(existing) + 1`, `parent_submission_id = root submission id`
- Managers can switch between versions in review dashboard

## Spreadsheet Schema

**Supported formats:** `.xlsx`, `.csv`

**Required columns (with common aliases normalized):**
- `date` (aliases: Date, transaction_date)
- `entry_no` (aliases: Entry No, Entry Number)
- `account_code` (aliases: Account Code, Code)
- `sub_account` (aliases: Sub Account, SubAccount)
- `details` (aliases: Details, Description)
- `debit_amount` or `credit_amount` (aliases: Debit, Credit, Amount Debit, Amount Credit)
- `class` (aliases: Class, Classification)
- `sub_class` (aliases: Sub Class, SubClass)
- `country` (aliases: Country, Ctry)
- `region` (aliases: Region, Rgn)

**AI Agent Pipeline Enrichment Columns (optional):**
- `dtcd_difference` / `dtcd difference` (Debit-Credit Transaction Difference)
- `validation_messages` / `validation messages` (AI pipeline validation/warning notes)
- `repairs_applied` / `repairs applied` (Specific repair action done by the agent)

**Validation Rules:**
- Reject empty files, unsupported extensions, oversized files
- Require all columns; normalize aliases
- Validate entry_no format (numeric or dotted notation)
- Each row must have debit XOR credit (not both, not neither)
- Amounts must be numeric
- Date must be parsable
- **DTCD Tolerance Check**: A validation alert is generated in the Manager's Validation Alerts page only if the absolute value of the debit-credit difference (`dtcd_difference`) exceeds a 1% tolerance threshold compared to the transaction amount (calculated as: `abs(dtcd_difference) > 0.01 * max(debit_amount, credit_amount)`).

## API Reference

**Base URL:** `http://localhost:8000/api`

### Auth
- `POST /auth/register` — Register employee/manager
- `POST /auth/login` — Get JWT token
- `POST /auth/refresh` — Refresh access token
- `POST /auth/logout` — Logout
- `GET /auth/me` — Current user
- `PATCH /auth/me` — Update profile (name)
- `POST /auth/change-password` — Change password

### Uploads
- `POST /uploads` — Upload file (employee only). File is parsed and saved under `initiated` (draft) status.
- `GET /uploads` — List user's submissions
- `GET /uploads/{upload_id}` — Get submission details
- `GET /uploads/{upload_id}/transactions` — Get all transaction rows for submission
- `POST /uploads/{submission_id}/reupload` — Submit re-upload (employee only)
- `POST /uploads/{upload_id}/submit` — Finalize and submit draft to manager, transitioning it from `initiated` to `pending` status (employee only)

### Comments
- `GET /submissions/{submission_id}/comments` — Fetch thread
- `POST /submissions/{submission_id}/comments` — Post comment

### Approvals
- `POST /approvals/approve` — Approve submission (manager only)
- `POST /approvals/reject` — Reject submission (manager only)
- `POST /approvals/request-reupload` — Request re-upload (manager only)
- `GET /approvals/verify-token?token=...` — Verify manager review link

### Alerts
- `GET /alerts` — List alerts
- `POST /alerts` — Create alert
- `PATCH /alerts/{alert_id}/read` — Mark alert read
- `PATCH /alerts/read-all` — Mark all alerts read

### Analytics
- `GET /analytics/kpis` — KPI data with optional date_from, date_to, status filters

### Audit
- `GET /audit` — Audit log (admin only)

### Admin
- `GET /admin/managers` — List managers (admin only)
- `GET /admin/employees` — List employees (admin only)
- `POST /admin/assign` — Assign employee to manager (admin only)
- `POST /admin/reassign` — Reassign employee (admin only)

## Important Workflow Rules

Upload:

- Only employees can upload through `/api/uploads`.
- Upload creates a submission, persists typed transaction rows after parsing, and sets the submission status to `initiated` (draft).
- The employee can preview the parsed/cleaned data in the Upload Center and must click "Approve & Submit to Manager" (`POST /uploads/{upload_id}/submit`) to promote the submission status to `pending`.
- Once promoted to `pending`, the submission moves into manager review, triggers real-time WebSocket notifications, and sends review links to the assigned manager (if email is enabled).
- Rows with non-zero `dtcd_difference` exceeding the 1% tolerance threshold generate validation alerts which are pushed directly to the manager's Validation Alerts view.

Review:

- Only the assigned manager can review a submission.
- Only pending submissions can be reviewed.
- Managers only see submissions in their queue that have been promoted to a non-draft state (i.e. review_status is not `initiated`). Drafts remain hidden from their workspace until submitted by the employee.
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
- `SubmissionsPage.jsx` opens comments in a modal with chat bubbles and a composer; it also opens an Excel-lite transactions modal powered by `GET /api/uploads/{upload_id}/transactions`.

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
- `upload.failed`
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
- `UploadCenter.jsx` tracks the active upload id in a ref so `upload_progress`, `upload.complete`, and `upload.failed` WebSocket events cannot be missed by a stale React closure or applied to the wrong upload.
- Alert transaction enrichment must fail soft for legacy/simple `entry_no` values; not every alert entry number has the dotted `group.line` shape.
- Email sending is best-effort and disabled unless configured.
- The current WebSocket manager is in memory and single-process only.
- **Automatic Viewport Scaling**: Implemented globally inside `main.jsx` and `styles.css`. It dynamically listens to window resize events on desktop screens (>1024px) and calculates a scale factor targeting a 1536px width layout. The scale is set as a CSS custom variable `--app-scale` on the document root. The React `#root` element is scaled using a CSS transform (`transform: scale(var(--app-scale))`) with adjusted dimensions (`calc(100% / var(--app-scale))`) to fit the viewport width exactly, while letting the page flow naturally to preserve native vertical scrolling.
- **Table Responsive Containment**: Restructured `.data-table-card` and `.data-table-scroll` in `styles.css` with `max-width: 100%` and `overflow-x: auto` to contain wide data previews (such as the 10-column general ledger table). This prevents tables from horizontally stretching parent containers beyond the client viewport boundaries and ensures elements like topbars and action buttons remain fully visible on the screen, while letting columns scroll inside the card.

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
