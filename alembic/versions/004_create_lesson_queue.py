"""Create lesson_queue table.

Revision ID: 004
Revises: 003
Create Date: 2026-01-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create lesson_queue table."""
    op.create_table(
        "lesson_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.Enum("kanji", "vocab", name="itemtype"), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_item"),
    )
    op.create_index("ix_lesson_queue_user_id", "lesson_queue", ["user_id"], unique=False)
    # Explicit composite index for query optimization (unique constraint already creates an index)
    op.create_index(
        "ix_lesson_queue_user_item",
        "lesson_queue",
        ["user_id", "item_type", "item_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop lesson_queue table."""
    op.drop_index("ix_lesson_queue_user_item", table_name="lesson_queue")
    op.drop_index("ix_lesson_queue_user_id", table_name="lesson_queue")
    op.drop_table("lesson_queue")
