"""Offline JMdict dictionary lookup via jamdict.

Wraps jamdict (the same bundled JMdict/KanjiDic data used by the kanji seed
script) so vocab can be searched and imported without calling jisho.org.
The Jamdict handle opens a bundled SQLite DB; it is created once and reused.
"""

import re
from functools import lru_cache
from typing import TypedDict

from jamdict import Jamdict

# Priority tags JMdict uses to flag frequently-used words. Mirrors what Jisho
# surfaces as a "common word".
_COMMON_PRI = {"news1", "ichi1", "spec1", "spec2", "gai1"}

# Matches any hiragana, katakana, or CJK ideograph — used to decide whether to
# append a wildcard for prefix matching (Japanese) vs. an English gloss search.
_JAPANESE_RE = re.compile(r"[぀-ヿ㐀-鿿]")


class DictionaryEntry(TypedDict):
    """A single dictionary lookup result, shaped for the vocab create form."""

    word: str
    readings: list[str]
    meanings: list[str]
    pos: list[str]
    is_common: bool


@lru_cache(maxsize=1)
def _jam() -> Jamdict:
    """Return a shared Jamdict handle (opens the bundled SQLite DB once)."""
    return Jamdict()


def search_jmdict(query: str, limit: int = 20) -> list[DictionaryEntry]:
    """Look up dictionary entries for a query (Japanese or English).

    Japanese queries get a trailing wildcard for prefix matching; English
    queries are searched against glosses as-is. Returns at most ``limit``
    entries. This is a blocking call (SQLite); run it off the event loop.
    """
    query = query.strip()
    if not query:
        return []

    lookup_query = query
    if _JAPANESE_RE.search(query) and "%" not in query and "?" not in query:
        lookup_query = f"{query}%"

    result = _jam().lookup(lookup_query)

    entries: list[DictionaryEntry] = []
    for entry in result.entries[:limit]:
        kanji_forms = [k.text for k in entry.kanji_forms]
        kana_forms = [k.text for k in entry.kana_forms]

        # Prefer the kanji form as the headword; fall back to kana.
        word = kanji_forms[0] if kanji_forms else (kana_forms[0] if kana_forms else "")
        if not word:
            continue

        meanings: list[str] = []
        pos: list[str] = []
        for sense in entry.senses:
            meanings.extend(str(g) for g in sense.gloss)
            for p in sense.pos:
                if p not in pos:
                    pos.append(p)

        pri_tags = {p for k in entry.kanji_forms for p in (k.pri or [])}
        pri_tags |= {p for k in entry.kana_forms for p in (k.pri or [])}

        entries.append(
            DictionaryEntry(
                word=word,
                readings=kana_forms,
                meanings=meanings,
                pos=pos,
                is_common=bool(pri_tags & _COMMON_PRI),
            )
        )

    return entries
