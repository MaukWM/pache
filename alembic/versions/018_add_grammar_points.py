"""Add personal grammar-point bank + sentence links.

Creates `grammar_points` (per-user canonical grammar points, LLM-extracted from the user's own
production sentences) and `sentence_grammar_points` (M2M sentence↔point with the instantiating
substring as evidence).

Revision ID: 018
Revises: 017
Create Date: 2026-07-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "grammar_points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("meaning_en", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "key", name="uq_grammar_points_user_key"),
    )
    op.create_index("ix_grammar_points_user_id", "grammar_points", ["user_id"], unique=False)

    op.create_table(
        "sentence_grammar_points",
        sa.Column("sentence_id", sa.Integer(), nullable=False),
        sa.Column("grammar_point_id", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["sentence_id"], ["production_sentences.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["grammar_point_id"], ["grammar_points.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sentence_id", "grammar_point_id"),
    )


def downgrade() -> None:
    op.drop_table("sentence_grammar_points")
    op.drop_index("ix_grammar_points_user_id", table_name="grammar_points")
    op.drop_table("grammar_points")
