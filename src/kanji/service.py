"""Kanji service layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.kanji.models import Kanji


class KanjiService:
    """Service for kanji operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def get_by_id(self, kanji_id: int) -> Kanji | None:
        """Get kanji by ID."""
        result = await self.db.execute(select(Kanji).where(Kanji.id == kanji_id))
        return result.scalar_one_or_none()

    async def get_by_character(self, character: str) -> Kanji | None:
        """Get kanji by character."""
        result = await self.db.execute(select(Kanji).where(Kanji.character == character))
        return result.scalar_one_or_none()

    async def get_all(self, include_inactive: bool = False) -> list[Kanji]:
        """Get all kanji, optionally including inactive ones."""
        query = select(Kanji)
        if not include_inactive:
            query = query.where(Kanji.active == True)  # noqa: E712
        result = await self.db.execute(query)
        return list(result.scalars().all())
