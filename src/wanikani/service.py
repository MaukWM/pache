"""WaniKani import service."""

from datetime import UTC, datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ItemType, ProgressSource
from src.kanji.models import Kanji
from src.logging import logger
from src.progress.models import UserItemProgress
from src.wanikani.schemas import WaniKaniImportResponse

WK_API_BASE = "https://api.wanikani.com/v2"

# WK SRS stages 5+ = Guru and above (same numbering as ours)
GURU_AND_ABOVE_STAGES = [5, 6, 7, 8, 9]


class WaniKaniService:
    """Handles WaniKani API integration and import."""

    def __init__(self, db: AsyncSession, api_key: str):
        self.db = db
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Wanikani-Revision": "20170710",
        }

    async def import_guru_plus_kanji(self, user_id: int) -> WaniKaniImportResponse:
        """Fetch kanji at Guru+ from WaniKani and import into user progress."""
        # Fetch all assignments for kanji at Guru level and above
        assignments: list[dict] = []
        srs_param = ",".join(str(s) for s in GURU_AND_ABOVE_STAGES)
        url: str | None = (
            f"{WK_API_BASE}/assignments"
            f"?subject_types=kanji&srs_stages={srs_param}"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                try:
                    resp = await client.get(url, headers=self.headers)
                except httpx.RequestError as e:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"WaniKani API unavailable: {e}",
                    )

                if resp.status_code == 401:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid WaniKani API key",
                    )
                if resp.status_code == 429:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="WaniKani rate limit hit, try again later",
                    )
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"WaniKani API error: {resp.status_code}",
                    )

                data = resp.json()
                for item in data["data"]:
                    assignments.append({
                        "subject_id": item["data"]["subject_id"],
                        "srs_stage": item["data"]["srs_stage"],
                    })

                url = data["pages"]["next_url"]

                logger.info(
                    "wk_import_page",
                    user_id=user_id,
                    fetched_so_far=len(assignments),
                )

            # Now fetch subject characters for all subject IDs
            subject_ids = [a["subject_id"] for a in assignments]
            char_map = await self._fetch_subject_characters(client, subject_ids)

        total_fetched = len(assignments)
        logger.info("wk_import_fetched", user_id=user_id, total=total_fetched)

        # Match to our kanji DB and create/update progress
        imported = 0
        skipped = 0
        already_existed = 0
        now = datetime.now(UTC)

        for assignment in assignments:
            char = char_map.get(assignment["subject_id"])
            if not char:
                skipped += 1
                continue

            # Find kanji in our DB
            result = await self.db.execute(
                select(Kanji).where(Kanji.character == char)
            )
            kanji = result.scalar_one_or_none()

            if kanji is None:
                skipped += 1
                continue

            # Check if user already has progress for this kanji
            result = await self.db.execute(
                select(UserItemProgress).where(
                    UserItemProgress.user_id == user_id,
                    UserItemProgress.item_type == ItemType.KANJI,
                    UserItemProgress.item_id == kanji.id,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                already_existed += 1
                continue

            # Map WK SRS stage to ours (same numbering)
            wk_stage = assignment["srs_stage"]
            is_burned = wk_stage == 9

            progress = UserItemProgress(
                user_id=user_id,
                item_type=ItemType.KANJI,
                item_id=kanji.id,
                srs_stage=wk_stage,
                next_review_at=None if is_burned else now,
                unlocked_at=now,
                burned_at=now if is_burned else None,
                source=ProgressSource.WANIKANI,
            )
            self.db.add(progress)

            # Activate kanji if not already
            if not kanji.active:
                kanji.active = True

            imported += 1

        await self.db.commit()

        logger.info(
            "wk_import_complete",
            user_id=user_id,
            imported=imported,
            skipped=skipped,
            already_existed=already_existed,
            total=total_fetched,
        )

        return WaniKaniImportResponse(
            imported_count=imported,
            skipped_count=skipped,
            already_existed=already_existed,
            total_fetched=total_fetched,
        )

    async def _fetch_subject_characters(
        self, client: httpx.AsyncClient, subject_ids: list[int]
    ) -> dict[int, str]:
        """Fetch kanji characters for a list of subject IDs. Returns {subject_id: character}."""
        char_map: dict[int, str] = {}
        # WK API allows fetching subjects by IDs (comma-separated)
        # Batch in groups of 100 to avoid URL length limits
        for i in range(0, len(subject_ids), 100):
            batch = subject_ids[i : i + 100]
            ids_param = ",".join(str(sid) for sid in batch)
            url = f"{WK_API_BASE}/subjects?ids={ids_param}&types=kanji"

            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                continue

            data = resp.json()
            for item in data["data"]:
                char = item["data"].get("characters")
                if char:
                    char_map[item["id"]] = char

        return char_map
