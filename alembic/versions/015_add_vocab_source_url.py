"""Add source_url to vocab table.

Revision ID: 015
Revises: 014
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vocab",
        sa.Column("source_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vocab", "source_url")
