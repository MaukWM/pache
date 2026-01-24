"""Tests for progress models."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.models import User
from src.core.constants import ItemType
from src.kanji.models import Kanji
from src.progress.models import LessonQueue
from src.vocab.models import Vocab


@pytest.mark.asyncio
async def test_lesson_queue_model_creation(db_session: AsyncSession) -> None:
    """Test creating a LessonQueue model with all required fields."""
    # Create a user first
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create a kanji item
    kanji = Kanji(
        character="漢",
        meanings=["Chinese"],
        readings_on=["kan"],
        readings_kun=[],
        stroke_count=13,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create lesson queue item
    queue_item = LessonQueue(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    db_session.add(queue_item)
    await db_session.flush()

    # Verify
    assert queue_item.id is not None
    assert queue_item.user_id == user.id
    assert queue_item.item_type == ItemType.KANJI
    assert queue_item.item_id == kanji.id
    assert queue_item.added_at is not None


@pytest.mark.asyncio
async def test_lesson_queue_composite_unique_constraint(db_session: AsyncSession) -> None:
    """Test that composite unique constraint prevents duplicate items."""
    # Create a user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create a kanji item
    kanji = Kanji(
        character="漢",
        meanings=["Chinese"],
        readings_on=["kan"],
        readings_kun=[],
        stroke_count=13,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create first queue item
    queue_item1 = LessonQueue(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    db_session.add(queue_item1)
    await db_session.flush()

    # Try to create duplicate (same user, item_type, item_id)
    queue_item2 = LessonQueue(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    db_session.add(queue_item2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_lesson_queue_different_users_can_have_same_item(
    db_session: AsyncSession,
) -> None:
    """Test that different users can have the same item in their queue."""
    # Create two users
    user1 = User(username="user1")
    user2 = User(username="user2")
    db_session.add(user1)
    db_session.add(user2)
    await db_session.flush()

    # Create a kanji item
    kanji = Kanji(
        character="漢",
        meanings=["Chinese"],
        readings_on=["kan"],
        readings_kun=[],
        stroke_count=13,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create queue items for both users
    queue_item1 = LessonQueue(
        user_id=user1.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    queue_item2 = LessonQueue(
        user_id=user2.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    db_session.add(queue_item1)
    db_session.add(queue_item2)
    await db_session.flush()

    # Both should be created successfully
    assert queue_item1.id is not None
    assert queue_item2.id is not None
    assert queue_item1.id != queue_item2.id


@pytest.mark.asyncio
async def test_lesson_queue_user_relationship(db_session: AsyncSession) -> None:
    """Test that LessonQueue has proper relationship to User."""
    # Create a user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create a kanji item
    kanji = Kanji(
        character="漢",
        meanings=["Chinese"],
        readings_on=["kan"],
        readings_kun=[],
        stroke_count=13,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create queue item
    queue_item = LessonQueue(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    db_session.add(queue_item)
    await db_session.flush()

    # Verify relationship
    assert queue_item.user.id == user.id
    assert queue_item.user.username == user.username

    # Verify reverse relationship
    result = await db_session.execute(
        select(User).where(User.id == user.id).options(selectinload(User.lesson_queue_items))
    )
    loaded_user = result.scalar_one()
    assert len(loaded_user.lesson_queue_items) == 1
    assert loaded_user.lesson_queue_items[0].id == queue_item.id


@pytest.mark.asyncio
async def test_lesson_queue_vocab_item_type(db_session: AsyncSession) -> None:
    """Test that LessonQueue can store vocab items."""
    # Create a user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create a vocab item
    vocab = Vocab(
        word="日本語",
        readings=["にほんご"],
        meanings=["Japanese language"],
        creator_id=user.id,
    )
    db_session.add(vocab)
    await db_session.flush()

    # Create lesson queue item for vocab
    queue_item = LessonQueue(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
    )
    db_session.add(queue_item)
    await db_session.flush()

    # Verify
    assert queue_item.id is not None
    assert queue_item.item_type == ItemType.VOCAB
    assert queue_item.item_id == vocab.id
