"""Pytest configuration and fixtures."""

from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.auth.models import Session, User  # noqa: F401
from src.database import Base, get_db

# Import all models to ensure they're registered with Base.metadata
from src.kanji.models import Kanji  # noqa: F401
from src.main import app
from src.progress.models import LessonQueue, UserItemProgress  # noqa: F401
from src.reviews.models import ReviewLog  # noqa: F401
from src.vocab.models import Tag, Vocab  # noqa: F401

# Create test database engine (in-memory SQLite)
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    future=True,
)

# Create test session factory
test_async_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="function", autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override get_db to use test database."""
    async with test_async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture(scope="function", autouse=True)
def override_dependency() -> Generator[None, None, None]:
    """Override get_db dependency for all tests."""
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    async with test_async_session_maker() as session:
        yield session
        await session.rollback()
        await session.close()
