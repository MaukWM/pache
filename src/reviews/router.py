"""Review API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.logging import logger
from src.reviews.schemas import DueReviewsResponse, ReviewCreateRequest, ReviewResponse
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
    Returns 400 if validation error occurs (e.g., invalid user_id).
    Returns 500 if a database error occurs.
    """
    try:
        service = ReviewService(db)
        items = await service.get_due_reviews(user_id=current_user.id)
        return DueReviewsResponse(items=items, count=len(items))
    except ValueError as e:
        # Invalid user_id or other validation errors
        logger.warning(
            "validation_error_in_get_due_reviews_endpoint",
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_get_due_reviews_endpoint",
            user_id=current_user.id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving due reviews. Please try again later.",
        ) from e


@router.post("", response_model=ReviewResponse, status_code=200)
async def submit_review(
    request: ReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Submit a review for an item.

    Updates the item's SRS stage based on review correctness.
    Both reading and meaning must be correct to advance stage.

    Requires authentication. Returns 401 if not authenticated.
    Returns 400 if item is not in progress, is burned, or validation fails.
    Returns 500 if a database error occurs.
    """
    try:
        service = ReviewService(db)
        return await service.submit_review(user_id=current_user.id, request=request)
    except ValueError as e:
        # Item not in progress, burned, or other validation errors
        logger.warning(
            "validation_error_in_submit_review_endpoint",
            user_id=current_user.id,
            item_type=request.item_type,
            item_id=request.item_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SQLAlchemyError as e:
        logger.error(
            "database_error_in_submit_review_endpoint",
            user_id=current_user.id,
            item_type=request.item_type,
            item_id=request.item_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while submitting review. Please try again later.",
        ) from e
