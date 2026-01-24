"""Create review_log table.

Revision ID: 006
Revises: 005
Create Date: 2026-01-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create review_log table."""
    op.create_table(
        "review_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.Enum("kanji", "vocab", name="itemtype"), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("reading_correct", sa.Boolean(), nullable=False),
        sa.Column("meaning_correct", sa.Boolean(), nullable=False),
        sa.Column("srs_stage_before", sa.Integer(), nullable=False),
        sa.Column("srs_stage_after", sa.Integer(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Index on user_id for querying user's review history
    op.create_index("ix_review_log_user_id", "review_log", ["user_id"], unique=False)
    # Index on reviewed_at for time-based queries (recent reviews, stats)
    op.create_index("ix_review_log_reviewed_at", "review_log", ["reviewed_at"], unique=False)
    # Composite index for user+item queries (common query pattern)
    op.create_index(
        "ix_review_log_user_item",
        "review_log",
        ["user_id", "item_type", "item_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop review_log table."""
    op.drop_index("ix_review_log_user_item", table_name="review_log")
    op.drop_index("ix_review_log_reviewed_at", table_name="review_log")
    op.drop_index("ix_review_log_user_id", table_name="review_log")
    op.drop_table("review_log")
