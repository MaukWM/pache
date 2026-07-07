# How to grade a produced sentence — research + design

Status: research / design reference for the production-SRS judge. Captured 2026-07-07. Companion to
`production-srs-design.md`. Grounds the prompt in `src/llm/judge.py` and the cases in
`scripts/judge/cases.py`.

Scope: how do you decide a learner's Japanese sentence is "right"? This surveys the grading models,
the error taxonomy, LLM-as-judge practice, and the Japanese-specific concerns — then locks the
design and points at the calibration loop.

---

## 1. What "grading a sentence" actually means

There is no single "correct". Translation/production grading decomposes into distinct axes, borrowed
from machine-translation evaluation (adequacy vs fluency) and second-language assessment:

| Axis | Question | Example failure |
|------|----------|-----------------|
| **Adequacy / meaning** | Does it convey the intended meaning? | negation flip: 死ぬ人がいる ("people die") for "no one died" |
| **Accuracy / grammar** | Is it grammatically well-formed? | し on a bare noun; 下がる (intr.) where 下げる (tr.) is needed |
| **Fluency / naturalness** | Would a native actually say it this way? | 対策の高さ — grammatical but not a real collocation |
| **Register / appropriateness** | Right politeness/formality for context? | polite です ending where the context is casual だ/plain |

The classic MT split is **adequacy** (meaning preserved) vs **fluency** (reads natively). SLA adds
**accuracy** (form) and **sociolinguistic appropriateness** (register). For a *production* trainer
aimed at native-like output, all four matter — and (design decision) naturalness + register are
first-class, not bonus.

## 2. Reference-based vs reference-free

Two grading strategies:

- **Reference-based**: compare to a gold answer. Classic metrics (BLEU, chrF, METEOR, BERTScore)
  and exact-match live here. **Fatal weakness for production**: one meaning has many valid
  surface forms. The user's own data shows 3+ natural ways to say the travel sentence; penalizing
  a good sentence for not matching the reference is wrong.
- **Reference-free (quality estimation)**: judge the sentence on its own merits (COMET-QE,
  LLM-as-judge). Handles paraphrase, but drifts without an anchor.

**Chosen hybrid**: reference-*anchored*, not reference-*matched*. The reference pins meaning +
naturalness + register as a benchmark; the judge must ACCEPT any different phrasing that is equally
natural, correct, and register-matched. Exact-match against the reference remains only as a free
fast-path (skip the LLM when the user reproduces it verbatim).

## 3. Error taxonomy (general + Japanese)

A grading rubric needs a shared vocabulary of failure. General L2 taxonomy: omission, addition,
substitution (wrong word), misordering, malformation (wrong conjugation). Applied to Japanese, the
high-frequency, high-signal categories — all observed in the user's writing:

| Category | JP specifics | User example |
|----------|--------------|--------------|
| **Particle error** | は/が, を/に, で/に | 弱い地震*だけが* (should be でも) |
| **Transitivity pair** | 下がる/下げる, 上がる/上げる, 変わる/変える | 依存を*下がる* (needs 下げる) |
| **Negation / polarity** | ～ない, ～ていない, existence いない/ない | 死ぬ人が*いる*ので (meaning inverted) |
| **Voice** | active vs passive 建てる/建てられる | *作ったのはない* → 建てられていない |
| **Wrong lexical choice** | near-synonyms, false friends | *妨害* (obstruction) for 被害 (damage); *不安* (anxious) for 不安定 (unstable) |
| **Nonexistent/miscombined word** | | *算数年* (算数 = school arithmetic) for 数年 |
| **Collocation / naturalness** | grammatical but non-native pairings | *対策の高さ* → 対策がしっかりしている |
| **Register mismatch** | 丁寧語 です/ます vs plain だ | polite ending in a casual exchange |
| **Conjunction misuse** | し, から, ので, のに attach to predicates | *出会いし* (し on bare noun) |
| **Word order / naming** | counters, scales | *6震度* → 震度6 |
| **Script** | leaving English mid-sentence | fuel / dependency / windmill untranslated |

This taxonomy is what the judge's `feedback` should name — "particle error", "transitivity",
"wrong word" — so the learner gets diagnosable, not vague, correction.

## 4. LLM-as-judge — practice and pitfalls

State of the art for open-ended language grading is an LLM judge with a rubric. What the literature
(and hard experience) says:

- **Rubric beats vibes.** Enumerate the axes and the pass/fail bar explicitly; don't ask "is this
  good?". Our prompt lists grammar/naturalness/register + the guards.
- **Reason before verdict.** Making the model justify *then* decide improves calibration. We use a
  reasoning model (native CoT) and additionally capture a short `reason` field for tuning
  visibility (transient — never persisted).
- **Known biases to counter**: verbosity bias (longer ≠ better), position bias (n/a — single item),
  self-consistency (same input can flip run-to-run near the boundary). Mitigate with a crisp bar
  and, if needed later, majority vote of N calls on borderline cases.
- **Binary vs graded**: we use binary correct/incorrect (drives SRS) because the earlier design
  dropped the numeric score — the reasoning model commits to a verdict directly. `feedback` carries
  the nuance a score would have.
- **Strictness is a prompt parameter, tuned empirically** — not guessable in the abstract. Hence the
  eval harness (§8).

## 5. Naturalness — the hard axis

Adequacy and grammar are relatively checkable; **naturalness is the one that needs a strong model
and careful calibration**. It's the difference between "technically correct" and "a native would
say this". Failure modes: unnatural collocations (対策の高さ), overly literal calques from English,
stiff textbook phrasing, wrong nuance among synonyms (発見 discovery vs 発明 invention).

Two risks pull opposite ways:
- **Too lax** → rewards foreign-sounding-but-parseable Japanese; defeats the whole point.
- **Too strict** → nitpicks acceptable sentences; SRS never advances; demoralizing.

The guard (design decision): mark incorrect only when a native would find it **odd/foreign/wrong**,
NOT merely when a more elegant phrasing exists. Where exactly that line sits is the #1 thing to tune
with the harness.

## 6. Japanese-specific grading concerns (deep-dive)

- **Register is structural, not lexical.** Politeness is set by the **sentence-final predicate**
  (です/ます vs だ/plain). Crucially, **subordinate and relative clauses take plain form even in
  polite speech**: 日本に住んで**いる**友達に会い**ます** is fully correct, not "mixed". A naive
  "detect plain+polite together → fail" rule would wrongly punish correct Japanese. This must be
  judged by a model that knows the rule (guard case in the calibration set).
- **Transitivity pairs** are a top production error and fully meaning-changing: 下がる/下げる,
  上がる/上げる, 始まる/始める, 変わる/変える.
- **Particle precision** — は/が (topic vs subject), を/に, で/に — subtle, high-frequency.
- **Existence & negation** — ある/いる (inanimate/animate) and their negatives ない/いない;
  ～ていない for "hasn't/isn't". Easy to invert meaning.
- **Collocation** — 被害が出る, 対策がしっかりしている, 歴史がある. Native pairings that
  don't follow from grammar alone.
- **Counters & scale naming** — 震度6 (not 6震度); the seismic 震度 scale ≠ magnitude.
- **Script discipline** — leaving English words in (fuel, dependency) is a production gap for a
  native-like target, though tolerated for genuine proper nouns (place names in katakana/latin).

## 7. Calibration methodology

You cannot pick the strictness bar in the abstract — you calibrate it against labeled examples:

1. Assemble a **gold set**: sentences with known correct/incorrect labels + the reason.
2. Run the judge, compare its verdict to the label, read its `reason`/`feedback`.
3. Where it disagrees, adjust the prompt (bar, wording, examples), rerun.
4. Repeat until verdicts AND feedback style satisfy.

This is exactly `scripts/judge/eval_judge.py` over `scripts/judge/cases.py`. The user's two conversations
are excellent gold data — real errors with corrections already worked out (see §9). The cases probe
each dial: grammar, negation, transitivity, wrong-word, collocation, register match/mismatch, valid
alternates (must pass), and the subordinate-clause guard (must pass).

## 8. Locked design (recap) + prompt structure

- Judge output: `{reason (transient), correct: bool, feedback: str|null}` → DB stores `correct` +
  `feedback` only.
- Bar: native-like. FAIL on grammar error, meaning change, unnaturalness, or sentence-final register
  mismatch. Guard against nitpicking + against false-flagging plain subordinate clauses.
- Reference = meaning/naturalness/register benchmark; accept valid alternates.
- Reasoning model; provider-swappable via `base_url` (OpenAI now).
- Prompts live in `src/llm/prompts/judge_system.md` (+ `judge_user.md`) — the tuning surface,
  loaded at runtime. Edit md → rerun harness, no code change.

---

## 9. Did the provided conversations contain bad examples? — YES (catalog)

Both conversations are dense with gradeable errors. This is the raw material now encoded in
`scripts/judge/cases.py`. Catalogued by category:

**Conversation 1 (travel/culture)**
- `出会いし` — し attached to a bare noun (needs a predicate: 出会えるし / 出会いだし). *[grammar]*
- (positive control) 新しい人との出会いもあるし… — a valid ALTERNATE that differs from the
  reference and must still PASS.

**Conversation 2 (earthquakes / Netherlands)** — richest source:
- `死ぬ人があるので` — negation/polarity inverted; meant "no one dies" (死者は出ていない). *[meaning]*
- `妨害よく起こる` — 妨害 (obstruction) for 被害 (damage). *[wrong word]*
- `算数年` — 算数 (arithmetic) for 数年 (several years). *[nonexistent combo]*
- `地が不安になって` — 不安 (anxious) for 不安定 (unstable); bare 地 for 地盤. *[wrong word]*
- `地震を超すために作ったのはない` — 超す for 耐える; active for passive 建てられていない. *[verb+voice]*
- `死者は出てないのがいないなんて` — stacked double negation. *[grammar]*
- `対策の高さが分かる` — unnatural collocation (→ 対策がしっかりしている). *[naturalness]*
- `依存を下がるつもり` — 下がる (intr.) for 下げる (tr.). *[transitivity]*
- `6震度` — word order (→ 震度6). *[ordering]*
- register: the exchange is casual (んだ/だよ/ね); a polite です ending would be a register
  mismatch (encoded as a dedicated case).
- script: fuel / dependency / windmill / dam left in English. *[script]*

Also embedded (already answered in-thread, noted for completeness): **受ける vs 受け取る** — "take
an exam" = 試験を受ける (undergo/receive), NOT 受け取る (physically collect). A classic
wrong-lexical-choice case; could be added to the set as a vocab case.

Verdict: the conversations give a ready-made, category-spanning gold set — correct forms, valid
alternates, and real errors with their corrections. Ideal for calibrating the judge.
