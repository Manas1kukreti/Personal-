# Railway Deployment

Deploy the backend and frontend as separate Railway services from this repo.

## Backend service

Set the service root to `backend` so Railway uses `backend/Dockerfile`.

Required variables:

```env
ENVIRONMENT=production
DATABASE_URL=${{Postgres.DATABASE_URL}}
UPLOAD_DIR=/app/storage/uploads
JWT_SECRET_KEY=<generate-a-random-64-character-secret>
CORS_ORIGINS=https://<your-frontend-domain>
FRONTEND_BASE_URL=https://<your-frontend-domain>
DEFAULT_ADMIN_EMAIL=<your-admin-email>
DEFAULT_ADMIN_PASSWORD=<strong-one-time-admin-password>
DEFAULT_ADMIN_NAME=LedgerFlow Admin
AGENT_EMAIL=<posting-agent-email>
AGENT_PASSWORD=<strong-posting-agent-password>
AGENT_NAME=LedgerFlow Posting Agent
EMAILS_ENABLED=false
```

Optional email variables, only if email notifications are enabled:

```env
EMAILS_ENABLED=true
SMTP_HOST=<smtp-host>
SMTP_PORT=587
SMTP_USERNAME=<smtp-username>
SMTP_PASSWORD=<smtp-password>
SMTP_FROM_EMAIL=<verified-sender-email>
SMTP_TLS=true
```

The backend listens on Railway's injected `PORT` variable and runs Alembic migrations before starting the API.

## Frontend service

Set the service root to `frontend` so Railway uses `frontend/Dockerfile`.

Build variable:

```env
VITE_API_BASE_URL=https://<your-backend-domain>
```

The frontend container also listens on Railway's injected `PORT` variable.

## Agent test endpoints

Give testers only the deployed backend URLs:

```text
POST https://<your-backend-domain>/api/agent/login
POST https://<your-backend-domain>/api/agent/upload
```

The tester needs an employee account. If `AGENT_EMAIL` and `AGENT_PASSWORD` are set, the backend seeds a dedicated employee account for this flow on startup. Manager and admin accounts cannot authenticate through the agent login endpoint.

## Security checklist

- Do not commit `.env` files or real credentials.
- Store all production secrets in Railway variables.
- Use an exact frontend origin in `CORS_ORIGINS`; do not use `*`.
- Rotate `DEFAULT_ADMIN_PASSWORD` after first login by replacing the admin account password in the app or database.
- Give every external posting agent its own employee account so uploads are attributable and access can be revoked.
- Use `.xlsx` or `.csv` only for agent uploads.
