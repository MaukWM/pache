"""Tests for grammar-point extraction plumbing: auto-link on create, bank + link endpoints."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Session, User
from src.core.constants import Politeness
from src.llm.validate import ExtractedGrammarPoint, PairValidation
from src.sentences.models import GrammarPoint, ProductionSentence, SentenceGrammarPoint
from src.sentences.schemas import (
    GrammarPointUpdateRequest,
    SentenceCreateRequest,
    SentenceUpdateRequest,
)
from src.sentences.service import SentenceService


async def _user(db: AsyncSession) -> User:
    user = User(username=f"grammar-{datetime.now(UTC).timestamp()}")
    db.add(user)
    await db.flush()
    return user


def _validation(points: list[ExtractedGrammarPoint], valid: bool = True) -> PairValidation:
    return PairValidation(
        valid=valid, reason="" if valid else "bad", politeness="casual", points=points
    )


def _fake_validate(result: PairValidation, calls: list | None = None):
    async def fake(en: str, ja: str, **kwargs) -> PairValidation:
        if calls is not None:
            calls.append((en, ja, kwargs))
        return result

    return fake


POINT_NIYORU = ExtractedGrammarPoint(key="〜による", meaning_en="depending on", evidence="曲による")
POINT_NDESU = ExtractedGrammarPoint(key="〜んです", meaning_en="explanatory tone", evidence="んだ")


# --- create auto-links extraction --------------------------------------------------------------


async def test_create_mints_and_links_all_points(db_session, monkeypatch) -> None:
    user = await _user(db_session)
    calls: list = []
    monkeypatch.setattr(
        "src.sentences.service.validate_pair",
        _fake_validate(_validation([POINT_NIYORU, POINT_NDESU]), calls),
    )

    response = await SentenceService(db_session).create(
        user.id, SentenceCreateRequest(english="en", japanese="ja")
    )

    points = (
        (await db_session.execute(select(GrammarPoint).where(GrammarPoint.user_id == user.id)))
        .scalars()
        .all()
    )
    assert {p.key for p in points} == {"〜による", "〜んです"}

    links = (
        (
            await db_session.execute(
                select(SentenceGrammarPoint).where(
                    SentenceGrammarPoint.sentence_id == response.sentence_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(links) == 2
    evidences = {link.evidence for link in links}
    assert evidences == {"曲による", "んだ"}


async def test_create_reuses_existing_points(db_session, monkeypatch) -> None:
    user = await _user(db_session)
    existing = GrammarPoint(user_id=user.id, key="〜による", meaning_en="depending on")
    db_session.add(existing)
    await db_session.flush()

    calls: list = []
    extracted = [
        POINT_NIYORU,
        ExtractedGrammarPoint(key="〜て", meaning_en="and; then", evidence="やって"),
    ]
    monkeypatch.setattr(
        "src.sentences.service.validate_pair", _fake_validate(_validation(extracted), calls)
    )

    response = await SentenceService(db_session).create(
        user.id, SentenceCreateRequest(english="en", japanese="ja")
    )

    points = (
        (await db_session.execute(select(GrammarPoint).where(GrammarPoint.user_id == user.id)))
        .scalars()
        .all()
    )
    assert len(points) == 2  # 〜による reused (no duplicate), 〜て minted

    links = (
        (
            await db_session.execute(
                select(SentenceGrammarPoint).where(
                    SentenceGrammarPoint.sentence_id == response.sentence_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(links) == 2
    assert existing.id in {link.grammar_point_id for link in links}

    # The current bank was fed into the LLM call (key-reuse mechanism).
    assert calls[0][2]["bank"] == {"〜による": "depending on"}


async def test_create_rejected_mints_nothing(db_session, monkeypatch) -> None:
    user = await _user(db_session)
    monkeypatch.setattr(
        "src.sentences.service.validate_pair",
        _fake_validate(_validation([POINT_NIYORU], valid=False)),
    )
    with pytest.raises(ValueError):
        await SentenceService(db_session).create(
            user.id, SentenceCreateRequest(english="en", japanese="ja")
        )
    points = (
        (await db_session.execute(select(GrammarPoint).where(GrammarPoint.user_id == user.id)))
        .scalars()
        .all()
    )
    assert points == []


async def test_update_replaces_links(db_session, monkeypatch) -> None:
    user = await _user(db_session)
    monkeypatch.setattr(
        "src.sentences.service.validate_pair", _fake_validate(_validation([POINT_NIYORU]))
    )
    service = SentenceService(db_session)
    response = await service.create(
        user.id, SentenceCreateRequest(english="en", japanese="ja")
    )

    monkeypatch.setattr(
        "src.sentences.service.validate_pair", _fake_validate(_validation([POINT_NDESU]))
    )
    await service.update_sentence(
        user.id, response.sentence_id, SentenceUpdateRequest(english="en2", japanese="ja2")
    )

    links = (
        (
            await db_session.execute(
                select(SentenceGrammarPoint, GrammarPoint)
                .join(GrammarPoint, GrammarPoint.id == SentenceGrammarPoint.grammar_point_id)
                .where(SentenceGrammarPoint.sentence_id == response.sentence_id)
            )
        )
        .all()
    )
    assert [point.key for _, point in links] == ["〜んです"]  # old link replaced
    # The old bank entry survives even at zero links.
    keys = (
        (await db_session.execute(select(GrammarPoint.key).where(GrammarPoint.user_id == user.id)))
        .scalars()
        .all()
    )
    assert set(keys) == {"〜による", "〜んです"}


# --- link corrections ---------------------------------------------------------------------------


async def _seed_bank(db: AsyncSession) -> tuple[User, ProductionSentence, GrammarPoint]:
    user = await _user(db)
    sentence = ProductionSentence(
        user_id=user.id, english="en", japanese="ja", politeness=Politeness.CASUAL
    )
    point = GrammarPoint(user_id=user.id, key="〜による", meaning_en="depending on")
    db.add_all([sentence, point])
    await db.flush()
    db.add(
        SentenceGrammarPoint(
            sentence_id=sentence.id, grammar_point_id=point.id, evidence="曲による"
        )
    )
    await db.flush()
    return user, sentence, point


async def test_detach_and_attach_grammar(db_session) -> None:
    user, sentence, point = await _seed_bank(db_session)
    service = SentenceService(db_session)

    await service.detach_grammar(user.id, sentence.id, point.id)
    links = ((await db_session.execute(select(SentenceGrammarPoint))).scalars().all())
    assert links == []
    assert await db_session.get(GrammarPoint, point.id) is not None  # bank entry survives

    item = await service.attach_grammar(user.id, sentence.id, point.id)
    assert item.key == "〜による"
    links = ((await db_session.execute(select(SentenceGrammarPoint))).scalars().all())
    assert len(links) == 1

    # Idempotent re-attach.
    await service.attach_grammar(user.id, sentence.id, point.id)
    links = ((await db_session.execute(select(SentenceGrammarPoint))).scalars().all())
    assert len(links) == 1


async def test_detach_not_owned_or_missing(db_session) -> None:
    user, sentence, point = await _seed_bank(db_session)
    other = await _user(db_session)
    service = SentenceService(db_session)
    with pytest.raises(ValueError):
        await service.detach_grammar(other.id, sentence.id, point.id)
    with pytest.raises(ValueError):
        await service.detach_grammar(user.id, sentence.id, point.id + 999)


async def test_get_sentence_includes_grammar(db_session) -> None:
    user, sentence, _ = await _seed_bank(db_session)
    detail = await SentenceService(db_session).get_sentence(user.id, sentence.id)
    assert len(detail.grammar) == 1
    assert detail.grammar[0].key == "〜による"
    assert detail.grammar[0].evidence == "曲による"


async def test_delete_sentence_removes_links_keeps_points(db_session) -> None:
    user, sentence, point = await _seed_bank(db_session)
    await SentenceService(db_session).delete_sentence(user.id, sentence.id)

    links = ((await db_session.execute(select(SentenceGrammarPoint))).scalars().all())
    assert links == []
    assert await db_session.get(GrammarPoint, point.id) is not None


# --- bank endpoints ------------------------------------------------------------------------------


async def test_list_grammar_counts(db_session) -> None:
    user, _, point = await _seed_bank(db_session)
    db_session.add(GrammarPoint(user_id=user.id, key="〜かも", meaning_en="might"))
    await db_session.flush()

    items = await SentenceService(db_session).list_grammar(user.id)
    assert [i.key for i in items] == ["〜による", "〜かも"]  # most-used first
    assert items[0].sentence_count == 1
    assert items[1].sentence_count == 0


async def test_get_grammar_point_detail(db_session) -> None:
    user, sentence, point = await _seed_bank(db_session)
    detail = await SentenceService(db_session).get_grammar_point(user.id, point.id)
    assert detail.key == "〜による"
    assert len(detail.sentences) == 1
    assert detail.sentences[0].sentence_id == sentence.id
    assert detail.sentences[0].evidence == "曲による"
    assert detail.sentences[0].srs_stage is None  # pending lesson


async def test_get_grammar_point_not_owned(db_session) -> None:
    _, _, point = await _seed_bank(db_session)
    other = await _user(db_session)
    with pytest.raises(ValueError):
        await SentenceService(db_session).get_grammar_point(other.id, point.id)


async def test_update_grammar_point_rename(db_session) -> None:
    user, _, point = await _seed_bank(db_session)
    service = SentenceService(db_session)

    updated = await service.update_grammar_point(
        user.id,
        point.id,
        GrammarPointUpdateRequest(key="〜によって", meaning_en="depending on it"),
    )
    assert updated.key == "〜によって"
    assert updated.meaning_en == "depending on it"


async def test_update_grammar_point_rename_collision(db_session) -> None:
    user, _, point = await _seed_bank(db_session)
    db_session.add(GrammarPoint(user_id=user.id, key="〜かも", meaning_en="might"))
    await db_session.flush()
    with pytest.raises(ValueError):
        await SentenceService(db_session).update_grammar_point(
            user.id, point.id, GrammarPointUpdateRequest(key="〜かも")
        )


# --- router smoke --------------------------------------------------------------------------------


async def test_grammar_endpoints_roundtrip(async_client, db_session, monkeypatch) -> None:
    user = User(username="u-tok-grammar", sentences_enabled=True)
    db_session.add(user)
    await db_session.flush()
    db_session.add(Session(user_id=user.id, token="tok-grammar"))
    await db_session.commit()
    headers = {"Authorization": "Bearer tok-grammar"}

    monkeypatch.setattr(
        "src.sentences.service.validate_pair", _fake_validate(_validation([POINT_NIYORU]))
    )

    create = await async_client.post(
        "/api/v1/me/sentences",
        headers=headers,
        json={"english": "en", "japanese": "ja"},
    )
    assert create.status_code == 201
    sentence_id = create.json()["sentence_id"]

    detail = await async_client.get(f"/api/v1/me/sentences/{sentence_id}", headers=headers)
    assert detail.status_code == 200
    grammar = detail.json()["grammar"]
    assert len(grammar) == 1
    assert grammar[0]["key"] == "〜による"
    point_id = grammar[0]["grammar_point_id"]

    bank = await async_client.get("/api/v1/me/grammar", headers=headers)
    assert bank.status_code == 200
    items = bank.json()["items"]
    assert len(items) == 1
    assert items[0]["sentence_count"] == 1

    point_detail = await async_client.get(f"/api/v1/me/grammar/{point_id}", headers=headers)
    assert point_detail.status_code == 200
    assert point_detail.json()["sentences"][0]["evidence"] == "曲による"

    unlink = await async_client.delete(
        f"/api/v1/me/sentences/{sentence_id}/grammar/{point_id}", headers=headers
    )
    assert unlink.status_code == 204

    relink = await async_client.post(
        f"/api/v1/me/sentences/{sentence_id}/grammar",
        headers=headers,
        json={"grammar_point_id": point_id},
    )
    assert relink.status_code == 200
    assert relink.json()["key"] == "〜による"

    patch = await async_client.patch(
        f"/api/v1/me/grammar/{point_id}",
        headers=headers,
        json={"key": "〜によって"},
    )
    assert patch.status_code == 200
    assert patch.json()["key"] == "〜によって"


# --- per-point scoring ---------------------------------------------------------------------------


async def _make_due(db: AsyncSession, user: User, sentence: ProductionSentence) -> None:
    from datetime import timedelta

    from src.core.constants import ItemType, ProgressSource
    from src.progress.models import UserItemProgress

    db.add(
        UserItemProgress(
            user_id=user.id,
            item_type=ItemType.SENTENCE,
            item_id=sentence.id,
            srs_stage=2,
            next_review_at=datetime.now(UTC) - timedelta(hours=1),
            source=ProgressSource.MANUAL,
        )
    )
    await db.flush()


async def test_submit_exact_match_marks_all_points_ok(db_session) -> None:
    from src.sentences.models import GrammarPointReviewLog
    from src.sentences.schemas import SentenceReviewCreateRequest

    user, sentence, point = await _seed_bank(db_session)
    await _make_due(db_session, user, sentence)

    await SentenceService(db_session).submit_review(
        user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="ja")
    )

    rows = ((await db_session.execute(select(GrammarPointReviewLog))).scalars().all())
    assert len(rows) == 1
    assert rows[0].grammar_point_id == point.id
    assert rows[0].ok is True


async def test_submit_judged_attributes_point_mistakes(db_session, monkeypatch) -> None:
    from src.llm.judge import JudgeResult, PointVerdict
    from src.sentences.models import GrammarPointReviewLog
    from src.sentences.schemas import SentenceReviewCreateRequest

    user, sentence, point = await _seed_bank(db_session)
    other = GrammarPoint(user_id=user.id, key="〜んです", meaning_en="explanatory")
    db_session.add(other)
    await db_session.flush()
    db_session.add(SentenceGrammarPoint(sentence_id=sentence.id, grammar_point_id=other.id))
    await _make_due(db_session, user, sentence)

    seen_points: dict = {}

    async def fake_judge(en, ref, sub, pol, override_reasons=None, grammar_points=None, **kw):
        seen_points.update(grammar_points or {})
        return JudgeResult(
            reason="",
            correct=False,
            feedback="による misused",
            point_verdicts=[PointVerdict(key="〜による", ok=False)],  # 〜んです unflagged
        )

    monkeypatch.setattr("src.sentences.service.judge", fake_judge)

    await SentenceService(db_session).submit_review(
        user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="wrong ja")
    )

    # The judge received the linked points...
    assert set(seen_points) == {"〜による", "〜んです"}
    # ...flagged one wrong; the unflagged one defaults ok.
    rows = ((await db_session.execute(select(GrammarPointReviewLog))).scalars().all())
    by_point = {r.grammar_point_id: r.ok for r in rows}
    assert by_point == {point.id: False, other.id: True}


async def test_override_flips_point_verdicts(db_session, monkeypatch) -> None:
    from src.llm.judge import JudgeResult, PointVerdict
    from src.sentences.models import GrammarPointReviewLog
    from src.sentences.schemas import SentenceReviewCreateRequest

    user, sentence, point = await _seed_bank(db_session)
    await _make_due(db_session, user, sentence)

    async def fake_judge(en, ref, sub, pol, override_reasons=None, **kw):
        return JudgeResult(
            reason="",
            correct=False,
            feedback="bad",
            point_verdicts=[PointVerdict(key="〜による", ok=False)],
        )

    monkeypatch.setattr("src.sentences.service.judge", fake_judge)

    service = SentenceService(db_session)
    await service.submit_review(
        user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="wrong ja")
    )
    await service.override_review(user.id, sentence.id, reason="it was fine")

    rows = ((await db_session.execute(select(GrammarPointReviewLog))).scalars().all())
    assert len(rows) == 1
    assert rows[0].ok is True  # judge's attribution voided with the override


async def test_list_grammar_includes_accuracy(db_session) -> None:
    from src.sentences.schemas import SentenceReviewCreateRequest

    user, sentence, point = await _seed_bank(db_session)
    await _make_due(db_session, user, sentence)
    await SentenceService(db_session).submit_review(
        user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="ja")
    )

    items = await SentenceService(db_session).list_grammar(user.id)
    assert items[0].review_count == 1
    assert items[0].correct_count == 1

    detail = await SentenceService(db_session).get_grammar_point(user.id, point.id)
    assert detail.review_count == 1
    assert detail.correct_count == 1


async def test_point_verdict_key_with_gloss_suffix_still_matches(db_session, monkeypatch) -> None:
    """The model sometimes echoes 'key — gloss' as the verdict key — must still match."""
    from src.llm.judge import JudgeResult, PointVerdict
    from src.sentences.models import GrammarPointReviewLog
    from src.sentences.schemas import SentenceReviewCreateRequest

    user, sentence, point = await _seed_bank(db_session)
    await _make_due(db_session, user, sentence)

    async def fake_judge(en, ref, sub, pol, override_reasons=None, **kw):
        return JudgeResult(
            reason="",
            correct=False,
            feedback="bad",
            point_verdicts=[PointVerdict(key="〜による — depending on", ok=False)],
        )

    monkeypatch.setattr("src.sentences.service.judge", fake_judge)
    await SentenceService(db_session).submit_review(
        user.id, SentenceReviewCreateRequest(sentence_id=sentence.id, submitted="wrong ja")
    )

    rows = ((await db_session.execute(select(GrammarPointReviewLog))).scalars().all())
    assert len(rows) == 1
    assert rows[0].grammar_point_id == point.id
    assert rows[0].ok is False  # gloss suffix stripped, matched, attributed
