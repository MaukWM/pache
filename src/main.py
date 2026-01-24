"""FastAPI application entry point."""

from fastapi import FastAPI

from src.logging import logger
from src.settings import settings

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)

# Initialize logging
logger.info("app_started", version=settings.api_version)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Kanji SRS Platform API", "version": settings.api_version}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
