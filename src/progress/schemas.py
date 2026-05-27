"""Progress tracking API schemas."""

from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field

from src.core.constants import ItemType


class KanjiItemDetails(TypedDict):
    """Type definition for kanji item details."""

    character: str
    meanings: list[str]
    readings_on: list[str]
    readings_kun: list[str]


class VocabItemDetails(TypedDict):
    """Type definition for vocabulary item details."""

    word: str
    readings: list[str]
    meanings: list[str]
    tags: list[str]
    creator_comment: str | None
    creator_username: str | None


class QueueItemRequest(BaseModel):
    """Request schema for adding an item to the lesson queue."""

    item_type: ItemType
    item_id: int = Field(..., gt=0, description="Positive item ID")


class QueueItemResponse(BaseModel):
    """Response schema for a queue item."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: ItemType
    item_id: int
    added_at: datetime
    item_details: KanjiItemDetails | VocabItemDetails


class QueueListResponse(BaseModel):
    """Response schema for listing queue items."""

    items: list[QueueItemResponse]


class SelectedItem(BaseModel):
    """Schema for a selected item in lesson completion request."""

    item_type: ItemType
    item_id: int = Field(..., gt=0, description="Positive item ID")


class LessonCompleteRequest(BaseModel):
    """Request schema for completing lessons.

    Items can be completed directly - queue membership is NOT required.
    If an item happens to be in the user's queue, it is auto-removed.
    """

    item_ids: list[SelectedItem] = Field(..., min_length=1, description="List of items to complete")


class LessonItemResponse(BaseModel):
    """Response schema for a completed lesson item."""

    model_config = ConfigDict(from_attributes=True)

    item_type: ItemType
    item_id: int
    srs_stage: int = Field(..., description="SRS stage (starts at 1 for Apprentice 1)")
    next_review_at: datetime = Field(..., description="Next scheduled review time")
    item_details: KanjiItemDetails | VocabItemDetails


class LessonCompleteResponse(BaseModel):
    """Response schema for completed lessons."""

    items: list[LessonItemResponse]
    count: int = Field(..., description="Actual number of items processed")


class ProgressItemResponse(BaseModel):
    """Response schema for a user's progress on a single item."""

    model_config = ConfigDict(from_attributes=True)

    item_type: ItemType
    item_id: int
    srs_stage: int
    next_review_at: datetime | None
    unlocked_at: datetime
    burned_at: datetime | None
    meaning_note: str | None
    reading_mnemonic: str | None
    source: str


class ResurrectResponse(BaseModel):
    """Response schema for a resurrected (un-burned) item."""

    model_config = ConfigDict(from_attributes=True)

    item_type: ItemType
    item_id: int = Field(..., gt=0)
    srs_stage: int = Field(..., ge=1, le=9, description="Reset SRS stage (always 1)")
    next_review_at: datetime = Field(..., description="Next review time (4h after resurrection)")
    unlocked_at: datetime = Field(..., description="Original lesson completion time (unchanged)")
    message: str = Field(default="Item resurrected successfully")
