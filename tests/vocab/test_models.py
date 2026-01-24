"""Tests for vocabulary models."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.models import User
from src.kanji.models import Kanji
from src.vocab.models import Tag, Vocab


@pytest.mark.asyncio
async def test_vocab_model_creation(db_session: AsyncSession) -> None:
    """Test creating a Vocab model with all required fields."""
    # Create a user first (required for creator_id)
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create vocab
    vocab = Vocab(
        word="日本語",
        reading="にほんご",
        meanings=["Japanese language"],
        creator_id=user.id,
        creator_comment="Test comment",
    )
    db_session.add(vocab)
    await db_session.flush()

    # Verify
    assert vocab.id is not None
    assert vocab.word == "日本語"
    assert vocab.reading == "にほんご"
    assert vocab.meanings == ["Japanese language"]
    assert vocab.creator_id == user.id
    assert vocab.creator_comment == "Test comment"
    assert vocab.created_at is not None


@pytest.mark.asyncio
async def test_vocab_creator_id_not_nullable(db_session: AsyncSession) -> None:
    """Test that Vocab.creator_id field is marked as not nullable in the model."""
    # Note: SQLite doesn't enforce FK constraints by default, so we test the model constraint
    # The FK constraint will be enforced in production MySQL
    from sqlalchemy import inspect

    mapper = inspect(Vocab)
    creator_id_col = mapper.columns["creator_id"]
    assert creator_id_col.nullable is False


@pytest.mark.asyncio
async def test_tag_model_creation(db_session: AsyncSession) -> None:
    """Test creating a Tag model."""
    tag = Tag(name="N5")
    db_session.add(tag)
    await db_session.flush()

    assert tag.id is not None
    assert tag.name == "N5"


@pytest.mark.asyncio
async def test_tag_uniqueness(db_session: AsyncSession) -> None:
    """Test that Tag names must be unique."""
    tag1 = Tag(name="slang")
    db_session.add(tag1)
    await db_session.flush()

    tag2 = Tag(name="slang")
    db_session.add(tag2)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_vocab_tag_relationship(db_session: AsyncSession) -> None:
    """Test many-to-many relationship between Vocab and Tag."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create tags
    tag1 = Tag(name="N5")
    tag2 = Tag(name="common")
    db_session.add_all([tag1, tag2])
    await db_session.flush()

    # Create vocab with tags
    vocab = Vocab(
        word="日本語",
        reading="にほんご",
        meanings=["Japanese language"],
        creator_id=user.id,
    )
    vocab.tags.append(tag1)
    vocab.tags.append(tag2)
    db_session.add(vocab)
    await db_session.flush()

    # Verify relationship
    result = await db_session.execute(select(Vocab).where(Vocab.id == vocab.id))
    loaded_vocab = result.scalar_one()
    assert len(loaded_vocab.tags) == 2
    assert {t.name for t in loaded_vocab.tags} == {"N5", "common"}


@pytest.mark.asyncio
async def test_vocab_kanji_relationship(db_session: AsyncSession) -> None:
    """Test many-to-many relationship between Vocab and Kanji."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji1 = Kanji(
        character="日",
        meanings=["day", "sun"],
        readings_on=["ニチ", "ジツ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    kanji2 = Kanji(
        character="本",
        meanings=["book", "origin"],
        readings_on=["ホン"],
        readings_kun=["もと"],
        stroke_count=5,
    )
    db_session.add_all([kanji1, kanji2])
    await db_session.flush()

    # Create vocab with kanji links
    vocab = Vocab(
        word="日本",
        reading="にほん",
        meanings=["Japan"],
        creator_id=user.id,
    )
    vocab.kanji.append(kanji1)
    vocab.kanji.append(kanji2)
    db_session.add(vocab)
    await db_session.flush()

    # Verify relationship
    result = await db_session.execute(select(Vocab).where(Vocab.id == vocab.id))
    loaded_vocab = result.scalar_one()
    assert len(loaded_vocab.kanji) == 2
    assert {k.character for k in loaded_vocab.kanji} == {"日", "本"}


@pytest.mark.asyncio
async def test_vocab_creator_relationship(db_session: AsyncSession) -> None:
    """Test relationship between Vocab and User (creator)."""
    # Create user
    user = User(username="floppa")
    db_session.add(user)
    await db_session.flush()

    # Create vocab
    vocab = Vocab(
        word="猫",
        reading="ねこ",
        meanings=["cat"],
        creator_id=user.id,
    )
    db_session.add(vocab)
    await db_session.flush()

    # Verify relationship - use selectinload for async
    result = await db_session.execute(
        select(Vocab).where(Vocab.id == vocab.id).options(selectinload(Vocab.creator))
    )
    loaded_vocab = result.scalar_one()
    assert loaded_vocab.creator.username == "floppa"

    # Verify reverse relationship - use selectinload for async
    result = await db_session.execute(
        select(User).where(User.id == user.id).options(selectinload(User.vocab_items))
    )
    loaded_user = result.scalar_one()
    assert len(loaded_user.vocab_items) == 1
    assert loaded_user.vocab_items[0].word == "猫"


@pytest.mark.asyncio
async def test_tag_vocab_items_relationship(db_session: AsyncSession) -> None:
    """Test reverse relationship from Tag to Vocab items."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create tag
    tag = Tag(name="animals")
    db_session.add(tag)
    await db_session.flush()

    # Create multiple vocab with same tag
    vocab1 = Vocab(
        word="猫",
        reading="ねこ",
        meanings=["cat"],
        creator_id=user.id,
    )
    vocab1.tags.append(tag)

    vocab2 = Vocab(
        word="犬",
        reading="いぬ",
        meanings=["dog"],
        creator_id=user.id,
    )
    vocab2.tags.append(tag)

    db_session.add_all([vocab1, vocab2])
    await db_session.flush()

    # Verify reverse relationship - use selectinload for async
    result = await db_session.execute(
        select(Tag).where(Tag.id == tag.id).options(selectinload(Tag.vocab_items))
    )
    loaded_tag = result.scalar_one()
    assert len(loaded_tag.vocab_items) == 2
    assert {v.word for v in loaded_tag.vocab_items} == {"猫", "犬"}
