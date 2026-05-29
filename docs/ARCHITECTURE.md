# LedgerFlow Analytics Architecture

## Current System Overview

**LedgerFlow Analytics** is an enterprise financial transaction management platform enabling employees to upload general-ledger spreadsheets, managers to review and approve submissions with real-time collaboration, comprehensive audit logging, intelligent alert detection, and role-based analytics dashboards.

The system has three primary layers:

- **React SPA**: Landing page with CTA, authentication workflows, protected routing, employee upload and submission management, real-time comment threads, transaction details, alert management with enrichment, manager review dashboard with approval queue, admin assignment and audit management, KPI analytics with charts.
- **FastAPI backend**: JWT and refresh-token authentication, role-based access control (RBAC), spreadsheet parsing and validation, review workflows, versioned re-uploads, submission comments with WebSocket broadcast, DTCD alert detection and enrichment, admin assignment and user management, complete audit logging, agent upload endpoints, analytics aggregation, optional email notifications.
- **PostgreSQL database**: users with role/manager_id, refresh tokens, submissions with versioning, reviews, comments, transaction rows, alerts with enrichment fields, immutable audit logs.

The active business flow captures financial transaction spreadsheets with a fixed GL schema, validates row-level data, persists normalized transactions, routes through a manager approval workflow with real-time collaboration, and maintains a complete immutable audit trail.


## Recent Updates (v2.0)

- **Landing Page** (`/`): Public hero section with CTA, auto-redirects authenticated users based on role
- **Settings Page** (`/settings`): Profile name update, secure password change, session management
- **Alerts Page** (`/alerts`): DTCD validation alerts with searchable/filterable UI, enriched transaction details modal, bulk read actions
- **Audit Page** (`/audit`, admin-only): Complete immutable audit log with user/action filters, timestamp tracking, compliance reporting
- **Upload Tracking**: Active upload ID tracking in refs to prevent race conditions and WebSocket event mismatches
- **Comment Threads**: Real-time WebSocket broadcast, email notifications (SMTP optional), modal-based UI with chat bubbles
- **Transaction Enrichment**: Alert API enriches alerts with matched transaction details (debit/credit accounts) when entry numbers resolve
- **Submission Transactions Endpoint**: `GET /api/uploads/{upload_id}/transactions` returns full transaction list for detailed review
- **Audit API** (`/api/audit`): Complete action log covering uploads, approvals, comments, assignments, logins with actor, timestamp, action type, target, detail
- **Admin Reassignment**: Drag-drop employee/manager reassignment workflow with persistence

```text
Browser
  React + Vite SPA (v19)
    Landing Page (public)
    AuthContext stores JWT session in localStorage
    Axios client sends Bearer tokens to /api/*
    Axios refreshes access token through /api/auth/refresh
    WebSocket client listens on /ws/{channel} for real-time updates
        |
        v
FastAPI API (Uvicorn)
  Auth router (/api/auth/*)
  Agent router (/api/agent/*)
  Upload router (/api/uploads/*)
  Comment router (/api/submissions/*/comments)
  Approval router (/api/approvals/*)
  Alert router (/api/alerts/*)
  Admin router (/api/admin/*)
  Audit router (/api/audit)
  Analytics router (/api/analytics/*)
  WebSocket router (/ws/{channel})
        |
        v
PostgreSQL 16
  users (role, manager_id)
  refresh_tokens
  submissions (version_number, parent_submission_id)
  submission_comments
  reviews
  transaction_rows
  alerts (entry_no, account_code, enrichment fields)
  audit_logs (immutable)
```

Local Docker Compose services:

- `postgres`: PostgreSQL 16 on host port `5433`
- `backend`: FastAPI on host port `8000`
- `frontend`: Vite dev server on host port `5173`
- Uploaded files live under the backend upload directory or `backend_uploads` Docker volume
- File parsing runs as a background FastAPI task

The backend container runs Alembic migrations on startup.

## User Roles & Permissions

The system supports three roles with distinct capabilities:

### Employee
- Register/login with `employee` role
- Upload `.xlsx` or `.csv` files with GL transaction data
- View own submissions, transaction previews, status, and version history
- Participate in comment threads with assigned manager
- Receive notifications on manager feedback, approvals, rejections
- Re-upload corrected versions when manager requests
- View personal analytics, KPI data, transaction history
- Access Settings page to update profile and password

### Manager
- Register/login with `manager` role
- View only assigned employee uploads and submissions
- Review submissions through Manager Dashboard with approval queue
- Participate in comment threads, provide feedback
- Approve submissions, reject with explanation, or request re-upload
- Receive email notifications on new submissions (SMTP-enabled)
- Receive system notifications on new comments
- Accept token-based manager review links from emails
- View assigned team analytics and KPI data
- Access Settings page

### Admin
- Seeded via `DEFAULT_ADMIN_EMAIL` and `DEFAULT_ADMIN_PASSWORD`
- View all users, submissions, transactions, analytics across the organization
- Assign employees to managers (one manager per employee)
- Reassign employees to different managers
- View system-wide audit log with comprehensive search/filter capabilities
- View and manage all alerts
- Access Settings page

**Access Control:**
- Frontend: `ProtectedRoute.jsx` redirects based on role
- Backend: `require_roles(...)` decorator validates JWT and role before API action
- Manager access is **assignment-scoped**: a manager can only view/comment on submissions where `employee.manager_id == manager.id`
- Admin access is **unrestricted**: sees all data

## Authentication Design

Authentication uses short-lived bearer JWTs plus refresh-token cookies.

Flow:

1. A user registers through `POST /api/auth/register` or logs in through `POST /api/auth/login`.
2. The backend validates credentials, stores a hashed refresh token, sets the `refresh_token` cookie, and returns an access token plus user profile.
3. The React `AuthContext` stores the access-token session under `ledgerflow_auth` in `localStorage`.
4. The Axios client adds `Authorization: Bearer <token>` to API requests.
5. On app load, `GET /api/auth/me` validates the stored token and refreshes the user context.
6. If a protected API returns `401`, the Axios client attempts `POST /api/auth/refresh`.
7. If refresh fails, the frontend clears local session state and redirects to `/login`.

Security implementation:

- Passwords are hashed with `passlib`.
- JWTs are signed with the configured algorithm, currently `HS256`.
- Access-token lifetime is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Refresh-token lifetime is currently 30 days in `backend/app/core/security.py`.
- Refresh tokens are stored as SHA-256 hashes in the `refresh_tokens` table.
- CORS origins are controlled by `CORS_ORIGINS`.
- Public registration allows `employee` and `manager` roles.
- Admin accounts are created through startup seeding from `DEFAULT_ADMIN_*`.
- If `AGENT_EMAIL` and `AGENT_PASSWORD` are configured, startup also seeds an employee account for the agent upload API.

Production validation in `backend/app/core/config.py` rejects unsafe default secrets, localhost database URLs, localhost CORS origins, weak admin passwords, and partially configured agent credentials.

## Email Review Links And Session Safety

Manager review links are generated in `backend/app/services/email.py`:

```text
{FRONTEND_BASE_URL}/manager?token=<signed-review-token>
```

The token contains:

- `submission_id`
- `manager_id`
- expiration
- purpose: `review_link`

Frontend behavior:

- `AuthPage.jsx` preserves the full requested destination including `pathname`, `search`, and `hash`.
- `ManagerDashboard.jsx` verifies `token` through `GET /api/approvals/verify-token`.
- If the currently logged-in manager id does not match the token's intended `manager_id`, the app logs out the stale user and redirects to login while preserving the original link.
- This prevents a browser session from opening a mail link under the previously logged-in manager.

## Frontend Structure

```text
frontend/
  src/
    api/
      client.js                    Axios API client with bearer token, auto-refresh, WebSocket helper
    auth/
      AuthContext.jsx              Login/register/logout/token validation and management
      ProtectedRoute.jsx           Route guard with role-based access control
    components/
      CommentThread.jsx            Real-time submission discussion thread with WebSocket updates
      DataTable.jsx                Reusable table component for preview, alerts, audit logs
      ProgressMilestones.jsx       Submission status and decision visualization
    hooks/
      useWebSocket.js              WebSocket subscription helper with auto-reconnect
    pages/
      AuthPage.jsx                 Login/Register UI with email, password, role selection
      LandingPage.jsx              Public hero page with CTA and authenticated user redirect
      UploadCenter.jsx             Drag-drop file upload, progress tracking, transaction preview, type filters
      SubmissionsPage.jsx          Submission history, kebab row actions (comments modal, transactions modal)
      Dashboard.jsx                KPI cards, analytics charts, transaction trends, recent activity
      AlertsPage.jsx               Alert listing, search/filter, enriched transaction details, bulk read
      SettingsPage.jsx             Profile name update, password change, session management
      ManagerDashboard.jsx         Approval queue (left panel), review panel (center), KPI cards (right), comment thread, approval actions
      AdminDashboard.jsx           Manager/employee listing, drag-drop assignment UI, reassignment workflow
      AuditPage.jsx                Searchable/filterable audit log with user, action type, date, detail
    shell/
      AppShell.jsx                 Authenticated app layout with topbar, collapsible sidebar, role-based nav
    main.jsx                       React Router tree, role-based home redirect, AppShell routing
    styles.css                     Global styles with design system tokens
```

**Current Route Map:**
```text
/            → Landing page; redirects to role home if authenticated
/login       → Public Auth page (login/register)
/dashboard   → Authenticated KPI and analytics dashboard
/uploads     → Authenticated file upload center
/submissions → Authenticated submission history with actions
/alerts      → Authenticated alert management
/settings    → Authenticated user settings
/manager     → Manager-only review dashboard with approval queue
/admin       → Admin-only user assignment dashboard
/audit       → Admin-only audit log viewer
```

## Backend Structure

```text
backend/
  app/
    api/
      auth.py              Register, login, refresh, logout, current user, profile update, password change
      uploads.py           Upload (multipart), re-upload, validation, listing, preview, transaction retrieval
      comments.py          Submission comment thread endpoints with WebSocket broadcast
      approvals.py         Approve, reject, request-reupload, review-link token verification
      alerts.py            List alerts, create alert, read/mark-all, enrichment fallback
      admin.py             Manager list, employee list, assign, reassign endpoints
      audit.py             Audit log retrieval with search/filter
      agent.py             Agent login and upload endpoints
      analytics.py         KPI aggregation, workflow totals, trends, role-scoped filtering
      websockets.py        WebSocket connection manager, channel broadcasting (/ws/{channel})
    core/
      config.py            Environment-backed settings, production validation, app initialization
      security.py          Password hashing (bcrypt), JWT signing, refresh token management, role checks
    db/
      session.py           Async SQLAlchemy engine and session factory
    services/
      email.py             SMTP notifications, manager review link generation
      excel_parser.py      Spreadsheet parsing, column normalization, GL transaction validation
      websocket_manager.py In-memory WebSocket broadcaster (channels, subscribe, broadcast, cleanup)
    models.py              SQLAlchemy ORM models and enums (users, submissions, comments, reviews, transactions, alerts, audit_logs)
    schemas.py             Pydantic request/response data contracts
    main.py                FastAPI app initialization, CORS, router registration, startup seeding
  alembic/
    versions/              Database migration scripts
    env.py                 Alembic configuration
  requirements.txt         Python dependencies (fastapi, sqlalchemy, pandas, pydantic, etc.)
```

**Key Design Patterns:**
- **Background Tasks**: File parsing runs async after upload persists
- **WebSocket Channels**: `uploads`, `manager`, `dashboard`, `comments`, `submissions` — broadcast-based (all subscribers get all events)
- **Role Scoping**: Queries filtered by user role in service layer
- **Soft Enrichment**: Alert enrichment fails gracefully for unmatchable entry numbers
- **Immutable Audit**: Audit logs append-only, never deleted or modified
    schemas.py         Pydantic request/response models
```

## Spreadsheet Contract

The upload pipeline supports `.xlsx` and `.csv`.

Required general-ledger columns:

- `date`
- `entry_no`
- `sub_account`
- `details`
- `account_code`
- `debit_amount` or `credit_amount`
- `class`
- `sub_class`
- `country`
- `region`

`excel_parser.py` normalizes common aliases such as `Entry no`, `Sub Account`, `Debit`, `Credit`, and `Account code`.

Validation behavior:

- Empty files are rejected.
- Unsupported extensions are rejected.
- Files over `MAX_UPLOAD_SIZE_MB` are rejected.
- Missing required columns are reported.
- Required cell values must be present.
- `entry_no` must parse into dotted group/line form such as `3.2`.
- Each row must have exactly one side populated: debit or credit, not both.
- Debit and credit values must be numeric when present.
- `date` must parse as a date.
- Up to 100 row-level validation errors are returned.

## Upload Processing Flow

1. An employee uploads a `.xlsx` or `.csv` file to `POST /api/uploads`.
2. The backend validates file extension, size, and non-empty content.
3. A `submissions` row is created with `review_status='processing'`, `version_number=1`, and no parent.
4. The raw file is written to the configured upload directory.
5. Pandas/OpenPyXL parses the spreadsheet.
6. `excel_parser.py` validates the required general-ledger schema.
7. Valid records are converted into typed `transaction_rows`.
8. Valid parsing persists rows, changes the submission to `pending`, and returns/refreshes preview data for review.
9. The upload UI filters `upload_progress`, `upload.complete`, and `upload.failed` WebSocket events by the active upload id ref, avoiding stale React closure races and cross-upload progress updates.
10. WebSocket events notify upload, manager, and dashboard clients.
11. If the uploading employee has an assigned manager and email is enabled, the manager receives a review notification.

Agent uploads reuse the same creation path through `POST /api/agent/upload`. Agent login through `POST /api/agent/login` only succeeds for employee accounts.

## Approval Workflow

Manager actions are handled through `backend/app/api/approvals.py`.

Available actions:

- Approve: `POST /api/approvals/{upload_id}/approve` or `POST /api/approvals/approve`
- Decline: `POST /api/approvals/{upload_id}/reject` or `POST /api/approvals/reject`
- Request re-upload: `POST /api/approvals/{upload_id}/request-reupload` or `POST /api/approvals/request-reupload`

Workflow:

1. A submission starts in `pending`.
2. The assigned manager reviews the parsed transaction rows and can discuss issues in the submission thread.
3. Approving changes `submissions.review_status` to `approved` and creates a `reviews` row.
4. Declining changes status to `declined`; the manager must first post feedback in the submission comment thread.
5. Requesting re-upload changes status to `reupload_requested`; the manager must first post feedback in the submission comment thread.
6. The database enforces one review per submission.
7. WebSocket events refresh upload status, manager queues, and dashboard KPIs.
8. If email is enabled, the uploading employee receives the review decision and can open LedgerFlow to see the thread.

Review feedback no longer lives primarily in `reviews.comment`. It lives in `submission_comments`. The `reviews.comment` column remains for compatibility but may be null.

Approved data is not copied into a separate table. All uploaded transaction rows stay in `transaction_rows`. Submission approval state is represented by `submissions.review_status`; transaction KPI state is represented by each row's `transaction_rows.status`.

## Submission Comment Thread

Submission comments are handled by `backend/app/api/comments.py`.

Endpoints:

- `GET /api/submissions/{submission_id}/comments`
- `POST /api/submissions/{submission_id}/comments`

Rules:

- Employees can comment on their own submissions.
- Managers can comment on submissions from assigned employees.
- Admins can access comments for all submissions.
- Access is checked using the same visibility rule as upload preview access.
- New comments broadcast a `new_comment` WebSocket event.
- When manager comments, employee gets a best-effort email notification.
- When employee comments, assigned manager gets a best-effort email notification.

Frontend:

- `CommentThread.jsx` fetches existing comments, subscribes to the `comments` WebSocket channel, and appends new real-time comments.
- `ManagerDashboard.jsx` embeds the thread in the review panel.
- `SubmissionsPage.jsx` opens each submission conversation in a modal from the row kebab menu. The modal shows existing comments as chat bubbles, a `No comments yet` empty state, and a textarea composer.

## Submissions Page Modals

The Submissions page uses a row kebab menu in the Actions column.

Actions:

- `Open comments`: opens a backdrop-close modal titled `Submission conversation`, includes a submission id badge, renders all existing comments as chat bubbles with author and timestamp, shows `No comments yet` when empty, and posts new comments through `POST /api/submissions/{submission_id}/comments`.
- `View transactions`: opens a backdrop-close modal with a plain spreadsheet-style table. It fetches rows from `GET /api/uploads/{upload_id}/transactions` and displays entry number, transaction id, account code, sub account, debit source, credit destination, debit amount, credit amount, difference, and simple colored status text.

## Re-Upload And Versioning Workflow

The schema already contains:

- `submissions.parent_submission_id`
- `submissions.version_number`

Endpoint:

- `POST /api/uploads/{submission_id}/reupload`

Rules:

- Only the employee who owns the submission can re-upload.
- The target submission must have status `reupload_requested`.
- If a newer version already exists, re-uploading the older version is blocked.
- A re-upload creates a new `submissions` row and new `transaction_rows`.
- The root submission is the first version. Later versions point to the root via `parent_submission_id`.
- The new version number is `max(existing version_number in the chain) + 1`.
- New versions start as `pending` for manager review.

Response behavior:

- `UploadPreview` includes `version_number`, `parent_submission_id`, and `version_history`.
- `UploadSummary` includes `version_number` and `parent_submission_id`.

Frontend:

- `SubmissionsPage.jsx` shows `Re-upload Required` and a `Re-upload` button for `reupload_requested` submissions.
- The button opens a file picker and posts multipart form data to `/api/uploads/{submission_id}/reupload`.
- `ManagerDashboard.jsx` shows version tabs (`v1`, `v2`, `v3`) when a submission has version history.
- Clicking a version tab loads that specific upload preview.

## Admin Assignment Workflow

Admin actions are handled through `backend/app/api/admin.py`.

Available actions:

- List managers: `GET /api/admin/managers`
- List employees: `GET /api/admin/employees`
- Assign employee: `POST /api/admin/assign`
- Reassign employee: `POST /api/admin/reassign`

Assignment behavior:

1. The admin dashboard loads manager and employee lists.
2. Managers are returned with assigned employee counts.
3. Employees are returned with current manager details and assignment status.
4. Assigning requires an employee id and manager id.
5. `assign` rejects employees who already have a manager.
6. `reassign` allows changing an existing assignment.
7. If email is enabled, assigned employees receive a manager assignment notification.

## Database Schema

Core tables:

- `users`: application users with email, hashed password, role, optional manager assignment, and creation timestamp.
- `refresh_tokens`: hashed refresh tokens, expiration, revoked flag, owning user.
- `submissions`: uploaded file metadata, file path, version metadata, parent submission reference, review status, and upload timestamp.
- `submission_comments`: discussion messages linked to a submission and user.
- `reviews`: manager decision and review timestamp. `comment` is nullable because feedback is stored in `submission_comments`.
- `transaction_rows`: normalized financial transaction rows linked to a submission.

Main relationships:

- `users.id` -> `submissions.user_id`
- `users.id` -> `reviews.manager_id`
- `users.id` -> `users.manager_id`
- `users.id` -> `submission_comments.user_id`
- `submissions.id` -> `reviews.submission_id`
- `submissions.id` -> `transaction_rows.submission_id`
- `submissions.id` -> `submission_comments.submission_id`
- `submissions.id` -> `submissions.parent_submission_id`
- `users.id` -> `refresh_tokens.user_id`

Important indexes and constraints:

- `idx_users_manager_id`
- `idx_submission_comments_submission_created`
- `uq_reviews_submission_id`
- transaction row indexes for submission, transaction id, date, and amount may exist depending on migration history.

Schema definitions are maintained in SQLAlchemy models and Alembic migrations under `backend/alembic/versions/`. Keep `database/schema.sql` aligned if it is still used for fresh database initialization outside Alembic.

## API Surface

Authentication:

- `POST /api/auth/register`: create an employee or manager and return a session.
- `POST /api/auth/login`: authenticate and return a session.
- `POST /api/auth/refresh`: rotate/refresh the access token using the refresh-token cookie.
- `POST /api/auth/logout`: revoke the refresh token and clear the cookie.
- `GET /api/auth/me`: return the current authenticated user.
- `PATCH /api/auth/me`: update the current user's account name.
- `POST /api/auth/change-password`: change current user's password.

Agent:

- `POST /api/agent/login`: authenticate an employee account for agent use and return a bearer token.
- `POST /api/agent/upload`: upload and parse a spreadsheet through the same upload pipeline. Requires `employee`.

Uploads:

- `POST /api/uploads`: upload and parse a new spreadsheet. Requires `employee`.
- `POST /api/uploads/{submission_id}/reupload`: upload a corrected version. Requires owning `employee` and `reupload_requested`.
- `GET /api/uploads`: list recent uploads with optional `status` filter. Requires `employee`, `manager`, or `admin`.
- `GET /api/uploads/{upload_id}`: fetch metadata, preview rows, and version history. Requires `employee`, `manager`, or `admin`, scoped by role.
- `GET /api/uploads/{upload_id}/transactions`: fetch all transaction rows for one submission. Requires `employee`, `manager`, or `admin`, scoped by the same preview access rule.

Submission comments:

- `GET /api/submissions/{submission_id}/comments`: fetch the comment thread.
- `POST /api/submissions/{submission_id}/comments`: add a comment.

Alerts:

- `GET /api/alerts`: list DTCD alerts with optional transaction-detail enrichment when an alert can be matched to a ledger row.
- `POST /api/alerts`: create a DTCD alert. Requires the configured agent account.
- `PATCH /api/alerts/{alert_id}/read`: mark one alert as read.
- `PATCH /api/alerts/read-all`: mark all alerts as read.

Approvals:

- `GET /api/approvals/verify-token`: validate a manager email review token.
- `POST /api/approvals/{upload_id}/approve`: approve a pending submission. Requires `manager`.
- `POST /api/approvals/{upload_id}/reject`: decline a pending submission. Requires `manager` and prior thread feedback.
- `POST /api/approvals/{upload_id}/request-reupload`: request a corrected upload. Requires `manager` and prior thread feedback.
- `POST /api/approvals/approve`: approve a pending submission by body `upload_id`. Requires `manager`.
- `POST /api/approvals/reject`: decline a pending submission by body `upload_id`. Requires `manager` and prior thread feedback.
- `POST /api/approvals/request-reupload`: request a corrected upload by body `upload_id`. Requires `manager` and prior thread feedback.

Admin:

- `GET /api/admin/managers`: list managers and assigned employee counts. Requires `admin`.
- `GET /api/admin/employees`: list employees and assignment status. Requires `admin`.
- `POST /api/admin/assign`: assign an unassigned employee to a manager. Requires `admin`.
- `POST /api/admin/reassign`: change an employee's manager assignment. Requires `admin`.

Analytics:

- `GET /api/analytics/kpis`: return transaction-date-scoped totals, workflow amounts, recent uploads, latest upload, latest transactions, transaction amount trend, and transaction trend data. Requires `employee`, `manager`, or `admin`.

Health:

- `GET /health`: backend health check.

## WebSocket Architecture

The backend exposes one dynamic WebSocket endpoint:

```text
/ws/{channel}
```

Current channels:

- `uploads`: upload progress and status changes.
- `manager`: new upload, review, and comment notifications for manager surfaces.
- `dashboard`: KPI and dashboard refresh notifications.
- `comments`: real-time submission comment thread updates.
- `submissions`: comment notifications for submission-history surfaces.

Current event names include:

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

Message shape:

```json
{
  "event": "new_comment",
  "payload": {
    "id": "uuid",
    "submission_id": "uuid",
    "user_id": "uuid",
    "user_name": "Manager Name",
    "user_role": "manager",
    "message": "Please fix row 23.",
    "created_at": "2026-05-21T10:30:00Z"
  }
}
```

The current WebSocket manager is in-memory, which is appropriate for a single backend process. Multi-instance deployment should replace or supplement it with Redis Pub/Sub, PostgreSQL LISTEN/NOTIFY, or another shared event bus.

## Analytics Model

`GET /api/analytics/kpis` aggregates KPI values from `transaction_rows` and applies role scope through the parent `submissions` rows.

Returned dashboard data includes:

- Total transaction count
- Transaction status counts from `transaction_rows.status`
- Total amount across all transaction statuses
- Successful transaction amount / cash total
- Initiated, pending, successful, and failed workflow amounts
- Recent uploads
- Latest upload metadata
- Latest upload transaction rows
- Full submission transaction rows through `GET /api/uploads/{upload_id}/transactions` for the Submissions page Excel-lite modal
- Latest upload transaction amount trend by transaction date
- Transaction trend grouped by `transaction_rows.transaction_date`

KPI status semantics:

- `Transaction Initiated` is the umbrella KPI. It equals all scoped transaction rows and all scoped transaction amount.
- `Pending`, `Successful`, and `Failed` are subsets of `Transaction Initiated`.
- `totals.uploads` is retained for frontend compatibility but represents total scoped transactions, not submission upload count.
- `totals.revenue` and `totals.total_amount` are grand totals across all statuses.
- `totals.cash` and `totals.approved_amount` represent `Successful` transaction amount.
- Latest upload and latest transactions remain most recent within the user's role scope and are intentionally not filtered by `date_from` / `date_to`.

Optional query filters:

- `status`: filters by `transaction_rows.status` values `Initiated`, `Pending`, `Successful`, or `Failed`.
- `date_from`: lower bound for `transaction_rows.transaction_date`.
- `date_to`: upper bound for `transaction_rows.transaction_date`.

Role scope:

- Employees only see their own submissions.
- Managers only see submissions from assigned employees.
- Admins see all submissions.

## Deployment Strategy

Development options:

- Run PostgreSQL with Docker Compose and run backend/frontend locally.
- Run all three services through Docker Compose.

Docker Compose services:

- `postgres`: PostgreSQL 16 Alpine.
- `backend`: FastAPI app served by Uvicorn on port `8000`.
- `frontend`: Vite build served through Nginx on port `5173`.

Production recommendations:

- Replace default JWT secret values before deployment.
- Replace default admin credentials before deployment.
- Use managed PostgreSQL with backups.
- Store uploaded files in object storage instead of local disk or a single Docker volume.
- Use Alembic migrations for controlled schema changes.
- Run FastAPI behind a production ASGI process manager or platform service.
- Serve the built frontend through Nginx, CDN, or static hosting.
- Configure SMTP only when notification email should be sent.
- Add structured logging, metrics, tracing, and alerting.

## Current Limitations

- WebSocket broadcasting is process-local.
- Upload parsing runs inline in the API request.
- Uploaded files are stored on local disk or a Docker volume.
- The app validates one fixed general-ledger transaction schema rather than arbitrary Excel structures.
- Email notifications are best-effort and disabled unless SMTP settings are configured.
- Automated backend and frontend tests are not yet present in the repository.
- Version history currently tracks submission metadata and rows per version; there is no side-by-side diff view yet.
- Review decisions are one per submission version.

## Roadmap

Phase 1: Current project level

- JWT auth and role-based access control.
- Refresh-token support.
- Employee upload flow for `.xlsx` and `.csv`.
- Financial transaction schema validation.
- Typed transaction row persistence.
- Manager approve, decline, and request-re-upload workflow.
- Thread-based review feedback.
- Employee re-upload/versioning flow.
- Admin manager assignment workflow.
- Optional SMTP notifications.
- Agent login/upload endpoint.
- KPI dashboard and WebSocket refresh events.
- Dockerized frontend, backend, and PostgreSQL services.

Phase 2: Stabilization

- Add automated backend and frontend tests.
- Improve validation feedback in the upload UI.
- Add audit views for review decisions and version history.
- Add side-by-side version diffing.
- Add transactional cleanup if file parsing fails after the raw file has been written.

Phase 3: Scale and reliability

- Move parsing into a background worker.
- Add chunked uploads and cancellation.
- Add object storage for raw uploads.
- Add Redis-backed WebSocket fanout.
- Add observability and production-grade logging.

Phase 4: Enterprise features

- Multi-tenant isolation.
- Advanced dashboard filters and drill-down reporting.
- Export workflows for approved or declined submissions.
- Configurable schema mappings.
- Notification integrations for review requests.
