# LedgerFlow Analytics Architecture

## Current System Overview

LedgerFlow Analytics is a full-stack financial transaction upload, validation, approval, discussion, re-upload, assignment, and analytics platform.

The system has three primary layers:

- React SPA: authentication, protected routing, employee upload workflow, submission history, comment threads, manager review dashboard, admin assignment dashboard, and KPI analytics.
- FastAPI backend: JWT and refresh-token authentication, role-based access control, spreadsheet parsing, validation, review workflow, versioned re-uploads, submission comments, admin assignment, agent upload endpoints, analytics aggregation, optional email notifications, and WebSocket notifications.
- PostgreSQL database: users, refresh tokens, manager assignments, submissions, reviews, submission comments, and normalized transaction rows.

The active business flow expects a financial transaction spreadsheet with a fixed schema and stores each valid row in typed transaction columns.

## Runtime Architecture

```text
Browser
  React + Vite SPA
    AuthContext stores JWT session in localStorage
    Axios client sends Bearer tokens to /api/*
    Axios refreshes access token through /api/auth/refresh
    WebSocket client listens on /ws/{channel}
        |
        v
FastAPI API
  Auth router
  Agent router
  Upload router
  Comment router
  Approval router
  Admin router
  Analytics router
  WebSocket router
        |
        v
PostgreSQL
  users
  refresh_tokens
  submissions
  submission_comments
  reviews
  transaction_rows
```

Local Docker Compose services:

- `postgres`: PostgreSQL 16 on host port `5433`.
- `backend`: FastAPI on host port `8000`.
- `frontend`: built frontend served on host port `5173`.
- Uploaded files live under the backend upload directory or the `backend_uploads` Docker volume.

The backend container runs Alembic migrations on startup:

```text
alembic -c alembic.ini upgrade head
```

## User Roles

The system supports three roles:

- `employee`: can register/login, upload financial transaction spreadsheets, list own uploads, view own upload previews, comment on own submissions, re-upload when requested, and view scoped analytics.
- `manager`: can register/login, view assigned employee uploads and analytics, comment on assigned submissions, approve submissions, decline submissions, or request re-upload.
- `admin`: is seeded from environment settings, can list managers, list employees, assign employees to managers, reassign employees, view uploads, and view analytics.

Protected routes are enforced in both layers:

- Frontend: `ProtectedRoute.jsx` redirects unauthenticated users to `/login`, blocks non-managers from `/manager`, and blocks non-admins from `/admin`.
- Backend: `require_roles(...)` validates the JWT and checks the user role before protected API actions run.

Manager access is assignment-scoped. A manager can only list, preview, comment on, or review submissions where the uploading employee's `manager_id` equals that manager's user id.

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
      client.js              Axios API client, refresh handling, WebSocket URL helper
    auth/
      AuthContext.jsx        Login/register/logout/session validation
      ProtectedRoute.jsx     Route guard and role guard
    components/
      CommentThread.jsx      Submission discussion thread with real-time updates
      DataTable.jsx          Reusable table for preview and dashboard data
      ProgressMilestones.jsx Upload/review progress UI
    hooks/
      useWebSocket.js        WebSocket subscription helper
    pages/
      AdminDashboard.jsx     Admin manager/employee assignment UI
      AuthPage.jsx           Login and registration UI
      Dashboard.jsx          KPI and analytics dashboard
      ManagerDashboard.jsx   Review queue, deep links, comments, version tabs, actions
      SubmissionsPage.jsx    Employee upload history, comments, re-upload action
      UploadCenter.jsx       File upload and validation preview
    shell/
      AppShell.jsx           Authenticated app layout/navigation
    main.jsx                 Route tree and app bootstrap
    styles.css               Global application styling
```

Current route map:

```text
/            -> redirects to role home or /login
/login       -> public login/register page
/dashboard   -> authenticated employee, manager, or admin dashboard
/uploads     -> authenticated employee, manager, or admin upload center route
/submissions -> authenticated employee, manager, or admin submission history
/settings    -> authenticated account settings
/manager     -> manager-only review dashboard
/admin       -> admin-only assignment dashboard
```

## Backend Structure

```text
backend/
  app/
    api/
      admin.py         Manager/employee listing and assignment endpoints
      agent.py         Agent login and upload endpoints
      analytics.py     KPI, workflow totals, trends, latest transactions
      approvals.py     Approve, decline, request-reupload, review-link verification
      auth.py          Register, login, refresh, logout, current user, settings
      comments.py      Submission discussion thread endpoints
      uploads.py       Upload, re-upload, validation, preview, listing, versions
      websockets.py    /ws/{channel} endpoint
    core/
      config.py        Environment-backed settings and production validation
      security.py      Password hashing, JWTs, refresh tokens, role dependencies
    db/
      session.py       Async SQLAlchemy engine/session
    services/
      email.py               Optional SMTP notifications and review links
      excel_parser.py        Spreadsheet parsing and financial validation
      websocket_manager.py   In-memory WebSocket channel broadcaster
    main.py            FastAPI app, CORS, routers, startup account seeding
    models.py          SQLAlchemy models and enums
    schemas.py         Pydantic request/response models
```

## Spreadsheet Contract

The upload pipeline supports `.xlsx` and `.csv`.

Required financial transaction columns:

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

Validation behavior:

- Empty files are rejected.
- Unsupported extensions are rejected.
- Files over `MAX_UPLOAD_SIZE_MB` are rejected.
- Missing required columns are reported.
- Required cell values must be present.
- `amount` must be numeric and greater than zero.
- `transaction_date` must parse as a date.
- Enum fields must match the allowed values.
- Up to 100 row-level validation errors are returned.

## Upload Processing Flow

1. An employee uploads a `.xlsx` or `.csv` file to `POST /api/uploads`.
2. The backend validates file extension, size, and non-empty content.
3. A `submissions` row is created with `review_status='processing'`, `version_number=1`, and no parent.
4. The raw file is written to the configured upload directory.
5. Pandas/OpenPyXL parses the spreadsheet.
6. `excel_parser.py` validates the required financial transaction schema.
7. Valid records are converted into typed `transaction_rows`.
8. Valid parsing persists rows, changes the submission to `pending`, and returns/refreshes preview data for review.
9. WebSocket events notify upload, manager, and dashboard clients.
10. If the uploading employee has an assigned manager and email is enabled, the manager receives a review notification.

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
- `SubmissionsPage.jsx` lets employees open a conversation for each submission.

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

Submission comments:

- `GET /api/submissions/{submission_id}/comments`: fetch the comment thread.
- `POST /api/submissions/{submission_id}/comments`: add a comment.

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
- The app validates one fixed financial transaction schema rather than arbitrary Excel structures.
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
