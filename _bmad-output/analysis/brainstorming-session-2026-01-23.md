---
stepsCompleted: [1, 2]
inputDocuments: []
session_topic: 'Backend architecture and database design for extensible SRS kanji platform'
session_goals: 'Extensible data models, kanji data sourcing, import strategy, solid API foundation'
selected_approach: 'AI-facilitated technical deep-dive'
techniques_used: ['requirements elicitation', 'data modeling', 'API design']
ideas_generated: []
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Floppa
**Date:** 2026-01-23

## Session Overview

**Topic:** Backend architecture and database design for extensible SRS kanji platform
**Goals:** Extensible data models, kanji data sourcing, WaniKani import strategy, solid API foundation

### Project Context

- Social SRS kanji learning platform with shared item pool
- Self-hosted on homeserver behind SSO (small user base)
- Backend-first development (FastAPI/Python)
- Frontend plugged on later
- Supplementary to WaniKani, not replacement

---

## Key Decisions

### SRS System (WaniKani Clone)

| Stage | Next Review |
|-------|-------------|
| Apprentice 1 → 2 | 4 hours |
| Apprentice 2 → 3 | 8 hours |
| Apprentice 3 → 4 | ~1 day |
| Apprentice 4 → Guru 1 | ~2 days |
| Guru 1 → 2 | 1 week |
| Guru 2 → Master | 2 weeks |
| Master → Enlightened | 1 month |
| Enlightened → Burned | 4 months |

- Wrong answer drops ~2 stages (WaniKani logic)
- Review batching by hour (not exact timestamps)
- Resurrection of burned items supported

### Review Mechanics

- Both Kanji and Vocab are reviewable with SRS
- Reviews: reading + meaning, both must pass to advance item
- Back-to-back review (reading → meaning for same item)
- Individual submission per answer (no batching - safety)
- Frontend validates correctness, backend records outcome

### Lessons

- Lessons exist (introduction before Apprentice 1)
- Batch lesson completion (WaniKani style)
- User-curated lesson queue ("desired lesson items")
- Users can write custom explanation (meaning) + mnemonic (reading) per item

### Shared Item Pool

- Kanji: pre-seeded from external source, but **dormant** until vocab attached
- Vocab: user-created, visible to all users
- Items show: creator, arbitrary tags
- Discovery: browse pool, filter by tag, filter by "already have it"
- "Already have it" = in review queue OR burned

### Learning Order Enforcement

- Kanji → Vocab prerequisite chain (strict)
- Multi-kanji vocab requires ALL constituent kanji learned first
- Radicals: optional metadata only, NOT prerequisite (v1)

### WaniKani Import

- Store WK API key on User (enables sync button)
- Import burned kanji → marks user progress, kanji stays dormant
- Source field on UserItemProgress: `manual` | `wanikani`

### Authentication

- Username only (v1) - no password hash, trusted users
- SSO integration later (keep sso_id field nullable)

---

## Data Model

```
┌─────────────────────────────────────────────────────────────────┐
│                         CORE ENTITIES                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User                         Kanji (seeded, ownerless)         │
│  ────                         ─────                             │
│  id                           id                                │
│  username (unique, login)     character (食)                    │
│  sso_id (nullable)            meanings[]                        │
│  wanikani_api_key (nullable)  primary_onyomi[]                  │
│  created_at                   primary_kunyomi[]                 │
│                               radicals[] (optional)             │
│                               jlpt_level                        │
│                               is_active (default: false)        │
│                                                                 │
│  Vocab (user-created)         Tag                               │
│  ─────                        ───                               │
│  id                           id                                │
│  word (食べる)                name                              │
│  reading (たべる)             created_by (user_id)              │
│  meanings[]                                                     │
│  example_sentences[]                                            │
│  created_by (user_id)                                           │
│  creator_comment                                                │
│  kanji_ids[] (linked)                                           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                       PROGRESS / SRS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  UserItemProgress                                               │
│  ────────────────                                               │
│  id                                                             │
│  user_id                                                        │
│  item_type (kanji | vocab)                                      │
│  item_id                                                        │
│  srs_stage (0-9: lesson→app1-4→guru1-2→master→enl→burned)      │
│  next_review_at                                                 │
│  unlocked_at                                                    │
│  burned_at (nullable)                                           │
│  meaning_note (user's custom explanation)                       │
│  reading_mnemonic (user's custom mnemonic)                      │
│  source (manual | wanikani)                                     │
│                                                                 │
│  ReviewLog                                                      │
│  ─────────                                                      │
│  id                                                             │
│  user_id                                                        │
│  item_type                                                      │
│  item_id                                                        │
│  review_type (reading | meaning)                                │
│  correct (bool)                                                 │
│  srs_stage_before                                               │
│  srs_stage_after                                                │
│  reviewed_at                                                    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                       RELATIONSHIPS                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  VocabTag (many-to-many)      LessonQueue                       │
│  ────────                     ───────────                       │
│  vocab_id                     user_id                           │
│  tag_id                       item_type                         │
│                               item_id                           │
│                               added_at                          │
│                               position (ordering)               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Structure

```
# Auth
POST   /auth/login              {username} → session/token

# Pool browsing
GET    /kanji                   ?active=true&tag=...
GET    /kanji/{id_or_char}      Supports both /kanji/123 and /kanji/食
GET    /vocab                   ?tag=...&not_in_queue=true&created_by=...
GET    /vocab/{id}
POST   /vocab                   Create new vocab (auto-activates linked kanji)

# User's learning
GET    /me/queue                Lesson queue
POST   /me/queue                Add items to lesson queue
DELETE /me/queue/{item}
GET    /me/reviews              Items due for review
POST   /me/reviews              Submit single review {item_type, item_id, review_type, correct}
GET    /me/progress             All user progress (filter by stage)

# Lessons
POST   /me/lessons              Batch complete lessons (moves items to Apprentice 1)

# WK Import
POST   /me/import/wanikani      Uses stored API key, imports burned kanji
```

---

## Open Decisions

| Decision | Status | Notes |
|----------|--------|-------|
| Kanji data source | Open | Leaning KANJIDIC2 for simplicity, jmdict-simplified also viable |
| Radical display | Deferred | Optional v2 feature, traditional radicals from KRADFILE |

---

## Technical Stack

- **Backend:** FastAPI + Python
- **Database:** TBD (PostgreSQL likely)
- **Deployment:** Self-hosted homeserver behind SSO
- **Scale:** Small user base, optimize for simplicity
