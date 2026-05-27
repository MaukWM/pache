"""Add vocab_sentences and vocab_sentence_links tables.

Revision ID: 010
Revises: 009
Create Date: 2026-05-27

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Clean up old JSON column if it exists from a previous version of this migration
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vocab' AND COLUMN_NAME = 'sentences'"
    ))
    if result.fetchone():
        op.drop_column("vocab", "sentences")

    # Check if tables already exist
    result = conn.execute(sa.text(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vocab_sentences'"
    ))
    if result.fetchone():
        return  # Already created

    op.create_table(
        "vocab_sentences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ja", sa.Text(), nullable=False),
        sa.Column("en", sa.Text(), nullable=False),
        sa.Column("added_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "vocab_sentence_links",
        sa.Column("vocab_id", sa.Integer(), sa.ForeignKey("vocab.id"), nullable=False),
        sa.Column("sentence_id", sa.Integer(), sa.ForeignKey("vocab_sentences.id"), nullable=False),
        sa.PrimaryKeyConstraint("vocab_id", "sentence_id"),
    )
    op.create_index(
        "ix_vocab_sentence_links_sentence_id",
        "vocab_sentence_links",
        ["sentence_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_vocab_sentence_links_sentence_id", table_name="vocab_sentence_links")
    op.drop_table("vocab_sentence_links")
    op.drop_table("vocab_sentences")
