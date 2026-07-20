"""Production-SRS sentence service layer.

Owner-scoped reads live HERE (single funnel) — so adding a visibility/sharing filter later is a
one-place change. Do NOT scatter `select(ProductionSentence)` into other domains.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from openai import OpenAIError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import SRS_INTERVALS, ItemType, Politeness, ProgressSource
from src.llm.judge import judge
from src.llm.validate import validate_pair
from src.logging import logger
from src.progress.models import UserItemProgress
from src.reviews.srs import calculate_next_review, truncate_to_hour
from src.sentences.models import ProductionSentence, ProductionSentenceReviewLog
from src.sentences.schemas import (
    DueSentenceResponse,
    SentenceCreateRequest,
    SentenceCreateResponse,
    SentenceDetailResponse,
    SentenceJudgeResponse,
    SentenceLessonItem,
    SentenceListItem,
    SentenceOverrideResponse,
    SentenceReviewCreateRequest,
    SentenceReviewLogItem,
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


class SentenceService:
    """Service for production-sentence review operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, user_id: int, request: SentenceCreateRequest
    ) -> SentenceCreateResponse:
        """Validate the EN/JP pair (server-side), then insert it as a PENDING LESSON.

        Raises ValueError if the pair is rejected (→ 422). LLM/DB errors propagate to the router.
        No SRS progress row yet — the sentence waits as a lesson (get_lessons) until the user
        learns it (complete_lessons), which is when it enters SRS at Apprentice 1.
        """
        result = await validate_pair(request.english, request.japanese)
        if not result.valid:
            raise ValueError(result.reason or "The English/Japanese pair was rejected.")

        politeness = Politeness(result.politeness)  # trust the validator's classification

        sentence = ProductionSentence(
            user_id=user_id,
            english=request.english,
            japanese=request.japanese,
            politeness=politeness,
        )
        self.db.add(sentence)
        await self.db.commit()

        return SentenceCreateResponse(
            sentence_id=sentence.id,
            english=sentence.english,
            japanese=sentence.japanese,
            politeness=politeness,
        )

    async def get_lessons(self, user_id: int) -> list[SentenceLessonItem]:
        """Pending sentence lessons: the user's sentences that have no SRS progress row yet."""
        query = (
            select(ProductionSentence)
            .outerjoin(
                UserItemProgress,
                (UserItemProgress.item_id == ProductionSentence.id)
                & (UserItemProgress.item_type == ItemType.SENTENCE)
                & (UserItemProgress.user_id == user_id),
            )
            .where(
                ProductionSentence.user_id == user_id,
                UserItemProgress.id.is_(None),  # no progress → not yet learned
            )
            .order_by(ProductionSentence.created_at.asc())
        )
        rows = (await self.db.execute(query)).scalars().all()
        return [
            SentenceLessonItem(
                sentence_id=s.id,
                english=s.english,
                japanese=s.japanese,
                politeness=s.politeness,
            )
            for s in rows
        ]

    async def complete_lessons(
        self, user_id: int, sentence_ids: list[int]
    ) -> list[int]:
        """Learn pending sentences → create SRS progress at Apprentice 1 (first review ~4h).

        Skips ids that aren't the user's or already have progress (idempotent). Returns the ids
        that were newly learned.
        """
        # Own, still-pending sentences only.
        owned = set(
            (
                await self.db.execute(
                    select(ProductionSentence.id).where(
                        ProductionSentence.id.in_(sentence_ids),
                        ProductionSentence.user_id == user_id,
                    )
                )
            ).scalars().all()
        )
        already = set(
            (
                await self.db.execute(
                    select(UserItemProgress.item_id).where(
                        UserItemProgress.user_id == user_id,
                        UserItemProgress.item_type == ItemType.SENTENCE,
                        UserItemProgress.item_id.in_(sentence_ids),
                    )
                )
            ).scalars().all()
        )
        to_learn = owned - already
        if not to_learn:
            return []

        next_review = datetime.now(UTC) + SRS_INTERVALS[1]  # Apprentice-1 wait (~4h)
        for sid in to_learn:
            self.db.add(
                UserItemProgress(
                    user_id=user_id,
                    item_type=ItemType.SENTENCE,
                    item_id=sid,
                    srs_stage=1,
                    next_review_at=next_review,
                    source=ProgressSource.MANUAL,
                )
            )
        await self.db.commit()
        return sorted(to_learn)

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
                        politeness=sentence.politeness,
                        srs_stage=progress.srs_stage,
                    )
                )
        return due

    async def list_sentences(self, user_id: int) -> list[SentenceListItem]:
        """All of the user's production sentences (newest first), with SRS state.

        Unlike get_due, this shows the reference japanese — it's the owner's own list.
        """
        # LEFT join so pending-lesson sentences (no progress row yet) still appear.
        query = (
            select(ProductionSentence, UserItemProgress)
            .outerjoin(
                UserItemProgress,
                (UserItemProgress.item_id == ProductionSentence.id)
                & (UserItemProgress.item_type == ItemType.SENTENCE)
                & (UserItemProgress.user_id == user_id),
            )
            .where(ProductionSentence.user_id == user_id)
            .order_by(ProductionSentence.created_at.desc())
        )
        rows = (await self.db.execute(query)).all()
        return [
            SentenceListItem(
                sentence_id=sentence.id,
                english=sentence.english,
                japanese=sentence.japanese,
                politeness=sentence.politeness,
                srs_stage=progress.srs_stage if progress else None,
                next_review_at=progress.next_review_at if progress else None,
                created_at=sentence.created_at,
            )
            for sentence, progress in rows
        ]

    async def get_sentence(self, user_id: int, sentence_id: int) -> SentenceDetailResponse:
        """One sentence with its full review history. Raises ValueError (→ 404) if not found."""
        sentence = await self.db.get(ProductionSentence, sentence_id)
        if sentence is None or sentence.user_id != user_id:
            raise ValueError("Sentence not found")

        progress = (
            await self.db.execute(
                select(UserItemProgress).where(
                    UserItemProgress.user_id == user_id,
                    UserItemProgress.item_type == ItemType.SENTENCE,
                    UserItemProgress.item_id == sentence_id,
                )
            )
        ).scalar_one_or_none()

        logs = (
            await self.db.execute(
                select(ProductionSentenceReviewLog)
                .where(ProductionSentenceReviewLog.sentence_id == sentence_id)
                .order_by(ProductionSentenceReviewLog.reviewed_at.desc())
            )
        ).scalars().all()

        return SentenceDetailResponse(
            sentence_id=sentence.id,
            english=sentence.english,
            japanese=sentence.japanese,
            politeness=sentence.politeness,
            srs_stage=progress.srs_stage if progress else None,  # None = pending lesson
            next_review_at=progress.next_review_at if progress else None,
            created_at=sentence.created_at,
            reviews=[SentenceReviewLogItem.model_validate(log) for log in logs],
        )

    async def judge_pair(
        self, user_id: int, sentence_id: int, submitted: str
    ) -> SentenceJudgeResponse:
        """Grade an attempt WITHOUT SRS side effects — for the lesson quiz gate.

        Exact-match fast path (free, instant); otherwise the LLM judge. No progress row is
        required (a pending lesson has none) and none is written. Raises ValueError (→ 404) if
        the sentence isn't the user's. LLM errors propagate (→ 503).
        """
        sentence = await self.db.get(ProductionSentence, sentence_id)
        if sentence is None or sentence.user_id != user_id:
            raise ValueError("Sentence not found")

        if _normalize(submitted) == _normalize(sentence.japanese):
            return SentenceJudgeResponse(
                correct=True, exact_match=True, feedback=None, reference=sentence.japanese
            )
        result = await judge(
            sentence.english, sentence.japanese, submitted, sentence.politeness.value
        )
        return SentenceJudgeResponse(
            correct=result.correct,
            exact_match=False,
            feedback=result.feedback,
            reference=sentence.japanese,
        )

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
            # DRY later (hour_reached / apply_review_outcome in srs.py) — see
            # production-srs-design.md "TECH DEBT". Deferred: don't touch mature ReviewService now.
            # TODO(lock): row lock is held across the LLM call below (~seconds). Fine at personal
            # scale (only blocks a concurrent submit of THE SAME sentence). Improve: judge before
            # locking, then lock → re-verify due → write. See production-srs-design.md "TECH DEBT".
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

            # Fast path: exact reproduction of the reference → correct, no LLM. Otherwise judge with
            # the LLM, honoring the learner's prior overrides for this sentence.
            if _normalize(request.submitted) == _normalize(sentence.japanese):
                verdict = Judgment(correct=True, exact_match=True)
            else:
                overrides = await self._prior_override_reasons(sentence.id)
                result = await judge(
                    sentence.english,
                    sentence.japanese,
                    request.submitted,
                    sentence.politeness.value,
                    override_reasons=overrides,
                )
                verdict = Judgment(
                    correct=result.correct, exact_match=False, feedback=result.feedback
                )

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
        except (OpenAIError, RuntimeError) as e:
            # LLM judge failed — leave SRS untouched so the user can retry (router → 503).
            await self.db.rollback()
            logger.warning(
                "llm_error_submitting_sentence_review",
                user_id=user_id,
                sentence_id=request.sentence_id,
                error_type=type(e).__name__,
                error=str(e),
            )
            raise
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

    async def override_review(
        self, user_id: int, sentence_id: int, reason: str | None
    ) -> SentenceOverrideResponse:
        """Override the latest rejected review — accept the answer, advance SRS, store the reason.

        Recomputes SRS from the rejected review's `srs_stage_before` as if correct. The log keeps
        the judge's verdict (`correct=False`) but is flagged `overridden`; the reason is fed to the
        judge on future reviews of this sentence. Raises ValueError (→ 400) if nothing to override.
        """
        try:
            now = datetime.now(UTC)

            log = (
                await self.db.execute(
                    select(ProductionSentenceReviewLog)
                    .where(
                        ProductionSentenceReviewLog.user_id == user_id,
                        ProductionSentenceReviewLog.sentence_id == sentence_id,
                    )
                    .order_by(ProductionSentenceReviewLog.reviewed_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            if log is None:
                raise ValueError("No review to override")
            if log.correct:
                raise ValueError("The last review was already correct")
            if log.overridden:
                raise ValueError("This review was already overridden")

            progress = (
                await self.db.execute(
                    select(UserItemProgress)
                    .where(
                        UserItemProgress.user_id == user_id,
                        UserItemProgress.item_type == ItemType.SENTENCE,
                        UserItemProgress.item_id == sentence_id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if progress is None:
                raise ValueError("Sentence not in progress")

            before = log.srs_stage_before
            new_stage, next_review_at = calculate_next_review(before, correct=True)

            log.overridden = True
            log.override_reason = reason
            log.srs_stage_after = new_stage
            progress.srs_stage = new_stage
            progress.next_review_at = next_review_at
            if new_stage == 9:
                progress.burned_at = now

            await self.db.commit()

            return SentenceOverrideResponse(
                sentence_id=sentence_id,
                srs_stage_before=before,
                srs_stage_after=new_stage,
                next_review_at=next_review_at,
            )
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(
                "database_error_overriding_sentence_review",
                user_id=user_id,
                sentence_id=sentence_id,
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    async def _prior_override_reasons(self, sentence_id: int) -> list[str]:
        """Past learner justifications for overriding THIS sentence — fed to the judge."""
        rows = await self.db.execute(
            select(ProductionSentenceReviewLog.override_reason).where(
                ProductionSentenceReviewLog.sentence_id == sentence_id,
                ProductionSentenceReviewLog.overridden.is_(True),
                ProductionSentenceReviewLog.override_reason.isnot(None),
            )
        )
        return [r for r in rows.scalars().all() if r]
