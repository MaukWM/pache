"""Add per-grammar-point review outcomes.

Creates `grammar_point_review_log`: one row per linked grammar point per first-attempt production
review (ok/failed, judge-attributed). Raw signal for per-point accuracy.

Revision ID: 019
Revises: 018
Create Date: 2026-07-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "grammar_point_review_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("grammar_point_id", sa.Integer(), nullable=False),
        sa.Column("review_log_id", sa.Integer(), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["grammar_point_id"], ["grammar_points.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["review_log_id"], ["production_sentence_review_log.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_grammar_point_review_log_user_id", "grammar_point_review_log", ["user_id"]
    )
    op.create_index(
        "ix_grammar_point_review_log_grammar_point_id",
        "grammar_point_review_log",
        ["grammar_point_id"],
    )
    op.create_index(
        "ix_grammar_point_review_log_review_log_id",
        "grammar_point_review_log",
        ["review_log_id"],
    )


def downgrade() -> None:
    # Dropping the table drops its indexes + FKs with it (MySQL refuses to drop an index
    # that backs a foreign key, so no separate drop_index calls here).
    op.drop_table("grammar_point_review_log")
