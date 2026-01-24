"""Review tracking database models."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import ItemType
from src.database import Base

if TYPE_CHECKING:
    from src.auth.models import User


class ReviewLog(Base):
    """Review log model for tracking individual review submissions.

    Records each review attempt for an item, consolidating both reading and
    meaning reviews into a single record. Tracks SRS stage progression and
    correctness of each component.

    This provides a complete audit trail of review history separate from
    UserItemProgress, which tracks only the current state.
    """

    __tablename__ = "review_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reading_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    meaning_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    srs_stage_before: Mapped[int] = mapped_column(Integer, nullable=False)
    srs_stage_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="review_logs")
