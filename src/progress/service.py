"""Progress tracking service layer."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ItemType
from src.kanji.models import Kanji
from src.progress.models import LessonQueue
from src.progress.schemas import (
    KanjiItemDetails,
    QueueItemResponse,
    VocabItemDetails,
)
from src.vocab.models import Vocab


class ProgressService:
    """Service for progress tracking and queue management."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def add_to_queue(
        self,
        user_id: int,
        item_type: ItemType,
        item_id: int,
    ) -> QueueItemResponse:
        """Add an item to the user's lesson queue.
        
        Example:
            response = await service.add_to_queue(
                user_id=1,
                item_type=ItemType.KANJI,
                item_id=42
            )
        """
        # Validate item exists
        item_details: KanjiItemDetails | VocabItemDetails
        if item_type == ItemType.KANJI:
            item = await self.db.get(Kanji, item_id)
            if item is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Kanji with id={item_id} not found",
                )
            item_details = {
                "character": item.character,
                "meanings": item.meanings,
            }
        elif item_type == ItemType.VOCAB:
            item = await self.db.get(Vocab, item_id)
            if item is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Vocab with id={item_id} not found",
                )
            item_details = {
                "word": item.word,
                "readings": item.readings,
                "meanings": item.meanings,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid item_type: {item_type}",
            )

        # Check for duplicate
        existing = await self.db.execute(
            select(LessonQueue).where(
                LessonQueue.user_id == user_id,
                LessonQueue.item_type == item_type,
                LessonQueue.item_id == item_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Item ({item_type.value}, {item_id}) already in queue",
            )

        # Create queue item
        queue_item = LessonQueue(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
        )
        self.db.add(queue_item)

        try:
            await self.db.commit()
            await self.db.refresh(queue_item)
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Item ({item_type.value}, {item_id}) already in queue",
            )

        return QueueItemResponse(
            id=queue_item.id,
            item_type=queue_item.item_type,
            item_id=queue_item.item_id,
            added_at=queue_item.added_at,
            item_details=item_details,
        )

    async def get_queue(self, user_id: int) -> list[QueueItemResponse]:
        """Get all items in the user's lesson queue.
        
        Example:
            responses = await service.get_queue(user_id=1)
            for item in responses:
                print(f"{item.item_type}: {item.item_details}")
        """
        query = (
            select(LessonQueue)
            .where(LessonQueue.user_id == user_id)
            .order_by(LessonQueue.added_at)
        )
        result = await self.db.execute(query)
        queue_items = list(result.scalars().all())

        if not queue_items:
            return []

        # Separate kanji and vocab IDs for bulk loading
        kanji_ids = [
            q.item_id for q in queue_items if q.item_type == ItemType.KANJI
        ]
        vocab_ids = [
            q.item_id for q in queue_items if q.item_type == ItemType.VOCAB
        ]

        # Bulk load kanji items
        kanji_map: dict[int, Kanji] = {}
        if kanji_ids:
            kanji_query = select(Kanji).where(Kanji.id.in_(kanji_ids))
            kanji_result = await self.db.execute(kanji_query)
            kanji_map = {kanji.id: kanji for kanji in kanji_result.scalars().all()}

        # Bulk load vocab items
        vocab_map: dict[int, Vocab] = {}
        if vocab_ids:
            vocab_query = select(Vocab).where(Vocab.id.in_(vocab_ids))
            vocab_result = await self.db.execute(vocab_query)
            vocab_map = {vocab.id: vocab for vocab in vocab_result.scalars().all()}

        # Build responses and clean up orphaned entries
        responses = []
        orphaned_queue_items = []

        for queue_item in queue_items:
            item_details: KanjiItemDetails | VocabItemDetails
            if queue_item.item_type == ItemType.KANJI:
                kanji = kanji_map.get(queue_item.item_id)
                if kanji:
                    item_details = {
                        "character": kanji.character,
                        "meanings": kanji.meanings,
                    }
                else:
                    # Item was deleted, mark for cleanup
                    orphaned_queue_items.append(queue_item)
                    continue
            elif queue_item.item_type == ItemType.VOCAB:
                vocab = vocab_map.get(queue_item.item_id)
                if vocab:
                    item_details = {
                        "word": vocab.word,
                        "readings": vocab.readings,
                        "meanings": vocab.meanings,
                    }
                else:
                    # Item was deleted, mark for cleanup
                    orphaned_queue_items.append(queue_item)
                    continue
            else:
                continue

            responses.append(
                QueueItemResponse(
                    id=queue_item.id,
                    item_type=queue_item.item_type,
                    item_id=queue_item.item_id,
                    added_at=queue_item.added_at,
                    item_details=item_details,
                )
            )

        # Clean up orphaned queue entries
        for orphaned_item in orphaned_queue_items:
            await self.db.delete(orphaned_item)
        if orphaned_queue_items:
            await self.db.commit()

        return responses

    async def remove_from_queue(
        self,
        user_id: int,
        item_type: ItemType,
        item_id: int,
    ) -> None:
        """Remove an item from the user's lesson queue.
        
        Example:
            await service.remove_from_queue(
                user_id=1,
                item_type=ItemType.VOCAB,
                item_id=123
            )
        """
        # Query for the queue item
        query = select(LessonQueue).where(
            LessonQueue.user_id == user_id,
            LessonQueue.item_type == item_type,
            LessonQueue.item_id == item_id,
        )
        result = await self.db.execute(query)
        queue_item = result.scalar_one_or_none()

        if queue_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item ({item_type.value}, {item_id}) not found in queue",
            )

        # Delete the queue item
        await self.db.delete(queue_item)
        await self.db.commit()
