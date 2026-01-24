"""Kanji database models."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Kanji(Base):
    """Kanji model representing a single kanji character."""

    __tablename__ = "kanji"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character: Mapped[str] = mapped_column(String(1), unique=True, nullable=False, index=True)
    meanings: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    readings_on: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    readings_kun: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jlpt_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stroke_count: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
