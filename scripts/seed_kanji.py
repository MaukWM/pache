"""Seed script for populating kanji from jamdict.

This script loads kanji data from jamdict's bundled kanjidic2 database
and inserts it into the application database.
The script is idempotent - safe to run multiple times.

Usage:
    python -m scripts.seed_kanji
"""

import asyncio

from jamdict import Jamdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tqdm import tqdm

from src.database import async_session_maker
from src.kanji.models import Kanji
from src.logging import logger


def load_kanji_from_jamdict() -> list[dict]:
    """Load kanji data from jamdict's kanjidic2 database."""
    jam = Jamdict()
    kanji_list = []

    # Get all character literals from jamdict's char table
    all_char_rows = jam.kd2.char.select()

    for char_row in tqdm(all_char_rows, desc="Loading from jamdict", unit="kanji"):
        # Get full character data (includes rm_groups with meanings/readings)
        char = jam.kd2.get_char(char_row.literal)
        if char is None:
            continue

        kanji_data = {
            "character": char.literal,
            "meanings": [],
            "readings_on": [],
            "readings_kun": [],
            "grade": char_row.grade,
            "jlpt_level": char_row.jlpt,
            "stroke_count": char_row.stroke_count or 0,
        }

        # Extract meanings and readings from rm_groups
        if char.rm_groups:
            for rm_group in char.rm_groups:
                # Extract meanings (English only - m_lang is empty, None, or 'en')
                for meaning in rm_group.meanings:
                    if not meaning.m_lang or meaning.m_lang == "en":
                        kanji_data["meanings"].append(meaning.value)

                # Extract readings
                for reading in rm_group.readings:
                    if reading.r_type == "ja_on":
                        kanji_data["readings_on"].append(reading.value)
                    elif reading.r_type == "ja_kun":
                        kanji_data["readings_kun"].append(reading.value)

        # Only add if we have at least meanings or readings
        if kanji_data["meanings"] or kanji_data["readings_on"] or kanji_data["readings_kun"]:
            kanji_list.append(kanji_data)

    return kanji_list


async def seed_kanji(db: AsyncSession, kanji_data_list: list[dict]) -> tuple[int, int]:
    """Insert kanji data into database (idempotent)."""
    inserted_count = 0
    skipped_count = 0

    for kanji_data in tqdm(kanji_data_list, desc="Seeding kanji", unit="kanji"):
        # Check if kanji already exists
        result = await db.execute(select(Kanji).where(Kanji.character == kanji_data["character"]))
        existing = result.scalar_one_or_none()

        if existing is not None:
            skipped_count += 1
            continue

        # Create new kanji record
        kanji = Kanji(
            character=kanji_data["character"],
            meanings=kanji_data["meanings"] or [],
            readings_on=kanji_data["readings_on"] or [],
            readings_kun=kanji_data["readings_kun"] or [],
            grade=kanji_data["grade"],
            jlpt_level=kanji_data["jlpt_level"],
            stroke_count=kanji_data["stroke_count"],
            active=False,  # All kanji start dormant
        )
        db.add(kanji)
        inserted_count += 1

        # Commit in batches for performance
        if inserted_count % 500 == 0:
            await db.commit()

    # Final commit
    await db.commit()
    return inserted_count, skipped_count


async def main() -> None:
    """Main entry point for seed script."""
    logger.info("seed_start", source="jamdict")

    # Load kanji from jamdict
    kanji_data_list = load_kanji_from_jamdict()
    logger.info("jamdict_loaded", count=len(kanji_data_list))

    # Insert into database
    async with async_session_maker() as db:
        inserted, skipped = await seed_kanji(db, kanji_data_list)
        logger.info("seed_complete", inserted=inserted, skipped=skipped)
        print(f"Seed complete: {inserted} inserted, {skipped} skipped (already existed)")


if __name__ == "__main__":
    asyncio.run(main())
