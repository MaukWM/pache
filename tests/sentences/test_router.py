"""Router smoke tests for production-sentence reviews."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Session, User
from src.core.constants import ItemType, Politeness
from src.progress.models import UserItemProgress
from src.sentences.models import ProductionSentence


async def _seed_authed(db: AsyncSession, token: str) -> ProductionSentence:
    user = User(username=f"u-{token}", sentences_enabled=True)
    db.add(user)
    await db.flush()
    db.add(Session(user_id=user.id, token=token))
    sentence = ProductionSentence(
        user_id=user.id, english="5 more days", japanese="あと5日", politeness=Politeness.CASUAL
    )
    db.add(sentence)
    await db.flush()
    db.add(
        UserItemProgress(
            user_id=user.id,
            item_type=ItemType.SENTENCE,
            item_id=sentence.id,
            srs_stage=1,
            next_review_at=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    await db.commit()
    return sentence


async def test_due_and_submit_roundtrip(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    sentence = await _seed_authed(db_session, "tok-sent-1")
    headers = {"Authorization": "Bearer tok-sent-1"}

    due = await async_client.get("/api/v1/me/sentences/reviews", headers=headers)
    assert due.status_code == 200
    body = due.json()
    assert body["count"] == 1
    assert body["items"][0]["english"] == "5 more days"
    assert "japanese" not in body["items"][0]  # reference not leaked

    submit = await async_client.post(
        "/api/v1/me/sentences/reviews",
        headers=headers,
        json={"sentence_id": sentence.id, "submitted": "あと5日"},
    )
    assert submit.status_code == 200
    result = submit.json()
    assert result["correct"] is True
    assert result["srs_stage_after"] == 2
    assert result["reference"] == "あと5日"


async def test_reviews_unauthenticated(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/me/sentences/reviews")
    assert resp.status_code in (401, 403)


async def test_create_sentence_endpoint(async_client, db_session, monkeypatch) -> None:
    from src.llm.validate import PairValidation

    async def fake_validate(en: str, ja: str, **kwargs) -> PairValidation:
        return PairValidation(valid=True, reason="", politeness="casual")

    monkeypatch.setattr("src.sentences.service.validate_pair", fake_validate)

    user = User(username="creator1", sentences_enabled=True)
    db_session.add(user)
    await db_session.flush()
    db_session.add(Session(user_id=user.id, token="tok-create-1"))
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/me/sentences",
        headers={"Authorization": "Bearer tok-create-1"},
        json={"english": "5 more days", "japanese": "あと5日"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["politeness"] == "casual" and "srs_stage" not in body


async def test_create_sentence_rejected_422(async_client, db_session, monkeypatch) -> None:
    from src.llm.validate import PairValidation

    async def fake_validate(en: str, ja: str, **kwargs) -> PairValidation:
        return PairValidation(valid=False, reason="unnatural", politeness="casual")

    monkeypatch.setattr("src.sentences.service.validate_pair", fake_validate)

    user = User(username="creator2", sentences_enabled=True)
    db_session.add(user)
    await db_session.flush()
    db_session.add(Session(user_id=user.id, token="tok-create-2"))
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/me/sentences",
        headers={"Authorization": "Bearer tok-create-2"},
        json={"english": "hi", "japanese": "変"},
    )
    assert resp.status_code == 422
    assert "unnatural" in resp.json()["detail"]


async def test_sentences_blocked_without_access(async_client, db_session) -> None:
    # Non-admin, flag off → 403 on any 作文 endpoint.
    user = User(username="noaccess", sentences_enabled=False)
    db_session.add(user)
    await db_session.flush()
    db_session.add(Session(user_id=user.id, token="tok-noaccess"))
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/me/sentences", headers={"Authorization": "Bearer tok-noaccess"}
    )
    assert resp.status_code == 403


async def test_sentences_allowed_for_admin_without_flag(async_client, db_session) -> None:
    # Admin always has access, even with the flag off.
    user = User(username="adminuser", is_admin=True, sentences_enabled=False)
    db_session.add(user)
    await db_session.flush()
    db_session.add(Session(user_id=user.id, token="tok-admin"))
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/me/sentences", headers={"Authorization": "Bearer tok-admin"}
    )
    assert resp.status_code == 200
