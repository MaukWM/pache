"""WaniKani import schemas."""

from pydantic import BaseModel, Field


class WaniKaniImportResponse(BaseModel):
    """Response schema for WaniKani import."""

    imported_count: int = Field(..., description="Number of kanji imported")
    skipped_count: int = Field(..., description="Number of kanji not found in DB")
    already_existed: int = Field(..., description="Number already in progress")
    total_fetched: int = Field(..., description="Total Guru+ kanji from WK")
