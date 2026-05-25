"""add audit logs

Revision ID: 0005_add_audit_logs
Revises: 0004_review_feedback_in_thread
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_add_audit_logs"
down_revision: Union[str, None] = "0004_review_feedback_in_thread"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    audit_action = postgresql.ENUM(
        "upload_created",
        "upload_approved",
        "upload_declined",
        "reupload_requested",
        "reupload_submitted",
        "comment_added",
        "user_assigned",
        "user_reassigned",
        "login",
        "logout",
        name="audit_action",
        create_type=False,
    )
    audit_action.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_name", sa.String(length=120), nullable=False),
        sa.Column("actor_role", sa.String(length=50), nullable=False),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("target_id", sa.String(length=255), nullable=True),
        sa.Column("target_label", sa.String(length=255), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("idx_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_index("idx_audit_logs_action", table_name="audit_logs")
    op.drop_index("idx_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.execute("DROP TYPE IF EXISTS audit_action")
