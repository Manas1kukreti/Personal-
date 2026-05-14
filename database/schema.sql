CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE user_role AS ENUM ('employee', 'manager', 'admin');
CREATE TYPE review_status AS ENUM ('pending', 'approved', 'declined', 'reupload_requested');
CREATE TYPE review_action AS ENUM ('approved', 'declined', 'reupload_requested');
CREATE TYPE transaction_type AS ENUM ('Payment', 'Debit', 'Credit', 'Transfer', 'Refund');
CREATE TYPE payment_method AS ENUM ('NEFT', 'UPI', 'Credit Card', 'Debit Card', 'Net Banking');
CREATE TYPE transaction_status AS ENUM ('Initiated', 'Pending', 'Successful', 'Failed');

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL DEFAULT '',
    role user_role NOT NULL DEFAULT 'employee',
    manager_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1,
    parent_submission_id UUID REFERENCES submissions(id),
    review_status review_status NOT NULL DEFAULT 'pending',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL UNIQUE REFERENCES submissions(id) ON DELETE CASCADE,
    manager_id UUID NOT NULL REFERENCES users(id),
    action review_action NOT NULL,
    comment TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_reviews_comment_required
        CHECK (action = 'approved' OR (comment IS NOT NULL AND length(trim(comment)) > 0))
);

CREATE TABLE IF NOT EXISTS transaction_rows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    customer_name VARCHAR(255) NOT NULL,
    account_number VARCHAR(80) NOT NULL,
    transaction_id VARCHAR(120) NOT NULL,
    transaction_date DATE NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    transaction_type transaction_type NOT NULL,
    merchant_name VARCHAR(255) NOT NULL,
    invoice_id VARCHAR(120) NOT NULL,
    payment_method payment_method NOT NULL,
    status transaction_status NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_submissions_user_uploaded ON submissions(user_id, uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_submissions_status_uploaded ON submissions(review_status, uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_submissions_parent ON submissions(parent_submission_id);
CREATE INDEX IF NOT EXISTS idx_users_manager_id ON users(manager_id);
CREATE INDEX IF NOT EXISTS idx_reviews_manager_reviewed ON reviews(manager_id, reviewed_at DESC);
CREATE INDEX IF NOT EXISTS idx_transaction_rows_submission ON transaction_rows(submission_id);
CREATE INDEX IF NOT EXISTS idx_transaction_rows_transaction_id ON transaction_rows(transaction_id);
CREATE INDEX IF NOT EXISTS idx_transaction_rows_date ON transaction_rows(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transaction_rows_amount ON transaction_rows(amount);
