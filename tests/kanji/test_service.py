"""Tests for KanjiService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.kanji.models import Kanji
from src.kanji.service import KanjiService


@pytest.mark.asyncio
async def test_get_by_id(db_session: AsyncSession):
    """Test getting kanji by ID."""
    # Create a kanji
    kanji = Kanji(
        character="日",
        meanings=["sun", "day"],
        readings_on=["ニチ", "ジツ"],
        readings_kun=["ひ", "か"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.commit()
    await db_session.refresh(kanji)

    # Test service
    service = KanjiService(db_session)
    result = await service.get_by_id(kanji.id)

    assert result is not None
    assert result.id == kanji.id
    assert result.character == "日"


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session: AsyncSession):
    """Test getting non-existent kanji by ID."""
    service = KanjiService(db_session)
    result = await service.get_by_id(99999)

    assert result is None


@pytest.mark.asyncio
async def test_get_by_character(db_session: AsyncSession):
    """Test getting kanji by character."""
    # Create a kanji
    kanji = Kanji(
        character="月",
        meanings=["moon", "month"],
        readings_on=["ゲツ", "ガツ"],
        readings_kun=["つき"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.commit()

    # Test service
    service = KanjiService(db_session)
    result = await service.get_by_character("月")

    assert result is not None
    assert result.character == "月"


@pytest.mark.asyncio
async def test_get_page_only_active(db_session: AsyncSession):
    """Test getting all kanji, only active ones by default."""
    # Create active and inactive kanji
    active_kanji = Kanji(
        character="日",
        meanings=["sun"],
        readings_on=["ニチ"],
        readings_kun=[],
        stroke_count=4,
        active=True,
    )
    inactive_kanji = Kanji(
        character="月",
        meanings=["moon"],
        readings_on=["ゲツ"],
        readings_kun=[],
        stroke_count=4,
        active=False,
    )
    db_session.add(active_kanji)
    db_session.add(inactive_kanji)
    await db_session.commit()

    # Test service - default should only return active
    service = KanjiService(db_session)
    result, total = await service.get_page()

    assert total == 1
    assert len(result) == 1
    assert result[0].character == "日"
    assert result[0].active is True


@pytest.mark.asyncio
async def test_get_page_include_inactive(db_session: AsyncSession):
    """Test getting all kanji including inactive ones."""
    # Create active and inactive kanji
    active_kanji = Kanji(
        character="日",
        meanings=["sun"],
        readings_on=["ニチ"],
        readings_kun=[],
        stroke_count=4,
        active=True,
    )
    inactive_kanji = Kanji(
        character="月",
        meanings=["moon"],
        readings_on=["ゲツ"],
        readings_kun=[],
        stroke_count=4,
        active=False,
    )
    db_session.add(active_kanji)
    db_session.add(inactive_kanji)
    await db_session.commit()

    # Test service - include inactive
    service = KanjiService(db_session)
    result, total = await service.get_page(include_inactive=True)

    assert total == 2
    assert len(result) == 2
    characters = {k.character for k in result}
    assert characters == {"日", "月"}


def _mk(char: str, *, freq: int | None = None, grade: int | None = None,
        jlpt: int | None = None, strokes: int = 5,
        meanings: list[str] | None = None,
        on: list[str] | None = None, kun: list[str] | None = None) -> Kanji:
    return Kanji(
        character=char,
        meanings=meanings or ["meaning"],
        readings_on=on or [],
        readings_kun=kun or [],
        stroke_count=strokes,
        frequency=freq,
        grade=grade,
        jlpt_level=jlpt,
        active=True,
    )


@pytest.mark.asyncio
async def test_get_page_pagination_and_total(db_session: AsyncSession):
    """limit/offset page through the sorted list; total reflects all matches."""
    db_session.add_all([_mk(c, freq=i + 1) for i, c in enumerate("一二三四五")])
    await db_session.commit()

    service = KanjiService(db_session)
    page1, total = await service.get_page(sort="frequency", limit=2, offset=0)
    page2, _ = await service.get_page(sort="frequency", limit=2, offset=2)

    assert total == 5
    assert [k.character for k in page1] == ["一", "二"]
    assert [k.character for k in page2] == ["三", "四"]


@pytest.mark.asyncio
async def test_get_page_sort_frequency_nulls_last(db_session: AsyncSession):
    """Frequency sort puts un-ranked kanji after ranked ones."""
    db_session.add_all([_mk("無"), _mk("二", freq=2), _mk("一", freq=1)])
    await db_session.commit()

    service = KanjiService(db_session)
    result, _ = await service.get_page(sort="frequency")
    assert [k.character for k in result] == ["一", "二", "無"]


@pytest.mark.asyncio
async def test_get_page_sort_jlpt_descending(db_session: AsyncSession):
    """JLPT sort: level 4 (easiest, old scale) first, unranked last."""
    db_session.add_all([_mk("難", jlpt=1), _mk("易", jlpt=4), _mk("無")])
    await db_session.commit()

    service = KanjiService(db_session)
    result, _ = await service.get_page(sort="jlpt")
    assert [k.character for k in result] == ["易", "難", "無"]


@pytest.mark.asyncio
async def test_get_page_search_character_meaning_reading(db_session: AsyncSession):
    """q matches exact character, meaning substring, or reading substring."""
    db_session.add_all([
        _mk("日", meanings=["sun", "day"], on=["ニチ"], kun=["ひ"]),
        _mk("月", meanings=["moon"], on=["ゲツ"], kun=["つき"]),
    ])
    await db_session.commit()

    service = KanjiService(db_session)

    by_char, total = await service.get_page(q="日")
    assert total == 1 and by_char[0].character == "日"

    by_meaning, _ = await service.get_page(q="moo")
    assert [k.character for k in by_meaning] == ["月"]

    by_reading, _ = await service.get_page(q="つき")
    assert [k.character for k in by_reading] == ["月"]


@pytest.mark.asyncio
async def test_get_page_search_romaji_kana(db_session: AsyncSession):
    """q_kana (hiragana) matches kun-readings directly and on-readings via katakana."""
    db_session.add_all([
        _mk("日", meanings=["sun"], on=["ニチ"], kun=["ひ"]),
        _mk("月", meanings=["moon"], on=["ゲツ"], kun=["つき"]),
    ])
    await db_session.commit()

    service = KanjiService(db_session)

    # "nichi" typed as romaji -> frontend sends q_kana="にち"; on-reading ニチ matches.
    result, _ = await service.get_page(q="nichi", q_kana="にち")
    assert [k.character for k in result] == ["日"]

    # kun-reading match via hiragana
    result, _ = await service.get_page(q="tsuki", q_kana="つき")
    assert [k.character for k in result] == ["月"]


@pytest.mark.asyncio
async def test_get_page_hide_known_excludes_progress(db_session: AsyncSession):
    """exclude_known_user_id drops kanji the user has progress on, any stage."""
    from src.auth.models import User
    from src.core.constants import ItemType
    from src.progress.models import UserItemProgress

    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    known = _mk("日", freq=1)
    unknown = _mk("月", freq=2)
    db_session.add_all([known, unknown])
    await db_session.flush()

    db_session.add(UserItemProgress(
        user_id=user.id, item_type=ItemType.KANJI, item_id=known.id, srs_stage=3,
    ))
    await db_session.commit()

    service = KanjiService(db_session)
    result, total = await service.get_page(exclude_known_user_id=user.id)
    assert total == 1
    assert [k.character for k in result] == ["月"]

    # Another user sees everything.
    other = User(username="other")
    db_session.add(other)
    await db_session.commit()
    _, other_total = await service.get_page(exclude_known_user_id=other.id)
    assert other_total == 2


@pytest.mark.asyncio
async def test_get_page_like_wildcards_escaped(db_session: AsyncSession):
    """% and _ in the query match literally, not as wildcards."""
    db_session.add(_mk("日", meanings=["sun"]))
    await db_session.commit()

    service = KanjiService(db_session)
    _, total = await service.get_page(q="%")
    assert total == 0
