"""Add users.sentences_enabled feature flag.

Gates access to the 作文 (production-SRS) feature per account. Defaults to false
for everyone; admins have access regardless (enforced in app code), and an admin
can flip this on for other users. Disabling is non-destructive — it only blocks
access; the user's sentences and SRS state (user_item_progress) are untouched, so
re-enabling resumes exactly where they left off.

Revision ID: 017
Revises: 016
Create Date: 2026-07-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "017"
down_revision: str | None = "016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "sentences_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "sentences_enabled")
