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


class WaniKaniSpreadStage(BaseModel):
    """Per-SRS-stage item counts on WaniKani, split by subject type."""

    srs_stage: int
    radical: int = 0
    kanji: int = 0
    vocab: int = 0


class WaniKaniSpreadResponse(BaseModel):
    """Live WaniKani SRS distribution for the dashboard item-spread views."""

    configured: bool = Field(..., description="Whether the user has a WK API key set")
    stages: list[WaniKaniSpreadStage] = Field(
        default_factory=list, description="Counts per SRS stage (1–9), split by type"
    )


class WaniKaniForecastResponse(BaseModel):
    """Live WaniKani review forecast for the dashboard charts."""

    configured: bool = Field(..., description="Whether the user has a WK API key set")
    available_now: int = Field(
        0, description="Reviews available right now on WaniKani"
    )
    upcoming: list[str] = Field(
        default_factory=list,
        description="ISO8601 available_at timestamps of reviews coming due within the window",
    )
