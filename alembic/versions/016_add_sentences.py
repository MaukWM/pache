"""Add production-SRS sentence tables and widen itemtype enum.

Creates `production_sentences` (personal EN/JP pairs) and `production_sentence_review_log`
(per-submission judge audit), and widens the inline itemtype ENUM to include 'sentence' on every
table that stores it. Named to parallel the existing `vocab_sentences` example-sentence table.

Revision ID: 014
Revises: 015
Create Date: 2026-07-07

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables carrying the polymorphic itemtype enum (inline MySQL ENUM).
_ENUM_TABLES = ("lesson_queue", "user_item_progress", "review_log")
_OLD_ENUM = sa.Enum("kanji", "vocab", name="itemtype")
_NEW_ENUM = sa.Enum("kanji", "vocab", "sentence", name="itemtype")


def upgrade() -> None:
    op.create_table(
        "production_sentences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("english", sa.Text(), nullable=False),
        sa.Column("japanese", sa.Text(), nullable=False),
        sa.Column(
            "politeness",
            sa.Enum("polite", "casual", "mixed", name="politeness"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_production_sentences_user_id", "production_sentences", ["user_id"], unique=False
    )

    op.create_table(
        "production_sentence_review_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sentence_id", sa.Integer(), nullable=False),
        sa.Column("submitted", sa.Text(), nullable=False),
        sa.Column("exact_match", sa.Boolean(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("overridden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("srs_stage_before", sa.Integer(), nullable=False),
        sa.Column("srs_stage_after", sa.Integer(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sentence_id"], ["production_sentences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_production_sentence_review_log_user_id",
        "production_sentence_review_log",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_production_sentence_review_log_sentence_id",
        "production_sentence_review_log",
        ["sentence_id"],
        unique=False,
    )
    op.create_index(
        "ix_production_sentence_review_log_reviewed_at",
        "production_sentence_review_log",
        ["reviewed_at"],
        unique=False,
    )

    # Widen the enum (MySQL: metadata-only when appending a value at the end).
    for table in _ENUM_TABLES:
        op.alter_column(
            table,
            "item_type",
            existing_type=_OLD_ENUM,
            type_=_NEW_ENUM,
            existing_nullable=False,
        )


def downgrade() -> None:
    for table in _ENUM_TABLES:
        op.alter_column(
            table,
            "item_type",
            existing_type=_NEW_ENUM,
            type_=_OLD_ENUM,
            existing_nullable=False,
        )
    op.drop_index(
        "ix_production_sentence_review_log_reviewed_at",
        table_name="production_sentence_review_log",
    )
    op.drop_index(
        "ix_production_sentence_review_log_sentence_id",
        table_name="production_sentence_review_log",
    )
    op.drop_index(
        "ix_production_sentence_review_log_user_id",
        table_name="production_sentence_review_log",
    )
    op.drop_table("production_sentence_review_log")
    op.drop_index("ix_production_sentences_user_id", table_name="production_sentences")
    op.drop_table("production_sentences")
