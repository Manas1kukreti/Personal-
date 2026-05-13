CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE user_role AS ENUM ('employee', 'manager', 'admin');
CREATE TYPE upload_status AS ENUM ('pending', 'approved', 'rejected', 'reupload_requested');

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL DEFAULT '',
    role user_role NOT NULL DEFAULT 'employee',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    status upload_status NOT NULL DEFAULT 'pending',
    total_rows INTEGER NOT NULL DEFAULT 0,
    total_columns INTEGER NOT NULL DEFAULT 0,
    columns JSONB NOT NULL DEFAULT '[]',
    detected_types JSONB NOT NULL DEFAULT '{}',
    preview_rows JSONB NOT NULL DEFAULT '[]',
    validation_summary JSONB NOT NULL DEFAULT '{}',
    source_path VARCHAR(500),
    uploaded_by_id UUID REFERENCES users(id),
    approved_by_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS pending_upload_rows (
    id BIGSERIAL PRIMARY KEY,
    upload_id UUID NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    row_index INTEGER NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS approved_transactions (
    id BIGSERIAL PRIMARY KEY,
    upload_id UUID NOT NULL REFERENCES uploads(id),
    row_index INTEGER NOT NULL,
    payload JSONB NOT NULL,
    amount NUMERIC(14, 2),
    department VARCHAR(120),
    employee_name VARCHAR(120),
    kpi_name VARCHAR(160),
    target_value NUMERIC(14, 2),
    actual_value NUMERIC(14, 2),
    attainment_pct NUMERIC(8, 2),
    transaction_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS manager_comments (
    id BIGSERIAL PRIMARY KEY,
    upload_id UUID NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    manager_id UUID REFERENCES users(id),
    decision VARCHAR(20) NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(120) NOT NULL,
    metric_value NUMERIC(18, 2) NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}',
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_uploads_status_created ON uploads(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pending_upload_rows_upload ON pending_upload_rows(upload_id);
CREATE INDEX IF NOT EXISTS idx_approved_transactions_upload ON approved_transactions(upload_id);
CREATE INDEX IF NOT EXISTS idx_approved_transactions_amount ON approved_transactions(amount);
CREATE INDEX IF NOT EXISTS idx_comments_upload ON manager_comments(upload_id);
