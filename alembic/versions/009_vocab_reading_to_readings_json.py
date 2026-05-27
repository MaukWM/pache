"""Change vocab.reading (varchar) to vocab.readings (json list).

Revision ID: 009
Revises: 008
Create Date: 2026-05-27

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Handle partial previous run: readings column may already exist, reading may be gone
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vocab'"
    ))
    columns = {row[0] for row in result}

    if "readings" not in columns:
        op.add_column("vocab", sa.Column("readings", sa.JSON(), nullable=True))

    if "reading" in columns:
        op.execute("UPDATE vocab SET readings = JSON_ARRAY(reading) WHERE readings IS NULL")
        op.drop_column("vocab", "reading")

    op.execute("ALTER TABLE vocab MODIFY COLUMN readings JSON NOT NULL")


def downgrade() -> None:
    op.add_column("vocab", sa.Column("reading", sa.String(100), nullable=True))
    op.execute("UPDATE vocab SET reading = JSON_UNQUOTE(JSON_EXTRACT(readings, '$[0]'))")
    op.drop_column("vocab", "readings")
    op.execute("ALTER TABLE vocab MODIFY COLUMN reading VARCHAR(100) NOT NULL")
