"""Tests for authentication models."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.models import Session, User


@pytest.mark.asyncio
async def test_user_model_creation(db_session: AsyncSession) -> None:
    """Test creating a User model with all required fields."""
    user = User(username="floppa")
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert user.username == "floppa"
    assert user.wk_api_key is None
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_user_with_wk_api_key(db_session: AsyncSession) -> None:
    """Test creating a User with WaniKani API key."""
    user = User(username="testuser", wk_api_key="some-api-key-123")
    db_session.add(user)
    await db_session.flush()

    assert user.wk_api_key == "some-api-key-123"


@pytest.mark.asyncio
async def test_user_username_unique(db_session: AsyncSession) -> None:
    """Test that usernames must be unique."""
    user1 = User(username="duplicate")
    db_session.add(user1)
    await db_session.flush()

    user2 = User(username="duplicate")
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_session_model_creation(db_session: AsyncSession) -> None:
    """Test creating a Session model."""
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token-abc123")
    db_session.add(session)
    await db_session.flush()

    assert session.id is not None
    assert session.user_id == user.id
    assert session.token == "test-token-abc123"
    assert session.created_at is not None


@pytest.mark.asyncio
async def test_session_token_unique(db_session: AsyncSession) -> None:
    """Test that session tokens must be unique."""
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session1 = Session(user_id=user.id, token="duplicate-token")
    db_session.add(session1)
    await db_session.flush()

    session2 = Session(user_id=user.id, token="duplicate-token")
    db_session.add(session2)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_user_sessions_relationship(db_session: AsyncSession) -> None:
    """Test relationship between User and Sessions."""
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session1 = Session(user_id=user.id, token="token-1")
    session2 = Session(user_id=user.id, token="token-2")
    db_session.add_all([session1, session2])
    await db_session.flush()

    # Verify relationship - use selectinload for async
    result = await db_session.execute(
        select(User).where(User.id == user.id).options(selectinload(User.sessions))
    )
    loaded_user = result.scalar_one()
    assert len(loaded_user.sessions) == 2
    assert {s.token for s in loaded_user.sessions} == {"token-1", "token-2"}


@pytest.mark.asyncio
async def test_session_user_relationship(db_session: AsyncSession) -> None:
    """Test reverse relationship from Session to User."""
    user = User(username="floppa")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="test-token")
    db_session.add(session)
    await db_session.flush()

    # Verify relationship - use selectinload for async
    result = await db_session.execute(
        select(Session).where(Session.id == session.id).options(selectinload(Session.user))
    )
    loaded_session = result.scalar_one()
    assert loaded_session.user.username == "floppa"
