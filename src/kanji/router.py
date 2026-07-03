"""Kanji API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.database import get_db
from src.kanji.schemas import KanjiListResponse, KanjiResponse
from src.kanji.service import KanjiService, KanjiSort

router = APIRouter(
    prefix="/kanji", tags=["kanji"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=KanjiListResponse)
async def list_kanji(
    include_inactive: bool = Query(default=False, description="Include inactive kanji"),
    limit: int | None = Query(default=None, ge=1, le=1000, description="Page size (None = all)"),
    offset: int = Query(default=0, ge=0, description="Rows to skip"),
    sort: KanjiSort = Query(default="default", description="Sort mode"),
    q: str | None = Query(default=None, max_length=100, description="Search text"),
    q_kana: str | None = Query(
        default=None, max_length=100, description="Hiragana rendering of a romaji search"
    ),
    hide_known: bool = Query(
        default=False, description="Exclude kanji the current user has progress on"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KanjiListResponse:
    """List kanji with optional pagination, sorting, search, and known-filter."""
    service = KanjiService(db)
    kanji_list, total = await service.get_page(
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
        sort=sort,
        q=q,
        q_kana=q_kana,
        exclude_known_user_id=current_user.id if hide_known else None,
    )
    return KanjiListResponse(
        items=[KanjiResponse.model_validate(kanji) for kanji in kanji_list],
        total=total,
    )


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
