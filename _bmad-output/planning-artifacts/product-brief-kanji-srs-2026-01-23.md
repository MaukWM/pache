---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments: [brainstorming-session-2026-01-23.md]
date: 2026-01-23
author: Floppa
status: complete
---

# Product Brief: Kanji SRS Platform

## Executive Summary

A self-hosted kanji learning platform that continues where WaniKani leaves off. Built for a small trusted friend group, it provides the same SRS intervals and reading/meaning review style that makes WaniKani effective, but with user-created vocabulary. When you encounter a term in the wild - Twitter slang, game terminology, character names - it finally has a home. The shared item pool turns solo grinding into a social experience where friends contribute, discover, and occasionally roast each other's additions.

---

## Core Vision

### Problem Statement

WaniKani ends. Your learning journey doesn't. After 2000+ kanji and 6000+ vocab items, dedicated learners "graduate" with no clear path to continue the daily ritual that worked so well. Meanwhile, interesting vocabulary encountered in the wild - slang, names, niche terms - has nowhere to go.

### Problem Impact

Terms get dropped and forgotten. The habit that took years to build has no continuation. Switching to general-purpose tools like Anki means losing the kanji foundation, the reading/meaning split, and the hourly SRS intervals that cement new items into memory.

### Why Existing Solutions Fall Short

| Solution | Gap |
|----------|-----|
| WaniKani | Ends. No custom content. |
| Anki | Daily-only SRS, no reading/meaning split, no kanji DB, sync friction, no social layer |
| Other apps | Too general, don't support Japanese learning patterns |

### Proposed Solution

A backend-first platform that replicates the WaniKani learning model with user-generated content:
- Identical SRS intervals (4h, 8h, 1d, 2d, 1w, 2w, 1mo, 4mo)
- Reading + meaning reviews for each item
- Pre-seeded kanji database that vocab links to
- Shared item pool where friends contribute and discover
- Self-hosted, fully controlled, fully extensible

### Key Differentiators

- **Yours**: Self-hosted, open to extend, data you own
- **Continues WaniKani**: Same intervals, same review style, imports your progress
- **Habitual Home**: One place for every term you encounter
- **Social by Default**: Shared pool, friend contributions, built-in banter potential

---

## Target Users

### Primary Users

**The Post-WaniKani Learner**

- Finished or nearly finished WaniKani (level 50+)
- Deep into Japanese learning, committed long-term
- Reviews multiple times daily: morning, evening, opportunistically throughout the day
- Encounters vocabulary in the wild (Twitter, games, media) and wants to capture it
- Part of a small trusted friend group with similar learning habits
- Comfortable with self-hosted tools

All users share this profile - no significant variation in needs or behavior within the group.

### Secondary Users

N/A - No secondary user types. All users are active learners participating in the same way.

### User Journey

1. **Onboarding**: Invited directly, imports WaniKani burned kanji to bootstrap progress
2. **Daily Rhythm**: Morning reviews → daytime encounters → add terms → evening reviews
3. **Contribution**: Adds vocab when encountering interesting terms, tags for discoverability
4. **Discovery**: Browses friends' additions, picks up items that look interesting
5. **Mastery**: Items burn over time, habit continues indefinitely post-WaniKani graduation

---

## Success Metrics

### User Success

| Metric | Target |
|--------|--------|
| Daily active use | Every day, minimum |
| Session frequency | Multiple times per day (for users with items in rotation) |
| Retention signal | Remembering items after 1+ month gap between reviews |

Learning effectiveness is assumed - users already trust the WaniKani SRS model works. Success is whether the habit forms and sticks.

### Business Objectives

N/A - Personal project for a small friend group. No revenue, growth, or market metrics.

### Key Performance Indicators

**Functional (MVP "done enough"):**
- Items can be added to the pool
- Items are browsable by all users
- Lessons work (move items into SRS rotation)
- Reviews work (correct SRS intervals, reading + meaning)

**Technical (table stakes):**
- Always up (reliable self-hosted deployment)
- Sufficiently fast (no noticeable lag on review submission)

---

## MVP Scope

### Core Features

**Backend (Primary Focus)**
- Username-only auth (trusted users, no password)
- Pre-seeded kanji database (dormant until vocab attached)
- User-created vocabulary (word, reading, meanings, linked kanji, tags)
- Shared pool browsing with filters (tag, creator, "not in my queue")
- Lesson queue (user-curated, batch completion to start SRS)
- Reviews (WaniKani intervals, reading + meaning, individual submission)
- SRS progression (Apprentice → Guru → Master → Enlightened → Burned)
- WaniKani import (burned kanji via stored API key)
- Personal notes/mnemonics per item

**Frontend (Minimal, Functional)**
- Sufficient UI to do lessons and reviews daily
- Vocab creation form
- Pool browsing
- Not polished, just usable

### Out of Scope for MVP

- Radical prerequisites (metadata only, not enforced)
- Password auth / SSO integration
- Review statistics / analytics dashboards
- Gamification / leaderboards / streaks
- Mobile app
- Offline support
- Public registration

### MVP Success Criteria

- Can add vocab and see it in shared pool
- Can do lessons (batch complete into Apprentice 1)
- Can do reviews (correct SRS timing, reading + meaning)
- Can import WaniKani burned kanji
- Usable daily via minimal frontend

### Future Vision

**Post-MVP possibilities:**
- SSO integration (replace username-only auth)
- Review statistics and progress visualization
- Radical display and optional prerequisite chains
- Polished frontend / mobile apps
- Public self-hosted release for others
