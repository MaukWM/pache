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
async def test_get_all_only_active(db_session: AsyncSession):
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
    result = await service.get_all()

    assert len(result) == 1
    assert result[0].character == "日"
    assert result[0].active is True


@pytest.mark.asyncio
async def test_get_all_include_inactive(db_session: AsyncSession):
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
    result = await service.get_all(include_inactive=True)

    assert len(result) == 2
    characters = {k.character for k in result}
    assert characters == {"日", "月"}
