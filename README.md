# LedgerFlow Analytics

Modern enterprise-grade financial transaction upload, analytics, approval, discussion, and re-upload platform.

## Stack

- Frontend: React, Vite, Tailwind CSS, React Router, Axios, Recharts, React Icons
- Backend: FastAPI, SQLAlchemy async, Pandas, OpenPyXL, WebSockets, Uvicorn
- Database: PostgreSQL
- Local orchestration: Docker Compose

## Quick Start

1. Copy environment files:

```powershell
Copy-Item backend\.env.example backend\.env
```

2. Start PostgreSQL:

```powershell
docker compose up -d postgres
```

3. Run backend:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

4. Run frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Main Capabilities

- Drag-and-drop `.xlsx` and `.csv` transaction uploads
- Fixed financial schema validation and typed transaction persistence
- Upload progress and status updates over WebSockets
- Manager approval queue with thread-based review feedback
- Employee re-upload flow with version history
- Real-time submission comment threads
- Transaction status analytics from `transaction_rows.status`
- KPI dashboard driven by `transaction_rows.transaction_date`, with transaction counts, status subsets, amount totals, recent activity, trends, and latest transactions

## Architecture Docs

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design, database relationships, endpoint design, WebSocket architecture, deployment strategy, scalability notes, and roadmap.
