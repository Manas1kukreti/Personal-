"""Add validation columns to transaction rows

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transaction_rows", sa.Column("dtcd_difference", sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column("transaction_rows", sa.Column("validation_messages", sa.String(length=500), nullable=True))
    op.add_column("transaction_rows", sa.Column("repairs_applied", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("transaction_rows", "repairs_applied")
    op.drop_column("transaction_rows", "validation_messages")
    op.drop_column("transaction_rows", "dtcd_difference")
