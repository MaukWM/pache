---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
status: complete
inputDocuments: ['product-brief-kanji-srs-2026-01-23.md', 'brainstorming-session-2026-01-23.md']
workflowType: 'prd'
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 1
  projectDocs: 0
classification:
  projectType: api_backend
  domain: edtech_personal
  complexity: low
  projectContext: greenfield
date: 2026-01-23
author: Floppa
---

# Product Requirements Document - Kanji SRS Platform

**Author:** Floppa
**Date:** 2026-01-23

## Executive Summary

A self-hosted kanji learning platform continuing where WaniKani ends. Built for a small trusted friend group, it replicates WaniKani's SRS intervals and reading/meaning review style with user-created vocabulary. When you encounter a term in the wild - Twitter slang, game terminology, character names - it finally has a home. The shared item pool turns solo grinding into a social experience.

**Tech:** FastAPI backend, PostgreSQL, self-hosted
**Users:** ~5 friends, all post-WaniKani learners
**MVP Focus:** Reviews, lessons, vocab creation, shared pool, WK import

## Success Criteria

*Carried forward from Product Brief - personal project, minimal formal metrics needed.*

### User Success
- Daily active use (habit formation)
- Multiple sessions per day for users with items in rotation
- Retention signal: remembering items after 1+ month review gaps

### Technical Success
- Always up (reliable self-hosted deployment)
- No noticeable lag on review submission

### MVP "Done Enough"
- Items can be added to the pool
- Items are browsable by all users
- Lessons work (move items into SRS rotation)
- Reviews work (correct SRS intervals, reading + meaning)

## Product Scope

### MVP
- Username-only auth
- Pre-seeded kanji database (dormant until vocab attached)
- User-created vocabulary with linked kanji and tags
- Shared pool browsing with filters
- Lesson queue and batch completion
- Reviews with WaniKani intervals (reading + meaning)
- WaniKani burned kanji import
- Personal notes/mnemonics per item

### Out of Scope (MVP)
- Radical prerequisites, password auth, analytics, gamification, mobile app, offline support, public registration

### Future Vision
- SSO integration, review statistics, radical display, polished frontend, public release

## User Journeys

### The Post-WaniKani Learner

**Profile:** All users share this profile - no variation in the friend group.
- Finished or nearly finished WaniKani (level 50+)
- Reviews multiple times daily (morning, evening, opportunistically)
- Encounters vocabulary in the wild (Twitter, games, media)
- Comfortable with self-hosted tools

**Journey:**

1. **Onboarding** - Invited directly by friend, imports WaniKani burned kanji to bootstrap progress
2. **Daily Rhythm** - Morning reviews → daytime encounters → add terms → evening reviews
3. **Contribution** - Adds vocab when encountering interesting terms, tags for discoverability
4. **Discovery** - Browses friends' additions, picks up items that look interesting
5. **Mastery** - Items burn over time, habit continues indefinitely post-WaniKani

### Journey Requirements Summary

| Journey Phase | Capabilities Required |
|---------------|----------------------|
| Onboarding | User creation, WaniKani API import |
| Daily Rhythm | Review queue, lesson queue, vocab creation |
| Contribution | Vocab form, kanji linking, tagging |
| Discovery | Pool browsing, filters (tag, creator, "not in my queue") |
| Mastery | SRS progression, burn tracking |

## API Backend Requirements

### Authentication
- Username-only login (v1) - no password, trusted users
- Session/token returned on login
- SSO integration planned for future (nullable `sso_id` field)

### API Structure
- **Base path:** `/v1/`
- **Format:** JSON request/response
- **Errors:** Standard HTTP status codes with JSON error body

### Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/auth/login` | Username login → session/token |
| GET | `/v1/kanji` | Browse kanji pool (filters: active, tag) |
| GET | `/v1/kanji/{id_or_char}` | Single kanji by ID or character |
| GET | `/v1/vocab` | Browse vocab pool (filters: tag, creator, not_in_queue) |
| GET | `/v1/vocab/{id}` | Single vocab |
| POST | `/v1/vocab` | Create vocab (auto-activates linked kanji) |
| GET | `/v1/me/queue` | User's lesson queue |
| POST | `/v1/me/queue` | Add items to lesson queue |
| DELETE | `/v1/me/queue/{item}` | Remove from queue |
| GET | `/v1/me/reviews` | Items due for review |
| POST | `/v1/me/reviews` | Submit single review |
| GET | `/v1/me/progress` | User's SRS progress |
| POST | `/v1/me/lessons` | Batch complete lessons |
| POST | `/v1/me/import/wanikani` | Import burned kanji from WK |

### Technical Constraints
- No rate limiting (trusted small user base)
- No API versioning beyond `/v1/` prefix
- No SDK - frontend consumes directly

## Functional Requirements

### Authentication & Users
- FR1: User can log in with username only (no password)
- FR2: User can store their WaniKani API key
- FR3: System maintains user session after login

### Kanji Database
- FR4: System pre-seeds kanji from external source (KANJIDIC2)
- FR5: Kanji remain dormant until vocabulary is attached
- FR6: Kanji activate automatically when linked vocab is created
- FR7: User can browse active kanji with filters (tag)
- FR8: User can view single kanji by ID or character

### Vocabulary Management
- FR9: User can create vocabulary with word, reading, meanings
- FR10: User can link vocabulary to constituent kanji
- FR11: User can add tags to vocabulary
- FR12: User can add creator comment to vocabulary
- FR13: System tracks vocabulary creator

### Shared Pool & Discovery
- FR14: User can browse all vocabulary in shared pool
- FR15: User can filter vocabulary by tag
- FR16: User can filter vocabulary by creator
- FR17: User can filter vocabulary by "not in my queue"
- FR18: User can see who created each vocabulary item

### Lesson System
- FR19: User can add items to personal lesson queue (optional "want to learn" wishlist)
- FR20: User can remove items from lesson queue
- FR21: User can complete lessons for any learnable item (single or batch) - queue membership not required
- FR22: System enforces kanji prerequisite before vocab lessons

### Review System (SRS)
- FR23: System calculates next review time using WaniKani intervals
- FR24: User can see items due for review
- FR25: User can submit review for an item (frontend validates reading + meaning, submits single result)
- FR26: Both reading and meaning must pass to advance SRS stage
- FR27: Incorrect answer drops item ~2 SRS stages
- FR28: System batches reviews by hour (not exact timestamp)
- FR29: User can resurrect burned items

### Progress & Notes
- FR30: User can view their SRS progress across all items
- FR31: User can filter progress by SRS stage
- FR32: User can add personal meaning note per item
- FR33: User can add personal reading mnemonic per item

### WaniKani Integration
- FR34: User can trigger WaniKani import
- FR35: System imports burned kanji from WaniKani API
- FR36: Imported progress is marked with source "wanikani"

## Non-Functional Requirements

### Performance
- NFR1: Review submission responds within 500ms under normal conditions
- NFR2: Pool browsing loads within 1 second

### Reliability
- NFR3: System recovers gracefully from restart (no data loss)
- NFR4: Database backups occur daily

### Integration
- NFR5: WaniKani import handles API rate limits gracefully
- NFR6: WaniKani import fails gracefully if API is unavailable

### Security
- NFR7: WaniKani API keys stored encrypted at rest
- NFR8: Sessions expire after reasonable inactivity period
