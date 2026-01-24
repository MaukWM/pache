"""Review module Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.core.constants import ItemType
from src.progress.schemas import KanjiItemDetails, VocabItemDetails


class ReviewCreateRequest(BaseModel):
    """Request schema for submitting a review.

    Consolidates reading and meaning reviews into a single submission.
    Both fields must be provided for each review.
    """

    item_type: ItemType = Field(..., description="Type of item being reviewed (kanji or vocab)")
    item_id: int = Field(..., gt=0, description="ID of the kanji or vocab item")
    reading_correct: bool = Field(..., description="Whether the reading answer was correct")
    meaning_correct: bool = Field(..., description="Whether the meaning answer was correct")


class ReviewResponse(BaseModel):
    """Response schema for a submitted review.

    Returns the outcome of the review submission including
    the new SRS stage and next review time.
    """

    item_type: ItemType
    item_id: int = Field(..., gt=0)
    reading_correct: bool
    meaning_correct: bool
    srs_stage_before: int = Field(..., ge=1, le=9, description="SRS stage before review")
    srs_stage_after: int = Field(..., ge=1, le=9, description="SRS stage after review")
    next_review_at: datetime | None = Field(..., description="Next review time, or None if burned")

    model_config = {"from_attributes": True}


class ReviewLogResponse(BaseModel):
    """Response schema for viewing review history.

    Used when fetching a user's review log entries.
    """

    id: int
    item_type: ItemType
    item_id: int = Field(..., gt=0)
    reading_correct: bool
    meaning_correct: bool
    srs_stage_before: int = Field(..., ge=1, le=9)
    srs_stage_after: int = Field(..., ge=1, le=9)
    reviewed_at: datetime

    model_config = {"from_attributes": True}


class ReviewItemResponse(BaseModel):
    """Response schema for a single review item due for review.

    Includes full item details for immediate use in the review session.
    """

    item_type: ItemType
    item_id: int = Field(..., gt=0)
    srs_stage: int = Field(..., ge=1, le=8, description="SRS stage (1-8, excludes burned items)")
    next_review_at: datetime
    item_details: KanjiItemDetails | VocabItemDetails

    model_config = {"from_attributes": True}


class DueReviewsResponse(BaseModel):
    """Response schema for listing items due for review.

    Returns all items where next_review_at (truncated to hour) <= current hour.
    """

    items: list[ReviewItemResponse]
    count: int = Field(..., ge=0, description="Number of items due for review")
