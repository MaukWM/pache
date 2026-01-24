"""Progress tracking API schemas."""

from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field

from src.core.constants import ItemType


class KanjiItemDetails(TypedDict):
    """Type definition for kanji item details."""

    character: str
    meanings: list[str]


class VocabItemDetails(TypedDict):
    """Type definition for vocabulary item details."""

    word: str
    readings: list[str]
    meanings: list[str]


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
