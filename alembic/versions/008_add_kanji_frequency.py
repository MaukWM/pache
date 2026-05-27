"""Add frequency column to kanji table.

Revision ID: 008
Revises: 007
Create Date: 2026-05-27

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("kanji", sa.Column("frequency", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("kanji", "frequency")
