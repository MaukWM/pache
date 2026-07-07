# Production SRS — design decisions & surface map

Status: **design in progress**. Captured 2026-07-05. Phase 1 scope. Companion to
`production-srs-idea-and-data-sources.md` (idea/theory/data) and `production-srs-data-licensing.md`.

Feature: an SRS that trains **production** (write Japanese from English prompt), judged by LLM,
progressing through the existing WaniKani SRS stages. Complements recognition (flashcards) +
shadowing. Theory + rationale in the idea doc.

---

## DECIDED

### Product / behavior
- **Phase 1 = sentence pair.** Item = English prompt + Japanese reference translation. User writes
  JP; system judges.
- **Grading flow:** exact-match (normalized) → SRS up, **no LLM call**. On miss → **reference-anchored
  LLM judge** (naturalness + closeness to reference meaning). Verdict drives SRS up/down.
- **Judge = LLM with a rubric** (grammar / naturalness / register), NOT embedding-cosine alone
  (cosine misses particles/register/naturalness). Returns verdict + score + feedback + natural version.
- **Assumption:** user submits correct EN/JP pairs — but this is NOT trusted (learners err). Mitigated
  by pair-validation at creation (below).
- **Override:** user may override a judge **rejection**. Secondary action + confirm step (harder than
  a flashcard keystroke — sentence judgment is bulkier/more consequential). Logged for judge-quality review.
- **Pair-validation at creation (must-fix):** validate the EN/JP pair once at create time (one LLM
  call: "correct + natural?"), **server-side in POST /sentences** — insert only on pass, else 422.
  Frontend triggers + shows result but does NOT gate (client gate is bypassable). No `validated`
  column — a stored row is valid by construction. Prevents garbage reference poisoning.
- **Sentences skip lessons** — user authored them, no lesson needed. Enter SRS directly at Apprentice
  stage 1. `lesson_queue` untouched.

### Data model
- **Distinct from the existing `VocabSentence` example-sentence system** (`vocab_sentences` table:
  ja/en/added_by, shared, linked M2M to vocab for reading context). Production sentences are their own thing.
- **2 new tables** (named to parallel `vocab_sentences`):
  1. `production_sentences` — content (EN prompt + JP reference).
  2. `production_sentence_review_log` — judge audit + LLM fields (submitted text, exact_match, correct,
     feedback, overridden, stage_before/after, reviewed_at). The 2-axis `review_log`
     (reading_correct/meaning_correct) can't hold single-axis + feedback → own table justified.
- **SRS state** reuses `user_item_progress` + `ItemType.SENTENCE` (★ resolved below — personal content,
  polymorphic SRS state). Content table `production_sentences` is per-user, holds NO SRS columns.
- Reuse `calculate_next_review` (pure fn on stage), `SRS_INTERVALS`, `truncate_to_hour`,
  stage 1–9 semantics, burn/resurrect.

### Frontend / UX
- Reviews are **WaniKani-style typed-input auto-grade** (NOT self-grade). Reading (kana/IME) + meaning
  (EN), 2 cards/item, graded by `evaluateAnswer` (normalized exact reading + Levenshtein meaning),
  instant. Backspace = deliberately fail. — established fact, drove the design below.
- **Separate review screen**, sibling of `ReviewPage`. Reuse `QuizShell` (fullscreen chrome, progress,
  exit). **New card body** (can't reuse single-line `QuizCard`): textarea/IME + async judge state +
  rich feedback panel.
- Route `/sentences`, **outside Layout** (focused mode, like `/reviews` `/lessons`).
- Dashboard: 3rd StatTile **作文** next to レッスン/復習, with due count.
- **Latency** is the one genuinely new UX problem: LLM ~2–5s vs instant local grade → needs loading
  state ("判定中…") so it doesn't read as broken.
- **Color: green** for sentences (pink=kanji, purple=vocab). Yellow rejected — collides with SRS
  stage-tier palettes (guru/master trend gold) → reads as a stage, not a type.

### Feedback-loop features
- **Override memory (per-sentence)** — DONE at judge level. `production_sentence_review_log.override_reason`
  stores the learner's justification when they override a verdict; on future reviews of THAT sentence,
  prior reasons are passed to `judge(override_reasons=[...])` and honored. Scoped per-sentence (not
  global) to bound blast radius + gaming. Proven E2E in `scripts/judge/eval_override.py` (fail → reason →
  pass). HTTP/service wiring (override endpoint + loading prior reasons on submit) lands with step 3/4.
- **Recurring-mistake detection (DEFERRED)** — analytics OVER `production_sentence_review_log` (which
  already stores submitted + feedback + correct), NOT fed into every judge call (cost/context bloat).
  Build later as periodic LLM summarization of a user's logs, or add an `error_category` column for
  cheap group-by. Not built now.

### Phase 2 (deferred, not now)
- Variation dashboard: at GURU, button generates variants → injected at Apprentice → multiple entries
  per sentence → generalization.
- Two variant axes: **paraphrase** (same meaning, diff structure → flexibility) and **slot swap**
  (same structure, diff content → pattern generalization). Dashboard offers both.
- Generated variants must be validated before injection (same pair-validation).
- Per-sentence variant cap to avoid review-load balloon.
- Grammar-pattern-with-slots framing (あと〜 + counter) + jkindrix dataset seed (CC-BY-SA, see
  licensing doc).

---

## ★ KEY DECISION — RESOLVED 2026-07-05: personal content + ItemType SRS state
Decision: **personal (per-user) content pool, separate from `vocab_sentences`** — AND still use the
polymorphic `ItemType`/`user_item_progress` machinery for SRS state. Content-ownership and
SRS-state-home are separate axes; a personal item lives fine in `user_item_progress` (it already
carries `user_id`). Reconciles both instincts: "item type made for this" + personal pool.

Final schema (locked):
```
ItemType += SENTENCE

NEW production_sentences  id, user_id (owner, index), english:Text, japanese:Text, created_at
                         -- content ONLY; no SRS columns. Named to parallel `vocab_sentences`.
                         -- no `validated` column: pair validated SERVER-SIDE at POST /sentences,
                         --   inserted only on pass → a persisted row is valid by construction.

NEW production_sentence_review_log
                         id, user_id, sentence_id(FK), submitted:Text, exact_match:bool,
                         correct:bool, feedback:Text|None,
                         overridden:bool default False, srs_stage_before, srs_stage_after,
                         reviewed_at (index)
                         -- no `score`: reasoning-model judge emits verdict directly (native CoT),
                         --   no numeric to store. Judge schema = {correct:bool, feedback:str|None}.

SRS state -> user_item_progress (item_type=SENTENCE, item_id -> production_sentences.id)
             app-level rule: progress.user_id == production_sentences.user_id
             enum widen ×3 (metadata-only in MySQL 8)

get_due_reviews -> add filter item_type IN (KANJI, VOCAB)  (sentences use own /sentences/due)
```
2 new tables + cheap enum widen. Personal content, standard SRS machinery, unified dashboard/burn/
resurrect free.

---

## OTHER OPEN DECISIONS
1. **LLM provider/model** — rec Claude **Haiku** for judge (cheap, fast, structured output). Same for
   pair-validator. Confirm provider (Anthropic) + model id.
2. **Judge output contract — DECIDED:** `{correct: bool, feedback: str | None}`. `correct` drives SRS;
   `feedback` is independent (why-wrong OR a better phrasing even when correct). No `score` — reasoning
   model does CoT natively, emits verdict directly. `feedback` not persisted as `reasoning` (transient).
3. **SRS bump parity** — exact-match and LLM-pass bump SRS the same (rec: same bump). No threshold
   (verdict is a direct bool, not a scored cutoff).
4. **Exact-match normalization** — whitespace strip, trailing 。, fullwidth↔halfwidth, kana handling.
   Define rules (can borrow `evaluateAnswer` normalization approach).
5. **Pair-validation timing** — sync gate at creation (rec) vs async background.
6. **LLM failure/timeout** — don't advance SRS, allow retry, surface "judge unavailable". Graceful degrade.
7. **Cost controls** — one LLM call per non-exact review. Cache identical submissions? Rate-limit?
   Budget ceiling? (Can defer; flagged.)
8. **Authoring UX** — where users add sentences: dedicated screen? dashboard entry? bulk import
   (jkindrix seed) later?
9. **Due-batching** — reuse hourly `truncate_to_hour` batching like reviews? (rec: yes.)

---

## TECH DEBT — DRY review services later (deferred, don't break ReviewService)
`SentenceService` + `ReviewService` share orchestration. SRS *math* already DRY
(`calculate_next_review`, `truncate_to_hour`). Still duplicated — extract LATER, only when touching
`ReviewService` is safe (it's mature + tested):
- `hour_reached(dt, now) -> bool` — the tz-normalize + hour-truncate compare, repeated ~4 sites
  (bug-prone `if tzinfo is None` idiom). Note: the `None` case differs by context (due-list excludes
  None in SQL; submit-guard treats None as due) → stays at call site.
- `apply_review_outcome(progress, correct, now) -> (before, after, next)` — identical 5-line
  stage/next/burn mutation in both submit paths; pure on `UserItemProgress`.
- Put both in `src/reviews/srs.py`.
- **Do NOT** build a shared base `ReviewService` / template-method — shallow coupling across domains,
  fights thin-per-domain convention. Guards *look* similar but will diverge (override, different due
  rules). Leave `get_due` / log-write / response / judge per-domain.
- When done: re-run `tests/reviews` + `tests/sentences`.

## SURFACE MAP (plan ahead)

### Backend
- `src/core/constants.py` — `ItemType += SENTENCE`
- **NEW** `src/sentences/` — `models.py`, `schemas.py`, `service.py`, `router.py` (domain-per-package)
- **NEW** LLM client — `src/llm/` or core. Provider client, structured-output judge, pair-validator,
  timeout/retry/error handling. **Greenfield — no LLM code exists today (only httpx).**
- `src/settings.py` — LLM API key, model id, provider (new env vars)
- alembic — 2 new tables (+ enum widen ×3: `user_item_progress`, `lesson_queue`, `review_log` —
  metadata-only in MySQL 8 when appending value at end)
- `src/reviews/service.py` — `get_due_reviews` add `item_type IN (KANJI,VOCAB)` filter
- `src/reviews/srs.py` — reuse, no change
- `src/main.py` — mount `sentences_router`
- `pyproject.toml` — add `anthropic` (or raw httpx calls)

### Frontend
- `src/App.tsx` — route `/sentences`, outside Layout
- **NEW** `src/pages/SentenceReviewPage.tsx` — reuse `QuizShell`; new card body (textarea/IME, async
  judge state, feedback panel, override action)
- **NEW** authoring UI — add-sentence form + creation-validation feedback
- `src/pages/DashboardPage.tsx` — StatTile 作文 + due-count query
- `src/lib/api.ts` — endpoints: list-due, submit-review, create-sentence, validate-pair
- theme — green tokens / badge color
- localization — JP strings (作文 etc.)

### Cross-cutting
- Cost / latency, LLM error states, per-user auth scoping.

---

## Endpoints (draft)
- `POST /api/v1/sentences` — create (runs pair-validation gate)
- `GET  /api/v1/sentences/due` — due queue (query `user_item_progress WHERE item_type=SENTENCE`
  + join `production_sentences`)
- `POST /api/v1/sentences/{id}/review` — submit answer → exact-match or LLM judge → SRS update + log
- `GET  /api/v1/sentences` — list user's sentences (management)
