"""Progress tracking API routes."""

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.core.constants import ItemType
from src.database import get_db
from src.progress.models import UserItemProgress
from src.progress.schemas import (
    ProgressItemResponse,
    QueueItemRequest,
    QueueItemResponse,
    QueueListResponse,
    ResurrectResponse,
)
from src.progress.service import ProgressService

router = APIRouter(prefix="/me/queue", tags=["progress"])
progress_router = APIRouter(prefix="/me/progress", tags=["progress"])


@progress_router.get("", response_model=list[ProgressItemResponse])
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProgressItemResponse]:
    """Get all progress items for the current user."""
    from sqlalchemy import select
    result = await db.execute(
        select(UserItemProgress).where(UserItemProgress.user_id == current_user.id)
    )
    items = result.scalars().all()
    return [
        ProgressItemResponse(
            item_type=item.item_type,
            item_id=item.item_id,
            srs_stage=item.srs_stage,
            next_review_at=item.next_review_at,
            unlocked_at=item.unlocked_at,
            burned_at=item.burned_at,
            meaning_note=item.meaning_note,
            reading_mnemonic=item.reading_mnemonic,
            source=item.source,
        )
        for item in items
    ]


@router.post("", response_model=QueueItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_queue(
    request: QueueItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueueItemResponse:
    """Add an item to the user's lesson queue."""
    service = ProgressService(db)
    return await service.add_to_queue(
        user_id=current_user.id,
        item_type=request.item_type,
        item_id=request.item_id,
    )


@router.get("", response_model=QueueListResponse)
async def get_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueueListResponse:
    """Get all items in the user's lesson queue."""
    service = ProgressService(db)
    items = await service.get_queue(user_id=current_user.id)
    return QueueListResponse(items=items)


@router.delete("/{item_type}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_queue(
    item_type: ItemType = Path(..., description="Type of item to remove (kanji or vocab)"),
    item_id: int = Path(..., gt=0, description="Positive item ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove an item from the user's lesson queue.

    Args:
        item_type: Type of item to remove (kanji or vocab)
        item_id: Positive ID of the item to remove from queue
    """
    service = ProgressService(db)
    await service.remove_from_queue(
        user_id=current_user.id,
        item_type=item_type,
        item_id=item_id,
    )


@progress_router.post(
    "/{item_type}/{item_id}/resurrect",
    response_model=ResurrectResponse,
    status_code=status.HTTP_200_OK,
)
async def resurrect_item(
    item_type: ItemType = Path(..., description="Type of item to resurrect (kanji or vocab)"),
    item_id: int = Path(..., gt=0, description="Positive item ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResurrectResponse:
    """Resurrect a burned item, resetting it to SRS stage 1."""
    service = ProgressService(db)
    return await service.resurrect_item(
        user_id=current_user.id,
        item_type=item_type,
        item_id=item_id,
    )
