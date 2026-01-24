"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import func, select

from src.database import async_session_maker
from src.kanji.models import Kanji
from src.kanji.router import router as kanji_router
from src.lessons.router import router as lessons_router
from src.logging import logger
from src.progress.router import router as progress_router
from src.reviews.router import router as reviews_router
from src.settings import settings
from src.vocab.router import router as vocab_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - seeds kanji on startup if table is empty."""
    async with async_session_maker() as db:
        result = await db.execute(select(func.count()).select_from(Kanji))
        count = result.scalar()

        if count == 0:
            logger.info("kanji_table_empty", message="Seeding kanji from jamdict...")
            from scripts.seed_kanji import load_kanji_from_jamdict, seed_kanji

            kanji_data = load_kanji_from_jamdict()
            inserted, skipped = await seed_kanji(db, kanji_data)
            logger.info("kanji_seed_complete", inserted=inserted, skipped=skipped)
        else:
            logger.info("kanji_table_populated", count=count)

    yield


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan,
)

# Initialize logging
logger.info("app_started", version=settings.api_version)

# Mount routers
app.include_router(kanji_router, prefix=settings.api_prefix)
app.include_router(vocab_router, prefix=settings.api_prefix)
app.include_router(progress_router, prefix=settings.api_prefix)
app.include_router(lessons_router, prefix=settings.api_prefix)
app.include_router(reviews_router, prefix=settings.api_prefix)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Kanji SRS Platform API", "version": settings.api_version}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
