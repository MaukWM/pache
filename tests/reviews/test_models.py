"""Tests for ReviewLog model."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.constants import ItemType
from src.reviews.models import ReviewLog


@pytest.mark.asyncio
async def test_review_log_creation(db_session: AsyncSession) -> None:
    """Test creating a ReviewLog entry."""
    # Create a test user first
    user = User(username="test_reviewer")
    db_session.add(user)
    await db_session.flush()

    # Create a review log entry
    review_log = ReviewLog(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=42,
        reading_correct=True,
        meaning_correct=True,
        srs_stage_before=3,
        srs_stage_after=4,
    )
    db_session.add(review_log)
    await db_session.flush()

    # Verify it was created
    result = await db_session.execute(select(ReviewLog).where(ReviewLog.id == review_log.id))
    fetched = result.scalar_one()

    assert fetched.user_id == user.id
    assert fetched.item_type == ItemType.KANJI
    assert fetched.item_id == 42
    assert fetched.reading_correct is True
    assert fetched.meaning_correct is True
    assert fetched.srs_stage_before == 3
    assert fetched.srs_stage_after == 4
    assert fetched.reviewed_at is not None


@pytest.mark.asyncio
async def test_review_log_with_partial_correct(db_session: AsyncSession) -> None:
    """Test creating a ReviewLog entry with partial correctness."""
    user = User(username="partial_reviewer")
    db_session.add(user)
    await db_session.flush()

    review_log = ReviewLog(
        user_id=user.id,
        item_type=ItemType.VOCAB,
        item_id=100,
        reading_correct=True,
        meaning_correct=False,
        srs_stage_before=5,
        srs_stage_after=3,
    )
    db_session.add(review_log)
    await db_session.flush()

    result = await db_session.execute(select(ReviewLog).where(ReviewLog.id == review_log.id))
    fetched = result.scalar_one()

    assert fetched.reading_correct is True
    assert fetched.meaning_correct is False
    assert fetched.srs_stage_before == 5
    assert fetched.srs_stage_after == 3


@pytest.mark.asyncio
async def test_review_log_reviewed_at_default(db_session: AsyncSession) -> None:
    """Test that reviewed_at defaults to current UTC time."""
    user = User(username="time_tester")
    db_session.add(user)
    await db_session.flush()

    before = datetime.now(UTC)

    review_log = ReviewLog(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=1,
        reading_correct=True,
        meaning_correct=True,
        srs_stage_before=1,
        srs_stage_after=2,
    )
    db_session.add(review_log)
    await db_session.flush()

    after = datetime.now(UTC)

    result = await db_session.execute(select(ReviewLog).where(ReviewLog.id == review_log.id))
    fetched = result.scalar_one()

    # reviewed_at should be set (not None)
    assert fetched.reviewed_at is not None
    # SQLite test DB may use naive datetime, so compare without timezone
    reviewed_at_naive = (
        fetched.reviewed_at.replace(tzinfo=None)
        if fetched.reviewed_at.tzinfo
        else fetched.reviewed_at
    )
    before_naive = before.replace(tzinfo=None)
    after_naive = after.replace(tzinfo=None)
    assert reviewed_at_naive >= before_naive
    assert reviewed_at_naive <= after_naive


@pytest.mark.asyncio
async def test_review_log_user_relationship(db_session: AsyncSession) -> None:
    """Test ReviewLog -> User relationship."""
    user = User(username="relationship_tester")
    db_session.add(user)
    await db_session.flush()

    review_log = ReviewLog(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=5,
        reading_correct=True,
        meaning_correct=True,
        srs_stage_before=2,
        srs_stage_after=3,
    )
    db_session.add(review_log)
    await db_session.flush()

    # Access the relationship
    result = await db_session.execute(select(ReviewLog).where(ReviewLog.id == review_log.id))
    fetched = result.scalar_one()

    assert fetched.user_id == user.id


@pytest.mark.asyncio
async def test_multiple_review_logs_for_same_user(db_session: AsyncSession) -> None:
    """Test creating multiple review logs for the same user."""
    user = User(username="multi_reviewer")
    db_session.add(user)
    await db_session.flush()

    # Create multiple review logs (one per item now that reading+meaning are combined)
    review_logs = [
        ReviewLog(
            user_id=user.id,
            item_type=ItemType.KANJI,
            item_id=1,
            reading_correct=True,
            meaning_correct=True,
            srs_stage_before=1,
            srs_stage_after=2,
        ),
        ReviewLog(
            user_id=user.id,
            item_type=ItemType.KANJI,
            item_id=2,
            reading_correct=True,
            meaning_correct=False,
            srs_stage_before=3,
            srs_stage_after=1,
        ),
        ReviewLog(
            user_id=user.id,
            item_type=ItemType.VOCAB,
            item_id=10,
            reading_correct=False,
            meaning_correct=True,
            srs_stage_before=4,
            srs_stage_after=2,
        ),
    ]

    for log in review_logs:
        db_session.add(log)
    await db_session.flush()

    # Verify all were created
    result = await db_session.execute(select(ReviewLog).where(ReviewLog.user_id == user.id))
    fetched_logs = result.scalars().all()

    assert len(fetched_logs) == 3


@pytest.mark.asyncio
async def test_review_log_cascade_delete_with_user(db_session: AsyncSession) -> None:
    """Test that review logs are deleted when user is deleted."""
    user = User(username="cascade_tester")
    db_session.add(user)
    await db_session.flush()
    user_id = user.id

    review_log = ReviewLog(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=1,
        reading_correct=True,
        meaning_correct=True,
        srs_stage_before=1,
        srs_stage_after=2,
    )
    db_session.add(review_log)
    await db_session.flush()

    # Delete the user
    await db_session.delete(user)
    await db_session.flush()

    # Verify review log was also deleted
    result = await db_session.execute(select(ReviewLog).where(ReviewLog.user_id == user_id))
    fetched_logs = result.scalars().all()

    assert len(fetched_logs) == 0
