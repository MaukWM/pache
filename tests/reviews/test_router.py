"""Tests for review router endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

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


@pytest.mark.asyncio
async def test_get_due_reviews_value_error_returns_400(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test that ValueError from service returns 400 Bad Request."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-valueerror")
    db_session.add(session)
    await db_session.commit()

    # Mock the service to raise ValueError (defensive validation scenario)
    with patch("src.reviews.router.ReviewService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.get_due_reviews = AsyncMock(
            side_effect=ValueError("Invalid user_id: -1 must be a positive integer")
        )
        mock_service_class.return_value = mock_service

        # Make request
        response = await async_client.get(
            "/api/v1/me/reviews",
            headers={"Authorization": "Bearer test-token-valueerror"},
        )

        # Verify 400 Bad Request response
        assert response.status_code == 400
        data = response.json()
        assert "Invalid user_id" in data["detail"]


# ============================================================================
# Tests for POST /api/v1/me/reviews (submit_review)
# ============================================================================


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_post_submit_review_success(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test POST /api/v1/me/reviews successfully submits review (AC1)."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-submit")
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
    response = await async_client.post(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-submit"},
        json={
            "item_type": "vocab",
            "item_id": vocab.id,
            "reading_correct": True,
            "meaning_correct": True,
        },
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["item_type"] == "vocab"
    assert data["item_id"] == vocab.id
    assert data["reading_correct"] is True
    assert data["meaning_correct"] is True
    assert data["srs_stage_before"] == 3
    assert data["srs_stage_after"] == 4
    assert data["next_review_at"] is not None


@pytest.mark.asyncio
async def test_post_submit_review_not_in_progress(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test POST /api/v1/me/reviews returns 400 when item not in progress (AC5)."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-not-progress")
    db_session.add(session)
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
    response = await async_client.post(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-not-progress"},
        json={
            "item_type": "vocab",
            "item_id": vocab.id,
            "reading_correct": True,
            "meaning_correct": True,
        },
    )

    # Verify 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "not in progress" in data["detail"].lower()


@pytest.mark.asyncio
async def test_post_submit_review_burned_item(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test POST /api/v1/me/reviews returns 400 when item is burned (AC6)."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-burned")
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
    response = await async_client.post(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-burned"},
        json={
            "item_type": "vocab",
            "item_id": vocab.id,
            "reading_correct": True,
            "meaning_correct": True,
        },
    )

    # Verify 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "burned" in data["detail"].lower()


@pytest.mark.asyncio
async def test_post_submit_review_missing_fields(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test POST /api/v1/me/reviews returns 400 when fields are missing (AC7)."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-missing")
    db_session.add(session)
    await db_session.commit()

    # Submit review with missing reading_correct
    response = await async_client.post(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-missing"},
        json={
            "item_type": "vocab",
            "item_id": 123,
            "meaning_correct": True,
            # reading_correct missing
        },
    )

    # Verify 422 Validation Error (FastAPI default for missing required fields)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_submit_review_invalid_item_type(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test POST /api/v1/me/reviews returns 400 when item_type is invalid (AC7)."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-invalid-type")
    db_session.add(session)
    await db_session.commit()

    # Submit review with invalid item_type
    response = await async_client.post(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-invalid-type"},
        json={
            "item_type": "invalid_type",
            "item_id": 123,
            "reading_correct": True,
            "meaning_correct": True,
        },
    )

    # Verify 422 Validation Error (FastAPI validates enum)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_submit_review_invalid_item_id(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test POST /api/v1/me/reviews returns 400 when item_id is invalid (AC7)."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-invalid-id")
    db_session.add(session)
    await db_session.commit()

    # Submit review with invalid item_id (non-positive)
    response = await async_client.post(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-invalid-id"},
        json={
            "item_type": "vocab",
            "item_id": 0,  # Invalid: must be > 0
            "reading_correct": True,
            "meaning_correct": True,
        },
    )

    # Verify 422 Validation Error (FastAPI validates Field(gt=0))
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_submit_review_unauthenticated(async_client: AsyncClient) -> None:
    """Test POST /api/v1/me/reviews returns 401 when not authenticated (AC8)."""
    # Make request without auth header
    response = await async_client.post(
        "/api/v1/me/reviews",
        json={
            "item_type": "vocab",
            "item_id": 123,
            "reading_correct": True,
            "meaning_correct": True,
        },
    )

    # Verify 401 Unauthorized
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
@freeze_time("2026-01-24 12:00:00", tz_offset=0)
async def test_post_submit_review_not_yet_due(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Test POST /api/v1/me/reviews returns 400 when item is not yet due for review."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-not-due")
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

    # Submit review for item not yet due
    response = await async_client.post(
        "/api/v1/me/reviews",
        headers={"Authorization": "Bearer test-token-not-due"},
        json={
            "item_type": "vocab",
            "item_id": vocab.id,
            "reading_correct": True,
            "meaning_correct": True,
        },
    )

    # Verify 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "not yet due for review" in data["detail"].lower()
