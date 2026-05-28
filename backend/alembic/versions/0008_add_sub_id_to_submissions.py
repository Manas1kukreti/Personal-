"""Add sub_id to submissions

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("sub_id", sa.Integer(), nullable=True))
    op.execute(
        """
        WITH numbered AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY uploaded_at) AS row_number
            FROM submissions
            WHERE review_status != 'parse_failed'
        )
        UPDATE submissions
        SET sub_id = numbered.row_number
        FROM numbered
        WHERE submissions.id = numbered.id
        """
    )


def downgrade() -> None:
    op.drop_column("submissions", "sub_id")
