"""Tests for Kanji model."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.kanji.models import Kanji


@pytest.mark.asyncio
async def test_kanji_model_creation(db_session: AsyncSession):
    """Test creating a Kanji instance."""
    kanji = Kanji(
        character="日",
        meanings=["sun", "day"],
        readings_on=["ニチ", "ジツ"],
        readings_kun=["ひ", "か"],
        grade=1,
        jlpt_level=5,
        stroke_count=4,
        active=False,
    )
    db_session.add(kanji)
    await db_session.commit()
    await db_session.refresh(kanji)

    assert kanji.id is not None
    assert kanji.character == "日"
    assert kanji.meanings == ["sun", "day"]
    assert kanji.readings_on == ["ニチ", "ジツ"]
    assert kanji.readings_kun == ["ひ", "か"]
    assert kanji.grade == 1
    assert kanji.jlpt_level == 5
    assert kanji.stroke_count == 4
    assert kanji.active is False


@pytest.mark.asyncio
async def test_kanji_active_defaults_to_false(db_session: AsyncSession):
    """Test that active defaults to False."""
    kanji = Kanji(
        character="月",
        meanings=["moon", "month"],
        readings_on=["ゲツ", "ガツ"],
        readings_kun=["つき"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.commit()

    assert kanji.active is False


@pytest.mark.asyncio
async def test_kanji_character_unique(db_session: AsyncSession):
    """Test that character must be unique."""
    kanji1 = Kanji(
        character="日",
        meanings=["sun"],
        readings_on=["ニチ"],
        readings_kun=[],
        stroke_count=4,
    )
    db_session.add(kanji1)
    await db_session.commit()

    kanji2 = Kanji(
        character="日",
        meanings=["sun"],
        readings_on=["ニチ"],
        readings_kun=[],
        stroke_count=4,
    )
    db_session.add(kanji2)

    with pytest.raises(Exception):  # Should raise IntegrityError
        await db_session.commit()
