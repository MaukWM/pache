"""Kanji API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.kanji.schemas import KanjiResponse
from src.kanji.service import KanjiService

router = APIRouter(prefix="/kanji", tags=["kanji"])


@router.get("", response_model=list[KanjiResponse])
async def list_kanji(
    include_inactive: bool = Query(default=False, description="Include inactive kanji"),
    db: AsyncSession = Depends(get_db),
) -> list[KanjiResponse]:
    """List all kanji, optionally including inactive ones."""
    service = KanjiService(db)
    kanji_list = await service.get_all(include_inactive=include_inactive)
    return [KanjiResponse.model_validate(kanji) for kanji in kanji_list]


@router.get("/{id_or_char}", response_model=KanjiResponse)
async def get_kanji(
    id_or_char: str | int,
    db: AsyncSession = Depends(get_db),
) -> KanjiResponse:
    """Get a single kanji by ID or character."""
    service = KanjiService(db)

    # Try to parse as integer (ID)
    try:
        kanji_id = int(id_or_char)
        kanji = await service.get_by_id(kanji_id)
    except ValueError:
        # Not an integer, treat as character
        if isinstance(id_or_char, str) and len(id_or_char) == 1:
            kanji = await service.get_by_character(id_or_char)
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid kanji identifier. Must be an integer ID or single character",
            )

    if kanji is None:
        raise HTTPException(status_code=404, detail="Kanji not found")

    return KanjiResponse.model_validate(kanji)
