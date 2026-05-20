"""Tests for progress service."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException, status
from freezegun import freeze_time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.constants import SRS_INTERVALS, ItemType
from src.kanji.models import Kanji
from src.progress.models import LessonQueue, UserItemProgress
from src.progress.service import ProgressService
from src.reviews.models import ReviewLog
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
    assert response.item_details["character"] == "漢"  # type: ignore[typeddict-item]
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
    assert response.item_details["word"] == "日本語"  # type: ignore[typeddict-item]
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
    assert kanji_item.item_details["character"] == "漢"  # type: ignore[typeddict-item]
    assert "meanings" in kanji_item.item_details

    vocab_item = next(item for item in items if item.item_type == ItemType.VOCAB)
    assert vocab_item.item_details["word"] == "日本語"  # type: ignore[typeddict-item]
    assert vocab_item.item_details["readings"] == ["にほんご"]  # type: ignore[typeddict-item]
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
    remaining = await db_session.execute(select(LessonQueue).where(LessonQueue.user_id == user.id))
    assert len(list(remaining.scalars().all())) == 0


@pytest.mark.asyncio
async def test_remove_from_queue_success(db_session: AsyncSession) -> None:
    """Test removing an item from queue successfully."""
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

    # Add to queue
    queue_item = LessonQueue(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    db_session.add(queue_item)
    await db_session.commit()

    # Remove from queue
    service = ProgressService(db_session)
    await service.remove_from_queue(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )

    # Verify item was removed
    result = await db_session.execute(
        select(LessonQueue).where(
            LessonQueue.user_id == user.id,
            LessonQueue.item_type == ItemType.KANJI,
            LessonQueue.item_id == kanji.id,
        )
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_remove_from_queue_not_found(db_session: AsyncSession) -> None:
    """Test removing an item not in queue raises 404."""
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
    await db_session.commit()

    # Try to remove item not in queue
    service = ProgressService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.remove_from_queue(
            user_id=user.id,
            item_type=ItemType.KANJI,
            item_id=kanji.id,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found in queue" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_remove_from_queue_only_user_items(db_session: AsyncSession) -> None:
    """Test that users can only remove their own items."""
    # Create two users
    user1 = User(username="user1")
    user2 = User(username="user2")
    db_session.add(user1)
    db_session.add(user2)
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

    # Add to queue for user1
    queue_item = LessonQueue(
        user_id=user1.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    db_session.add(queue_item)
    await db_session.commit()

    # Try to remove user1's item as user2
    service = ProgressService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.remove_from_queue(
            user_id=user2.id,
            item_type=ItemType.KANJI,
            item_id=kanji.id,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    # Verify user1's item still exists
    result = await db_session.execute(
        select(LessonQueue).where(
            LessonQueue.user_id == user1.id,
            LessonQueue.item_type == ItemType.KANJI,
            LessonQueue.item_id == kanji.id,
        )
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_resurrect_item_resets_burned_to_stage_one(db_session: AsyncSession) -> None:
    """Resurrecting a burned item resets stage, clears burned_at, schedules next review (AC1)."""
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    kanji = Kanji(character="漢", meanings=["Chinese"], readings_on=["kan"],
                  readings_kun=[], stroke_count=13)
    db_session.add(kanji)
    await db_session.flush()

    original_unlocked = datetime(2025, 1, 1, 8, 0, 0, tzinfo=UTC)
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=9,
        burned_at=datetime(2026, 1, 20, 9, 0, 0, tzinfo=UTC),
        next_review_at=None,
        unlocked_at=original_unlocked,
    )
    db_session.add(progress)
    await db_session.commit()

    service = ProgressService(db_session)
    response = await service.resurrect_item(
        user_id=user.id, item_type=ItemType.KANJI, item_id=kanji.id
    )

    assert response.item_type == ItemType.KANJI
    assert response.item_id == kanji.id
    assert response.srs_stage == 1
    assert response.next_review_at == datetime(2026, 1, 24, 12, 0, 0, tzinfo=UTC) + SRS_INTERVALS[1]

    await db_session.refresh(progress)
    assert progress.srs_stage == 1
    assert progress.burned_at is None
    # SQLite drops tzinfo on read; compare via UTC re-attach.
    actual_next = progress.next_review_at
    assert actual_next is not None
    if actual_next.tzinfo is None:
        actual_next = actual_next.replace(tzinfo=UTC)
    assert actual_next == datetime(2026, 1, 24, 16, 0, 0, tzinfo=UTC)
    # unlocked_at preserved
    actual_unlocked = progress.unlocked_at
    if actual_unlocked.tzinfo is None:
        actual_unlocked = actual_unlocked.replace(tzinfo=UTC)
    assert actual_unlocked == original_unlocked


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_resurrect_item_creates_review_log(db_session: AsyncSession) -> None:
    """Resurrection creates an audit ReviewLog with 9->1 stage transition (AC7)."""
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    vocab = Vocab(word="日本語", readings=["にほんご"],
                  meanings=["Japanese language"], creator_id=user.id)
    db_session.add(vocab)
    await db_session.flush()

    progress = UserItemProgress(
        user_id=user.id, item_type=ItemType.VOCAB, item_id=vocab.id,
        srs_stage=9, burned_at=datetime(2026, 1, 1, tzinfo=UTC), next_review_at=None,
    )
    db_session.add(progress)
    await db_session.commit()

    service = ProgressService(db_session)
    await service.resurrect_item(
        user_id=user.id, item_type=ItemType.VOCAB, item_id=vocab.id
    )

    log_result = await db_session.execute(
        select(ReviewLog).where(
            ReviewLog.user_id == user.id,
            ReviewLog.item_type == ItemType.VOCAB,
            ReviewLog.item_id == vocab.id,
        )
    )
    log = log_result.scalar_one()
    assert log.srs_stage_before == 9
    assert log.srs_stage_after == 1
    assert log.reading_correct is True
    assert log.meaning_correct is True


@pytest.mark.asyncio
async def test_resurrect_item_not_burned_returns_400(db_session: AsyncSession) -> None:
    """Resurrecting a non-burned item raises 400 (AC2)."""
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    kanji = Kanji(character="漢", meanings=["Chinese"], readings_on=["kan"],
                  readings_kun=[], stroke_count=13)
    db_session.add(kanji)
    await db_session.flush()

    progress = UserItemProgress(
        user_id=user.id, item_type=ItemType.KANJI, item_id=kanji.id,
        srs_stage=5,
        next_review_at=datetime.now(UTC) + timedelta(days=1),
    )
    db_session.add(progress)
    await db_session.commit()

    service = ProgressService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.resurrect_item(
            user_id=user.id, item_type=ItemType.KANJI, item_id=kanji.id
        )
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "not burned" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_resurrect_item_not_found_returns_404(db_session: AsyncSession) -> None:
    """Resurrecting an item with no progress row raises 404 (AC3)."""
    user = User(username="testuser")
    db_session.add(user)
    await db_session.commit()

    service = ProgressService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.resurrect_item(
            user_id=user.id, item_type=ItemType.KANJI, item_id=99999
        )
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_resurrect_item_other_users_burned_isolated(db_session: AsyncSession) -> None:
    """User cannot resurrect another user's burned item (404 from row not found)."""
    user1 = User(username="user1")
    user2 = User(username="user2")
    db_session.add_all([user1, user2])
    await db_session.flush()

    kanji = Kanji(character="漢", meanings=["Chinese"], readings_on=["kan"],
                  readings_kun=[], stroke_count=13)
    db_session.add(kanji)
    await db_session.flush()

    progress = UserItemProgress(
        user_id=user1.id, item_type=ItemType.KANJI, item_id=kanji.id,
        srs_stage=9, burned_at=datetime.now(UTC), next_review_at=None,
    )
    db_session.add(progress)
    await db_session.commit()

    service = ProgressService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.resurrect_item(
            user_id=user2.id, item_type=ItemType.KANJI, item_id=kanji.id
        )
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
