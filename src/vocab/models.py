"""Vocabulary database models."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.auth.models import User
    from src.kanji.models import Kanji


# Junction table for Vocab <-> Tag many-to-many relationship
vocab_tags = Table(
    "vocab_tags",
    Base.metadata,
    Column("vocab_id", Integer, ForeignKey("vocab.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

# Junction table for Vocab <-> Kanji many-to-many relationship
vocab_kanji = Table(
    "vocab_kanji",
    Base.metadata,
    Column("vocab_id", Integer, ForeignKey("vocab.id"), primary_key=True),
    Column("kanji_id", Integer, ForeignKey("kanji.id"), primary_key=True),
)


class Vocab(Base):
    """Vocabulary model representing a vocabulary term."""

    __tablename__ = "vocab"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    reading: Mapped[str] = mapped_column(String(100), nullable=False)
    meanings: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    creator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    creator_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="vocab_items")
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary=vocab_tags, back_populates="vocab_items"
    )
    kanji: Mapped[list["Kanji"]] = relationship("Kanji", secondary=vocab_kanji)


class Tag(Base):
    """Tag model for categorizing vocabulary."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    vocab_items: Mapped[list["Vocab"]] = relationship(
        "Vocab", secondary=vocab_tags, back_populates="tags"
    )
