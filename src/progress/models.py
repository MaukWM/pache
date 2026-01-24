"""Progress tracking database models."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import ItemType
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
    __table_args__ = (
        UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)  # Polymorphic FK: references kanji.id or vocab.id based on item_type
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="lesson_queue_items")
