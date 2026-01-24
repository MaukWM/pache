"""Progress tracking database models."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import ItemType, ProgressSource
from src.database import Base

if TYPE_CHECKING:
    from src.auth.models import User


class LessonQueue(Base):
    """Lesson queue model for user's personal lesson queue.

    Note on foreign key handling:
    The `item_id` field uses a polymorphic reference pattern - it references
    different tables (kanji or vocab) based on the `item_type` enum value.
    Since SQLAlchemy doesn't support polymorphic foreign keys directly, we use
    application-level validation and cleanup:
    - Item existence is validated in ProgressService.add_to_queue()
    - Orphaned entries are cleaned up in ProgressService.get_queue() when
      referenced items are deleted
    - Consider adding database triggers or application-level cleanup hooks
      when kanji/vocab items are deleted for proactive cleanup
    """

    __tablename__ = "lesson_queue"
    __table_args__ = (UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType), nullable=False)
    item_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Polymorphic FK: references kanji.id or vocab.id based on item_type
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="lesson_queue_items")


class UserItemProgress(Base):
    """User item progress model for tracking SRS progress on kanji and vocab items.

    Tracks the user's learning progress through the SRS (Spaced Repetition System) stages:
    - Stages 1-4: Apprentice (items start at stage 1 after lesson completion)
    - Stages 5-6: Guru (kanji must reach this level before vocab can be learned)
    - Stage 7: Master
    - Stage 8: Enlightened
    - Stage 9: Burned (complete - no more reviews)

    Note on foreign key handling:
    Similar to LessonQueue, the `item_id` field uses a polymorphic reference pattern.
    Application-level validation ensures item existence.
    """

    __tablename__ = "user_item_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_item_progress"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType), nullable=False)
    item_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Polymorphic FK: references kanji.id or vocab.id based on item_type
    srs_stage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    burned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meaning_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reading_mnemonic: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[ProgressSource] = mapped_column(
        Enum(ProgressSource), nullable=False, default=ProgressSource.MANUAL
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="item_progress")
