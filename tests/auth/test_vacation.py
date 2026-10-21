"""Tests for vacation mode: pausing SRS and shifting the schedule on resume."""

from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Session, User
from src.auth.schemas import VacationUpdateRequest
from src.auth.service import AuthService
from src.core.constants import ItemType, Politeness, ProgressSource
from src.core.time import ensure_utc
from src.kanji.models import Kanji
from src.progress.models import UserItemProgress
from src.sentences.models import ProductionSentence

TOKEN = "vacation-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


async def _user_with_progress(db: AsyncSession) -> tuple[User, list[datetime]]:
    """A user with three scheduled kanji, one scheduled sentence, one burned kanji."""
    user = User(username="holidaymaker", is_admin=True)  # admin → sentences access
    db.add(user)
    await db.flush()
    db.add(Session(user_id=user.id, token=TOKEN))
    now = datetime.now(UTC)
    dues = [now - timedelta(days=3), now + timedelta(hours=4), now + timedelta(days=14)]
    for i, (char, due) in enumerate(zip("日月火", dues, strict=True), start=1):
        # Real kanji rows so the due endpoint can hydrate item details.
        db.add(
            Kanji(
                id=i,
                character=char,
                meanings=["x"],
                readings_on=[],
                readings_kun=[],
                stroke_count=1,
            )
        )
        db.add(
            UserItemProgress(
                user_id=user.id,
                item_type=ItemType.KANJI,
                item_id=i,
                srs_stage=2,
                next_review_at=due,
            )
        )
    sentence = ProductionSentence(
        user_id=user.id, english="Hello.", japanese="こんにちは。", politeness=Politeness.POLITE
    )
    db.add(sentence)
    await db.flush()
    db.add(
        UserItemProgress(
            user_id=user.id,
            item_type=ItemType.SENTENCE,
            item_id=sentence.id,
            srs_stage=1,
            next_review_at=dues[0],
        )
    )
    # Burned item: no next_review_at, must be left alone.
    db.add(UserItemProgress(user_id=user.id, item_type=ItemType.KANJI, item_id=99, srs_stage=9))
    # WaniKani-sourced item: reviewed on WaniKani, any local next_review_at is stale.
    db.add(
        UserItemProgress(
            user_id=user.id,
            item_type=ItemType.KANJI,
            item_id=98,
            srs_stage=5,
            source=ProgressSource.WANIKANI,
            next_review_at=dues[1],
        )
    )
    await db.commit()
    return user, dues


async def _dues(db: AsyncSession, user_id: int) -> dict[tuple[str, int], datetime | None]:
    rows = (
        await db.execute(select(UserItemProgress).where(UserItemProgress.user_id == user_id))
    ).scalars()
    return {
        (p.item_type.value, p.item_id): (ensure_utc(p.next_review_at) if p.next_review_at else None)
        for p in rows
    }


# --- service ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_shifts_every_scheduled_item_by_duration(db_session: AsyncSession) -> None:
    """Ending pushes kanji AND sentence reviews forward by exactly the vacation length."""
    user, dues = await _user_with_progress(db_session)
    service = AuthService(db_session)

    with freeze_time("2026-10-01 12:00:00"):
        res = await service.set_vacation(user, VacationUpdateRequest(active=True))
    assert res.active is True
    assert ensure_utc(user.vacation_started_at) == datetime(2026, 10, 1, 12, tzinfo=UTC)

    with freeze_time("2026-10-08 12:00:00"):
        res = await service.set_vacation(user, VacationUpdateRequest(active=False))
    assert res.active is False
    assert res.shifted_items == 4
    assert res.shifted_seconds == 7 * 24 * 3600
    assert user.vacation_started_at is None

    after = await _dues(db_session, user.id)
    week = timedelta(days=7)
    for item_id, original in enumerate(dues, start=1):
        assert after[("kanji", item_id)] == ensure_utc(original) + week
    assert after[("sentence", 1)] == ensure_utc(dues[0]) + week
    assert after[("kanji", 99)] is None
    assert after[("kanji", 98)] == ensure_utc(dues[1])  # WaniKani row untouched


@pytest.mark.asyncio
async def test_start_and_end_are_idempotent(db_session: AsyncSession) -> None:
    """Starting twice keeps the first start; ending while inactive shifts nothing."""
    user, dues = await _user_with_progress(db_session)
    service = AuthService(db_session)

    res = await service.set_vacation(user, VacationUpdateRequest(active=False))
    assert res.active is False
    assert res.shifted_items == 0
    assert (await _dues(db_session, user.id))[("kanji", 1)] == ensure_utc(dues[0])

    with freeze_time("2026-10-01 12:00:00"):
        first = await service.set_vacation(user, VacationUpdateRequest(active=True))
    with freeze_time("2026-10-02 12:00:00"):
        again = await service.set_vacation(user, VacationUpdateRequest(active=True))
    assert again.started_at == first.started_at


# --- router ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vacation_blocks_srs_endpoints(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """While on vacation: due lists are empty, every SRS-mutating route is 409."""
    await _user_with_progress(db_session)

    res = await async_client.post("/api/v1/auth/vacation", json={"active": True}, headers=HEADERS)
    assert res.status_code == 200
    assert res.json()["active"] is True

    settings = await async_client.get("/api/v1/auth/settings", headers=HEADERS)
    # Must be an explicit UTC instant ("Z"), not a naive value a browser would read as local.
    assert settings.json()["vacation_started_at"].endswith("Z")

    for path in ("/api/v1/me/reviews", "/api/v1/me/sentences/reviews"):
        due = await async_client.get(path, headers=HEADERS)
        assert due.status_code == 200, path
        assert due.json()["count"] == 0, path

    blocked = [
        (
            "/api/v1/me/reviews",
            {"item_type": "kanji", "item_id": 1, "reading_correct": True, "meaning_correct": True},
        ),
        ("/api/v1/me/lessons", {"item_ids": [{"item_type": "kanji", "item_id": 1}]}),
        ("/api/v1/me/sentences/lessons", {"sentence_ids": [1]}),
        ("/api/v1/me/sentences/reviews", {"sentence_id": 1, "submitted": "x"}),
        ("/api/v1/me/sentences/1/override", {"reason": "x"}),
        ("/api/v1/me/progress/kanji/1/resurrect", None),
    ]
    for path, body in blocked:
        res = await async_client.post(path, json=body, headers=HEADERS)
        assert res.status_code == 409, (path, res.text)


@pytest.mark.asyncio
async def test_end_via_api_reports_shift_and_reviews_resume(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Ending through the API reports the shift; the overdue item is due again right away."""
    await _user_with_progress(db_session)
    with freeze_time("2026-10-14 12:00:00"):
        await async_client.post("/api/v1/auth/vacation", json={"active": True}, headers=HEADERS)
    with freeze_time("2026-10-15 12:00:00"):
        res = await async_client.post(
            "/api/v1/auth/vacation", json={"active": False}, headers=HEADERS
        )
        assert res.status_code == 200
        assert res.json()["shifted_items"] == 4
        assert res.json()["shifted_seconds"] == 24 * 3600

    # Item 1 was 3 days overdue → still overdue after a 1-day shift.
    due = await async_client.get("/api/v1/me/reviews", headers=HEADERS)
    assert [i["item_id"] for i in due.json()["items"]] == [1]
