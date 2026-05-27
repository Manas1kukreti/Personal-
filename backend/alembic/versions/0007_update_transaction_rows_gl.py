"""Replace transaction_rows columns with general ledger schema

Revision ID: 0007
Revises: 1859bbd362b3
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006_upload_processing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old enum-typed columns first (must drop before dropping enum types)
    op.drop_column("transaction_rows", "transaction_type")
    op.drop_column("transaction_rows", "payment_method")
    op.drop_column("transaction_rows", "status")

    # Drop remaining old columns
    op.drop_column("transaction_rows", "customer_name")
    op.drop_column("transaction_rows", "account_number")
    op.drop_column("transaction_rows", "transaction_id")
    op.drop_column("transaction_rows", "transaction_date")
    op.drop_column("transaction_rows", "amount")
    op.drop_column("transaction_rows", "merchant_name")
    op.drop_column("transaction_rows", "invoice_id")

    # Drop old enum types from PostgreSQL
    op.execute("DROP TYPE IF EXISTS transaction_type")
    op.execute("DROP TYPE IF EXISTS payment_method")
    op.execute("DROP TYPE IF EXISTS transaction_status")

    # Add new GL columns
    op.add_column("transaction_rows", sa.Column("date", sa.Date(), nullable=False, server_default="2000-01-01"))
    op.add_column("transaction_rows", sa.Column("entry_group", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("transaction_rows", sa.Column("entry_line", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("transaction_rows", sa.Column("sub_account", sa.String(255), nullable=False, server_default=""))
    op.add_column("transaction_rows", sa.Column("details", sa.String(255), nullable=False, server_default=""))
    op.add_column("transaction_rows", sa.Column("account_code", sa.String(80), nullable=False, server_default=""))
    op.add_column("transaction_rows", sa.Column("debit_amount", sa.Numeric(14, 2), nullable=True))
    op.add_column("transaction_rows", sa.Column("credit_amount", sa.Numeric(14, 2), nullable=True))
    op.add_column("transaction_rows", sa.Column("account_class", sa.String(120), nullable=False, server_default=""))
    op.add_column("transaction_rows", sa.Column("sub_class", sa.String(120), nullable=False, server_default=""))
    op.add_column("transaction_rows", sa.Column("country", sa.String(100), nullable=False, server_default=""))
    op.add_column("transaction_rows", sa.Column("region", sa.String(100), nullable=False, server_default=""))

    # Remove server defaults now that the column exists
    # (they were only needed to satisfy NOT NULL on existing rows during migration)
    op.alter_column("transaction_rows", "date", server_default=None)
    op.alter_column("transaction_rows", "entry_group", server_default=None)
    op.alter_column("transaction_rows", "entry_line", server_default=None)
    op.alter_column("transaction_rows", "sub_account", server_default=None)
    op.alter_column("transaction_rows", "details", server_default=None)
    op.alter_column("transaction_rows", "account_code", server_default=None)
    op.alter_column("transaction_rows", "account_class", server_default=None)
    op.alter_column("transaction_rows", "sub_class", server_default=None)
    op.alter_column("transaction_rows", "country", server_default=None)
    op.alter_column("transaction_rows", "region", server_default=None)


def downgrade() -> None:
    # Remove new GL columns
    op.drop_column("transaction_rows", "region")
    op.drop_column("transaction_rows", "country")
    op.drop_column("transaction_rows", "sub_class")
    op.drop_column("transaction_rows", "account_class")
    op.drop_column("transaction_rows", "credit_amount")
    op.drop_column("transaction_rows", "debit_amount")
    op.drop_column("transaction_rows", "account_code")
    op.drop_column("transaction_rows", "details")
    op.drop_column("transaction_rows", "sub_account")
    op.drop_column("transaction_rows", "entry_line")
    op.drop_column("transaction_rows", "entry_group")
    op.drop_column("transaction_rows", "date")

    # Recreate old enum types
    op.execute("CREATE TYPE transaction_type AS ENUM ('Payment','Debit','Credit','Transfer','Refund')")
    op.execute("CREATE TYPE payment_method AS ENUM ('NEFT','UPI','Credit Card','Debit Card','Net Banking')")
    op.execute("CREATE TYPE transaction_status AS ENUM ('Initiated','Pending','Successful','Failed')")

    # Restore old columns
    op.add_column("transaction_rows", sa.Column("customer_name", sa.String(255), nullable=False, server_default=""))
    op.add_column("transaction_rows", sa.Column("account_number", sa.String(80), nullable=False, server_default=""))
    op.add_column("transaction_rows", sa.Column("transaction_id", sa.String(120), nullable=False, server_default=""))
    op.add_column("transaction_rows", sa.Column("transaction_date", sa.Date(), nullable=False, server_default="2000-01-01"))
    op.add_column("transaction_rows", sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("transaction_rows", sa.Column("merchant_name", sa.String(255), nullable=False, server_default=""))
    op.add_column("transaction_rows", sa.Column("invoice_id", sa.String(120), nullable=False, server_default=""))
    op.add_column("transaction_rows", sa.Column("transaction_type", sa.Enum(name="transaction_type"), nullable=False, server_default="Payment"))
    op.add_column("transaction_rows", sa.Column("payment_method", sa.Enum(name="payment_method"), nullable=False, server_default="NEFT"))
    op.add_column("transaction_rows", sa.Column("status", sa.Enum(name="transaction_status"), nullable=False, server_default="Initiated"))