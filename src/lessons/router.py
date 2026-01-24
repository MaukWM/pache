"""Lesson API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.lessons.service import LessonService
from src.progress.schemas import LessonCompleteRequest, LessonCompleteResponse

router = APIRouter(prefix="/me/lessons", tags=["lessons"])


@router.post("", response_model=LessonCompleteResponse, status_code=status.HTTP_200_OK)
async def complete_lessons(
    request: LessonCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonCompleteResponse:
    """Complete lessons from the user's queue.

    For vocab items, checks that all constituent kanji are learned.
    """
    service = LessonService(db)
    return await service.complete_lessons(
        user_id=current_user.id,
        request=request,
    )
