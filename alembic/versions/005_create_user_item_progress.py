"""Create user_item_progress table.

Revision ID: 005
Revises: 004
Create Date: 2026-01-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user_item_progress table."""
    # Create progresssource enum type
    op.execute("CREATE TYPE progresssource AS ENUM ('manual', 'wanikani')")

    op.create_table(
        "user_item_progress",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.Enum("kanji", "vocab", name="itemtype"), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("srs_stage", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("burned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meaning_note", sa.Text(), nullable=True),
        sa.Column("reading_mnemonic", sa.Text(), nullable=True),
        sa.Column(
            "source",
            sa.Enum("manual", "wanikani", name="progresssource"),
            nullable=False,
            server_default="'manual'",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_item_progress"),
    )
    op.create_index(
        "ix_user_item_progress_user_id", "user_item_progress", ["user_id"], unique=False
    )
    # Explicit composite index for query optimization
    op.create_index(
        "ix_user_item_progress_user_item",
        "user_item_progress",
        ["user_id", "item_type", "item_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop user_item_progress table."""
    op.drop_index("ix_user_item_progress_user_item", table_name="user_item_progress")
    op.drop_index("ix_user_item_progress_user_id", table_name="user_item_progress")
    op.drop_table("user_item_progress")
    # Drop the enum types
    op.execute("DROP TYPE IF EXISTS progresssource")
