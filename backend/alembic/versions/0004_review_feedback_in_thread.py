"""move review feedback to submission comments

Revision ID: 0004_review_feedback_in_thread
Revises: 0003_submission_comments
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004_review_feedback_in_thread"
down_revision: Union[str, None] = "0003_submission_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE reviews DROP CONSTRAINT IF EXISTS ck_reviews_comment_required")


def downgrade() -> None:
    op.execute(
        "ALTER TABLE reviews ADD CONSTRAINT ck_reviews_comment_required "
        "CHECK ((action = 'approved') OR (comment IS NOT NULL AND length(trim(comment)) > 0))"
    )
