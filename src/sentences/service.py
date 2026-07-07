"""Production-SRS sentence service layer.

Owner-scoped reads live HERE (single funnel) — so adding a visibility/sharing filter later is a
one-place change. Do NOT scatter `select(ProductionSentence)` into other domains.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ItemType
from src.logging import logger
from src.progress.models import UserItemProgress
from src.reviews.srs import calculate_next_review, truncate_to_hour
from src.sentences.models import ProductionSentence, ProductionSentenceReviewLog
from src.sentences.schemas import (
    DueSentenceResponse,
    SentenceReviewCreateRequest,
    SentenceReviewResponse,
)


def _normalize(text: str) -> str:
    """Minimal normalization for the exact-match fast path.

    Strips surrounding whitespace, removes spaces (Japanese doesn't use them), and drops a
    trailing period. Near-misses fall through to the LLM judge (step 3), which is the real
    safety net — so this stays deliberately small.
    """
    return text.strip().replace(" ", "").replace("　", "").rstrip("。.")


@dataclass(frozen=True)
class Judgment:
    """Result of judging a submission against the reference."""

    correct: bool  # drives SRS
    exact_match: bool  # passed via normalized exact-match (no LLM)
    feedback: str | None = None  # why wrong, or a better phrasing when correct


def _judge(submitted: str, reference: str) -> Judgment:
    """Judge a submission.

    ponytail: exact-match only for now. Step 3 swaps the miss-branch for an LLM call that
    judges naturalness/closeness and returns feedback. Return type stays `Judgment`.
    """
    if _normalize(submitted) == _normalize(reference):
        return Judgment(correct=True, exact_match=True)
    return Judgment(correct=False, exact_match=False)  # step 3: miss -> LLM judge


class SentenceService:
    """Service for production-sentence review operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_due(self, user_id: int) -> list[DueSentenceResponse]:
        """Return the user's production sentences due for review (hour-batched, FR28).

        Omits the reference Japanese — the user must produce it.
        """
        now = datetime.now(UTC)
        current_hour = truncate_to_hour(now)

        query = (
            select(UserItemProgress, ProductionSentence)
            .join(
                ProductionSentence,
                ProductionSentence.id == UserItemProgress.item_id,
            )
            .where(
                UserItemProgress.user_id == user_id,
                UserItemProgress.item_type == ItemType.SENTENCE,
                UserItemProgress.srs_stage < 9,  # not burned
                UserItemProgress.next_review_at.isnot(None),
            )
            .order_by(UserItemProgress.next_review_at.asc())
        )
        rows = (await self.db.execute(query)).all()

        # Hour precision in Python (SQLite test compatibility, matches ReviewService).
        due: list[DueSentenceResponse] = []
        for progress, sentence in rows:
            item_dt = progress.next_review_at
            if item_dt.tzinfo is None:
                item_dt = item_dt.replace(tzinfo=UTC)
            if truncate_to_hour(item_dt) <= current_hour:
                due.append(
                    DueSentenceResponse(
                        sentence_id=sentence.id,
                        english=sentence.english,
                        srs_stage=progress.srs_stage,
                    )
                )
        return due

    async def submit_review(
        self, user_id: int, request: SentenceReviewCreateRequest
    ) -> SentenceReviewResponse:
        """Judge a submitted attempt, advance/reset SRS, and log it."""
        try:
            now = datetime.now(UTC)

            # Lock the progress row for the transaction (mirrors ReviewService) to prevent
            # concurrent submissions racing on stage progression / duplicate log rows.
            progress = (
                await self.db.execute(
                    select(UserItemProgress)
                    .where(
                        UserItemProgress.user_id == user_id,
                        UserItemProgress.item_type == ItemType.SENTENCE,
                        UserItemProgress.item_id == request.sentence_id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()

            # ponytail: guard + due-check + outcome below duplicate ReviewService orchestration.
            # DRY later (hour_reached / apply_review_outcome in srs.py) — see production-srs-design.md
            # "TECH DEBT". Deferred to avoid touching mature ReviewService now.
            if progress is None:
                raise ValueError("Sentence not in progress")
            if progress.srs_stage >= 9:
                raise ValueError("Sentence is burned")
            if progress.next_review_at is not None:
                item_dt = progress.next_review_at
                if item_dt.tzinfo is None:
                    item_dt = item_dt.replace(tzinfo=UTC)
                if truncate_to_hour(item_dt) > truncate_to_hour(now):
                    raise ValueError("Sentence is not yet due for review")

            sentence = await self.db.get(ProductionSentence, request.sentence_id)
            if sentence is None or sentence.user_id != user_id:
                raise ValueError("Sentence not found")

            verdict = _judge(request.submitted, sentence.japanese)
            current_stage = progress.srs_stage
            new_stage, next_review_at = calculate_next_review(current_stage, verdict.correct)

            self.db.add(
                ProductionSentenceReviewLog(
                    user_id=user_id,
                    sentence_id=sentence.id,
                    submitted=request.submitted,
                    exact_match=verdict.exact_match,
                    correct=verdict.correct,
                    feedback=verdict.feedback,
                    srs_stage_before=current_stage,
                    srs_stage_after=new_stage,
                    reviewed_at=now,
                )
            )
            progress.srs_stage = new_stage
            progress.next_review_at = next_review_at
            if new_stage == 9:
                progress.burned_at = now

            await self.db.commit()

            return SentenceReviewResponse(
                sentence_id=sentence.id,
                correct=verdict.correct,
                exact_match=verdict.exact_match,
                feedback=verdict.feedback,
                reference=sentence.japanese,
                srs_stage_before=current_stage,
                srs_stage_after=new_stage,
                next_review_at=next_review_at,
            )
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(
                "database_error_submitting_sentence_review",
                user_id=user_id,
                sentence_id=request.sentence_id,
                error_type=type(e).__name__,
                error=str(e),
            )
            raise
