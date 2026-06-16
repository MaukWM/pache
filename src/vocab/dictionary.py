"""Offline JMdict dictionary lookup via jamdict.

Wraps jamdict (the same bundled JMdict/KanjiDic data used by the kanji seed
script) so vocab can be searched and imported without calling jisho.org.
The Jamdict handle opens a bundled SQLite DB; it is created once and reused.
"""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import TypedDict

from jamdict import Jamdict

# jamdict opens a SQLite connection that can only be used from the thread that
# created it. A single dedicated worker keeps every lookup on one thread, so the
# cached handle and its connection stay valid across requests.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="jamdict")

# Priority tags JMdict uses to flag frequently-used words. Mirrors what Jisho
# surfaces as a "common word".
_COMMON_PRI = {"news1", "ichi1", "spec1", "spec2", "gai1"}

# Matches any hiragana, katakana, or CJK ideograph — used to decide whether to
# append a wildcard for prefix matching (Japanese) vs. an English gloss search.
_JAPANESE_RE = re.compile(r"[぀-ヿ㐀-鿿]")


class DictionarySense(TypedDict):
    """A single JMdict sense (one numbered definition with its own glosses + pos)."""

    glosses: list[str]
    pos: list[str]


class DictionaryEntry(TypedDict):
    """A single dictionary lookup result, shaped for the vocab create form."""

    word: str
    readings: list[str]
    # Flattened glosses across all senses (kept for back-compat / quick display).
    meanings: list[str]
    pos: list[str]
    # Per-sense breakdown so the UI can show numbered senses Jisho-style and let
    # the user import one or several senses' glosses.
    senses: list[DictionarySense]
    is_common: bool


@lru_cache(maxsize=1)
def _jam() -> Jamdict:
    """Return a shared Jamdict handle (opens the bundled SQLite DB once).

    Only ever called from the single ``_executor`` thread, so the SQLite
    connection it opens stays bound to that one thread.
    """
    return Jamdict()


async def search_jmdict_async(query: str, limit: int = 20) -> list["DictionaryEntry"]:
    """Async wrapper that runs the blocking lookup on the dedicated thread."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, search_jmdict, query, limit)


def search_jmdict(query: str, limit: int = 20) -> list[DictionaryEntry]:
    """Look up dictionary entries for a query (Japanese or English).

    Japanese queries get a trailing wildcard for prefix matching; English
    queries are searched against glosses as-is. Returns at most ``limit``
    entries. This is a blocking call (SQLite); run it off the event loop.
    """
    query = query.strip()
    if not query:
        return []

    is_japanese = bool(_JAPANESE_RE.search(query))
    has_wildcard = "%" in query or "?" in query
    # Japanese queries need a wildcard for prefix matching (an exact lookup of a
    # partial word returns nothing); English queries search glosses directly.
    lookup_query = f"{query}%" if (is_japanese and not has_wildcard) else query

    result = _jam().lookup(lookup_query)

    entries: list[DictionaryEntry] = []
    # Cap raw rows: a bare wildcard can match hundreds, and we filter/sort below.
    for entry in result.entries[:300]:
        kanji_forms = [k.text for k in entry.kanji_forms]
        kana_forms = [k.text for k in entry.kana_forms]

        # Prefer the kanji form as the headword; fall back to kana.
        word = kanji_forms[0] if kanji_forms else (kana_forms[0] if kana_forms else "")
        if not word:
            continue

        meanings: list[str] = []
        pos: list[str] = []
        senses: list[DictionarySense] = []
        for sense in entry.senses:
            glosses = [str(g) for g in sense.gloss]
            meanings.extend(glosses)
            sense_pos = list(sense.pos)
            for p in sense_pos:
                if p not in pos:
                    pos.append(p)
            if glosses:
                senses.append(DictionarySense(glosses=glosses, pos=sense_pos))

        pri_tags = {p for k in entry.kanji_forms for p in (k.pri or [])}
        pri_tags |= {p for k in entry.kana_forms for p in (k.pri or [])}

        entries.append(
            DictionaryEntry(
                word=word,
                readings=kana_forms,
                meanings=meanings,
                pos=pos,
                senses=senses,
                is_common=bool(pri_tags & _COMMON_PRI),
            )
        )

    if is_japanese and not has_wildcard:
        # jamdict's wildcard search is noisy and idseq-ordered. Keep only entries
        # that actually contain the typed text, then rank by relevance.
        entries = [
            e
            for e in entries
            if query in e["word"] or any(query in r for r in e["readings"])
        ]
        entries.sort(
            key=lambda e: (not e["word"].startswith(query), not e["is_common"], len(e["word"]))
        )
    else:
        entries.sort(key=lambda e: (not e["is_common"], len(e["word"])))

    return entries[:limit]
