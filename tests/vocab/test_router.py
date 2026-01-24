"""Tests for vocabulary router."""

import pytest
from fastapi import status
from httpx import AsyncClient

from src.auth.models import Session, User
from src.kanji.models import Kanji


@pytest.mark.asyncio
async def test_create_vocab_success(async_client: AsyncClient, db_session) -> None:
    """Test successful vocabulary creation."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

    # Create kanji for testing
    # Note: "日本語" contains 3 characters, but we only link 2 kanji (日, 本)
    # The third character (語) is not in our test data - this tests partial linking
    # which is valid: not all characters in a word need to be linked kanji
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
    await db_session.commit()

    # Create vocab
    response = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本語",
            "readings": ["にほんご"],
            "meanings": ["Japanese language"],
            "kanji_ids": [kanji1.id, kanji2.id],
            "tags": ["language", "N5"],
            "creator_comment": "Found in my textbook",
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["word"] == "日本語"
    assert data["readings"] == ["にほんご"]
    assert data["meanings"] == ["Japanese language"]
    assert data["creator_id"] == user.id
    assert data["creator_username"] == "testuser"
    assert data["creator_comment"] == "Found in my textbook"
    assert len(data["kanji"]) == 2
    assert len(data["tags"]) == 2
    assert {t["name"] for t in data["tags"]} == {"language", "N5"}


@pytest.mark.asyncio
async def test_create_vocab_invalid_kanji_id(async_client: AsyncClient, db_session) -> None:
    """Test vocabulary creation with invalid kanji ID returns 400."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

    # Try to create vocab with invalid kanji ID
    response = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本語",
            "readings": ["にほんご"],
            "meanings": ["Japanese language"],
            "kanji_ids": [99999],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_vocab_unauthorized(async_client: AsyncClient) -> None:
    """Test vocabulary creation without authentication returns 401."""
    response = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本語",
            "readings": ["にほんご"],
            "meanings": ["Japanese language"],
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_vocab_invalid_token(async_client: AsyncClient) -> None:
    """Test vocabulary creation with invalid token returns 401."""
    response = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本語",
            "readings": ["にほんご"],
            "meanings": ["Japanese language"],
        },
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_vocab_duplicate_word(async_client: AsyncClient, db_session) -> None:
    """Test vocabulary creation with duplicate word returns 400."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

    # Create first vocab
    response1 = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本",
            "readings": ["にほん"],
            "meanings": ["Japan"],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )
    assert response1.status_code == status.HTTP_201_CREATED

    # Try to create duplicate
    response2 = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本",  # Same word
            "readings": ["にっぽん"],
            "meanings": ["Japan"],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_vocab_auto_activates_kanji(async_client: AsyncClient, db_session) -> None:
    """Test that creating vocab activates linked kanji."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

    # Create inactive kanji
    kanji = Kanji(
        character="日",
        meanings=["day"],
        readings_on=["ニチ"],
        readings_kun=["ひ"],
        stroke_count=4,
        active=False,
    )
    db_session.add(kanji)
    await db_session.commit()

    assert kanji.active is False

    # Create vocab linking to kanji
    response = await async_client.post(
        "/api/v1/vocab",
        json={
            "word": "日本",
            "readings": ["にほん"],
            "meanings": ["Japan"],
            "kanji_ids": [kanji.id],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    # Verify kanji was activated
    await db_session.refresh(kanji)
    assert kanji.active is True
