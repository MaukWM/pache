"""Add components column to kanji table.

Stores the KRADFILE visual radical decomposition (component characters)
for each kanji, e.g. 語 -> ["一", "言", "口", "五"]. Populated by the
seed script from jamdict's bundled KRADFILE data.

Revision ID: 011
Revises: 010
Create Date: 2026-06-14

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add nullable first so it succeeds on a populated table, backfill existing
    # rows with an empty array, then enforce NOT NULL to match the model.
    op.add_column(
        "kanji",
        sa.Column("components", sa.JSON(), nullable=True),
    )
    op.execute("UPDATE kanji SET components = JSON_ARRAY() WHERE components IS NULL")
    op.alter_column("kanji", "components", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    op.drop_column("kanji", "components")
