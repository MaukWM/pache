"""Tests for the production-sentence review service (step 2: exact-match, no LLM)."""

from datetime import UTC, datetime, timedelta

import pytest
from openai import OpenAIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.constants import ItemType, Politeness
from src.llm.judge import JudgeResult
from src.llm.validate import PairValidation
from src.progress.models import UserItemProgress
from src.sentences.models import ProductionSentence, ProductionSentenceReviewLog
from src.sentences.schemas import SentenceCreateRequest, SentenceReviewCreateRequest
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
    sentence = ProductionSentence(
        user_id=user.id, english="5 more days", japanese=japanese, politeness=Politeness.CASUAL
    )
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


async def test_list_sentences_returns_reference_and_stage(db_session: AsyncSession) -> None:
    user, sentence = await _seed(db_session, stage=3)
    items = await SentenceService(db_session).list_sentences(user.id)
    assert len(items) == 1
    assert items[0].sentence_id == sentence.id
    assert items[0].japanese == "あと5日"  # owner's list DOES show the reference
    assert items[0].srs_stage == 3


async def test_list_sentences_scoped_to_user(db_session: AsyncSession) -> None:
    user, _ = await _seed(db_session)
    other, _ = await _seed(db_session)
    items = await SentenceService(db_session).list_sentences(user.id)
    assert len(items) == 1  # only own sentences


async def test_list_includes_pending_lessons_with_null_stage(db_session: AsyncSession) -> None:
    user, _ = await _seed(db_session, stage=3)  # a learned one
    # A pending-lesson sentence: sentence row, no progress.
    pending = ProductionSentence(
        user_id=user.id, english="pending", japanese="保留", politeness=Politeness.CASUAL
    )
    db_session.add(pending)
    await db_session.flush()

    items = await SentenceService(db_session).list_sentences(user.id)
    assert len(items) == 2
    by_id = {i.sentence_id: i for i in items}
    assert by_id[pending.id].srs_stage is None
    assert by_id[pending.id].next_review_at is None


async def test_get_sentence_includes_review_history(db_session: AsyncSession) -> None:
    user, sentence = await _seed(db_session, stage=1)
    db_session.add(
        ProductionSentenceReviewLog(
            user_id=user.id,
            sentence_id=sentence.id,
            submitted="wrong",
            exact_match=False,
            correct=False,
            feedback="not natural",
            srs_stage_before=1,
            srs_stage_after=1,
            reviewed_at=datetime.now(UTC),
        )
    )
    await db_session.flush()
    detail = await SentenceService(db_session).get_sentence(user.id, sentence.id)
    assert detail.sentence_id == sentence.id
    assert detail.japanese == "あと5日"
    assert len(detail.reviews) == 1
    assert detail.reviews[0].feedback == "not natural"


async def test_get_sentence_other_user_404(db_session: AsyncSession) -> None:
    _, sentence = await _seed(db_session)
    other, _ = await _seed(db_session)
    with pytest.raises(ValueError, match="not found"):
        await SentenceService(db_session).get_sentence(other.id, sentence.id)


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


async def test_submit_non_exact_judged_incorrect(db_session, monkeypatch) -> None:
    async def fake_judge(en, ref, sub, pol, override_reasons=None):
        return JudgeResult(reason="wrong word", correct=False, feedback="use を, not は")

    monkeypatch.setattr("src.sentences.service.judge", fake_judge)
    user, sentence = await _seed(db_session, japanese="あと5日", stage=3)
    resp = await SentenceService(db_session).submit_review(
        user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="間違い")
    )
    assert resp.correct is False
    assert resp.exact_match is False
    assert resp.feedback == "use を, not は"  # judge feedback surfaced + stored
    assert resp.srs_stage_after < 3  # incorrect penalty applied


async def test_submit_non_exact_judged_correct_advances(db_session, monkeypatch) -> None:
    async def fake_judge(en, ref, sub, pol, override_reasons=None):
        return JudgeResult(reason="natural alternate", correct=True, feedback=None)

    monkeypatch.setattr("src.sentences.service.judge", fake_judge)
    user, sentence = await _seed(db_session, japanese="あと5日", stage=1)
    resp = await SentenceService(db_session).submit_review(
        user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="あと五日間")
    )
    assert resp.correct is True and resp.exact_match is False and resp.srs_stage_after == 2


async def test_submit_feeds_prior_override_reasons_to_judge(db_session, monkeypatch) -> None:
    captured: dict = {}

    async def fake_judge(en, ref, sub, pol, override_reasons=None):
        captured["overrides"] = override_reasons
        return JudgeResult(reason="ok", correct=True, feedback=None)

    monkeypatch.setattr("src.sentences.service.judge", fake_judge)
    user, sentence = await _seed(db_session, japanese="あと5日", stage=1)
    db_session.add(
        ProductionSentenceReviewLog(
            user_id=user.id,
            sentence_id=sentence.id,
            submitted="past attempt",
            exact_match=False,
            correct=False,
            overridden=True,
            override_reason="polite form is fine here",
            srs_stage_before=1,
            srs_stage_after=1,
            reviewed_at=datetime.now(UTC),
        )
    )
    await db_session.flush()

    await SentenceService(db_session).submit_review(
        user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="別の文")
    )
    assert captured["overrides"] == ["polite form is fine here"]


async def test_submit_llm_error_leaves_srs_unchanged(db_session, monkeypatch) -> None:
    async def boom(en, ref, sub, pol, override_reasons=None):
        raise OpenAIError("service down")

    monkeypatch.setattr("src.sentences.service.judge", boom)
    user, sentence = await _seed(db_session, japanese="あと5日", stage=2)
    with pytest.raises(OpenAIError):
        await SentenceService(db_session).submit_review(
            user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="miss")
        )


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


# --- creation flow (③a): validate_pair is mocked so no network/LLM ---


async def _user(db: AsyncSession) -> User:
    user = User(username=f"author-{datetime.now(UTC).timestamp()}")
    db.add(user)
    await db.flush()
    return user


async def test_create_valid_inserts_as_pending_lesson(db_session, monkeypatch) -> None:
    async def fake_validate(en: str, ja: str) -> PairValidation:
        return PairValidation(valid=True, reason="", politeness="casual")

    monkeypatch.setattr("src.sentences.service.validate_pair", fake_validate)
    user = await _user(db_session)

    resp = await SentenceService(db_session).create(
        user.id, SentenceCreateRequest(english="5 more days", japanese="あと5日")
    )
    assert resp.sentence_id > 0
    assert resp.politeness == Politeness.CASUAL

    # No SRS progress yet — it's a pending lesson until learned.
    progress = await db_session.scalar(
        select(UserItemProgress).where(
            UserItemProgress.item_type == ItemType.SENTENCE,
            UserItemProgress.item_id == resp.sentence_id,
        )
    )
    assert progress is None
    # ...and it shows up as a pending lesson.
    lessons = await SentenceService(db_session).get_lessons(user.id)
    assert [x.sentence_id for x in lessons] == [resp.sentence_id]


async def test_complete_lessons_enters_srs(db_session, monkeypatch) -> None:
    async def fake_validate(en: str, ja: str) -> PairValidation:
        return PairValidation(valid=True, reason="", politeness="casual")

    monkeypatch.setattr("src.sentences.service.validate_pair", fake_validate)
    user = await _user(db_session)
    svc = SentenceService(db_session)
    created = await svc.create(
        user.id, SentenceCreateRequest(english="5 more days", japanese="あと5日")
    )

    learned = await svc.complete_lessons(user.id, [created.sentence_id])
    assert learned == [created.sentence_id]

    progress = await db_session.scalar(
        select(UserItemProgress).where(
            UserItemProgress.item_type == ItemType.SENTENCE,
            UserItemProgress.item_id == created.sentence_id,
        )
    )
    assert progress is not None and progress.srs_stage == 1 and progress.next_review_at is not None
    # No longer a pending lesson; re-learning is a no-op.
    assert await svc.get_lessons(user.id) == []
    assert await svc.complete_lessons(user.id, [created.sentence_id]) == []


async def test_create_invalid_pair_raises_and_stores_nothing(db_session, monkeypatch) -> None:
    async def fake_validate(en: str, ja: str) -> PairValidation:
        return PairValidation(
            valid=False, reason="Japanese does not match the English.", politeness="casual"
        )

    monkeypatch.setattr("src.sentences.service.validate_pair", fake_validate)
    user = await _user(db_session)

    with pytest.raises(ValueError, match="does not match"):
        await SentenceService(db_session).create(
            user.id, SentenceCreateRequest(english="hello", japanese="間違い")
        )
    # nothing persisted
    assert await db_session.scalar(select(ProductionSentence)) is None


async def test_create_uses_validator_politeness(db_session, monkeypatch) -> None:
    async def fake_validate(en: str, ja: str) -> PairValidation:
        return PairValidation(valid=True, reason="", politeness="polite")

    monkeypatch.setattr("src.sentences.service.validate_pair", fake_validate)
    user = await _user(db_session)

    resp = await SentenceService(db_session).create(
        user.id, SentenceCreateRequest(english="x", japanese="あります")
    )
    assert resp.politeness == Politeness.POLITE  # from the validator (no override anymore)


# --- override endpoint (③c) ---


async def test_override_advances_srs_and_stores_reason(db_session) -> None:
    user, sentence = await _seed(db_session, stage=1)  # progress dropped to 1 after a miss
    db_session.add(
        ProductionSentenceReviewLog(
            user_id=user.id,
            sentence_id=sentence.id,
            submitted="wrong",
            exact_match=False,
            correct=False,
            srs_stage_before=3,
            srs_stage_after=1,
            reviewed_at=datetime.now(UTC),
        )
    )
    await db_session.flush()

    resp = await SentenceService(db_session).override_review(user.id, sentence.id, "polite is fine")
    assert resp.srs_stage_before == 3
    assert resp.srs_stage_after == 4  # calculate_next_review(3, correct=True) → advance
    prog = await db_session.scalar(
        select(UserItemProgress).where(
            UserItemProgress.item_type == ItemType.SENTENCE,
            UserItemProgress.item_id == sentence.id,
        )
    )
    assert prog.srs_stage == 4
    log = await db_session.scalar(select(ProductionSentenceReviewLog))
    assert log.overridden is True
    assert log.override_reason == "polite is fine"
    assert log.correct is False  # judge verdict preserved for analytics


async def test_override_no_review_raises(db_session) -> None:
    user, sentence = await _seed(db_session)
    with pytest.raises(ValueError, match="No review"):
        await SentenceService(db_session).override_review(user.id, sentence.id, None)


async def test_override_already_correct_raises(db_session) -> None:
    user, sentence = await _seed(db_session)
    db_session.add(
        ProductionSentenceReviewLog(
            user_id=user.id,
            sentence_id=sentence.id,
            submitted="ok",
            exact_match=True,
            correct=True,
            srs_stage_before=1,
            srs_stage_after=2,
            reviewed_at=datetime.now(UTC),
        )
    )
    await db_session.flush()
    with pytest.raises(ValueError, match="already correct"):
        await SentenceService(db_session).override_review(user.id, sentence.id, None)


async def test_override_already_overridden_raises(db_session) -> None:
    user, sentence = await _seed(db_session)
    db_session.add(
        ProductionSentenceReviewLog(
            user_id=user.id,
            sentence_id=sentence.id,
            submitted="x",
            exact_match=False,
            correct=False,
            overridden=True,
            srs_stage_before=2,
            srs_stage_after=2,
            reviewed_at=datetime.now(UTC),
        )
    )
    await db_session.flush()
    with pytest.raises(ValueError, match="already overridden"):
        await SentenceService(db_session).override_review(user.id, sentence.id, None)
