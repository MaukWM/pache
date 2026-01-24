"""Tests for progress router."""

import pytest
from fastapi import status
from httpx import AsyncClient

from src.auth.models import Session, User
from src.core.constants import ItemType
from src.kanji.models import Kanji
from src.progress.models import LessonQueue
from src.vocab.models import Vocab


@pytest.mark.asyncio
async def test_add_to_queue_success(async_client: AsyncClient, db_session) -> None:
    """Test successful addition to queue returns 201."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

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

    # Add to queue
    response = await async_client.post(
        "/api/v1/me/queue",
        json={
            "item_type": "kanji",
            "item_id": kanji.id,
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["item_type"] == "kanji"
    assert data["item_id"] == kanji.id
    assert "added_at" in data
    assert "item_details" in data
    assert data["item_details"]["character"] == "漢"


@pytest.mark.asyncio
async def test_add_to_queue_duplicate_returns_409(async_client: AsyncClient, db_session) -> None:
    """Test that adding duplicate item returns 409 Conflict."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

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
    queue_item = LessonQueue(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
    )
    db_session.add(queue_item)
    await db_session.commit()

    # Try to add duplicate
    response = await async_client.post(
        "/api/v1/me/queue",
        json={
            "item_type": "kanji",
            "item_id": kanji.id,
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already in queue" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_add_to_queue_invalid_item_id_returns_400(
    async_client: AsyncClient, db_session
) -> None:
    """Test that adding invalid item_id returns 400 Bad Request."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

    # Try to add non-existent kanji
    response = await async_client.post(
        "/api/v1/me/queue",
        json={
            "item_type": "kanji",
            "item_id": 99999,
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_add_to_queue_unauthorized_returns_401(async_client: AsyncClient) -> None:
    """Test that unauthenticated request returns 401 Unauthorized."""
    response = await async_client.post(
        "/api/v1/me/queue",
        json={
            "item_type": "kanji",
            "item_id": 1,
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_queue_success(async_client: AsyncClient, db_session) -> None:
    """Test successful retrieval of queue returns 200."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

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
    response = await async_client.get(
        "/api/v1/me/queue",
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 2

    # Verify item details are included
    kanji_item = next(item for item in data["items"] if item["item_type"] == "kanji")
    assert kanji_item["item_details"]["character"] == "漢"

    vocab_item = next(item for item in data["items"] if item["item_type"] == "vocab")
    assert vocab_item["item_details"]["word"] == "日本語"


@pytest.mark.asyncio
async def test_get_queue_empty_returns_empty_list(async_client: AsyncClient, db_session) -> None:
    """Test that empty queue returns empty list."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

    # Get queue
    response = await async_client.get(
        "/api/v1/me/queue",
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_queue_unauthorized_returns_401(async_client: AsyncClient) -> None:
    """Test that unauthenticated request returns 401 Unauthorized."""
    response = await async_client.get("/api/v1/me/queue")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
