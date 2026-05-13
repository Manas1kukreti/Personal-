# ExcelFlow Analytics Architecture

## Complete System Architecture

ExcelFlow is split into three deployable layers:

- React SPA: upload center, dynamic data preview, KPI dashboard, and manager approval dashboard.
- FastAPI service: REST APIs, spreadsheet parsing, approval workflow, analytics aggregation, and WebSocket broadcasts.
- PostgreSQL: normalized workflow tables plus JSONB row payloads for dynamic Excel structures.

Flow:

1. User uploads `.xlsx` or `.csv` from the React upload module.
2. FastAPI validates the file, stores the raw file, and sends progress over `/ws/uploads`.
3. Pandas/OpenPyXL parses rows and columns into structured JSON.
4. Upload metadata and row payloads are stored in staging tables.
5. Manager receives a real-time notification over `/ws/manager`.
6. Manager approves or rejects with comments.
7. Approved rows are copied into `approved_transactions`.
8. Dashboard clients receive `/ws/dashboard` refresh events and reload KPIs.

## Frontend Folder Structure

```text
frontend/
  src/
    api/client.js
    components/DataTable.jsx
    hooks/useWebSocket.js
    pages/Dashboard.jsx
    pages/ManagerDashboard.jsx
    pages/UploadCenter.jsx
    shell/AppShell.jsx
    main.jsx
    styles.css
```

## Backend Folder Structure

```text
backend/
  app/
    api/
      analytics.py
      approvals.py
      uploads.py
      websockets.py
    core/config.py
    db/session.py
    services/
      excel_parser.py
      websocket_manager.py
    main.py
    models.py
    schemas.py
```

## PostgreSQL Schema

Core tables:

- `users`: analysts, managers, admins.
- `uploads`: file metadata, status, dynamic columns, preview rows.
- `pending_upload_rows`: staged JSONB row payloads awaiting approval.
- `approved_transactions`: approved JSONB row payloads with optional inferred amount/date fields.
- `manager_comments`: approval or rejection comments.
- `kpi_snapshots`: optional persisted analytics snapshots.

Relationships:

- `users.id` -> `uploads.uploaded_by_id`
- `users.id` -> `uploads.approved_by_id`
- `uploads.id` -> `pending_upload_rows.upload_id`
- `uploads.id` -> `approved_transactions.upload_id`
- `uploads.id` -> `manager_comments.upload_id`

## API Endpoint Design

- `POST /api/uploads`: upload `.xlsx` or `.csv`, parse file, create staging rows, return preview.
- `GET /api/uploads`: list upload history, optionally filtered by status.
- `GET /api/uploads/{upload_id}`: fetch dynamic preview and metadata.
- `POST /api/approvals/{upload_id}/approve`: move staged rows into approved transactions.
- `POST /api/approvals/{upload_id}/reject`: mark upload rejected and store feedback.
- `GET /api/analytics/kpis`: return KPI totals, recent uploads, trend data, and last transactions.
- `GET /health`: service health.

## WebSocket Architecture

Channels:

- `/ws/uploads`: upload progress, processing completion, status changes.
- `/ws/manager`: new upload notifications and review status updates.
- `/ws/dashboard`: analytics refresh events.

Message shape:

```json
{
  "event": "dashboard_refresh",
  "payload": {
    "upload_id": "uuid",
    "status": "approved"
  }
}
```

## Manager Approval Workflow

1. Uploaded file is parsed and inserted into `uploads` with `status='pending'`.
2. Parsed rows are inserted into `pending_upload_rows`.
3. Manager opens the preview in the approval queue.
4. Approval inserts rows into `approved_transactions`, stores a comment, and changes status to `approved`.
5. Rejection stores feedback, leaves staged data available for audit, and changes status to `rejected`.
6. All connected dashboards receive refresh events.

## React Component Hierarchy

```text
AppShell
  Dashboard
    Kpi cards
    Recharts upload trend
    Recent uploads list
    Last transactions table
  UploadCenter
    Drag/drop upload panel
    WebSocket progress indicator
    Dynamic preview metrics
    DataTable
  ManagerDashboard
    Approval queue
    Review panel
    Comment box
    DataTable
```

## Dashboard Layout Design

- Fixed enterprise navigation on desktop and compact icon navigation on mobile.
- Top KPI row for operational metrics.
- Large trend chart for upload activity.
- Recent uploads and transaction tables for audit visibility.
- Neutral palette with teal and blue accents, 8px radii, compact cards, and responsive grids.

## Deployment Strategy

Development:

- PostgreSQL via Docker Compose.
- FastAPI via Uvicorn.
- React via Vite.

Production:

- Build React into static assets and serve from CDN or Nginx.
- Deploy FastAPI behind Nginx or an API gateway.
- Use managed PostgreSQL with automated backups.
- Store raw uploads in object storage such as S3/Azure Blob instead of local disk.
- Use Alembic migrations for schema evolution.
- Run Uvicorn workers behind Gunicorn or use an ASGI process manager.

## Scalability Considerations

- Move large Excel parsing into a background worker queue such as Celery, RQ, Dramatiq, or Arq.
- Stream large CSV files in chunks instead of loading entire files into memory.
- Use Redis Pub/Sub or PostgreSQL LISTEN/NOTIFY to broadcast WebSocket events across multiple API replicas.
- Partition large transaction tables by upload date or tenant.
- Add tenant IDs and row-level access control for multi-tenant enterprise use.
- Add database indexes for frequently queried JSONB fields once business columns stabilize.
- Persist KPI aggregates for high-volume dashboards.
- Add virus scanning and content-type validation before parsing uploaded files.

## Full Development Roadmap

Phase 1:

- Current scaffold: upload, parse, staging, approval, dashboard, WebSockets.
- Add authentication and role-based access control.
- Add Alembic migrations.

Phase 2:

- Background processing for large files.
- Chunked upload progress and cancellation.
- Detailed validation rules and schema mapping UI.
- Audit log and immutable approval history.

Phase 3:

- Advanced analytics, saved dashboard filters, and drill-down reports.
- Export approved data and rejected feedback.
- Email/Slack approval notifications.
- Data lineage and upload comparison views.

Phase 4:

- Multi-tenant isolation.
- Object storage for raw uploads.
- Horizontal WebSocket scaling with Redis.
- Observability: metrics, traces, structured logs, alerting.
