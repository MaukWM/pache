"""Tests for database connection and session management."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.main import app


@pytest.mark.asyncio
async def test_get_db_returns_async_session(db_session: AsyncSession):
    """Test that db_session fixture returns an AsyncSession."""
    assert isinstance(db_session, AsyncSession)


@pytest.mark.asyncio
async def test_database_session_can_execute_query(db_session: AsyncSession):
    """Test that database session can execute a simple query."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
