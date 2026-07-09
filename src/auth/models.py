"""Authentication database models."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.progress.models import LessonQueue, UserItemProgress
    from src.reviews.models import ReviewLog
    from src.vocab.models import Vocab


class User(Base):
    """User model representing a system user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Gates access to the 作文 (production-SRS) feature. Admins always have access
    # regardless (see require_sentences_access); this flag grants it to non-admins.
    sentences_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wk_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Review session ordering: "paired" (reading+meaning back-to-back per item)
    # or "scrambled" (all cards shuffled). Default is paired.
    review_mode: Mapped[str] = mapped_column(
        String(16), default="paired", server_default="paired", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    vocab_items: Mapped[list["Vocab"]] = relationship("Vocab", back_populates="creator")
    lesson_queue_items: Mapped[list["LessonQueue"]] = relationship(
        "LessonQueue", back_populates="user", cascade="all, delete-orphan"
    )
    item_progress: Mapped[list["UserItemProgress"]] = relationship(
        "UserItemProgress", back_populates="user", cascade="all, delete-orphan"
    )
    review_logs: Mapped[list["ReviewLog"]] = relationship(
        "ReviewLog", back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    """Session model for user authentication tokens."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
