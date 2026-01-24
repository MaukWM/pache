"""Tests for authentication dependencies."""

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import Session, User


@pytest.mark.asyncio
async def test_get_current_user_valid_token(db_session: AsyncSession) -> None:
    """Test get_current_user with valid token returns user."""
    # Create user and session
    user = User(username="testuser")
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id, token="valid-token-123")
    db_session.add(session)
    await db_session.commit()

    # Create credentials object
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token-123")

    # Call dependency
    result_user = await get_current_user(credentials=credentials, db=db_session)

    assert result_user.id == user.id
    assert result_user.username == "testuser"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db_session: AsyncSession) -> None:
    """Test get_current_user with invalid token raises 401."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid authentication token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_missing_user(db_session: AsyncSession) -> None:
    """Test get_current_user when session exists but user is missing raises 401."""
    # Create session with invalid user_id
    session = Session(user_id=99999, token="orphan-token")
    db_session.add(session)
    await db_session.commit()

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="orphan-token")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "User not found" in exc_info.value.detail
