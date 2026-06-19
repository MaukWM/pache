"""WaniKani import routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.wanikani.schemas import (
    WaniKaniForecastResponse,
    WaniKaniImportResponse,
    WaniKaniSpreadResponse,
    WaniKaniSpreadStage,
    WaniKaniStatusResponse,
)
from src.wanikani.service import WaniKaniService

router = APIRouter(prefix="/me/import", tags=["wanikani"])
status_router = APIRouter(prefix="/me/wanikani", tags=["wanikani"])


@status_router.get("/status", response_model=WaniKaniStatusResponse)
async def wanikani_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WaniKaniStatusResponse:
    """Live count of reviews currently due on WaniKani for this user."""
    if not current_user.wk_api_key:
        return WaniKaniStatusResponse(configured=False, reviews_due=None)
    service = WaniKaniService(db, current_user.wk_api_key)
    reviews_due = await service.get_review_status()
    return WaniKaniStatusResponse(configured=True, reviews_due=reviews_due)


@status_router.get("/forecast", response_model=WaniKaniForecastResponse)
async def wanikani_forecast(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WaniKaniForecastResponse:
    """Live WaniKani review forecast (next 7 days) for the dashboard charts."""
    if not current_user.wk_api_key:
        return WaniKaniForecastResponse(configured=False)
    service = WaniKaniService(db, current_user.wk_api_key)
    available_now, upcoming = await service.get_review_forecast()
    return WaniKaniForecastResponse(
        configured=True, available_now=available_now, upcoming=upcoming
    )


@status_router.get("/spread", response_model=WaniKaniSpreadResponse)
async def wanikani_spread(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WaniKaniSpreadResponse:
    """Live WaniKani SRS distribution for the dashboard item-spread views."""
    if not current_user.wk_api_key:
        return WaniKaniSpreadResponse(configured=False)
    service = WaniKaniService(db, current_user.wk_api_key)
    counts = await service.get_srs_spread()
    stages = [
        WaniKaniSpreadStage(srs_stage=stage, **types) for stage, types in sorted(counts.items())
    ]
    return WaniKaniSpreadResponse(configured=True, stages=stages)


@router.post("/wanikani", response_model=WaniKaniImportResponse)
async def import_wanikani(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WaniKaniImportResponse:
    """Import burned kanji from WaniKani."""
    if not current_user.wk_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WaniKani API key not configured. Set it in settings first.",
        )
    service = WaniKaniService(db, current_user.wk_api_key)
    return await service.import_guru_plus_kanji(current_user.id)
