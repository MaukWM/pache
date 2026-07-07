# Grammar Production SRS — idea + data source research

Status: **brainstorm / paper trail**. Captured 2026-07-01. Not scheduled. Possibly built later
("when in Canada"). Licensing deep-dive lives in sibling `production-srs-data-licensing.md`.

---

## 1. The idea

A **production** SRS (current platform trains recognition only — form→meaning, WaniKani-style).
Flow:

```
English prompt  →  user writes the Japanese  →  LLM (or embedding model) judges semantic +
grammatical match  →  SRS stage up/down  →  feedback on the mistake  →  spaced repeat
```

Plus: LLM alters nouns/verbs so you don't reproduce the same surface sentence — forces the
*pattern*, not a memorized string.

**Grammar-first framing (preferred over sentence-first):** the SRS item is a **grammar pattern
with slots**, not a whole sentence. Example:

```
pattern:  あと〜 (ato + counter) = "N more [units]"
prompt:   "5 more days"  → あと5日
slots:    {number}, {counter}
variants: "3 more days" / "2 more weeks" / "5 more minutes"
```

Card = the construction machine, not the sentence. SRS schedules the pattern; each review fills
slots with fresh values → kills rote, drills the generative rule.

Slot detection: **hybrid** — user marks slots manually AND/OR LLM proposes slots (LLM has the
grammar internally). One structured LLM call can emit `verdict`, `score`, `mistake_note`,
`variant_prompt`, `slots` together.

**Skip the parse tree** — flat slot-template is 90% of value at 10% of work. LLM parses at
judge-time; don't rebuild a Japanese parser.

## 2. Why it works (theory)

**Swain's Output Hypothesis (1985)** — input alone insufficient to produce. Output triggers:
1. **Noticing** — trying to say it makes the gap conscious (input never forces this).
2. **Hypothesis testing** — guess a form, judge reacts, adjust. Output = the test.
3. **Metalinguistic reflection** — producing makes you reflect on *how* the language works.

(Origin fittingly Canadian — French-immersion kids: years of input, still weak output.)

This idea = Output Hypothesis operationalized as an SRS engine. Legit, well-backed,
rarely built this cleanly.

## 3. Three-modality stack (why practice in parallel)

| Practice | Trains | Knowledge type |
|---|---|---|
| Flashcards | form→meaning recognition | lexical, declarative |
| Shadowing | sound, prosody, chunking | phonological, automaticity |
| **Production SRS** | syntactic assembly, construction retrieval | **procedural** |

- Recognition = raw material. Shadowing = automatic sound. Production SRS = converter that turns
  passive vocab into active. Without it the other two stay inert.
- **Speed gain:** repeated forced production → declarative becomes procedural
  (proceduralization) — the actual mechanism behind fluency.
- **Texting spontaneity:** production SRS *is* typed-compose practice → direct transfer, fastest
  visible gain.
- **Speak groundwork:** construction retrieval transfers; real-time speed does not (writing lets
  you pause). Pattern SRS "loads the magazine"; speaking pulls the trigger. Pair with shadowing
  the **same patterns** → assembled (SRS) + automatic sound (shadowing) overlap = speak groundwork.

## 4. Risks / make-or-break

1. **Judge design is the crux.** Embedding cosine alone = dangerous — catches meaning, misses
   particles, register, naturalness. A broken sentence can score high. Need **LLM judge with a
   rubric** (grammar / naturalness / register), not just similarity. Noisy judge → noisy SRS
   signal → garbage scheduling.
2. **Many valid answers.** Japanese has multiple right translations. Binary pass/fail too crude →
   graded score + accept-set.
3. **Write ≠ speak.** Writing trains assembly, not real-time speech retrieval. Partial transfer.
4. **Variation is essential, not optional** — without noun/verb swap you rote-memorize sentences
   instead of learning patterns.

---

## 5. Data source landscape (grammar DB tagged by JLPT)

Research done 2026-07-01. **Key finding: no JMdict-equivalent for grammar exists.** Vocab is a
closed lexicon (→ JMdict, CC-BY-SA, powers Jisho). Grammar points are pedagogical constructs with
no agreed enumeration — every JLPT list traces informally to Jonathan Waller's lists
(tanos.co.uk), all under copyright. No open canonical grammar corpus.

### Usable datasets, ranked for a grammar-pattern SRS

| Repo / source | Format | Count (JLPT) | Meaning lang | License | Slot / structure info |
|---|---|---|---|---|---|
| **jkindrix/japanese-language-data** | JSON per level | 595 (N5–N1) | EN | **CC-BY-SA 4.0** | ✅ `formation` = slot template + `related[]` graph + examples |
| **muzuiyo/jlptgrammar** | SQLite | 762 (N1–N5) | 中文 | MIT | pattern + examples, no slots |
| Hanekawa-00/JLPT-Grammar | JSON | 739 (N1–N5) | 中文 | none | `usage` pattern |
| Sigmabond01/jlpt-grammar-api | live API | ~N5(80)+N4 only | EN | MIT | thin, clean fields |
| SelimJB/jlpt-grammar-cards | txt (semicolon) | N4/N5 only | EN | none (Bunpro-derived) | richest schema (register, cautions, syn/ant) |
| aiko-tanaka/Grammar-Dictionaries | Yomitan JSON | DoJG + others | EN | none | positional-array, deconjugation POS; incomplete DoJG |

### Content sources — copyrighted, scrape/seed only, DO NOT redistribute
- **Bunpro** (bunpro.jp/grammar_points) — best content: structure, register, synonyms/antonyms,
  cautions, multiple examples. Complete N5–N2, partial N1. **Proprietary.**
  - Hidden JSON: `https://bunpro.jp/_next/data/<BUILD_HASH>/en/grammar_points/N5.json` — hash
    rotates every deploy; read current hash from site `__NEXT_DATA__` at request time.
  - Community API ref: cbullard-dev/bunpro-community-api (MIT, has Bunpro's blessing; endpoints in
    `spec/frontend.yaml`). User-data API needs account token.
- **JLPT Sensei** (jlptsensei.com/complete-jlpt-grammar-list/) — per-level lists. **Copyrighted**
  (derived from Waller's lists). No scraped *grammar* dataset on GitHub found; only a *vocab*
  table scraper exists (ikroeber/jlptsensei-table-scraper, MIT, script-only, no data).
- **DoJG** (Dictionary of Japanese Grammar) — published books, **copyrighted**. Machine form =
  aiko-tanaka Yomitan dict (incomplete, no license) + AnkiWeb decks (.apkg, not queryable). Use at
  most for cross-referencing pattern names.

### Adjacent / not grammar-content
- **J-UniMorph** (arxiv 2402.14411) — morphological *inflection* schema (conjugation features).
  Useful for a conjugation/slot **engine**, not for grammar-point content.
- **JMdict** (edrdg.org/jmdict, CC-BY-SA) — vocab, powers Jisho. The model of what grammar lacks.
- kananinirav/jlptbenkyo, tristcoil/hanabira.org (MIT) — full JLPT apps with grammar embedded, no
  standalone exported dataset.
- Note: GitHub topic `jlpt-grammar` is empty/unused — search by repo name, not topic.

### Recommended pipeline
1. **Seed:** jkindrix/japanese-language-data — only source that is English + licensed (CC-BY-SA) +
   has `formation` slot templates. Schema maps ~1:1 to a grammar-pattern SRS item:
   `id, pattern, level, meaning_en, meaning_detailed, formation, formation_notes[], formality,
   related[], examples[]{japanese, english, source}, review_status, sources`.
2. **Fill list gaps:** cross-ref muzuiyo/jlptgrammar (762, MIT); translate 中文 glosses.
3. **Enrich:** LLM generates slot variants + fresh examples (own content — don't redistribute
   Bunpro's). Model the field richness on SelimJB schema.
4. **Caveat:** jkindrix all `review_status: draft`, 0 native-reviewed → spot-check before trusting.

### Licensing bottom line
- This project = **AGPL-3.0**. jkindrix = **CC-BY-SA 4.0**. Compatible (separate works; CC-BY-SA
  4.0 one-way GPL-compatible). Obligations: attribution + share-alike on *adapted grammar data*
  (keep data files under own CC-BY-SA notice, separate from app code). Full detail + TODOs in
  `production-srs-data-licensing.md`.

---

## Source links
- jkindrix/japanese-language-data — https://github.com/jkindrix/japanese-language-data
- muzuiyo/jlptgrammar — https://github.com/muzuiyo/jlptgrammar
- Hanekawa-00/JLPT-Grammar — https://github.com/Hanekawa-00/JLPT-Grammar
- Sigmabond01/jlpt-grammar-api — https://github.com/Sigmabond01/jlpt-grammar-api (live: https://jlpt-grammar-api.vercel.app/api/grammar)
- SelimJB/jlpt-grammar-cards — https://github.com/SelimJB/jlpt-grammar-cards
- aiko-tanaka/Grammar-Dictionaries — https://github.com/aiko-tanaka/Grammar-Dictionaries
- cbullard-dev/bunpro-community-api — https://github.com/cbullard-dev/bunpro-community-api
- ikroeber/jlptsensei-table-scraper — https://github.com/ikroeber/jlptsensei-table-scraper
- Bunpro — https://bunpro.jp/grammar_points
- JLPT Sensei — https://jlptsensei.com/complete-jlpt-grammar-list/
- J-UniMorph — https://arxiv.org/abs/2402.14411
- JMdict — https://www.edrdg.org/jmdict/jmdictart.html
