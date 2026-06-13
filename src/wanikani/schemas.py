"""WaniKani import schemas."""

from pydantic import BaseModel, Field


class WaniKaniImportResponse(BaseModel):
    """Response schema for WaniKani import."""

    imported_count: int = Field(..., description="Number of kanji imported")
    skipped_count: int = Field(..., description="Number of kanji not found in DB")
    already_existed: int = Field(..., description="Number already in progress")
    total_fetched: int = Field(..., description="Total Guru+ kanji from WK")


class WaniKaniStatusResponse(BaseModel):
    """Live WaniKani review status for the dashboard."""

    configured: bool = Field(..., description="Whether the user has a WK API key set")
    reviews_due: int | None = Field(
        None, description="Reviews available right now on WaniKani (null if not configured)"
    )
