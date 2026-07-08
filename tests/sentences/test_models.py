"""Schema smoke test for baby-step 1: sentence tables + ItemType.SENTENCE round-trip."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.constants import ItemType, Politeness
from src.progress.models import UserItemProgress
from src.sentences.models import ProductionSentence, ProductionSentenceReviewLog


async def test_sentence_srs_roundtrip(db_session: AsyncSession) -> None:
    user = User(username="composer", password_hash="x")
    db_session.add(user)
    await db_session.flush()

    sentence = ProductionSentence(
        user_id=user.id, english="5 more days", japanese="あと5日", politeness=Politeness.CASUAL
    )
    db_session.add(sentence)
    await db_session.flush()

    # SRS state lives in the shared progress table under the new item type.
    progress = UserItemProgress(
        user_id=user.id, item_type=ItemType.SENTENCE, item_id=sentence.id, srs_stage=1
    )
    log = ProductionSentenceReviewLog(
        user_id=user.id,
        sentence_id=sentence.id,
        submitted="あと五日",
        exact_match=False,
        correct=True,
        feedback="natural; kanji-vs-arabic numeral only",
        srs_stage_before=1,
        srs_stage_after=2,
    )
    db_session.add_all([progress, log])
    await db_session.flush()

    assert log.overridden is False  # defaults applied
    fetched = await db_session.scalar(
        select(UserItemProgress).where(UserItemProgress.item_type == ItemType.SENTENCE)
    )
    assert fetched is not None and fetched.item_id == sentence.id
