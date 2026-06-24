"""add initiated status to review status

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-15
"""
from alembic import op


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE review_status ADD VALUE IF NOT EXISTS 'initiated' BEFORE 'pending'")


def downgrade() -> None:
    op.execute("UPDATE submissions SET review_status = 'pending' WHERE review_status = 'initiated'")
    op.execute("ALTER TYPE review_status RENAME TO review_status_old")
    op.execute("CREATE TYPE review_status AS ENUM ('processing', 'pending', 'approved', 'declined', 'parse_failed', 'reupload_requested')")
    op.execute(
        "ALTER TABLE submissions ALTER COLUMN review_status TYPE review_status "
        "USING review_status::text::review_status"
    )
    op.execute("DROP TYPE review_status_old")
