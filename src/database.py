"""Database configuration and session management."""

import json
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.settings import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL debugging
    future=True,
    # Store JSON columns as raw UTF-8 (not \uXXXX escapes) so kana survives a
    # CAST-to-text LIKE search on every backend, including SQLite in tests.
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for declarative models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
