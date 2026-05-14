"""baseline schema

Revision ID: 0001_baseline
Revises: None
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    if inspect(op.get_bind()).has_table("users"):
        return
    user_role = postgresql.ENUM("employee", "manager", name="user_role")
    review_status = postgresql.ENUM("pending", "approved", "declined", "reupload_requested", name="review_status")
    review_action = postgresql.ENUM("approved", "declined", "reupload_requested", name="review_action")
    transaction_type = postgresql.ENUM("Payment", "Debit", "Credit", "Transfer", "Refund", name="transaction_type")
    payment_method = postgresql.ENUM("NEFT", "UPI", "Credit Card", "Debit Card", "Net Banking", name="payment_method")
    transaction_status = postgresql.ENUM("Initiated", "Pending", "Successful", "Failed", name="transaction_status")

    user_role.create(op.get_bind(), checkfirst=True)
    review_status.create(op.get_bind(), checkfirst=True)
    review_action.create(op.get_bind(), checkfirst=True)
    transaction_type.create(op.get_bind(), checkfirst=True)
    payment_method.create(op.get_bind(), checkfirst=True)
    transaction_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("role", user_role, nullable=False, server_default="employee"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.id")),
        sa.Column("review_status", review_status, nullable=False, server_default="pending"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", review_action, nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("(action = 'approved') OR (comment IS NOT NULL AND length(trim(comment)) > 0)", name="ck_reviews_comment_required"),
    )
    op.create_table(
        "transaction_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("account_number", sa.String(length=80), nullable=False),
        sa.Column("transaction_id", sa.String(length=120), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("transaction_type", transaction_type, nullable=False),
        sa.Column("merchant_name", sa.String(length=255), nullable=False),
        sa.Column("invoice_id", sa.String(length=120), nullable=False),
        sa.Column("payment_method", payment_method, nullable=False),
        sa.Column("status", transaction_status, nullable=False),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_submissions_user_uploaded ON submissions(user_id, uploaded_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_submissions_status_uploaded ON submissions(review_status, uploaded_at DESC)")
    op.create_index("idx_submissions_parent", "submissions", ["parent_submission_id"])
    op.execute("CREATE INDEX IF NOT EXISTS idx_reviews_manager_reviewed ON reviews(manager_id, reviewed_at DESC)")
    op.create_index("idx_transaction_rows_submission", "transaction_rows", ["submission_id"])
    op.create_index("idx_transaction_rows_transaction_id", "transaction_rows", ["transaction_id"])
    op.create_index("idx_transaction_rows_date", "transaction_rows", ["transaction_date"])
    op.create_index("idx_transaction_rows_amount", "transaction_rows", ["amount"])


def downgrade() -> None:
    op.drop_table("transaction_rows")
    op.drop_table("reviews")
    op.drop_table("submissions")
    op.drop_table("users")
    for enum_name in ("transaction_status", "payment_method", "transaction_type", "review_action", "review_status", "user_role"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
