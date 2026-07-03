"""Kanji service layer."""

from typing import Any, Literal

from sqlalchemy import String, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from src.core.constants import ItemType
from src.kanji.models import Kanji
from src.progress.models import UserItemProgress

KanjiSort = Literal["frequency", "grade", "jlpt", "strokes", "default"]

# Hiragana -> katakana (on-readings are stored in katakana, kun in hiragana).
_HIRA_TO_KATA = str.maketrans(
    {chr(code): chr(code + 0x60) for code in range(0x3041, 0x3097)}
)


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user input matches literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _sort_order(sort: KanjiSort) -> list[Any]:
    """ORDER BY clauses per sort mode; NULLs last, id as stable tiebreak.

    `col IS NULL` sorts False (0) first on both MySQL and SQLite, which is the
    portable spelling of NULLS LAST.
    """
    if sort == "frequency":
        return [Kanji.frequency.is_(None), Kanji.frequency, Kanji.id]
    if sort == "grade":
        return [Kanji.grade.is_(None), Kanji.grade, Kanji.stroke_count, Kanji.id]
    if sort == "jlpt":
        # Old JLPT scale: 4 is easiest, so descending puts N5/N4 first.
        return [
            Kanji.jlpt_level.is_(None),
            Kanji.jlpt_level.desc(),
            Kanji.grade.is_(None),
            Kanji.grade,
            Kanji.id,
        ]
    if sort == "strokes":
        return [Kanji.stroke_count, Kanji.id]
    return [Kanji.id]


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

    async def get_page(
        self,
        *,
        include_inactive: bool = False,
        limit: int | None = None,
        offset: int = 0,
        sort: KanjiSort = "default",
        q: str | None = None,
        q_kana: str | None = None,
        exclude_known_user_id: int | None = None,
    ) -> tuple[list[Kanji], int]:
        """Get one page of kanji plus the total match count.

        Args:
            include_inactive: Include kanji not yet activated.
            limit: Page size; None returns all matches.
            offset: Rows to skip (pagination cursor).
            sort: Sort mode (frequency/grade/jlpt/strokes/default).
            q: Free-text search: exact character, or substring of meanings or
                readings (as typed).
            q_kana: Hiragana rendering of a romaji query; matched against
                kun-readings as-is and on-readings converted to katakana.
            exclude_known_user_id: If set, drop kanji this user already has
                progress on (any SRS stage).
        """
        query = select(Kanji)
        if not include_inactive:
            query = query.where(Kanji.active == True)  # noqa: E712

        if q and (q := q.strip()):
            like = f"%{_escape_like(q.lower())}%"
            conditions: list[ColumnElement[bool]] = [
                Kanji.character == q,
                func.lower(cast(Kanji.meanings, String)).like(like, escape="\\"),
                cast(Kanji.readings_on, String).like(f"%{_escape_like(q)}%", escape="\\"),
                cast(Kanji.readings_kun, String).like(f"%{_escape_like(q)}%", escape="\\"),
            ]
            if q_kana and (q_kana := q_kana.strip()):
                kata = q_kana.translate(_HIRA_TO_KATA)
                conditions.append(
                    cast(Kanji.readings_on, String).like(f"%{_escape_like(kata)}%", escape="\\")
                )
                conditions.append(
                    cast(Kanji.readings_kun, String).like(f"%{_escape_like(q_kana)}%", escape="\\")
                )
            query = query.where(or_(*conditions))

        if exclude_known_user_id is not None:
            has_progress = exists().where(
                UserItemProgress.user_id == exclude_known_user_id,
                UserItemProgress.item_type == ItemType.KANJI,
                UserItemProgress.item_id == Kanji.id,
            )
            query = query.where(~has_progress)

        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        query = query.order_by(*_sort_order(sort)).offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total
