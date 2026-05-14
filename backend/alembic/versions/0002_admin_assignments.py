"""admin role and manager assignments

Revision ID: 0002_admin_assignments
Revises: 0001_baseline
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0002_admin_assignments"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin'")
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("users")}
    if "manager_id" not in columns:
        op.add_column("users", sa.Column("manager_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key("fk_users_manager_id_users", "users", "users", ["manager_id"], ["id"])
    op.create_index("idx_users_manager_id", "users", ["manager_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("idx_users_manager_id", table_name="users")
    op.drop_constraint("fk_users_manager_id_users", "users", type_="foreignkey")
    op.drop_column("users", "manager_id")
