# LedgerFlow Analytics

A comprehensive enterprise-grade financial transaction management platform with real-time validation, audit tracking, intelligent alerts, and role-based dashboards for secure ledger reconciliation and compliance.

## Stack

- **Frontend**: React 19, Vite, Tailwind CSS, React Router, Axios, Recharts, React Icons
- **Backend**: FastAPI, SQLAlchemy async, Pandas, OpenPyXL, WebSockets, Uvicorn, PostgreSQL
- **Database**: PostgreSQL 16 with Alembic migrations
- **Orchestration**: Docker Compose
- **Real-time**: WebSocket-based live updates across all connected clients

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 16

### Setup

1. **Clone and setup environment:**

```powershell
Copy-Item backend\.env.example backend\.env
```

2. **Start services with Docker:**

```powershell
docker compose up --build
```

Or run services individually:

```powershell
# Terminal 1: PostgreSQL
docker compose up -d postgres

# Terminal 2: Backend
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 3: Frontend
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

**Ports:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5433

## Platform Features

### 📤 Upload & Validation
- Drag-and-drop `.xlsx` and `.csv` transaction uploads
- Automatic schema validation against fixed general-ledger format
- Real-time upload progress tracking via WebSockets
- Transaction preview with live filtering by type
- Row-level validation with detailed error reporting
- Support for 10+ transaction columns (date, entry_no, account_code, debit/credit, etc.)

### 👥 Role-Based Workflows
- **Employees**: Upload files, track submissions, re-upload when requested, view personal analytics
- **Managers**: Review assigned submissions, provide feedback via comments, approve/reject/request re-upload with audit trail
- **Admins**: Assign/reassign employees to managers, view system-wide audit logs, manage user access
- Token-based manager review links with automatic session verification

### 💬 Collaboration & Feedback
- Real-time comment threads on submissions
- Thread-based review feedback with full conversation history
- Best-effort email notifications (SMTP configurable)
- WebSocket-driven live comment updates across all team members
- Nested comment threads for targeted discussions

### 🚨 Intelligent Alerts
- DTCD (Double Transaction Correction/Detection) validation alerts
- Transaction-level anomaly detection and flagging
- Alerts page with searchable, filterable alerts list
- Manual alert creation API for external systems
- Alert enrichment with matched transaction details
- Mark individual or bulk alerts as read

### 📊 Analytics & Dashboards
- **KPI Dashboard**: Transaction counts, status breakdown, revenue totals, approved amounts
- **Analytics Charts**: Upload activity trends, transaction amount curves, recent transaction logs
- **Role-scoped analytics**: Employees see personal data, managers see team data, admins see all data
- Date range filtering for temporal analysis
- Real-time KPI updates via WebSockets

### 🔍 Audit & Compliance
- Complete audit log of all system actions (uploads, approvals, comments, assignments, logins)
- Search and filter audit logs by user, action, date, or target
- Timestamp tracking for all critical events
- Role-based audit data visibility
- Comprehensive audit trail for compliance reporting

### ⚙️ User Settings
- Profile name management
- Secure password changes
- Session management
- User preference management

### 🔐 Authentication & Security
- Email/password registration and login
- JWT token-based sessions
- Refresh token rotation with cookie-based storage
- Password hashing with bcrypt
- Role-based access control (RBAC)
- Protected routes with automatic redirect on auth failure
- Multi-instance deployment support with shared WebSocket bus readiness

## Main Workflows

### Upload & Review Cycle
1. Employee uploads `.xlsx` or `.csv` file with transaction data
2. System validates rows against schema in real-time
3. Employee previews transactions before submission
4. Manager receives email notification with review link
5. Manager reviews in dashboard, discusses via comments
6. Manager approves, declines, or requests re-upload
7. Employee receives notification and re-uploads if needed
8. New version tracked with full version history

### Alerts & Anomaly Response
1. System detects DTCD or validation anomalies
2. Alerts generated with detailed transaction context
3. User reviews alerts on Alerts page
4. Mark as read individually or bulk-mark batch
5. Alert enrichment provides linked transaction details
6. External systems can post alerts via API

### Audit & Compliance
1. All actions logged to audit table with user, timestamp, action type
2. Admins view audit logs via Audit page
3. Search by user name, action type, or date range
4. Export audit trail for compliance review
5. Track manager assignments, approval decisions, re-uploads

## Documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Detailed system design, data model, API contracts, WebSocket architecture
- **[docs/RAILWAY_DEPLOYMENT.md](docs/RAILWAY_DEPLOYMENT.md)** — Production deployment instructions
- **[DESIGN_SYSTEM.md](DESIGN_SYSTEM.md)** — UI/UX design tokens, components, typography, colors
- **[DESIGN_QUICK_REFERENCE.md](DESIGN_QUICK_REFERENCE.md)** — Quick-reference guide for UI development
- **[agent.md](agent.md)** — Developer handoff document with tech stack, paths, and workflows

## Environment Variables

See `backend/.env.example` for available configuration. Key settings:

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/ledgerflow
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
MAX_UPLOAD_SIZE_MB=50
MAX_PREVIEW_ROWS=500
EMAILS_ENABLED=false
FRONTEND_BASE_URL=http://localhost:5173
```

## API Reference

**Authentication**
- `POST /api/auth/register` — Register new user (employee/manager)
- `POST /api/auth/login` — Login and get JWT token
- `POST /api/auth/refresh` — Refresh access token
- `POST /api/auth/logout` — Logout and revoke tokens
- `GET /api/auth/me` — Get current user
- `PATCH /api/auth/me` — Update user profile
- `POST /api/auth/change-password` — Change password

**Uploads**
- `POST /api/uploads` — Upload transaction file
- `GET /api/uploads` — List user's submissions
- `GET /api/uploads/{upload_id}` — Get submission details
- `GET /api/uploads/{upload_id}/transactions` — Get all transaction rows
- `POST /api/uploads/{submission_id}/reupload` — Submit corrected version

**Comments & Discussion**
- `GET /api/submissions/{submission_id}/comments` — Fetch comment thread
- `POST /api/submissions/{submission_id}/comments` — Post comment

**Approvals**
- `POST /api/approvals/approve` — Manager approves submission
- `POST /api/approvals/reject` — Manager declines submission
- `POST /api/approvals/request-reupload` — Request employee correction
- `GET /api/approvals/verify-token?token=...` — Verify manager review link

**Alerts**
- `GET /api/alerts` — List unread alerts
- `POST /api/alerts` — Create alert
- `PATCH /api/alerts/{alert_id}/read` — Mark alert read
- `PATCH /api/alerts/read-all` — Mark all alerts read

**Analytics**
- `GET /api/analytics/kpis` — Fetch KPI data with optional date/status filters

**Audit**
- `GET /api/audit` — List audit log entries (admin only)

**Admin**
- `GET /api/admin/managers` — List all managers
- `GET /api/admin/employees` — List all employees
- `POST /api/admin/assign` — Assign employee to manager
- `POST /api/admin/reassign` — Reassign employee to different manager

## WebSocket Events

**Channels:** `uploads`, `manager`, `dashboard`, `comments`, `submissions`

**Events:**
- `upload_progress` — Live file upload progress
- `upload.complete` / `upload.failed` — Upload result notification
- `new_comment` — New comment in thread
- `approval.decision` — Manager approval/rejection
- `dashboard_refresh` — KPI data updated
- `new_upload` — New submission available for review

## Development

### Code Style
- React 19+ with hooks and functional components
- FastAPI async/await patterns
- SQLAlchemy ORM with async session management
- Tailwind CSS with custom design tokens

### Testing

Backend syntax check:
```powershell
py -3 -m compileall backend\app
```

Frontend build:
```powershell
cd frontend && npm run build
```

### Docker Rebuild

```powershell
docker compose down
docker compose up --build --force-recreate
```

Hard refresh frontend: `Ctrl + F5` at `http://localhost:5173`

## Deployment

- **Railway**: See [docs/RAILWAY_DEPLOYMENT.md](docs/RAILWAY_DEPLOYMENT.md)
- **Docker**: Full stack via `docker-compose.yml`
- **Multi-instance**: WebSocket manager supports Redis Pub/Sub or PostgreSQL LISTEN/NOTIFY for distributed deployments

## Roadmap

- [ ] Excel workbook import with multiple sheet handling
- [ ] Scheduled automated validation jobs
- [ ] Advanced anomaly detection (ML-based)
- [ ] Customizable approval workflows
- [ ] API rate limiting and quota management
- [ ] Granular field-level audit logging
- [ ] Custom transaction schema configuration
- [ ] Multi-tenant support with organization scoping

## Support & Issues

For bugs, feature requests, or questions:
1. Check [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical details
2. Review [agent.md](agent.md) for developer context
3. Open an issue on GitHub with detailed reproduction steps

## License

Proprietary — All rights reserved.
