"""Progress tracking API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.progress.schemas import QueueItemRequest, QueueItemResponse, QueueListResponse
from src.progress.service import ProgressService

router = APIRouter(prefix="/me/queue", tags=["progress"])


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
