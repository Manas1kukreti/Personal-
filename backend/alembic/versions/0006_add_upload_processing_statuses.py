"""add upload processing statuses

Revision ID: 0006_upload_processing
Revises: 0005_add_audit_logs
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006_upload_processing"
down_revision: Union[str, None] = "0005_add_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'processing' BEFORE 'pending'")
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'parse_failed' BEFORE 'reupload_requested'")


def downgrade() -> None:
    op.execute("UPDATE submissions SET review_status = 'pending' WHERE review_status IN ('processing', 'parse_failed')")
    op.execute("ALTER TYPE review_status RENAME TO review_status_old")
    op.execute("CREATE TYPE review_status AS ENUM ('pending', 'approved', 'declined', 'reupload_requested')")
    op.execute(
        "ALTER TABLE submissions ALTER COLUMN review_status TYPE review_status "
        "USING review_status::text::review_status"
    )
    op.execute("DROP TYPE review_status_old")
