"""WaniKani import routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.wanikani.schemas import WaniKaniImportResponse
from src.wanikani.service import WaniKaniService

router = APIRouter(prefix="/me/import", tags=["wanikani"])


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
