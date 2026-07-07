"""Tests for the production-sentence review service (step 2: exact-match, no LLM)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.constants import ItemType
from src.progress.models import UserItemProgress
from src.sentences.models import ProductionSentence, ProductionSentenceReviewLog
from src.sentences.schemas import SentenceReviewCreateRequest
from src.sentences.service import SentenceService


async def _seed(
    db: AsyncSession,
    *,
    japanese: str = "あと5日",
    stage: int = 1,
    due_offset: timedelta = timedelta(hours=-1),
) -> tuple[User, ProductionSentence]:
    """Create a user + sentence + due progress row."""
    user = User(username=f"composer-{datetime.now(UTC).timestamp()}")
    db.add(user)
    await db.flush()
    sentence = ProductionSentence(user_id=user.id, english="5 more days", japanese=japanese)
    db.add(sentence)
    await db.flush()
    db.add(
        UserItemProgress(
            user_id=user.id,
            item_type=ItemType.SENTENCE,
            item_id=sentence.id,
            srs_stage=stage,
            next_review_at=datetime.now(UTC) + due_offset,
        )
    )
    await db.flush()
    return user, sentence


async def test_get_due_returns_due_without_leaking_reference(db_session: AsyncSession) -> None:
    user, sentence = await _seed(db_session)
    due = await SentenceService(db_session).get_due(user.id)
    assert len(due) == 1
    assert due[0].sentence_id == sentence.id
    assert due[0].english == "5 more days"
    # Schema has no `japanese` field — reference cannot leak in the due queue.
    assert not hasattr(due[0], "japanese")


async def test_get_due_excludes_future_and_burned(db_session: AsyncSession) -> None:
    user, _ = await _seed(db_session, due_offset=timedelta(hours=5))  # not due
    burned_user, burned = await _seed(db_session, stage=9)
    assert await SentenceService(db_session).get_due(user.id) == []
    assert await SentenceService(db_session).get_due(burned_user.id) == []


async def test_submit_exact_match_advances_stage(db_session: AsyncSession) -> None:
    user, sentence = await _seed(db_session, stage=1)
    resp = await SentenceService(db_session).submit_review(
        user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="あと5日")
    )
    assert resp.correct is True
    assert resp.exact_match is True
    assert resp.reference == "あと5日"
    assert resp.srs_stage_before == 1
    assert resp.srs_stage_after == 2
    assert resp.next_review_at is not None

    log = await db_session.scalar(select(ProductionSentenceReviewLog))
    assert log is not None and log.correct is True and log.exact_match is True


async def test_submit_normalizes_whitespace_and_trailing_period(db_session: AsyncSession) -> None:
    user, sentence = await _seed(db_session, japanese="あと5日")
    resp = await SentenceService(db_session).submit_review(
        user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="  あと5日。 ")
    )
    assert resp.exact_match is True


async def test_submit_miss_does_not_advance(db_session: AsyncSession) -> None:
    user, sentence = await _seed(db_session, japanese="あと5日", stage=3)
    resp = await SentenceService(db_session).submit_review(
        user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="間違い")
    )
    # step 2: any non-exact answer is a miss (LLM judge arrives in step 3).
    assert resp.correct is False
    assert resp.exact_match is False
    assert resp.srs_stage_after < 3  # incorrect penalty applied


async def test_submit_unknown_sentence_raises(db_session: AsyncSession) -> None:
    user, _ = await _seed(db_session)
    with pytest.raises(ValueError, match="not in progress"):
        await SentenceService(db_session).submit_review(
            user.id, SentenceReviewCreateRequest(sentence_id=999999, submitted="x")
        )


async def test_submit_not_due_raises(db_session: AsyncSession) -> None:
    user, sentence = await _seed(db_session, due_offset=timedelta(hours=5))
    with pytest.raises(ValueError, match="not yet due"):
        await SentenceService(db_session).submit_review(
            user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="あと5日")
        )
