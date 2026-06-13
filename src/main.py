"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from src.auth.router import router as auth_router
from src.database import async_session_maker
from src.kanji.models import Kanji
from src.kanji.router import router as kanji_router
from src.lessons.router import router as lessons_router
from src.logging import logger
from src.progress.router import progress_router as progress_actions_router
from src.progress.router import router as progress_router
from src.reviews.router import router as reviews_router
from src.settings import settings
from src.vocab.router import router as vocab_router
from src.wanikani.router import router as wanikani_router


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

# CORS - allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logging
logger.info("app_started", version=settings.api_version)

# Mount routers
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(kanji_router, prefix=settings.api_prefix)
app.include_router(vocab_router, prefix=settings.api_prefix)
app.include_router(progress_router, prefix=settings.api_prefix)
app.include_router(progress_actions_router, prefix=settings.api_prefix)
app.include_router(lessons_router, prefix=settings.api_prefix)
app.include_router(reviews_router, prefix=settings.api_prefix)
app.include_router(wanikani_router, prefix=settings.api_prefix)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Serve the built frontend (SPA) when present (production image).
# In local dev the Vite server handles the UI, so this block is a no-op.
_STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend_dist"

if _STATIC_DIR.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=_STATIC_DIR / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve static files, falling back to index.html for client-side routes."""
        candidate = _STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_STATIC_DIR / "index.html")

else:

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint (API-only mode, no bundled frontend)."""
        return {"message": "Kanji SRS Platform API", "version": settings.api_version}
