"""Tests for progress service."""

import pytest
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.constants import ItemType
from src.kanji.models import Kanji
from src.progress.models import LessonQueue
from src.progress.service import ProgressService
from src.vocab.models import Vocab


@pytest.mark.asyncio
async def test_add_to_queue_kanji_success(db_session: AsyncSession) -> None:
    """Test adding a kanji item to queue successfully."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="漢",
        meanings=["Chinese"],
        readings_on=["kan"],
        readings_kun=[],
        stroke_count=13,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Add to queue via service
    service = ProgressService(db_session)
    response = await service.add_to_queue(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )

    # Verify response
    assert response.id is not None
    assert response.item_type == ItemType.KANJI
    assert response.item_id == kanji.id
    assert response.added_at is not None
    assert "character" in response.item_details
    assert response.item_details["character"] == "漢"
    assert "meanings" in response.item_details

    # Verify database record
    await db_session.refresh(user, ["lesson_queue_items"])
    assert len(user.lesson_queue_items) == 1
    assert user.lesson_queue_items[0].item_id == kanji.id


@pytest.mark.asyncio
async def test_add_to_queue_vocab_success(db_session: AsyncSession) -> None:
    """Test adding a vocab item to queue successfully."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create vocab
    vocab = Vocab(
        word="日本語",
        readings=["にほんご"],
        meanings=["Japanese language"],
        creator_id=user.id,
    )
    db_session.add(vocab)
    await db_session.flush()

    # Add to queue via service
    service = ProgressService(db_session)
    response = await service.add_to_queue(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
    )

    # Verify response
    assert response.id is not None
    assert response.item_type == ItemType.VOCAB
    assert response.item_id == vocab.id
    assert "word" in response.item_details
    assert response.item_details["word"] == "日本語"
    assert "readings" in response.item_details
    assert "meanings" in response.item_details


@pytest.mark.asyncio
async def test_add_to_queue_duplicate_raises_409(db_session: AsyncSession) -> None:
    """Test that adding duplicate item raises 409 Conflict."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="漢",
        meanings=["Chinese"],
        readings_on=["kan"],
        readings_kun=[],
        stroke_count=13,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Add to queue first time
    service = ProgressService(db_session)
    await service.add_to_queue(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )

    # Try to add duplicate
    with pytest.raises(HTTPException) as exc_info:
        await service.add_to_queue(
            user_id=user.id,
            item_type=ItemType.KANJI,
            item_id=kanji.id,
        )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "already in queue" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_add_to_queue_invalid_kanji_id_raises_400(db_session: AsyncSession) -> None:
    """Test that adding invalid kanji ID raises 400 Bad Request."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Try to add non-existent kanji
    service = ProgressService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.add_to_queue(
            user_id=user.id,
            item_type=ItemType.KANJI,
            item_id=99999,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_add_to_queue_invalid_vocab_id_raises_400(db_session: AsyncSession) -> None:
    """Test that adding invalid vocab ID raises 400 Bad Request."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Try to add non-existent vocab
    service = ProgressService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.add_to_queue(
            user_id=user.id,
            item_type=ItemType.VOCAB,
            item_id=99999,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_queue_returns_user_items(db_session: AsyncSession) -> None:
    """Test that get_queue returns all items for the user."""
    # Create two users
    user1 = User(username="user1")
    user2 = User(username="user2")
    db_session.add_all([user1, user2])
    await db_session.flush()

    # Create kanji and vocab
    kanji = Kanji(
        character="漢",
        meanings=["Chinese"],
        readings_on=["kan"],
        readings_kun=[],
        stroke_count=13,
    )
    vocab = Vocab(
        word="日本語",
        readings=["にほんご"],
        meanings=["Japanese language"],
        creator_id=user1.id,
    )
    db_session.add_all([kanji, vocab])
    await db_session.flush()

    # Add items to user1's queue
    queue1 = LessonQueue(
        user_id=user1.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    queue2 = LessonQueue(
        user_id=user1.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
    )
    # Add item to user2's queue (should not appear in user1's results)
    queue3 = LessonQueue(
        user_id=user2.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    db_session.add_all([queue1, queue2, queue3])
    await db_session.commit()

    # Get user1's queue
    service = ProgressService(db_session)
    items = await service.get_queue(user_id=user1.id)

    # Verify only user1's items are returned
    assert len(items) == 2
    item_ids = {(item.item_type, item.item_id) for item in items}
    assert (ItemType.KANJI, kanji.id) in item_ids
    assert (ItemType.VOCAB, vocab.id) in item_ids
    assert (ItemType.KANJI, kanji.id) not in [
        (item.item_type, item.item_id) for item in items if item.id == queue3.id
    ]


@pytest.mark.asyncio
async def test_get_queue_includes_item_details(db_session: AsyncSession) -> None:
    """Test that get_queue includes item details for each item."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji and vocab
    kanji = Kanji(
        character="漢",
        meanings=["Chinese"],
        readings_on=["kan"],
        readings_kun=[],
        stroke_count=13,
    )
    vocab = Vocab(
        word="日本語",
        readings=["にほんご"],
        meanings=["Japanese language"],
        creator_id=user.id,
    )
    db_session.add_all([kanji, vocab])
    await db_session.flush()

    # Add items to queue
    queue1 = LessonQueue(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    queue2 = LessonQueue(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
    )
    db_session.add_all([queue1, queue2])
    await db_session.commit()

    # Get queue
    service = ProgressService(db_session)
    items = await service.get_queue(user_id=user.id)

    # Verify item details
    assert len(items) == 2
    kanji_item = next(item for item in items if item.item_type == ItemType.KANJI)
    assert kanji_item.item_details["character"] == "漢"
    assert "meanings" in kanji_item.item_details

    vocab_item = next(item for item in items if item.item_type == ItemType.VOCAB)
    assert vocab_item.item_details["word"] == "日本語"
    assert vocab_item.item_details["readings"] == ["にほんご"]
    assert vocab_item.item_details["meanings"] == ["Japanese language"]


@pytest.mark.asyncio
async def test_get_queue_empty_returns_empty_list(db_session: AsyncSession) -> None:
    """Test that get_queue returns empty list when user has no items."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Get queue
    service = ProgressService(db_session)
    items = await service.get_queue(user_id=user.id)

    # Verify empty list
    assert items == []


@pytest.mark.asyncio
async def test_get_queue_cleans_up_orphaned_entries(db_session: AsyncSession) -> None:
    """Test that get_queue removes orphaned entries when referenced items are deleted."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji and vocab
    kanji = Kanji(
        character="漢",
        meanings=["Chinese"],
        readings_on=["kan"],
        readings_kun=[],
        stroke_count=13,
    )
    vocab = Vocab(
        word="日本語",
        readings=["にほんご"],
        meanings=["Japanese language"],
        creator_id=user.id,
    )
    db_session.add_all([kanji, vocab])
    await db_session.flush()

    # Add items to queue
    queue1 = LessonQueue(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    queue2 = LessonQueue(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
    )
    db_session.add_all([queue1, queue2])
    await db_session.commit()

    # Delete the referenced items (simulating deletion)
    await db_session.delete(kanji)
    await db_session.delete(vocab)
    await db_session.commit()

    # Get queue - should clean up orphaned entries
    service = ProgressService(db_session)
    items = await service.get_queue(user_id=user.id)

    # Verify orphaned entries were removed
    assert len(items) == 0

    # Verify queue entries were deleted from database
    remaining = await db_session.execute(
        select(LessonQueue).where(LessonQueue.user_id == user.id)
    )
    assert len(list(remaining.scalars().all())) == 0
