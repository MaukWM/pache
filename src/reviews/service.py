"""Review service layer for managing due reviews."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ItemType
from src.kanji.models import Kanji
from src.progress.models import UserItemProgress
from src.progress.schemas import KanjiItemDetails, VocabItemDetails
from src.reviews.schemas import ReviewItemResponse
from src.reviews.srs import truncate_to_hour
from src.vocab.models import Vocab


class ReviewService:
    """Service for managing review operations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def get_due_reviews(self, user_id: int) -> list[ReviewItemResponse]:
        """Get all items due for review for a user.

        Returns items where:
        - srs_stage < 9 (not burned)
        - next_review_at is not None
        - next_review_at (truncated to hour) <= current hour

        Items are ordered by next_review_at ascending (oldest first).
        Each item includes full details (kanji or vocab) for immediate use.

        Args:
            user_id: The ID of the user to get due reviews for.

        Returns:
            A list of ReviewItemResponse objects with item details.
        """
        current_hour = truncate_to_hour(datetime.now(UTC))

        # Query UserItemProgress for items due for review
        query = (
            select(UserItemProgress)
            .where(
                UserItemProgress.user_id == user_id,
                UserItemProgress.srs_stage < 9,  # Not burned
                UserItemProgress.next_review_at.isnot(None),
            )
            .order_by(UserItemProgress.next_review_at.asc())
        )

        result = await self.db.execute(query)
        progress_items = list(result.scalars().all())

        if not progress_items:
            return []

        # Filter by hour-truncated time (done in Python for SQLite compatibility)
        due_items = [
            item
            for item in progress_items
            if item.next_review_at and truncate_to_hour(item.next_review_at) <= current_hour
        ]

        if not due_items:
            return []

        # Separate kanji and vocab IDs for bulk loading
        kanji_ids = [p.item_id for p in due_items if p.item_type == ItemType.KANJI]
        vocab_ids = [p.item_id for p in due_items if p.item_type == ItemType.VOCAB]

        # Bulk load kanji items
        kanji_map: dict[int, Kanji] = {}
        if kanji_ids:
            kanji_query = select(Kanji).where(Kanji.id.in_(kanji_ids))
            kanji_result = await self.db.execute(kanji_query)
            kanji_map = {k.id: k for k in kanji_result.scalars().all()}

        # Bulk load vocab items
        vocab_map: dict[int, Vocab] = {}
        if vocab_ids:
            vocab_query = select(Vocab).where(Vocab.id.in_(vocab_ids))
            vocab_result = await self.db.execute(vocab_query)
            vocab_map = {v.id: v for v in vocab_result.scalars().all()}

        # Build response with item details
        responses: list[ReviewItemResponse] = []
        for progress in due_items:
            item_details: KanjiItemDetails | VocabItemDetails

            if progress.item_type == ItemType.KANJI:
                kanji = kanji_map.get(progress.item_id)
                if not kanji:
                    # Skip orphaned progress entries
                    continue
                item_details = KanjiItemDetails(
                    character=kanji.character,
                    meanings=kanji.meanings,
                    readings_on=kanji.readings_on,
                    readings_kun=kanji.readings_kun,
                )
            elif progress.item_type == ItemType.VOCAB:
                vocab = vocab_map.get(progress.item_id)
                if not vocab:
                    # Skip orphaned progress entries
                    continue
                item_details = VocabItemDetails(
                    word=vocab.word,
                    readings=vocab.readings,
                    meanings=vocab.meanings,
                )
            else:
                # Unknown item type, skip
                continue

            responses.append(
                ReviewItemResponse(
                    item_type=progress.item_type,
                    item_id=progress.item_id,
                    srs_stage=progress.srs_stage,
                    next_review_at=progress.next_review_at,
                    item_details=item_details,
                )
            )

        return responses
