"""Tests for lesson service."""

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.constants import SRS_INTERVALS, ItemType
from src.kanji.models import Kanji
from src.lessons.service import LessonService
from src.progress.models import LessonQueue, UserItemProgress
from src.progress.schemas import LessonCompleteRequest, SelectedItem
from src.vocab.models import Vocab


@pytest.mark.asyncio
async def test_complete_lessons_direct_without_queue(db_session: AsyncSession) -> None:
    """Test completing lessons directly without items being in queue."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji items (NOT in queue)
    kanji1 = Kanji(
        character="漢",
        meanings=["Chinese"],
        readings_on=["kan"],
        readings_kun=[],
        stroke_count=13,
    )
    kanji2 = Kanji(
        character="字",
        meanings=["character"],
        readings_on=["ji"],
        readings_kun=[],
        stroke_count=6,
    )
    db_session.add_all([kanji1, kanji2])
    await db_session.flush()

    # Complete lessons directly (items not in queue - should work!)
    service = LessonService(db_session)
    request = LessonCompleteRequest(
        item_ids=[
            SelectedItem(item_type=ItemType.KANJI, item_id=kanji1.id),
            SelectedItem(item_type=ItemType.KANJI, item_id=kanji2.id),
        ],
    )
    response = await service.complete_lessons(user_id=user.id, request=request)

    # Verify response
    assert response.count == 2
    assert len(response.items) == 2

    # Verify UserItemProgress records created with correct SRS stage
    progress_query = select(UserItemProgress).where(UserItemProgress.user_id == user.id)
    result = await db_session.execute(progress_query)
    progress_records = list(result.scalars().all())
    assert len(progress_records) == 2

    # Verify SRS stage is 1 (Apprentice 1), not 0
    for progress in progress_records:
        assert progress.srs_stage == 1
        assert progress.next_review_at is not None


@pytest.mark.asyncio
async def test_complete_lessons_auto_removes_from_queue(db_session: AsyncSession) -> None:
    """Test that items in queue are auto-removed when lesson is completed."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji items
    kanji1 = Kanji(
        character="漢",
        meanings=["Chinese"],
        readings_on=["kan"],
        readings_kun=[],
        stroke_count=13,
    )
    kanji2 = Kanji(
        character="字",
        meanings=["character"],
        readings_on=["ji"],
        readings_kun=[],
        stroke_count=6,
    )
    db_session.add_all([kanji1, kanji2])
    await db_session.flush()

    # Add items to queue
    queue1 = LessonQueue(user_id=user.id, item_type=ItemType.KANJI, item_id=kanji1.id)
    queue2 = LessonQueue(user_id=user.id, item_type=ItemType.KANJI, item_id=kanji2.id)
    db_session.add_all([queue1, queue2])
    await db_session.flush()

    # Complete lessons
    service = LessonService(db_session)
    request = LessonCompleteRequest(
        item_ids=[
            SelectedItem(item_type=ItemType.KANJI, item_id=kanji1.id),
            SelectedItem(item_type=ItemType.KANJI, item_id=kanji2.id),
        ],
    )
    response = await service.complete_lessons(user_id=user.id, request=request)

    # Verify response
    assert response.count == 2
    assert len(response.items) == 2

    # Verify UserItemProgress records created
    progress_query = select(UserItemProgress).where(UserItemProgress.user_id == user.id)
    result = await db_session.execute(progress_query)
    progress_records = list(result.scalars().all())
    assert len(progress_records) == 2

    # Verify items auto-removed from queue
    queue_query = select(LessonQueue).where(LessonQueue.user_id == user.id)
    result = await db_session.execute(queue_query)
    remaining_queue = list(result.scalars().all())
    assert len(remaining_queue) == 0


@pytest.mark.asyncio
async def test_complete_lessons_sets_next_review_time(db_session: AsyncSession) -> None:
    """Test that completed lessons have next_review_at set correctly."""
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

    # Complete lesson
    before_complete = datetime.now(UTC)
    service = LessonService(db_session)
    request = LessonCompleteRequest(
        item_ids=[SelectedItem(item_type=ItemType.KANJI, item_id=kanji.id)],
    )
    response = await service.complete_lessons(user_id=user.id, request=request)
    after_complete = datetime.now(UTC)

    # Verify response has next_review_at
    assert response.count == 1
    assert response.items[0].srs_stage == 1
    assert response.items[0].next_review_at is not None

    # Verify next_review_at is approximately 4 hours from now
    expected_min = before_complete + SRS_INTERVALS[1]
    expected_max = after_complete + SRS_INTERVALS[1]
    assert expected_min <= response.items[0].next_review_at <= expected_max

    # Verify in database
    progress_query = select(UserItemProgress).where(UserItemProgress.user_id == user.id)
    result = await db_session.execute(progress_query)
    progress = result.scalar_one()
    assert progress.srs_stage == 1
    assert progress.next_review_at is not None
    # Handle both timezone-aware and naive datetimes from DB (SQLite may lose timezone info)
    db_next_review = progress.next_review_at
    if db_next_review.tzinfo is None:
        db_next_review = db_next_review.replace(tzinfo=UTC)
    assert expected_min <= db_next_review <= expected_max


@pytest.mark.asyncio
async def test_complete_lessons_prerequisite_enforcement(
    db_session: AsyncSession,
) -> None:
    """Test that vocab items require learned kanji prerequisites."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji (not learned)
    kanji = Kanji(
        character="日",
        meanings=["day", "sun"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create vocab with kanji
    vocab = Vocab(
        word="日本",
        readings=["にほん"],
        meanings=["Japan"],
        creator_id=user.id,
    )
    vocab.kanji.append(kanji)
    db_session.add(vocab)
    await db_session.flush()

    # Try to complete lesson (should fail - kanji not at GURU stage)
    # Note: Queue membership is NOT required anymore
    service = LessonService(db_session)
    request = LessonCompleteRequest(
        item_ids=[SelectedItem(item_type=ItemType.VOCAB, item_id=vocab.id)],
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.complete_lessons(user_id=user.id, request=request)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "requires learned kanji" in exc_info.value.detail.lower()

    # Verify no progress record created
    progress_query = select(UserItemProgress).where(UserItemProgress.user_id == user.id)
    result = await db_session.execute(progress_query)
    progress_records = list(result.scalars().all())
    assert len(progress_records) == 0


@pytest.mark.asyncio
async def test_complete_lessons_prerequisite_satisfied(db_session: AsyncSession) -> None:
    """Test that vocab items can be learned when kanji prerequisites are met."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="日",
        meanings=["day", "sun"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create vocab with kanji
    vocab = Vocab(
        word="日本",
        readings=["にほん"],
        meanings=["Japan"],
        creator_id=user.id,
    )
    vocab.kanji.append(kanji)
    db_session.add(vocab)
    await db_session.flush()

    # Learn the kanji (create progress with srs_stage >= 5, GURU stage)
    kanji_progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=5,  # GURU stage (required for vocab)
    )
    db_session.add(kanji_progress)
    await db_session.flush()

    # Complete lesson (should succeed - kanji at GURU stage)
    # Note: Queue membership is NOT required anymore
    service = LessonService(db_session)
    request = LessonCompleteRequest(
        item_ids=[SelectedItem(item_type=ItemType.VOCAB, item_id=vocab.id)],
    )
    response = await service.complete_lessons(user_id=user.id, request=request)

    # Verify response
    assert response.count == 1
    assert len(response.items) == 1
    assert response.items[0].item_type == ItemType.VOCAB
    assert response.items[0].item_id == vocab.id
    assert response.items[0].srs_stage == 1  # Apprentice 1, not 0
    assert response.items[0].next_review_at is not None

    # Verify vocab progress record created
    progress_query = select(UserItemProgress).where(
        UserItemProgress.user_id == user.id,
        UserItemProgress.item_type == ItemType.VOCAB,
    )
    result = await db_session.execute(progress_query)
    vocab_progress = result.scalar_one_or_none()
    assert vocab_progress is not None
    assert vocab_progress.srs_stage == 1  # Apprentice 1, not 0
    assert vocab_progress.next_review_at is not None


@pytest.mark.asyncio
async def test_complete_lessons_already_learned(db_session: AsyncSession) -> None:
    """Test that completing already learned items raises error."""
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

    # Create progress record (already learned)
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=1,
    )
    db_session.add(progress)
    await db_session.flush()

    # Try to complete lesson (should fail - already learned)
    # Note: Queue membership is NOT required anymore
    service = LessonService(db_session)
    request = LessonCompleteRequest(
        item_ids=[SelectedItem(item_type=ItemType.KANJI, item_id=kanji.id)],
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.complete_lessons(user_id=user.id, request=request)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "already learned" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_complete_lessons_item_not_found(db_session: AsyncSession) -> None:
    """Test that completing non-existent items raises error."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Try to complete lesson for non-existent kanji
    service = LessonService(db_session)
    request = LessonCompleteRequest(
        item_ids=[SelectedItem(item_type=ItemType.KANJI, item_id=99999)],
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.complete_lessons(user_id=user.id, request=request)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "not found" in exc_info.value.detail.lower()

    # Try to complete lesson for non-existent vocab
    request = LessonCompleteRequest(
        item_ids=[SelectedItem(item_type=ItemType.VOCAB, item_id=99999)],
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.complete_lessons(user_id=user.id, request=request)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_complete_lessons_vocab_no_kanji_prerequisites(
    db_session: AsyncSession,
) -> None:
    """Test that vocab with no kanji can be learned without prerequisites."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create vocab without kanji (NOT in queue)
    vocab = Vocab(
        word="こんにちは",
        readings=["こんにちは"],
        meanings=["hello"],
        creator_id=user.id,
    )
    db_session.add(vocab)
    await db_session.flush()

    # Complete lesson (should succeed - no kanji prerequisites, queue not required)
    service = LessonService(db_session)
    request = LessonCompleteRequest(
        item_ids=[SelectedItem(item_type=ItemType.VOCAB, item_id=vocab.id)],
    )
    response = await service.complete_lessons(user_id=user.id, request=request)

    # Verify response
    assert response.count == 1
    assert len(response.items) == 1
    assert response.items[0].srs_stage == 1
    assert response.items[0].next_review_at is not None

    # Verify vocab progress record created
    progress_query = select(UserItemProgress).where(
        UserItemProgress.user_id == user.id,
        UserItemProgress.item_type == ItemType.VOCAB,
    )
    result = await db_session.execute(progress_query)
    vocab_progress = result.scalar_one_or_none()
    assert vocab_progress is not None
    assert vocab_progress.srs_stage == 1
    assert vocab_progress.next_review_at is not None


@pytest.mark.asyncio
async def test_complete_lessons_mixed_success_and_failure(
    db_session: AsyncSession,
) -> None:
    """Test that batch fails atomically when one item has errors."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji1 = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    kanji2 = Kanji(
        character="本",
        meanings=["book"],
        readings_on=["ホン"],
        readings_kun=["もと"],
        stroke_count=5,
    )
    db_session.add_all([kanji1, kanji2])
    await db_session.flush()

    # Learn kanji1 (at low stage, not GURU - so vocab prereqs not met)
    kanji1_progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji1.id,
        srs_stage=1,  # Apprentice 1, not GURU
    )
    db_session.add(kanji1_progress)
    await db_session.flush()

    # Create vocab with both kanji (neither at GURU stage)
    vocab = Vocab(
        word="日本",
        readings=["にほん"],
        meanings=["Japan"],
        creator_id=user.id,
    )
    vocab.kanji.extend([kanji1, kanji2])
    db_session.add(vocab)
    await db_session.flush()

    # Try to complete kanji2 and vocab (kanji1 already learned, vocab should fail)
    # Note: Queue membership is NOT required anymore
    service = LessonService(db_session)
    request = LessonCompleteRequest(
        item_ids=[
            SelectedItem(item_type=ItemType.KANJI, item_id=kanji2.id),
            SelectedItem(item_type=ItemType.VOCAB, item_id=vocab.id),
        ],
    )

    # Should raise error because vocab fails prereqs (kanji not at GURU stage)
    with pytest.raises(HTTPException) as exc_info:
        await service.complete_lessons(user_id=user.id, request=request)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "requires learned kanji" in exc_info.value.detail.lower()

    # Verify kanji2 NOT learned (atomic rollback - all or nothing)
    progress_query = select(UserItemProgress).where(
        UserItemProgress.user_id == user.id,
        UserItemProgress.item_type == ItemType.KANJI,
        UserItemProgress.item_id == kanji2.id,
    )
    result = await db_session.execute(progress_query)
    kanji2_progress = result.scalar_one_or_none()
    assert kanji2_progress is None  # Not created due to atomic failure
