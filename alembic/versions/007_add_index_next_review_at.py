"""Add index on next_review_at column.

Revision ID: 007
Revises: 006
Create Date: 2026-01-24

"""

from collections.abc import Sequence

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add indexes on next_review_at for query optimization."""
    # Index on next_review_at for efficient filtering of due reviews
    op.create_index(
        "ix_user_item_progress_next_review_at",
        "user_item_progress",
        ["next_review_at"],
        unique=False,
    )
    # Composite index for optimal query performance on user_id + next_review_at + srs_stage
    # This covers the common query pattern: get due reviews for a user (excluding burned)
    op.create_index(
        "ix_user_item_progress_user_review_stage",
        "user_item_progress",
        ["user_id", "next_review_at", "srs_stage"],
        unique=False,
    )


def downgrade() -> None:
    """Remove indexes on next_review_at."""
    op.drop_index("ix_user_item_progress_user_review_stage", table_name="user_item_progress")
    op.drop_index("ix_user_item_progress_next_review_at", table_name="user_item_progress")
