"""Tests for review service."""

from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.constants import ItemType
from src.kanji.models import Kanji
from src.progress.models import UserItemProgress
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
    assert reviews[0].item_details["character"] == "日"


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
    details = reviews[0].item_details
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
    details = reviews[0].item_details
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
