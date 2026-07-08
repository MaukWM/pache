# Production SRS — design decisions & surface map

Status: **backend COMPLETE (③a/③b/③c), frontend ④ next.** Updated 2026-07-08. Phase 1 scope.
Companion to `production-srs-idea-and-data-sources.md` (idea/theory/data) and
`production-srs-data-licensing.md`. Judge tuning: `production-srs-grading-research.md`.

Progress:
- ① schema · ② review slice · ③ judge plumbing · ③a create+validate · ③b judge→submit · ③c override
  → ALL DONE, committed. 316 tests, ruff + mypy clean.
- Live LLM (OpenAI gpt-5.5) via `scripts/judge/{eval_judge,eval_override,eval_submit}.py` (harness,
  not committed by choice). Judge scored 15/15 on the calibration set.
- ④ frontend = only remaining piece (see "FRONTEND HANDOFF" at bottom).

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
  (cosine misses particles/register/naturalness). Returns `{correct, feedback}` (see DECISIONS #2).
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
- **Review interaction — Option A (LOCKED):** Submit = commit + judge in one call (one shot, no
  retry-till-pass — that would game SRS). Show verdict + feedback. Correct → Enter advances. Wrong →
  feedback + **[Override]** button (→ override endpoint, optional reason) OR Enter to accept the miss.
  Kanji's Backspace-redo does NOT map (it's typo-fix; here retry = gaming). Override = principled
  disagreement, not redo. SRS momentarily drops then rises on override (invisible, final state right).
- **Show the politeness target** ("write: casual/polite") on the review card — the user can't see the
  reference while producing, so the target must be shown (fairness).
- Route `/sentences`, **outside Layout** (focused mode, like `/reviews` `/lessons`).
- Dashboard: 3rd StatTile **作文** next to レッスン/復習, with due count.
- **Latency** is the one genuinely new UX problem: LLM ~2–5s vs instant local grade → needs loading
  state ("判定中…") so it doesn't read as broken.
- **Color: green** for sentences (pink=kanji, purple=vocab). Yellow rejected — collides with SRS
  stage-tier palettes (guru/master trend gold) → reads as a stage, not a type.

### Feedback-loop features
- **Override memory (per-sentence)** — FULLY WIRED (③c).
  `POST /me/sentences/{id}/override {reason?}` overrides the latest rejected review: recomputes SRS
  from `srs_stage_before` as correct, flags the log `overridden` (keeps the judge's `correct=False`
  for analytics), stores `override_reason`. On future reviews, `submit_review` loads prior reasons
  and passes them to `judge(override_reasons=[...])`, which honors them (③b). Scoped per-sentence to
  bound blast radius + gaming. Proven E2E in `scripts/judge/eval_override.py` (fail → reason → pass).
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

get_due_reviews -> add filter item_type IN (KANJI, VOCAB)  (sentences use own /me/sentences/reviews)
```
2 new tables + cheap enum widen. Personal content, standard SRS machinery, unified dashboard/burn/
resurrect free.

---

## DECISIONS — all resolved (was "open")
1. **LLM provider/model** ✅ **OpenAI `gpt-5.5`** (user set `OPENAI_API_KEY`). Provider-swappable via
   `settings.llm_base_url` (OpenAI/OpenRouter/Orq/local) — one file (`src/llm/client.py`).
2. **Judge output** ✅ `{reason (transient), correct, feedback}` → DB stores `correct` + `feedback`.
   Feedback in ENGLISH, targeted fix, no reference-restatement, + one usage mini-example on grammar.
3. **SRS bump parity** ✅ exact-match and LLM-pass bump the same; no threshold (verdict is a bool).
4. **Exact-match normalization** ✅ strip whitespace + spaces (incl. 　) + trailing 。/. (`_normalize`).
   Minimal — LLM is the safety net for near-misses.
5. **Pair-validation timing** ✅ sync gate in `POST /me/sentences` — insert only on `valid`, else 422.
6. **LLM failure/timeout** ✅ rollback, SRS unchanged, → 503 with clear message. (create + submit.)
7. **Politeness** ✅ classified at create (`validate_pair` → polite/casual/mixed), stored, shown as
   target, judge matches; `mixed` = any register accepted. No user override of the classification.
8. **Prompts** ✅ in `src/llm/prompts/*.md`; shared `{{include: _core_rubric.md}}` fragment so judge +
   validator share the grammar/naturalness/meaning/politeness rubric (can't drift). Loader:
   `src/llm/prompt_loader.py`.
9. **Due-batching** ✅ reuses hourly `truncate_to_hour`.
10. **Cost controls** — DEFERRED. One LLM call per non-exact review; ~cents/mo at 20–30/day. No cache
    /rate-limit yet.
11. **Authoring UX** — ④ frontend decision (form location). Bulk jkindrix seed = phase 2.

---

## TECH DEBT — lock held across the LLM call (submit path)
`SentenceService.submit_review` locks the progress row (`with_for_update`) then calls the LLM judge
while holding it (~2–5s). Fine at personal scale — it only blocks a *concurrent submit of the same
sentence* (double-click / two tabs); all other requests (other sentences, due list, kanji reviews)
are unaffected. Improve when concurrency matters: judge BEFORE locking, then acquire the lock,
re-verify still-due/not-burned, write log + update, commit — lock held for ~ms, not the network call.
Marked `TODO(lock)` in the code.

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
- `src/lib/api.ts` — endpoints: create-sentence, list-due, submit-review, override (validation is
  server-side inside create — no separate validate endpoint)
- theme — green tokens / badge color
- localization — JP strings (作文 etc.)

### Cross-cutting
- Cost / latency, LLM error states, per-user auth scoping.

---

## FRONTEND HANDOFF (④) — backend is DONE, build against this

### API contract (implemented, prefix `/api/v1`, auth `Bearer <token>`)
```
POST /me/sentences {english, japanese}
  201 {sentence_id, english, japanese, politeness, srs_stage}   politeness: polite|casual|mixed
  422 {detail}   pair rejected — show detail near the input (English, actionable)
  503            LLM validator down — try again
GET  /me/sentences/reviews
  200 {items:[{sentence_id, english, srs_stage}], count}        japanese HIDDEN (must produce it)
POST /me/sentences/reviews {sentence_id, submitted}
  200 {sentence_id, correct, exact_match, feedback, reference, srs_stage_before, srs_stage_after,
       next_review_at}                                          reference revealed after submit
  400 not due / burned / unknown       503 LLM down (SRS unchanged)
POST /me/sentences/{sentence_id}/override {reason?}
  200 {sentence_id, overridden, srs_stage_before, srs_stage_after, next_review_at}
  400 nothing to override
```

### Screens
- `src/App.tsx` — route `/sentences`, OUTSIDE Layout (focused, like `/reviews` `/lessons`)
- **NEW** review page — reuse `QuizShell`; card body = textarea/IME + async "判定中…" state + feedback
  panel + [Override] button (Option A flow, see Frontend/UX above). Show politeness target on card.
- **NEW** authoring form — POST create; on 422 render `detail`
- `DashboardPage` — 作文 StatTile + due count (mirror レッスン/復習 tiles)
- `src/lib/api.ts` — createSentence, getDueSentences, submitSentenceReview, overrideSentenceReview
- theme — GREEN tint (kanji=pink, vocab=purple)

### Prereqs (or calls fail)
1. **CORS** — `main.py` has no CORS middleware; Vite dev (:5173) → API (:8000) is cross-origin.
   Fix: Vite dev proxy (no backend change) OR add `CORSMiddleware`. DECIDE.
2. Confirm login endpoint shape when wiring `api.ts` (auth_router IS mounted).
3. Product is now **pache** (from remote merge) — naming in UI.

### Reference implementations already in repo
`src/pages/ReviewPage.tsx`, `components/QuizShell.tsx`, `components/QuizCard.tsx`,
`lib/quiz.ts` (grading/normalize), `DashboardPage.tsx` StatTile pattern, `lib/api.ts`.
