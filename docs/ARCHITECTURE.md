# ExcelFlow Analytics Architecture

## Current System Overview

ExcelFlow Analytics is a full-stack financial transaction upload, validation, approval, and analytics platform.

The current project is built around three main application layers:

- React SPA: authentication, protected routing, employee upload workflow, KPI dashboard, and manager review dashboard.
- FastAPI backend: JWT authentication, role-based access control, spreadsheet parsing, validation, review workflow, analytics aggregation, and WebSocket notifications.
- PostgreSQL database: users, submissions, manager reviews, and normalized transaction rows.

The active business flow is no longer a generic Excel-to-JSON staging system. The app now expects a financial transaction spreadsheet with a fixed schema and stores each valid row in typed transaction columns.

## Runtime Architecture

```text
Browser
  React + Vite SPA
    AuthContext stores JWT session in localStorage
    Axios client sends Bearer tokens to /api/*
    WebSocket client listens on /ws/{channel}
        |
        v
FastAPI API
  Auth router
  Upload router
  Approval router
  Analytics router
  WebSocket router
        |
        v
PostgreSQL
  users
  submissions
  reviews
  transaction_rows
```

Local development can run either as separate services or through Docker Compose:

- PostgreSQL runs on host port `5433`.
- Backend runs on port `8000`.
- Frontend runs on port `5173`.
- Uploaded files are stored under the backend upload directory, or in the `backend_uploads` Docker volume.

## User Roles

The system currently supports two roles:

- `employee`: can register/login, upload financial transaction spreadsheets, list uploads, view upload previews, and view analytics.
- `manager`: can register/login, view upload previews and analytics, approve submissions, decline submissions, or request reupload with comments.

Protected routes are enforced in both layers:

- Frontend: `ProtectedRoute.jsx` redirects unauthenticated users to `/login` and blocks non-managers from `/manager`.
- Backend: `require_roles(...)` validates the JWT and checks the user role before protected API actions run.

## Authentication Design

Authentication uses bearer JWTs.

Flow:

1. A user registers through `POST /api/auth/register` or logs in through `POST /api/auth/login`.
2. The backend validates credentials and returns an access token plus user profile.
3. The React `AuthContext` stores the session under `excelflow_auth` in `localStorage`.
4. The Axios client adds `Authorization: Bearer <token>` to API requests.
5. On app load, `GET /api/auth/me` validates the stored token and refreshes the user context.
6. If the API returns an unexpected `401`, the frontend clears the session and redirects to `/login`.

Security implementation:

- Passwords are hashed with `passlib` using `pbkdf2_sha256`.
- JWTs are signed with `HS256`.
- Token lifetime is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES`.
- CORS origins are controlled by `CORS_ORIGINS`.

## Frontend Structure

```text
frontend/
  src/
    api/
      client.js              Axios API client and WebSocket URL helper
    auth/
      AuthContext.jsx        Login/register/logout/session validation
      ProtectedRoute.jsx     Route guard and role guard
    components/
      DataTable.jsx          Reusable table for preview and dashboard data
    hooks/
      useWebSocket.js        WebSocket subscription helper
    pages/
      AuthPage.jsx           Login and registration UI
      Dashboard.jsx          KPI and analytics dashboard
      ManagerDashboard.jsx   Review queue and approval actions
      UploadCenter.jsx       File upload and validation preview
    shell/
      AppShell.jsx           Authenticated app layout/navigation
    main.jsx                 Route tree and app bootstrap
    styles.css               Global application styling
```

Current route map:

```text
/          -> redirects to /dashboard or /login
/login     -> public login/register page
/dashboard -> authenticated employee or manager dashboard
/uploads   -> authenticated employee or manager upload center
/manager   -> manager-only review dashboard
```

## Backend Structure

```text
backend/
  app/
    api/
      analytics.py     KPI, workflow totals, trends, latest transactions
      approvals.py     Approve, decline, and request-reupload actions
      auth.py          Register, login, current-user endpoints
      uploads.py       Spreadsheet upload, validation, preview, listing
      websockets.py    /ws/{channel} endpoint
    core/
      config.py        Environment-backed settings
      security.py      Password hashing, JWTs, role dependencies
    db/
      session.py       Async SQLAlchemy engine/session
    services/
      excel_parser.py        Spreadsheet parsing and financial validation
      websocket_manager.py   In-memory WebSocket channel broadcaster
    main.py            FastAPI app, CORS, routers, startup table creation
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
3. A `submissions` record is created with `review_status='pending'`.
4. The raw file is written to the configured upload directory.
5. Pandas/OpenPyXL parses the spreadsheet.
6. `excel_parser.py` validates the required financial transaction schema.
7. Valid records are converted into typed `transaction_rows`.
8. The upload returns a preview response with columns, row count, detected types, validation metadata, and preview rows.
9. WebSocket events notify upload, manager, and dashboard clients.

## Approval Workflow

Manager actions are handled through `backend/app/api/approvals.py`.

Available actions:

- Approve: `POST /api/approvals/{upload_id}/approve`
- Decline: `POST /api/approvals/{upload_id}/reject`
- Request reupload: `POST /api/approvals/{upload_id}/request-reupload`

Workflow:

1. A submission starts in `pending`.
2. A manager reviews the parsed transaction rows.
3. Approving changes `submissions.review_status` to `approved` and creates a `reviews` row.
4. Declining changes status to `declined`; a comment is required.
5. Requesting reupload changes status to `reupload_requested`; a comment is required.
6. The database enforces one review per submission.
7. WebSocket events refresh upload status, manager queues, and dashboard KPIs.

Unlike the earlier architecture, approved data is not copied into a separate `approved_transactions` table. All uploaded transaction rows stay in `transaction_rows`, and approval state is represented by the parent `submissions.review_status`.

## Database Schema

Core tables:

- `users`: application users with email, hashed password, and role.
- `submissions`: uploaded file metadata, file path, version metadata, parent submission reference, review status, and upload timestamp.
- `reviews`: manager decision, required comments for non-approval actions, and review timestamp.
- `transaction_rows`: normalized financial transaction rows linked to a submission.

Main relationships:

- `users.id` -> `submissions.user_id`
- `users.id` -> `reviews.manager_id`
- `submissions.id` -> `reviews.submission_id`
- `submissions.id` -> `transaction_rows.submission_id`
- `submissions.id` -> `submissions.parent_submission_id`

Important indexes:

- `idx_submissions_user_uploaded`
- `idx_submissions_status_uploaded`
- `idx_submissions_parent`
- `idx_reviews_manager_reviewed`
- `idx_transaction_rows_submission`
- `idx_transaction_rows_transaction_id`
- `idx_transaction_rows_date`
- `idx_transaction_rows_amount`

## API Surface

Authentication:

- `POST /api/auth/register`: create a user and return a JWT session.
- `POST /api/auth/login`: authenticate and return a JWT session.
- `GET /api/auth/me`: return the current authenticated user.

Uploads:

- `POST /api/uploads`: upload and parse a spreadsheet. Requires `employee`.
- `GET /api/uploads`: list recent uploads with optional `status` filter. Requires `employee` or `manager`.
- `GET /api/uploads/{upload_id}`: fetch metadata and preview rows. Requires `employee` or `manager`.

Approvals:

- `POST /api/approvals/{upload_id}/approve`: approve a pending submission. Requires `manager`.
- `POST /api/approvals/{upload_id}/reject`: decline a pending submission with comment. Requires `manager`.
- `POST /api/approvals/{upload_id}/request-reupload`: request a corrected upload with comment. Requires `manager`.

Analytics:

- `GET /api/analytics/kpis`: return totals, workflow amounts, recent uploads, latest upload, latest transactions, transaction amount trend, and upload trend data. Requires `employee` or `manager`.

Health:

- `GET /health`: backend health check.

## WebSocket Architecture

The backend exposes one dynamic WebSocket endpoint:

```text
/ws/{channel}
```

Current channels:

- `uploads`: upload progress and status changes.
- `manager`: new upload and review notifications.
- `dashboard`: KPI and dashboard refresh notifications.

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

Message shape:

```json
{
  "event": "dashboard_refresh",
  "payload": {
    "upload_id": "uuid",
    "status": "approved",
    "filename": "transactions.xlsx"
  }
}
```

The current WebSocket manager is in-memory, which is appropriate for a single backend process. Multi-instance deployment should replace or supplement it with Redis Pub/Sub, PostgreSQL LISTEN/NOTIFY, or another shared event bus.

## Analytics Model

`GET /api/analytics/kpis` aggregates data from `submissions` and `transaction_rows`.

Returned dashboard data includes:

- Total uploads
- Approved upload count
- Pending upload count
- Total transaction row count
- Approved revenue total
- Approved successful cash total
- Initiated, pending, approved, and declined workflow amounts
- Recent uploads
- Latest upload metadata
- Latest upload transaction rows
- Latest upload transaction amount trend by transaction date
- Upload trend by upload date

Optional query filters:

- `status`
- `date_from`
- `date_to`

## Deployment Strategy

Development options:

- Run PostgreSQL with Docker Compose and run backend/frontend locally.
- Run all three services through Docker Compose.

Docker Compose services:

- `postgres`: PostgreSQL 16 Alpine, initialized from `database/schema.sql`.
- `backend`: FastAPI app served by Uvicorn on port `8000`.
- `frontend`: Vite build served through Nginx on port `5173`.

Production recommendations:

- Replace default JWT secret values before deployment.
- Use managed PostgreSQL with backups.
- Store uploaded files in object storage instead of local disk or a single Docker volume.
- Use Alembic migrations instead of startup `Base.metadata.create_all` for controlled schema changes.
- Run FastAPI behind a production ASGI process manager or platform service.
- Serve the built frontend through Nginx, CDN, or static hosting.
- Add structured logging, metrics, tracing, and alerting.

## Current Limitations

- WebSocket broadcasting is process-local.
- Upload parsing runs inline in the API request.
- There is no Alembic migration history yet.
- Uploaded files are stored on local disk or a Docker volume.
- Reupload versioning fields exist in the schema, but the upload endpoint does not yet create linked replacement submissions.
- Manager comments are stored as the review record, not as a separate discussion thread.
- The app validates one fixed financial transaction schema rather than arbitrary Excel structures.

## Roadmap

Phase 1: Current project level

- JWT auth and role-based access control.
- Employee upload flow for `.xlsx` and `.csv`.
- Financial transaction schema validation.
- Typed transaction row persistence.
- Manager approve, decline, and request-reupload workflow.
- KPI dashboard and WebSocket refresh events.
- Dockerized frontend, backend, and PostgreSQL services.

Phase 2: Stabilization

- Add Alembic migrations.
- Add automated backend and frontend tests.
- Improve validation feedback in the upload UI.
- Implement linked reupload/version history.
- Add audit views for review decisions.

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
