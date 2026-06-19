"""Add review_mode preference to users table.

Revision ID: 014
Revises: 013
Create Date: 2026-06-19

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "review_mode",
            sa.String(length=16),
            nullable=False,
            server_default="paired",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "review_mode")
