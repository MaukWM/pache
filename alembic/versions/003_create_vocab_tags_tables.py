"""Create vocab, tags, vocab_tags, and vocab_kanji tables.

Revision ID: 003
Revises: 002
Create Date: 2026-01-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create vocab, tags, and junction tables."""
    # Create tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    # Create vocab table
    op.create_table(
        "vocab",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("word", sa.String(100), nullable=False),
        sa.Column("reading", sa.String(100), nullable=False),
        sa.Column("meanings", sa.JSON(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("creator_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vocab_word", "vocab", ["word"], unique=False)

    # Create vocab_tags junction table
    op.create_table(
        "vocab_tags",
        sa.Column("vocab_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["vocab_id"], ["vocab.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("vocab_id", "tag_id"),
    )

    # Create vocab_kanji junction table
    op.create_table(
        "vocab_kanji",
        sa.Column("vocab_id", sa.Integer(), nullable=False),
        sa.Column("kanji_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["vocab_id"], ["vocab.id"]),
        sa.ForeignKeyConstraint(["kanji_id"], ["kanji.id"]),
        sa.PrimaryKeyConstraint("vocab_id", "kanji_id"),
    )


def downgrade() -> None:
    """Drop vocab, tags, and junction tables."""
    op.drop_table("vocab_kanji")
    op.drop_table("vocab_tags")
    op.drop_index("ix_vocab_word", table_name="vocab")
    op.drop_table("vocab")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")
