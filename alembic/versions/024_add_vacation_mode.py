"""Vacation mode.

`users.vacation_started_at` is non-null while the user is on vacation. While set, lessons and
reviews (kanji/vocab and production sentences) are paused. On ending vacation, every pending
`user_item_progress.next_review_at` for the user is shifted forward by the vacation's duration,
so the schedule resumes exactly where it was paused (WaniKani semantics).

Revision ID: 024
Revises: 023
Create Date: 2026-10-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "024"
down_revision: str | None = "023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("vacation_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "vacation_started_at")
