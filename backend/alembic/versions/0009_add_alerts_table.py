"""Add alerts table

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("entry_no", sa.String(length=80), nullable=False),
        sa.Column("account_code", sa.String(length=80), nullable=False),
        sa.Column("sub_account", sa.String(length=255), nullable=False),
        sa.Column("difference", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="FAILED"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_alerts_created_at", "alerts", ["created_at"])
    op.create_index("idx_alerts_entry_account", "alerts", ["entry_no", "account_code"])
    op.create_index("idx_alerts_is_read", "alerts", ["is_read"])


def downgrade() -> None:
    op.drop_index("idx_alerts_is_read", table_name="alerts")
    op.drop_index("idx_alerts_entry_account", table_name="alerts")
    op.drop_index("idx_alerts_created_at", table_name="alerts")
    op.drop_table("alerts")
