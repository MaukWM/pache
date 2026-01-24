"""Review API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.reviews.schemas import DueReviewsResponse
from src.reviews.service import ReviewService

router = APIRouter(prefix="/me/reviews", tags=["reviews"])


@router.get("", response_model=DueReviewsResponse)
async def get_due_reviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DueReviewsResponse:
    """Get items due for review.

    Returns all items where next_review_at (truncated to hour) <= current hour.
    Items with srs_stage=9 (burned) are excluded.

    Requires authentication. Returns 401 if not authenticated.
    """
    service = ReviewService(db)
    items = await service.get_due_reviews(user_id=current_user.id)
    return DueReviewsResponse(items=items, count=len(items))
