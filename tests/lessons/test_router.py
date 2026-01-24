"""Tests for lessons router."""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select

from src.auth.models import Session, User
from src.core.constants import ItemType, ProgressSource
from src.kanji.models import Kanji
from src.progress.models import LessonQueue, UserItemProgress
from src.vocab.models import Vocab


@pytest.mark.asyncio
async def test_complete_lessons_direct_without_queue(
    async_client: AsyncClient, db_session
) -> None:
    """Test completing lessons directly without queue membership returns 200."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

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
    await db_session.commit()

    # Complete lessons directly (no queue required)
    response = await async_client.post(
        "/api/v1/me/lessons",
        json={
            "item_ids": [
                {"item_type": "kanji", "item_id": kanji1.id},
                {"item_type": "kanji", "item_id": kanji2.id},
            ],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["count"] == 2
    assert len(data["items"]) == 2
    # Verify SRS stage is 1 (Apprentice 1)
    assert data["items"][0]["srs_stage"] == 1
    assert data["items"][1]["srs_stage"] == 1
    # Verify next_review_at is set
    assert data["items"][0]["next_review_at"] is not None
    assert data["items"][1]["next_review_at"] is not None


@pytest.mark.asyncio
async def test_complete_lessons_auto_removes_from_queue(
    async_client: AsyncClient, db_session
) -> None:
    """Test that items in queue are auto-removed when lesson is completed."""
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
    queue = LessonQueue(user_id=user.id, item_type=ItemType.KANJI, item_id=kanji.id)
    db_session.add(queue)
    await db_session.commit()

    # Complete lesson
    response = await async_client.post(
        "/api/v1/me/lessons",
        json={
            "item_ids": [{"item_type": "kanji", "item_id": kanji.id}],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_200_OK

    # Verify item was auto-removed from queue
    queue_query = select(LessonQueue).where(LessonQueue.user_id == user.id)
    result = await db_session.execute(queue_query)
    remaining_queue = list(result.scalars().all())
    assert len(remaining_queue) == 0


@pytest.mark.asyncio
async def test_complete_lessons_already_learned(
    async_client: AsyncClient, db_session
) -> None:
    """Test that completing already learned items returns 400."""
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

    # Create progress record (already learned)
    progress = UserItemProgress(
        user_id=user.id,
        item_type=ItemType.KANJI,
        item_id=kanji.id,
        srs_stage=1,
    )
    db_session.add(progress)
    await db_session.commit()

    # Try to complete lesson (should fail - already learned)
    # Note: Queue membership is NOT required anymore
    response = await async_client.post(
        "/api/v1/me/lessons",
        json={
            "item_ids": [{"item_type": "kanji", "item_id": kanji.id}],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already learned" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_complete_lessons_prerequisite_failure(
    async_client: AsyncClient, db_session
) -> None:
    """Test that vocab items without learned kanji prerequisites return 400."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

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
    await db_session.commit()

    # Try to complete lesson (should fail - kanji not at GURU stage)
    # Note: Queue membership is NOT required anymore
    response = await async_client.post(
        "/api/v1/me/lessons",
        json={
            "item_ids": [{"item_type": "vocab", "item_id": vocab.id}],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "requires learned kanji" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_complete_lessons_unauthenticated(async_client: AsyncClient) -> None:
    """Test that unauthenticated request returns 401."""
    # Try to complete lessons without authentication
    response = await async_client.post(
        "/api/v1/me/lessons",
        json={
            "item_ids": [{"item_type": "kanji", "item_id": 1}],
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_complete_lessons_prerequisite_satisfied(
    async_client: AsyncClient, db_session
) -> None:
    """Test that vocab items can be learned when kanji prerequisites are met."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-123")
    db_session.add(session)
    await db_session.commit()

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
    await db_session.commit()

    # Complete lesson (should succeed - kanji at GURU stage)
    # Note: Queue membership is NOT required anymore
    response = await async_client.post(
        "/api/v1/me/lessons",
        json={
            "item_ids": [{"item_type": "vocab", "item_id": vocab.id}],
        },
        headers={"Authorization": "Bearer test-token-123"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["item_type"] == "vocab"
    assert data["items"][0]["item_id"] == vocab.id
    assert data["items"][0]["srs_stage"] == 1  # Apprentice 1, not 0
    assert data["items"][0]["next_review_at"] is not None
