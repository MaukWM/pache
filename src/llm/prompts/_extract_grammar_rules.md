Grammar-point extraction:

Also extract the grammar points the Japanese sentence exercises, for the learner's personal
grammar-tracking bank.

What counts as a grammar point — learner-relevant units at the granularity of a typical grammar
reference or JLPT study list:
- Constructions: 〜による/によって, 〜ぶり, 〜たら, 〜し, 〜しかない
- Conjugation paradigms (abstract keys are fine): 可能形, 受身形, 使役形, 意向形, 〜ちゃう/てしまう, 〜とく/ておく, 〜てみる
- Sentence-ending patterns: 〜んです, 〜よね, 〜かも
- Quoting/nominalizing: 〜と（引用）, 〜って, 〜こと
- Notable particle usage — only when the usage IS the construction (で as means, から as reason)

Do NOT extract: basic case particles doing their default job (は topic, が subject, を object,
に destination/time), plain vocabulary, or the polite/plain distinction itself (tracked separately
as politeness). A typical sentence has 1–5 points; long multi-clause sentences may have more.

Canonical keys — CRITICAL:
1. The learner's existing bank is provided in the user message. If a point is already in the bank —
   even under a different surface form, conjugation, or contraction — you MUST reuse the bank's
   exact `key` string (による → reuse 〜によって; 減っちゃった → reuse 〜ちゃう).
2. Only if genuinely absent, mint a new key: dictionary-citation style, kanji where standard,
   leading 〜 when the pattern attaches to something. If a new key would collide with a bank entry
   that is a DIFFERENT grammar point (homograph, e.g. nominalizing 〜さ vs sentence-final さ),
   disambiguate the new key with a short parenthetical (e.g. 〜さ（名詞化）).

For each point emit: `key`, `meaning_en` (short English gloss, ≤8 words), `evidence` (the exact
substring of the sentence that instantiates it).
