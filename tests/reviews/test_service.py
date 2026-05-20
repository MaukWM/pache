"""Tests for review service."""

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from freezegun import freeze_time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.constants import ItemType
from src.kanji.models import Kanji
from src.progress.models import UserItemProgress
from src.progress.schemas import KanjiItemDetails, VocabItemDetails
from src.reviews.models import ReviewLog
from src.reviews.schemas import ReviewCreateRequest, ReviewResponse
from src.reviews.service import ReviewService
from src.vocab.models import Vocab


@pytest.mark.asyncio
async def test_get_due_reviews_returns_due_items(db_session: AsyncSession) -> None:
    """Test get_due_reviews returns items that are due."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="日",
        meanings=["day", "sun"],
        readings_on=["ニチ", "ジツ"],
        readings_kun=["ひ", "か"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create progress record with past review time (due now)
    past_time = datetime.now(UTC) - timedelta(hours=2)
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=3,
        next_review_at=past_time,
    )
    db_session.add(progress)
    await db_session.commit()

    # Get due reviews
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Verify
    assert len(reviews) == 1
    assert reviews[0].item_type == ItemType.KANJI
    assert reviews[0].item_id == kanji.id
    assert reviews[0].srs_stage == 3
    # Type narrowing for kanji details
    kanji_details = cast(KanjiItemDetails, reviews[0].item_details)
    assert kanji_details["character"] == "日"


@pytest.mark.asyncio
async def test_get_due_reviews_excludes_burned_items(db_session: AsyncSession) -> None:
    """Test get_due_reviews excludes items with srs_stage=9 (burned)."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create burned progress record
    past_time = datetime.now(UTC) - timedelta(hours=2)
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=9,  # Burned
        next_review_at=past_time,
    )
    db_session.add(progress)
    await db_session.commit()

    # Get due reviews
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Verify burned item is excluded
    assert len(reviews) == 0


@pytest.mark.asyncio
async def test_get_due_reviews_excludes_future_items(db_session: AsyncSession) -> None:
    """Test get_due_reviews excludes items with future next_review_at."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create progress record with future review time
    future_time = datetime.now(UTC) + timedelta(hours=5)
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=3,
        next_review_at=future_time,
    )
    db_session.add(progress)
    await db_session.commit()

    # Get due reviews
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Verify future item is excluded
    assert len(reviews) == 0


@pytest.mark.asyncio
@freeze_time("2026-01-24 14:30:00", tz_offset=0)
async def test_get_due_reviews_hour_batching(db_session: AsyncSession) -> None:
    """Test get_due_reviews includes items due within current hour (FR28)."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create progress record due later in the current hour (14:45)
    # Hour batching means items due at 14:xx are available at 14:00
    # So item due at 14:45 should be included when current time is 14:30
    item_due_time = datetime(2026, 1, 24, 14, 45, 0, 0, tzinfo=UTC)
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=3,
        next_review_at=item_due_time,
    )
    db_session.add(progress)
    await db_session.commit()

    # Get due reviews
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Item should be included because it's due within the current hour
    assert len(reviews) == 1


@pytest.mark.asyncio
@freeze_time("2026-01-24 14:00:00", tz_offset=0)
async def test_get_due_reviews_hour_batching_at_hour_start(db_session: AsyncSession) -> None:
    """Test get_due_reviews includes items due at start of hour."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create progress record due at start of hour (14:00)
    item_due_time = datetime(2026, 1, 24, 14, 0, 0, 0, tzinfo=UTC)
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=3,
        next_review_at=item_due_time,
    )
    db_session.add(progress)
    await db_session.commit()

    # Get due reviews
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Item should be included because it's due at the start of the current hour
    assert len(reviews) == 1


@pytest.mark.asyncio
@freeze_time("2026-01-24 14:59:59", tz_offset=0)
async def test_get_due_reviews_hour_batching_at_hour_end(db_session: AsyncSession) -> None:
    """Test get_due_reviews includes items due at end of hour."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create progress record due at end of hour (14:59)
    item_due_time = datetime(2026, 1, 24, 14, 59, 0, 0, tzinfo=UTC)
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=3,
        next_review_at=item_due_time,
    )
    db_session.add(progress)
    await db_session.commit()

    # Get due reviews
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Item should be included because it's due within the current hour
    assert len(reviews) == 1


@pytest.mark.asyncio
async def test_get_due_reviews_orders_by_next_review_at(db_session: AsyncSession) -> None:
    """Test get_due_reviews orders items by next_review_at ascending (oldest first)."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create two kanji
    kanji1 = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    kanji2 = Kanji(
        character="月",
        meanings=["moon"],
        readings_on=["ゲツ"],
        readings_kun=["つき"],
        stroke_count=4,
    )
    db_session.add_all([kanji1, kanji2])
    await db_session.flush()

    # Create progress records with different times
    older_time = datetime.now(UTC) - timedelta(hours=5)
    newer_time = datetime.now(UTC) - timedelta(hours=2)

    progress1 = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji1.id,
        srs_stage=3,
        next_review_at=newer_time,  # Newer
    )
    progress2 = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji2.id,
        srs_stage=4,
        next_review_at=older_time,  # Older - should come first
    )
    db_session.add_all([progress1, progress2])
    await db_session.commit()

    # Get due reviews
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Verify order - older first
    assert len(reviews) == 2
    assert reviews[0].item_id == kanji2.id  # Older
    assert reviews[1].item_id == kanji1.id  # Newer


@pytest.mark.asyncio
async def test_get_due_reviews_empty_when_no_items_due(db_session: AsyncSession) -> None:
    """Test get_due_reviews returns empty list when no items are due."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.commit()

    # Get due reviews (no progress records)
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Verify empty
    assert reviews == []


@pytest.mark.asyncio
async def test_get_due_reviews_includes_correct_kanji_details(db_session: AsyncSession) -> None:
    """Test get_due_reviews includes correct kanji item details."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji with full details
    kanji = Kanji(
        character="日",
        meanings=["day", "sun"],
        readings_on=["ニチ", "ジツ"],
        readings_kun=["ひ", "か"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create progress record
    past_time = datetime.now(UTC) - timedelta(hours=2)
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=3,
        next_review_at=past_time,
    )
    db_session.add(progress)
    await db_session.commit()

    # Get due reviews
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Verify kanji details
    assert len(reviews) == 1
    assert reviews[0].item_type == ItemType.KANJI
    # Type narrowing for kanji details
    details = cast(KanjiItemDetails, reviews[0].item_details)
    assert details["character"] == "日"
    assert details["meanings"] == ["day", "sun"]
    assert details["readings_on"] == ["ニチ", "ジツ"]
    assert details["readings_kun"] == ["ひ", "か"]


@pytest.mark.asyncio
async def test_get_due_reviews_includes_correct_vocab_details(db_session: AsyncSession) -> None:
    """Test get_due_reviews includes correct vocab item details."""
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

    # Create progress record
    past_time = datetime.now(UTC) - timedelta(hours=2)
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=5,
        next_review_at=past_time,
    )
    db_session.add(progress)
    await db_session.commit()

    # Get due reviews
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Verify vocab details
    assert len(reviews) == 1
    assert reviews[0].item_type == ItemType.VOCAB
    # Type narrowing for vocab details
    details = cast(VocabItemDetails, reviews[0].item_details)
    assert details["word"] == "日本語"
    assert details["readings"] == ["にほんご"]
    assert details["meanings"] == ["Japanese language"]


@pytest.mark.asyncio
async def test_get_due_reviews_mixed_kanji_and_vocab(db_session: AsyncSession) -> None:
    """Test get_due_reviews handles mixed kanji and vocab items."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji and vocab
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    vocab = Vocab(
        word="日本",
        readings=["にほん"],
        meanings=["Japan"],
        creator_id=user.id,
    )
    db_session.add_all([kanji, vocab])
    await db_session.flush()

    # Create progress records
    past_time = datetime.now(UTC) - timedelta(hours=2)
    progress1 = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=3,
        next_review_at=past_time,
    )
    progress2 = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=4,
        next_review_at=past_time,
    )
    db_session.add_all([progress1, progress2])
    await db_session.commit()

    # Get due reviews
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Verify both types returned
    assert len(reviews) == 2
    item_types = {r.item_type for r in reviews}
    assert ItemType.KANJI in item_types
    assert ItemType.VOCAB in item_types


@pytest.mark.asyncio
async def test_get_due_reviews_only_user_items(db_session: AsyncSession) -> None:
    """Test get_due_reviews only returns items for the specified user."""
    # Create two users
    user1 = User(username="user1")
    user2 = User(username="user2")
    db_session.add_all([user1, user2])
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create progress records for both users
    past_time = datetime.now(UTC) - timedelta(hours=2)
    progress1 = UserItemProgress(
        user_id=user1.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=3,
        next_review_at=past_time,
    )
    progress2 = UserItemProgress(
        user_id=user2.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=5,
        next_review_at=past_time,
    )
    db_session.add_all([progress1, progress2])
    await db_session.commit()

    # Get due reviews for user1 only
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user1.id)

    # Verify only user1's item returned
    assert len(reviews) == 1
    assert reviews[0].srs_stage == 3  # user1's stage


@pytest.mark.asyncio
async def test_get_due_reviews_excludes_null_next_review_at(db_session: AsyncSession) -> None:
    """Test get_due_reviews excludes items with null next_review_at."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
    )
    db_session.add(kanji)
    await db_session.flush()

    # Create progress record with null next_review_at
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=3,
        next_review_at=None,  # No review scheduled
    )
    db_session.add(progress)
    await db_session.commit()

    # Get due reviews
    service = ReviewService(db_session)
    reviews = await service.get_due_reviews(user_id=user.id)

    # Verify item with null next_review_at is excluded
    assert len(reviews) == 0


@pytest.mark.asyncio
async def test_get_due_reviews_invalid_user_id(db_session: AsyncSession) -> None:
    """Test get_due_reviews raises ValueError for invalid user_id."""
    service = ReviewService(db_session)

    # Test negative user_id
    with pytest.raises(ValueError, match="Invalid user_id.*must be a positive integer"):
        await service.get_due_reviews(user_id=-1)

    # Test zero user_id
    with pytest.raises(ValueError, match="Invalid user_id.*must be a positive integer"):
        await service.get_due_reviews(user_id=0)


# ============================================================================
# Tests for submit_review
# ============================================================================


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_submit_review_both_correct_advances_stage(db_session: AsyncSession) -> None:
    """Test submit_review advances stage when both reading and meaning are correct (AC1)."""
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

    # Create progress record at stage 3
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=3,
        next_review_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(progress)
    await db_session.commit()

    # Submit review with both correct
    service = ReviewService(db_session)
    request = ReviewCreateRequest(
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        reading_correct=True,
        meaning_correct=True,
    )
    response = await service.submit_review(user_id=user.id, request=request)

    # Verify response
    assert isinstance(response, ReviewResponse)
    assert response.item_type == ItemType.VOCAB
    assert response.item_id == vocab.id
    assert response.reading_correct is True
    assert response.meaning_correct is True
    assert response.srs_stage_before == 3
    assert response.srs_stage_after == 4
    assert response.next_review_at is not None
    # Stage 3 interval is 1 day, so next_review_at should be ~24 hours from now
    expected_next = datetime(2026, 1, 25, 12, 0, 0, tzinfo=UTC)
    assert response.next_review_at == expected_next

    # Verify ReviewLog was created
    await db_session.refresh(progress)
    log_query = await db_session.execute(
        select(ReviewLog).where(ReviewLog.user_id == user.id, ReviewLog.item_id == vocab.id)
    )
    log = log_query.scalar_one_or_none()
    assert log is not None
    assert log.reading_correct is True
    assert log.meaning_correct is True
    assert log.srs_stage_before == 3
    assert log.srs_stage_after == 4

    # Verify UserItemProgress was updated
    await db_session.refresh(progress)
    assert progress.srs_stage == 4
    # SQLite drops tzinfo on read; re-attach UTC for comparison.
    actual_next = progress.next_review_at
    if actual_next is not None and actual_next.tzinfo is None:
        actual_next = actual_next.replace(tzinfo=UTC)
    assert actual_next == expected_next


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_submit_review_both_incorrect_drops_stage(db_session: AsyncSession) -> None:
    """Test submit_review drops stage when both reading and meaning are incorrect (AC2)."""
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

    # Create progress record at stage 5
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=5,
        next_review_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(progress)
    await db_session.commit()

    # Submit review with both incorrect
    service = ReviewService(db_session)
    request = ReviewCreateRequest(
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        reading_correct=False,
        meaning_correct=False,
    )
    response = await service.submit_review(user_id=user.id, request=request)

    # Verify response - should drop from 5 to 3 (max(1, 5-2))
    assert response.srs_stage_before == 5
    assert response.srs_stage_after == 3
    assert response.next_review_at is not None
    # Stage 3 interval is 1 day
    expected_next = datetime(2026, 1, 25, 12, 0, 0, tzinfo=UTC)
    assert response.next_review_at == expected_next

    # Verify UserItemProgress was updated
    await db_session.refresh(progress)
    assert progress.srs_stage == 3
    # SQLite drops tzinfo on read; re-attach UTC for comparison.
    actual_next = progress.next_review_at
    if actual_next is not None and actual_next.tzinfo is None:
        actual_next = actual_next.replace(tzinfo=UTC)
    assert actual_next == expected_next


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_submit_review_mixed_result_drops_stage(db_session: AsyncSession) -> None:
    """Test submit_review drops stage when one is correct and one is incorrect (AC3)."""
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

    # Create progress record at stage 4
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=4,
        next_review_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(progress)
    await db_session.commit()

    # Submit review with reading incorrect, meaning correct
    service = ReviewService(db_session)
    request = ReviewCreateRequest(
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        reading_correct=False,
        meaning_correct=True,
    )
    response = await service.submit_review(user_id=user.id, request=request)

    # Verify response - should drop from 4 to 2 (max(1, 4-2))
    assert response.srs_stage_before == 4
    assert response.srs_stage_after == 2
    assert response.reading_correct is False
    assert response.meaning_correct is True
    # Stage 2 interval is 8 hours
    expected_next = datetime(2026, 1, 24, 20, 0, 0, tzinfo=UTC)
    assert response.next_review_at == expected_next

    # Verify UserItemProgress was updated
    await db_session.refresh(progress)
    assert progress.srs_stage == 2


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_submit_review_burns_item_at_stage_8(db_session: AsyncSession) -> None:
    """Test submit_review burns item when at stage 8 with both correct (AC4)."""
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

    # Create progress record at stage 8
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=8,
        next_review_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(progress)
    await db_session.commit()

    # Submit review with both correct
    service = ReviewService(db_session)
    request = ReviewCreateRequest(
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        reading_correct=True,
        meaning_correct=True,
    )
    response = await service.submit_review(user_id=user.id, request=request)

    # Verify response - should advance to stage 9 (burned)
    assert response.srs_stage_before == 8
    assert response.srs_stage_after == 9
    assert response.next_review_at is None

    # Verify UserItemProgress was updated
    await db_session.refresh(progress)
    assert progress.srs_stage == 9
    assert progress.burned_at is not None
    # SQLite drops tzinfo on read; re-attach UTC for comparison.
    actual_burned = progress.burned_at
    if actual_burned.tzinfo is None:
        actual_burned = actual_burned.replace(tzinfo=UTC)
    assert actual_burned == datetime(2026, 1, 24, 12, 0, 0, tzinfo=UTC)
    assert progress.next_review_at is None


@pytest.mark.asyncio
async def test_submit_review_item_not_in_progress(db_session: AsyncSession) -> None:
    """Test submit_review raises ValueError when item not in UserItemProgress (AC5)."""
    # Create user
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    # Create vocab (but no progress record)
    vocab = Vocab(
        word="日本語",
        readings=["にほんご"],
        meanings=["Japanese language"],
        creator_id=user.id,
    )
    db_session.add(vocab)
    await db_session.commit()

    # Submit review for item not in progress
    service = ReviewService(db_session)
    request = ReviewCreateRequest(
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        reading_correct=True,
        meaning_correct=True,
    )

    with pytest.raises(ValueError, match="Item not in progress"):
        await service.submit_review(user_id=user.id, request=request)


@pytest.mark.asyncio
async def test_submit_review_burned_item_rejected(db_session: AsyncSession) -> None:
    """Test submit_review raises ValueError when item is burned (AC6)."""
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

    # Create burned progress record
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=9,  # Burned
        next_review_at=None,
        burned_at=datetime.now(UTC),
    )
    db_session.add(progress)
    await db_session.commit()

    # Submit review for burned item
    service = ReviewService(db_session)
    request = ReviewCreateRequest(
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        reading_correct=True,
        meaning_correct=True,
    )

    with pytest.raises(ValueError, match="Item is burned"):
        await service.submit_review(user_id=user.id, request=request)


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_submit_review_item_not_yet_due(db_session: AsyncSession) -> None:
    """Test submit_review raises ValueError when item is not yet due for review."""
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

    # Create progress record at stage 7 (30 day wait) with future review time
    # Item was reviewed yesterday, so next_review_at is 29 days from now
    future_time = datetime(2026, 2, 22, 12, 0, 0, tzinfo=UTC)  # 29 days later
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=7,
        next_review_at=future_time,  # Not due yet
    )
    db_session.add(progress)
    await db_session.commit()

    # Submit review for item not yet due
    service = ReviewService(db_session)
    request = ReviewCreateRequest(
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        reading_correct=True,
        meaning_correct=True,
    )

    with pytest.raises(ValueError, match="not yet due for review"):
        await service.submit_review(user_id=user.id, request=request)


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_submit_review_item_not_yet_due_stage_8(db_session: AsyncSession) -> None:
    """Test submit_review raises ValueError when stage 8 item (4 month wait) is not yet due."""
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

    # Create progress record at stage 8 (120 day wait) with future review time
    # Item was reviewed 1 day ago, so next_review_at is 119 days from now
    future_time = datetime(2026, 5, 23, 12, 0, 0, tzinfo=UTC)  # ~119 days later
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=8,
        next_review_at=future_time,  # Not due yet - 4 month wait, only 1 day passed
    )
    db_session.add(progress)
    await db_session.commit()

    # Submit review for item not yet due (trying to review after 1 day when 4 months required)
    service = ReviewService(db_session)
    request = ReviewCreateRequest(
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        reading_correct=True,
        meaning_correct=True,
    )

    with pytest.raises(ValueError, match="not yet due for review"):
        await service.submit_review(user_id=user.id, request=request)


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_submit_review_stage_1_minimum(db_session: AsyncSession) -> None:
    """Test submit_review doesn't drop below stage 1."""
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

    # Create progress record at stage 1
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=1,
        next_review_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(progress)
    await db_session.commit()

    # Submit review with both incorrect
    service = ReviewService(db_session)
    request = ReviewCreateRequest(
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        reading_correct=False,
        meaning_correct=False,
    )
    response = await service.submit_review(user_id=user.id, request=request)

    # Verify stage stays at 1 (minimum)
    assert response.srs_stage_before == 1
    assert response.srs_stage_after == 1
    # Stage 1 interval is 4 hours
    expected_next = datetime(2026, 1, 24, 16, 0, 0, tzinfo=UTC)
    assert response.next_review_at == expected_next

    # Verify UserItemProgress was updated
    await db_session.refresh(progress)
    assert progress.srs_stage == 1


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_submit_review_stage_2_minimum(db_session: AsyncSession) -> None:
    """Test submit_review drops to stage 1 when at stage 2."""
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

    # Create progress record at stage 2
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=2,
        next_review_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(progress)
    await db_session.commit()

    # Submit review with both incorrect
    service = ReviewService(db_session)
    request = ReviewCreateRequest(
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        reading_correct=False,
        meaning_correct=False,
    )
    response = await service.submit_review(user_id=user.id, request=request)

    # Verify stage drops to 1 (max(1, 2-2) = 1)
    assert response.srs_stage_before == 2
    assert response.srs_stage_after == 1
    # Stage 1 interval is 4 hours
    expected_next = datetime(2026, 1, 24, 16, 0, 0, tzinfo=UTC)
    assert response.next_review_at == expected_next

    # Verify UserItemProgress was updated
    await db_session.refresh(progress)
    assert progress.srs_stage == 1


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_submit_review_transaction_atomicity(db_session: AsyncSession) -> None:
    """Test submit_review atomicity: ReviewLog and UserItemProgress update together."""
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

    # Create progress record at stage 3
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        srs_stage=3,
        next_review_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(progress)
    await db_session.commit()

    # Submit review
    service = ReviewService(db_session)
    request = ReviewCreateRequest(
        item_type=ItemType.VOCAB,
        item_id=vocab.id,
        reading_correct=True,
        meaning_correct=True,
    )
    response = await service.submit_review(user_id=user.id, request=request)

    # Verify both ReviewLog and UserItemProgress were updated
    await db_session.refresh(progress)

    # Check ReviewLog was created
    log_query = await db_session.execute(
        select(ReviewLog).where(ReviewLog.user_id == user.id, ReviewLog.item_id == vocab.id)
    )
    log = log_query.scalar_one_or_none()
    assert log is not None
    assert log.srs_stage_before == 3
    assert log.srs_stage_after == 4

    # Check UserItemProgress was updated
    assert progress.srs_stage == 4
    assert response.srs_stage_after == 4
    # Both should reflect the same stage progression
    assert log.srs_stage_after == progress.srs_stage
