"""Tests for review router endpoints."""

from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Session, User
from src.core.constants import ItemType
from src.kanji.models import Kanji
from src.progress.models import UserItemProgress
from src.vocab.models import Vocab


@pytest.mark.asyncio
async def test_get_due_reviews_success(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Test GET /api/v1/me/reviews returns due items."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
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

    # Create progress record due for review
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

    # Make request
    response = await async_client.get(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-123"},
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["item_type"] == "kanji"
    assert data["items"][0]["item_id"] == kanji.id
    assert data["items"][0]["srs_stage"] == 3
    assert data["items"][0]["item_details"]["character"] == "日"


@pytest.mark.asyncio
async def test_get_due_reviews_empty_response(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test GET /api/v1/me/reviews returns empty list when no items due."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-456")
    db_session.add(session)
    await db_session.commit()

    # Make request (no progress records)
    response = await async_client.get(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-456"},
    )

    # Verify empty response
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_due_reviews_unauthenticated(async_client: AsyncClient) -> None:
    """Test GET /api/v1/me/reviews returns 401 when not authenticated."""
    # Make request without auth header
    response = await async_client.get("/api/v1/me/reviews")

    # Verify 401 response
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_due_reviews_invalid_token(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test GET /api/v1/me/reviews returns 401 with invalid token."""
    # Create user but no session for the token
    user = User(username="testuser")
    db_session.add(user)
    await db_session.commit()

    # Make request with invalid token
    response = await async_client.get(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer invalid-token"},
    )

    # Verify 401 response
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_due_reviews_multiple_items(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test GET /api/v1/me/reviews returns multiple due items."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-789")
    db_session.add(session)
    await db_session.flush()

    # Create multiple kanji
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

    # Create progress records
    past_time = datetime.now(UTC) - timedelta(hours=2)
    progress1 = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji1.id,
        srs_stage=3,
        next_review_at=past_time,
    )
    progress2 = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji2.id,
        srs_stage=5,
        next_review_at=past_time,
    )
    db_session.add_all([progress1, progress2])
    await db_session.commit()

    # Make request
    response = await async_client.get(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-789"},
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_due_reviews_excludes_other_users(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test GET /api/v1/me/reviews only returns authenticated user's items."""
    # Create two users
    user1 = User(username="user1")
    user2 = User(username="user2")
    db_session.add_all([user1, user2])
    await db_session.flush()

    # Create session for user1 only
    session = Session(user_id=user1.id, token="user1-token")
    db_session.add(session)
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

    # Create progress for user2 (should not be returned)
    past_time = datetime.now(UTC) - timedelta(hours=2)
    progress = UserItemProgress(
        user_id=user2.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=3,
        next_review_at=past_time,
    )
    db_session.add(progress)
    await db_session.commit()

    # Make request as user1
    response = await async_client.get(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer user1-token"},
    )

    # Verify empty (user1 has no items)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_due_reviews_excludes_burned_items(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test GET /api/v1/me/reviews excludes items with srs_stage=9 (burned)."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-burned")
    db_session.add(session)
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

    # Create burned progress record (should be excluded)
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

    # Make request
    response = await async_client.get(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-burned"},
    )

    # Verify burned item is excluded
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_due_reviews_excludes_future_items(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test GET /api/v1/me/reviews excludes items with future next_review_at."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-future")
    db_session.add(session)
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

    # Make request
    response = await async_client.get(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-future"},
    )

    # Verify future item is excluded
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
@freeze_time("2026-01-24 14:30:00", tz_offset=0)
async def test_get_due_reviews_hour_batching(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test GET /api/v1/me/reviews includes items due within current hour (FR28)."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-hour")
    db_session.add(session)
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

    # Make request
    response = await async_client.get(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-hour"},
    )

    # Item should be included because it's due within the current hour
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_get_due_reviews_orders_by_next_review_at(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test GET /api/v1/me/reviews orders items by next_review_at ascending (oldest first)."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-order")
    db_session.add(session)
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

    # Make request
    response = await async_client.get(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-order"},
    )

    # Verify order - older first
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["item_id"] == kanji2.id  # Older
    assert data["items"][1]["item_id"] == kanji1.id  # Newer


@pytest.mark.asyncio
async def test_get_due_reviews_includes_vocab_details(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test GET /api/v1/me/reviews includes correct vocab item details."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-vocab")
    db_session.add(session)
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

    # Make request
    response = await async_client.get(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-vocab"},
    )

    # Verify vocab details
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["item_type"] == "vocab"
    assert data["items"][0]["item_id"] == vocab.id
    details = data["items"][0]["item_details"]
    assert details["word"] == "日本語"
    assert details["readings"] == ["にほんご"]
    assert details["meanings"] == ["Japanese language"]


@pytest.mark.asyncio
async def test_get_due_reviews_excludes_null_next_review_at(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test GET /api/v1/me/reviews excludes items with null next_review_at."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-null")
    db_session.add(session)
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

    # Make request
    response = await async_client.get(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-null"},
    )

    # Verify item with null next_review_at is excluded
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["items"] == []
