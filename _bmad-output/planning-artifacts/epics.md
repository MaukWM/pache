---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics']
inputDocuments: ['prd.md', 'architecture.md']
---

# Kanji SRS Platform - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Kanji SRS Platform, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: User can log in with username only (no password)
FR2: User can store their WaniKani API key
FR3: System maintains user session after login
FR4: System pre-seeds kanji from external source (KANJIDIC2)
FR5: Kanji remain dormant until vocabulary is attached
FR6: Kanji activate automatically when linked vocab is created
FR7: User can browse active kanji with filters (tag)
FR8: User can view single kanji by ID or character
FR9: User can create vocabulary with word, reading, meanings
FR10: User can link vocabulary to constituent kanji
FR11: User can add tags to vocabulary
FR12: User can add creator comment to vocabulary
FR13: System tracks vocabulary creator
FR14: User can browse all vocabulary in shared pool
FR15: User can filter vocabulary by tag
FR16: User can filter vocabulary by creator
FR17: User can filter vocabulary by "not in my queue"
FR18: User can see who created each vocabulary item
FR19: User can add items to personal lesson queue
FR20: User can remove items from lesson queue
FR21: User can batch-complete lessons in two modes: random batch of 5 OR self-selected items
FR22: System enforces kanji prerequisite before vocab lessons
FR23: System calculates next review time using WaniKani intervals
FR24: User can see items due for review
FR25: User can submit review for an item (frontend validates reading + meaning, submits single result)
FR26: Both reading and meaning must pass to advance SRS stage
FR27: Incorrect answer drops item ~2 SRS stages
FR28: System batches reviews by hour (not exact timestamp)
FR29: User can resurrect burned items
FR30: User can view their SRS progress across all items
FR31: User can filter progress by SRS stage
FR32: User can add personal meaning note per item
FR33: User can add personal reading mnemonic per item
FR34: User can trigger WaniKani import
FR35: System imports burned kanji from WaniKani API
FR36: Imported progress is marked with source "wanikani"

### NonFunctional Requirements

NFR1: Review submission responds within 500ms under normal conditions
NFR2: Pool browsing loads within 1 second
NFR3: System recovers gracefully from restart (no data loss)
NFR4: Database backups occur daily
NFR5: WaniKani import handles API rate limits gracefully
NFR6: WaniKani import fails gracefully if API is unavailable
NFR7: WaniKani API keys stored encrypted at rest
NFR8: Sessions expire after reasonable inactivity period

### Additional Requirements

**From Architecture - Starter/Setup:**
- Manual setup (no template) - greenfield project
- Project structure must follow architecture document exactly
- Initialize with uv package manager

**From Architecture - Tech Stack:**
- Python 3.12+, FastAPI 0.115+, Pydantic v2
- SQLAlchemy 2.0+ async with asyncmy driver
- Alembic for migrations
- MySQL 8.0+
- structlog for logging
- pytest + pytest-asyncio for testing

**From Architecture - Infrastructure:**
- Docker + Docker Compose deployment
- Pre-commit hooks: ruff, ruff-format, mypy, gitleaks
- CI workflow in .github/workflows/ci.yml

**From Architecture - Patterns:**
- Service layer pattern (thin routes, business logic in services)
- Async throughout
- Absolute imports from `src`
- Naming conventions per architecture document

**From Architecture - Data:**
- Idempotent kanji seeding script via jamdict (~13000 kanji)
- SRS intervals hardcoded per WaniKani spec
- Reviews batched by hour (truncate timestamp)
- Item type polymorphism via discriminator in UserItemProgress

**From Architecture - API:**
- URL prefix: `/api/v1/`
- Bearer token authentication header
- JSON request/response throughout

### FR Coverage Map

FR1: Epic 1 - Username-only login
FR2: Epic 1 - Store WaniKani API key
FR3: Epic 1 - Session management
FR4: Epic 2 - Pre-seed kanji from KANJIDIC2
FR5: Epic 2 - Kanji dormant until vocab attached
FR6: Epic 2 - Kanji auto-activate on vocab link
FR7: Epic 2 - Browse active kanji with filters
FR8: Epic 2 - View single kanji by ID or character
FR9: Epic 3 - Create vocabulary with word, reading, meanings
FR10: Epic 3 - Link vocabulary to constituent kanji
FR11: Epic 3 - Add tags to vocabulary
FR12: Epic 3 - Add creator comment to vocabulary
FR13: Epic 3 - Track vocabulary creator
FR14: Epic 3 - Browse all vocabulary in shared pool
FR15: Epic 3 - Filter vocabulary by tag
FR16: Epic 3 - Filter vocabulary by creator
FR17: Epic 3 - Filter vocabulary by "not in my queue"
FR18: Epic 3 - See who created each vocabulary item
FR19: Epic 4 - Add items to personal lesson queue
FR20: Epic 4 - Remove items from lesson queue
FR21: Epic 4 - Batch-complete lessons (random 5 or self-selected)
FR22: Epic 4 - Enforce kanji prerequisite before vocab lessons
FR23: Epic 5 - Calculate next review time using WaniKani intervals
FR24: Epic 5 - See items due for review
FR25: Epic 5 - Submit review for an item
FR26: Epic 5 - Both reading and meaning must pass to advance
FR27: Epic 5 - Incorrect answer drops item ~2 SRS stages
FR28: Epic 5 - Batch reviews by hour
FR29: Epic 5 - Resurrect burned items
FR30: Epic 6 - View SRS progress across all items
FR31: Epic 6 - Filter progress by SRS stage
FR32: Epic 6 - Add personal meaning note per item
FR33: Epic 6 - Add personal reading mnemonic per item
FR34: Epic 7 - Trigger WaniKani import
FR35: Epic 7 - Import burned kanji from WaniKani API
FR36: Epic 7 - Mark imported progress with source "wanikani"

## Epic List

### Epic 1: Project Foundation & User Access
Users can access and authenticate to the system. Includes all architecture setup (project structure, Docker, pre-commit, database, migrations) enabling development to begin.
**FRs covered:** FR1, FR2, FR3

### Epic 2: Kanji Database Foundation
Users can explore the pre-seeded kanji database. Implements idempotent seed script from KANJIDIC2 with dormant activation pattern.
**FRs covered:** FR4, FR5, FR6, FR7, FR8

### Epic 3: Vocabulary Creation & Shared Pool
Users can create vocabulary terms they encounter in the wild, browse friends' contributions, and build the shared knowledge pool. Auto-activates linked kanji, tracks creators, supports filtering.
**FRs covered:** FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR18

### Epic 4: Lesson System
Users can add items to their personal queue and batch-complete lessons to begin SRS rotation. Enforces kanji prerequisites, supports two lesson modes.
**FRs covered:** FR19, FR20, FR21, FR22

### Epic 5: SRS Review System
Users can complete reviews with WaniKani-style intervals, progressing items toward burn. Core SRS algorithm with hour-batched reviews and resurrection capability.
**FRs covered:** FR23, FR24, FR25, FR26, FR27, FR28, FR29

### Epic 6: Progress Tracking & Personalization
Users can view their SRS progress across all items and add personal meaning notes and reading mnemonics. Filter by SRS stage supported.
**FRs covered:** FR30, FR31, FR32, FR33

### Epic 7: WaniKani Integration
Users can import their burned kanji from WaniKani to bootstrap progress. Includes WK API client with rate limit handling and source tracking.
**FRs covered:** FR34, FR35, FR36

---

## Epic 1: Project Foundation & User Access

Users can access and authenticate to the system. Includes all architecture setup (project structure, Docker, pre-commit, database, migrations) enabling development to begin.

### Story 1.1: Project Initialization

As a **developer**,
I want **the project structure, dependencies, and tooling set up per the architecture document**,
So that **development can begin with consistent code quality and deployment capability**.

**Acceptance Criteria:**

**Given** a new project directory
**When** the project is initialized
**Then** the following structure exists per architecture document:
- `src/` with `__init__.py`, `main.py`, `settings.py`, `logging.py`, `database.py`
- `src/core/` with `__init__.py`, `exceptions.py`, `constants.py`
- `src/auth/`, `src/kanji/`, `src/vocab/`, `src/reviews/`, `src/lessons/`, `src/progress/`, `src/wanikani/` directories with `__init__.py`
- `tests/` directory structure mirroring `src/`
- `scripts/` directory
- `alembic/` directory with `env.py`

**And** `pyproject.toml` includes:
- Python 3.12+
- fastapi, sqlalchemy[asyncio], asyncmy, alembic, pydantic-settings, structlog, uvicorn
- Dev dependencies: pre-commit, pytest, pytest-asyncio, ruff, mypy, httpx

**And** `.pre-commit-config.yaml` includes ruff, ruff-format, mypy, gitleaks hooks

**And** `docker-compose.yml` defines API service and MySQL 8.0 service with persistent volume

**And** `Dockerfile` builds the FastAPI application

**And** `.env.example` documents required environment variables

**And** `src/main.py` creates a minimal FastAPI app that starts successfully

**And** `src/settings.py` uses Pydantic Settings to load configuration from environment

**And** `src/logging.py` configures structlog

---

### Story 1.2: Database Connection & Auth Models

As a **developer**,
I want **async database connectivity and the User/Session models**,
So that **authentication can be implemented in subsequent stories**.

**Acceptance Criteria:**

**Given** the project from Story 1.1
**When** database models are created
**Then** `src/database.py` provides:
- Async SQLAlchemy engine using asyncmy driver
- Async session factory
- `get_db` dependency for FastAPI

**And** `src/auth/models.py` defines:
- `User` model with columns: `id`, `username` (unique), `wk_api_key` (nullable), `created_at`
- `Session` model with columns: `id`, `user_id` (FK), `token` (unique, indexed), `created_at`

**And** Alembic is configured for async SQLAlchemy

**And** initial migration creates `users` and `sessions` tables

**And** `docker-compose up` successfully starts MySQL and runs migrations

**And** `src/core/constants.py` defines `ItemType` enum (kanji, vocab) for future use

---

### Story 1.3: User Login Endpoint

As a **user**,
I want **to log in with just my username**,
So that **I can access the system without password complexity** (trusted friend group).

**Acceptance Criteria:**

**Given** a user exists with username "floppa"
**When** POST `/api/v1/auth/login` is called with `{"username": "floppa"}`
**Then** response status is 200
**And** response body contains `{"token": "<session_token>", "user": {"id": 1, "username": "floppa"}}`
**And** a new Session record is created in the database

**Given** no user exists with username "newuser"
**When** POST `/api/v1/auth/login` is called with `{"username": "newuser"}`
**Then** a new User record is created with username "newuser"
**And** response status is 200
**And** response body contains valid token and user object

**Given** a valid session token
**When** any authenticated endpoint is called with `Authorization: Bearer <token>` header
**Then** `get_current_user` dependency returns the authenticated User

**Given** an invalid or missing token
**When** any authenticated endpoint is called
**Then** response status is 401 Unauthorized

**And** `src/auth/router.py` mounts at `/api/v1/auth`
**And** `src/auth/service.py` contains `AuthService` with login logic
**And** `src/auth/schemas.py` defines `LoginRequest`, `LoginResponse`, `UserResponse`
**And** `src/auth/dependencies.py` provides `get_current_user` dependency

---

### Story 1.4: Store WaniKani API Key

As a **user**,
I want **to store my WaniKani API key**,
So that **I can later import my burned kanji**.

**Acceptance Criteria:**

**Given** an authenticated user
**When** POST `/api/v1/me/settings` is called with `{"wk_api_key": "my-api-key"}`
**Then** response status is 200
**And** the user's `wk_api_key` field is updated in the database
**And** response confirms the key was saved (without echoing the key back)

**Given** an authenticated user with a stored WK API key
**When** GET `/api/v1/me/settings` is called
**Then** response indicates whether a WK API key is configured (boolean, not the actual key)

**Given** an unauthenticated request
**When** either settings endpoint is called
**Then** response status is 401 Unauthorized

---

## Epic 2: Kanji Database Foundation

Users can explore the pre-seeded kanji database. Implements idempotent seed script from KANJIDIC2 with dormant activation pattern.

### Story 2.1: Kanji Model & Seed Script

As a **developer**,
I want **the Kanji model and a seed script that populates kanji from KANJIDIC2**,
So that **the kanji database is ready for vocabulary linking**.

**Acceptance Criteria:**

**Given** the database from Epic 1
**When** the Kanji model is created
**Then** `src/kanji/models.py` defines a `Kanji` model with columns:
- `id` (primary key)
- `character` (single kanji character, unique, indexed)
- `meanings` (JSON array of English meanings)
- `readings_on` (JSON array of on'yomi readings)
- `readings_kun` (JSON array of kun'yomi readings)
- `grade` (nullable, school grade level)
- `jlpt_level` (nullable)
- `stroke_count`
- `active` (boolean, default False) - dormant until vocab attached
- `created_at`

**And** Alembic migration creates the `kanji` table

**Given** the seed script `scripts/seed_kanji.py`
**When** it is executed
**Then** kanji data is loaded from KANJIDIC2 (XML or pre-processed JSON)
**And** approximately 3000 kanji records are inserted
**And** all kanji are inserted with `active=False` (dormant)
**And** the script is idempotent (safe to run multiple times, skips existing records)
**And** the script can be run via `python -m scripts.seed_kanji` or similar

**And** `src/kanji/service.py` contains `KanjiService` with basic query methods
**And** `src/kanji/schemas.py` defines `KanjiResponse`

---

### Story 2.2: Browse & View Kanji Endpoints

As a **user**,
I want **to browse and view kanji in the database**,
So that **I can see which kanji are available and their details**.

**Acceptance Criteria:**

**Given** kanji have been seeded in the database
**When** GET `/api/v1/kanji` is called
**Then** response returns a list of kanji
**And** by default, only active kanji are returned (empty list initially)
**And** query param `?include_inactive=true` includes dormant kanji

**Given** a kanji with id=42 or character="日" exists
**When** GET `/api/v1/kanji/42` or GET `/api/v1/kanji/日` is called
**Then** response returns the full kanji details including meanings and readings
**And** response status is 200

**Given** no kanji matches the id or character
**When** GET `/api/v1/kanji/{id_or_char}` is called
**Then** response status is 404

**And** `src/kanji/router.py` mounts at `/api/v1/kanji`
**And** endpoints do NOT require authentication (kanji pool is public)

---

## Epic 3: Vocabulary Creation & Shared Pool

Users can create vocabulary terms they encounter in the wild, browse friends' contributions, and build the shared knowledge pool. Auto-activates linked kanji, tracks creators, supports filtering.

### Story 3.1: Vocab, Tag & Linking Models

As a **developer**,
I want **the Vocab, Tag, and linking models**,
So that **vocabulary creation and browsing can be implemented**.

**Acceptance Criteria:**

**Given** the database from Epic 2
**When** the Vocab models are created
**Then** `src/vocab/models.py` defines:

**Vocab model:**
- `id` (primary key)
- `word` (the vocabulary term, indexed)
- `reading` (hiragana/katakana reading)
- `meanings` (JSON array of English meanings)
- `creator_id` (FK to users)
- `creator_comment` (nullable text)
- `created_at`

**Tag model:**
- `id` (primary key)
- `name` (unique, indexed)

**VocabTag junction table:**
- `vocab_id` (FK)
- `tag_id` (FK)
- Composite primary key

**VocabKanji junction table:**
- `vocab_id` (FK)
- `kanji_id` (FK)
- Composite primary key

**And** Alembic migration creates `vocab`, `tags`, `vocab_tags`, `vocab_kanji` tables
**And** `src/vocab/schemas.py` defines `VocabCreateRequest`, `VocabResponse`, `TagResponse`

---

### Story 3.2: Create Vocabulary

As a **user**,
I want **to create vocabulary with kanji links and tags**,
So that **I can add terms I encounter to the shared pool**.

**Acceptance Criteria:**

**Given** an authenticated user
**When** POST `/api/v1/vocab` is called with:
```json
{
  "word": "日本語",
  "reading": "にほんご",
  "meanings": ["Japanese language"],
  "kanji_ids": [42, 55, 78],
  "tags": ["language", "N5"],
  "creator_comment": "Found in my textbook"
}
```
**Then** response status is 201
**And** a new Vocab record is created with creator_id set to current user
**And** VocabKanji links are created for each kanji_id
**And** Tags are created if they don't exist, VocabTag links are created
**And** linked kanji are set to `active=True` (FR6 - auto-activation)
**And** response includes the created vocab with all details

**Given** kanji_ids contains an invalid kanji id
**When** POST `/api/v1/vocab` is called
**Then** response status is 400 with error message

**Given** an unauthenticated request
**When** POST `/api/v1/vocab` is called
**Then** response status is 401 Unauthorized

**And** `src/vocab/router.py` mounts at `/api/v1/vocab`
**And** `src/vocab/service.py` contains `VocabService` with creation logic
**And** kanji activation is handled within the create transaction

---

### Story 3.3: Browse & Filter Vocabulary

As a **user**,
I want **to browse the shared vocabulary pool with filters**,
So that **I can discover interesting terms added by friends**.

**Acceptance Criteria:**

**Given** vocabulary exists in the database
**When** GET `/api/v1/vocab` is called
**Then** response returns a list of all vocabulary
**And** each vocab item includes creator username (FR18)
**And** each vocab item includes linked kanji characters
**And** each vocab item includes tags

**Given** vocabulary with tag "slang" exists
**When** GET `/api/v1/vocab?tag=slang` is called
**Then** response returns only vocabulary with that tag

**Given** vocabulary created by user "floppa" exists
**When** GET `/api/v1/vocab?creator=floppa` is called
**Then** response returns only vocabulary created by that user

**Given** multiple filters are provided
**When** GET `/api/v1/vocab?tag=slang&creator=floppa` is called
**Then** response returns vocabulary matching ALL filters (AND logic)

**Given** a vocab with id=123 exists
**When** GET `/api/v1/vocab/123` is called
**Then** response returns full vocab details including meanings, readings, kanji, tags, creator

**Given** no vocab with that id exists
**When** GET `/api/v1/vocab/999` is called
**Then** response status is 404

**And** browse endpoint does NOT require authentication (pool is shared/public)
**And** FR17 (not_in_queue filter) will be added in Epic 4 when LessonQueue exists

---

## Epic 4: Lesson System

Users can add items to their personal queue and batch-complete lessons to begin SRS rotation. Enforces kanji prerequisites, supports two lesson modes.

### Story 4.1: Lesson Queue Model & Add Items to Queue

As a **user**,
I want **to add vocabulary and kanji items to my personal lesson queue**,
So that **I can prepare them for batch lesson completion**.

**Acceptance Criteria:**

**Given** the database from Epic 3
**When** the Lesson Queue models are created
**Then** `src/progress/models.py` defines:

**LessonQueue model:**
- `id` (primary key)
- `user_id` (FK to users, indexed)
- `item_type` (enum: kanji | vocab)
- `item_id` (FK to kanji or vocab, depending on item_type)
- `added_at` (timestamp)
- Composite unique constraint on `(user_id, item_type, item_id)` to prevent duplicates

**And** Alembic migration creates `lesson_queue` table
**And** `src/progress/schemas.py` defines `QueueItemRequest`, `QueueItemResponse`, `QueueListResponse`

**Given** an authenticated user
**When** POST `/api/v1/me/queue` is called with:
```json
{
  "item_type": "vocab",
  "item_id": 123
}
```
**Then** response status is 201
**And** a new LessonQueue record is created for the current user
**And** response includes the queued item details

**Given** an authenticated user with vocab id=123 already in their queue
**When** POST `/api/v1/me/queue` is called with the same item
**Then** response status is 409 Conflict with error message indicating item already in queue

**Given** an authenticated user
**When** POST `/api/v1/me/queue` is called with invalid item_id (e.g., vocab id=99999 doesn't exist)
**Then** response status is 400 with error message indicating item not found

**Given** an authenticated user
**When** GET `/api/v1/me/queue` is called
**Then** response status is 200
**And** response returns a list of all items in the user's lesson queue
**And** each item includes item_type, item_id, and item details (kanji character or vocab word)

**Given** an unauthenticated request
**When** POST `/api/v1/me/queue` or GET `/api/v1/me/queue` is called
**Then** response status is 401 Unauthorized

**And** `src/progress/router.py` mounts queue endpoints at `/api/v1/me/queue`
**And** `src/progress/service.py` contains `ProgressService` with queue management logic

---

### Story 4.2: Remove Items from Lesson Queue

As a **user**,
I want **to remove items from my lesson queue**,
So that **I can manage which items I want to learn**.

**Acceptance Criteria:**

**Given** an authenticated user with items in their lesson queue
**When** DELETE `/api/v1/me/queue/{item_type}/{item_id}` is called (e.g., `/api/v1/me/queue/vocab/123`)
**Then** response status is 204 No Content
**And** the LessonQueue record is removed from the database

**Given** an authenticated user
**When** DELETE `/api/v1/me/queue/vocab/999` is called for an item not in their queue
**Then** response status is 404 Not Found

**Given** an authenticated user
**When** DELETE `/api/v1/me/queue/invalid_type/123` is called with invalid item_type
**Then** response status is 400 Bad Request with error message

**Given** an unauthenticated request
**When** DELETE `/api/v1/me/queue/{item_type}/{item_id}` is called
**Then** response status is 401 Unauthorized

**And** delete endpoint requires authentication
**And** users can only delete items from their own queue

---

### Story 4.3: Batch Complete Lessons with Prerequisite Enforcement

As a **user**,
I want **to batch-complete lessons from my queue in two modes: random batch of 5 OR self-selected items**,
So that **I can efficiently move items into SRS rotation while respecting kanji prerequisites**.

**Acceptance Criteria:**

**Given** the database from Story 4.1
**When** the UserItemProgress model is created
**Then** `src/progress/models.py` defines:

**UserItemProgress model:**
- `id` (primary key)
- `user_id` (FK to users, indexed)
- `item_type` (enum: kanji | vocab, discriminator)
- `item_id` (FK to kanji or vocab)
- `srs_stage` (integer, 0-9: 0=lesson, 1-4=apprentice, 5-6=guru, 7=master, 8=enlightened, 9=burned)
- `next_review_at` (nullable datetime, set when item enters SRS)
- `unlocked_at` (datetime, when lesson was completed)
- `burned_at` (nullable datetime)
- `meaning_note` (nullable text, user's custom explanation)
- `reading_mnemonic` (nullable text, user's custom mnemonic)
- `source` (enum: manual | wanikani, default: manual)
- Composite unique constraint on `(user_id, item_type, item_id)`

**And** Alembic migration creates `user_item_progress` table
**And** `src/progress/schemas.py` defines `LessonCompleteRequest`, `LessonCompleteResponse`

**Given** an authenticated user with items in their lesson queue
**When** POST `/api/v1/me/lessons` is called with:
```json
{
  "mode": "random",
  "count": 5
}
```
**Then** response status is 200
**And** up to 5 random items are selected from the user's queue
**And** for each selected item:
  - A UserItemProgress record is created with `srs_stage=0` (lesson stage)
  - `unlocked_at` is set to current timestamp
  - `next_review_at` is calculated using WaniKani intervals (will be implemented in Epic 5)
  - The item is removed from LessonQueue
**And** response includes list of completed lesson items

**Given** an authenticated user with items in their lesson queue
**When** POST `/api/v1/me/lessons` is called with:
```json
{
  "mode": "selected",
  "item_ids": [
    {"item_type": "kanji", "item_id": 42},
    {"item_type": "vocab", "item_id": 123}
  ]
}
```
**Then** response status is 200
**And** UserItemProgress records are created for each specified item
**And** specified items are removed from LessonQueue
**And** response includes list of completed lesson items

**Given** an authenticated user attempting to lesson a vocab item
**When** the vocab item has constituent kanji that are NOT in the user's UserItemProgress (not learned)
**Then** response status is 400 Bad Request
**And** error message indicates which kanji prerequisites are missing (FR22 - prerequisite enforcement)
**And** the vocab item remains in the lesson queue

**Given** an authenticated user attempting to lesson a vocab item
**When** all constituent kanji are in the user's UserItemProgress with `srs_stage >= 1` (learned)
**Then** the vocab lesson completes successfully
**And** UserItemProgress record is created for the vocab item

**Given** an authenticated user with fewer than 5 items in queue
**When** POST `/api/v1/me/lessons` is called with `mode: "random", count: 5`
**Then** response status is 200
**And** all available items are processed (less than 5)
**And** response indicates actual count processed

**Given** an authenticated user
**When** POST `/api/v1/me/lessons` is called with invalid mode (not "random" or "selected")
**Then** response status is 400 Bad Request with error message

**Given** an authenticated user
**When** POST `/api/v1/me/lessons` is called with `mode: "selected"` and item_ids containing items not in their queue
**Then** response status is 400 Bad Request
**And** error message indicates which items are not in queue

**Given** an authenticated user attempting to lesson an item already in UserItemProgress
**When** POST `/api/v1/me/lessons` is called with that item
**Then** response status is 400 Bad Request
**And** error message indicates item already learned

**Given** an unauthenticated request
**When** POST `/api/v1/me/lessons` is called
**Then** response status is 401 Unauthorized

**And** `src/lessons/router.py` mounts at `/api/v1/me/lessons`
**And** `src/lessons/service.py` contains `LessonService` with batch completion and prerequisite checking logic
**And** prerequisite checking queries UserItemProgress to verify all constituent kanji are learned before allowing vocab lessons

---

## Epic 5: SRS Review System

Users can complete reviews with WaniKani-style intervals, progressing items toward burn. Core SRS algorithm with hour-batched reviews and resurrection capability.

### Story 5.1: SRS Core Logic & Review Log Model

As a **developer**,
I want **the SRS interval calculation logic and ReviewLog model**,
So that **review submissions can calculate next review times and track review history**.

**Acceptance Criteria:**

**Given** the database from Epic 4
**When** the SRS core logic is created
**Then** `src/core/constants.py` defines:
- `SRS_INTERVALS` dictionary mapping stage transitions to timedelta intervals:
  - Stage 1→2: 4 hours
  - Stage 2→3: 8 hours
  - Stage 3→4: 1 day
  - Stage 4→5: 2 days
  - Stage 5→6: 1 week
  - Stage 6→7: 2 weeks
  - Stage 7→8: 30 days
  - Stage 8→9: 120 days

**And** `src/reviews/srs.py` provides:
- `calculate_next_review(current_stage: int, correct: bool) -> tuple[int, datetime]` function
- When `correct=True`: advances to next stage, calculates `next_review_at` using SRS_INTERVALS
- When `correct=False`: drops ~2 stages (minimum stage 1), recalculates `next_review_at`
- Handles stage 9 (burned) - cannot advance further
- Returns (new_stage, next_review_at) tuple

**When** the ReviewLog model is created
**Then** `src/reviews/models.py` defines:

**ReviewLog model:**
- `id` (primary key)
- `user_id` (FK to users, indexed)
- `item_type` (enum: kanji | vocab)
- `item_id` (FK to kanji or vocab)
- `review_type` (enum: reading | meaning)
- `correct` (boolean)
- `srs_stage_before` (integer, stage before review)
- `srs_stage_after` (integer, stage after review)
- `reviewed_at` (datetime, indexed for querying)

**And** Alembic migration creates `review_log` table
**And** `src/reviews/schemas.py` defines `ReviewCreateRequest`, `ReviewResponse`, `ReviewLogResponse`

**And** `src/core/constants.py` defines `ItemType` enum (kanji, vocab) and `ReviewType` enum (reading, meaning)

---

### Story 5.2: View Items Due for Review

As a **user**,
I want **to see items that are due for review**,
So that **I know what to study next**.

**Acceptance Criteria:**

**Given** an authenticated user with items in UserItemProgress
**When** GET `/api/v1/me/reviews` is called
**Then** response status is 200
**And** response returns a list of items where `next_review_at <= current_time` (batched by hour - FR28)
**And** query truncates `next_review_at` to hour precision for comparison (not exact timestamp)
**And** only items with `srs_stage >= 1` are returned (excludes lesson stage 0)
**And** each item includes:
  - `item_type`, `item_id`
  - `srs_stage`
  - `next_review_at`
  - Item details (kanji character or vocab word/reading/meanings)

**Given** an authenticated user with no items due
**When** GET `/api/v1/me/reviews` is called
**Then** response status is 200
**And** response returns empty list `[]`

**Given** an authenticated user
**When** GET `/api/v1/me/reviews?limit=10` is called with optional limit parameter
**Then** response returns at most 10 items

**Given** an unauthenticated request
**When** GET `/api/v1/me/reviews` is called
**Then** response status is 401 Unauthorized

**And** `src/reviews/router.py` mounts at `/api/v1/me/reviews`
**And** `src/reviews/service.py` contains `ReviewService` with `get_due_reviews` method
**And** hour-batching logic truncates timestamps to hour precision before comparison

---

### Story 5.3: Submit Review with Stage Progression

As a **user**,
I want **to submit review results for an item**,
So that **items progress through SRS stages based on my performance**.

**Acceptance Criteria:**

**Given** an authenticated user with an item in UserItemProgress at stage 3
**When** POST `/api/v1/me/reviews` is called with:
```json
{
  "item_type": "vocab",
  "item_id": 123,
  "review_type": "reading",
  "correct": true
}
```
**Then** response status is 200
**And** a ReviewLog record is created with review details
**And** UserItemProgress is NOT updated yet (waiting for both reading and meaning - FR26)

**Given** the same user submits the meaning review for the same item
**When** POST `/api/v1/me/reviews` is called with:
```json
{
  "item_type": "vocab",
  "item_id": 123,
  "review_type": "meaning",
  "correct": true
}
```
**Then** response status is 200
**And** a ReviewLog record is created for the meaning review
**And** UserItemProgress is updated:
  - `srs_stage` advances from 3 to 4 (both reading and meaning passed - FR26)
  - `next_review_at` is calculated using SRS_INTERVALS[3] = 1 day from now (FR23)
  - Both reading and meaning ReviewLog records exist for this review cycle

**Given** an authenticated user submits a review with `correct: false`
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 200
**And** ReviewLog record is created
**And** if both reading and meaning have been submitted (regardless of correctness):
  - UserItemProgress `srs_stage` drops ~2 stages (minimum stage 1) (FR27)
  - `next_review_at` is recalculated based on new stage
  - If only one review type submitted, stage doesn't change yet

**Given** an authenticated user submits reading review with `correct: false`
**When** meaning review is then submitted with `correct: true`
**Then** UserItemProgress stage still drops (because reading failed - FR26: both must pass)

**Given** an authenticated user submits review for item not in their UserItemProgress
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 400 Bad Request with error message

**Given** an authenticated user submits review for item at stage 9 (burned)
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 400 Bad Request with error indicating item is burned

**Given** an authenticated user submits review with invalid `review_type` (not "reading" or "meaning")
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 400 Bad Request with validation error

**Given** an unauthenticated request
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 401 Unauthorized

**And** `src/reviews/service.py` contains `submit_review` method with:
  - ReviewLog creation logic
  - Stage progression logic (only when both reading and meaning submitted)
  - SRS interval calculation using `src/reviews/srs.py`
  - Transaction handling to ensure data consistency

**And** response time for review submission is under 500ms under normal conditions (NFR1)

---

### Story 5.4: Resurrect Burned Items

As a **user**,
I want **to resurrect burned items**,
So that **I can review items I've forgotten**.

**Acceptance Criteria:**

**Given** an authenticated user with an item at stage 9 (burned) in UserItemProgress
**When** POST `/api/v1/me/progress/{item_type}/{item_id}/resurrect` is called
**Then** response status is 200
**And** UserItemProgress is updated:
  - `srs_stage` is reset to 1 (Apprentice 1)
  - `burned_at` is set to NULL
  - `next_review_at` is recalculated based on stage 1 (4 hours from now)
  - `unlocked_at` remains unchanged

**Given** an authenticated user with an item not at stage 9
**When** POST `/api/v1/me/progress/{item_type}/{item_id}/resurrect` is called
**Then** response status is 400 Bad Request with error indicating item is not burned

**Given** an authenticated user attempting to resurrect an item not in their UserItemProgress
**When** POST `/api/v1/me/progress/{item_type}/{item_id}/resurrect` is called
**Then** response status is 404 Not Found

**Given** an unauthenticated request
**When** POST `/api/v1/me/progress/{item_type}/{item_id}/resurrect` is called
**Then** response status is 401 Unauthorized

**And** resurrection endpoint is added to `src/progress/router.py`
**And** `src/progress/service.py` contains `resurrect_item` method
**And** resurrection creates a ReviewLog entry indicating the resurrection action

---

## Epic 6: Progress Tracking & Personalization

Users can view their SRS progress across all items and add personal meaning notes and reading mnemonics. Filter by SRS stage supported.

### Story 6.1: View SRS Progress with Filtering

As a **user**,
I want **to view my SRS progress across all items with filtering**,
So that **I can track my learning journey and see items at different stages**.

**Acceptance Criteria:**

**Given** an authenticated user with items in UserItemProgress
**When** GET `/api/v1/me/progress` is called
**Then** response status is 200
**And** response returns a list of all UserItemProgress records for the current user
**And** each item includes:
  - `item_type`, `item_id`
  - `srs_stage`
  - `next_review_at`
  - `unlocked_at`
  - `burned_at` (if burned)
  - `meaning_note`, `reading_mnemonic` (if set)
  - `source` (manual | wanikani)
  - Item details (kanji character or vocab word/reading/meanings)

**Given** an authenticated user
**When** GET `/api/v1/me/progress?srs_stage=5` is called with srs_stage filter
**Then** response returns only items at stage 5 (Guru 1) (FR31)

**Given** an authenticated user
**When** GET `/api/v1/me/progress?srs_stage=9` is called
**Then** response returns only burned items

**Given** an authenticated user
**When** GET `/api/v1/me/progress?item_type=kanji` is called with item_type filter
**Then** response returns only kanji items

**Given** an authenticated user
**When** GET `/api/v1/me/progress?srs_stage=5&item_type=vocab` is called with multiple filters
**Then** response returns items matching ALL filters (AND logic)

**Given** an authenticated user with no progress items
**When** GET `/api/v1/me/progress` is called
**Then** response status is 200
**And** response returns empty list `[]`

**Given** an unauthenticated request
**When** GET `/api/v1/me/progress` is called
**Then** response status is 401 Unauthorized

**And** `src/progress/router.py` mounts progress endpoints at `/api/v1/me/progress`
**And** `src/progress/service.py` contains `get_user_progress` method with filtering logic
**And** `src/progress/schemas.py` defines `ProgressResponse`, `ProgressListResponse` with filtering query params

---

### Story 6.2: Add Personal Notes and Mnemonics

As a **user**,
I want **to add personal meaning notes and reading mnemonics to items**,
So that **I can personalize my learning experience**.

**Acceptance Criteria:**

**Given** an authenticated user with an item in UserItemProgress
**When** PATCH `/api/v1/me/progress/{item_type}/{item_id}` is called with:
```json
{
  "meaning_note": "My custom explanation for this item"
}
```
**Then** response status is 200
**And** UserItemProgress `meaning_note` field is updated (FR32)
**And** response includes updated progress item

**Given** an authenticated user with an item in UserItemProgress
**When** PATCH `/api/v1/me/progress/{item_type}/{item_id}` is called with:
```json
{
  "reading_mnemonic": "My custom mnemonic for remembering the reading"
}
```
**Then** response status is 200
**And** UserItemProgress `reading_mnemonic` field is updated (FR33)
**And** response includes updated progress item

**Given** an authenticated user
**When** PATCH `/api/v1/me/progress/{item_type}/{item_id}` is called with both fields:
```json
{
  "meaning_note": "Custom note",
  "reading_mnemonic": "Custom mnemonic"
}
```
**Then** response status is 200
**And** both fields are updated

**Given** an authenticated user
**When** PATCH `/api/v1/me/progress/{item_type}/{item_id}` is called with empty string:
```json
{
  "meaning_note": ""
}
```
**Then** response status is 200
**And** `meaning_note` is set to NULL (clearing the note)

**Given** an authenticated user attempting to update an item not in their UserItemProgress
**When** PATCH `/api/v1/me/progress/{item_type}/{item_id}` is called
**Then** response status is 404 Not Found

**Given** an authenticated user
**When** PATCH `/api/v1/me/progress/{item_type}/{item_id}` is called with invalid fields (not meaning_note or reading_mnemonic)
**Then** response status is 400 Bad Request with validation error

**Given** an unauthenticated request
**When** PATCH `/api/v1/me/progress/{item_type}/{item_id}` is called
**Then** response status is 401 Unauthorized

**And** update endpoint is added to `src/progress/router.py`
**And** `src/progress/service.py` contains `update_progress_item` method
**And** `src/progress/schemas.py` defines `ProgressUpdateRequest` with optional `meaning_note` and `reading_mnemonic` fields

---

## Epic 7: WaniKani Integration

Users can import their burned kanji from WaniKani to bootstrap progress. Includes WK API client with rate limit handling and source tracking.

### Story 7.1: WaniKani API Client & Import Endpoint

As a **user**,
I want **to import my burned kanji from WaniKani**,
So that **I can bootstrap my progress with items I've already mastered**.

**Acceptance Criteria:**

**Given** the database from Epic 1
**When** the WaniKani API client is created
**Then** `src/wanikani/service.py` contains `WaniKaniService` with:
- `__init__` method accepting API key
- `get_burned_kanji()` method that calls WaniKani API `/subjects?types=kanji&hidden=true`
- Rate limit handling: respects `RateLimit-Remaining` header, waits when needed (NFR5)
- Error handling for API failures (NFR6): returns graceful error if API unavailable

**And** `src/wanikani/schemas.py` defines `WaniKaniImportRequest`, `WaniKaniImportResponse`, `BurnedKanjiItem`

**Given** an authenticated user with a stored WaniKani API key
**When** POST `/api/v1/me/import/wanikani` is called
**Then** response status is 200
**And** WaniKaniService fetches burned kanji from WaniKani API
**And** for each burned kanji:
  - Kanji character is matched to existing Kanji in database (by character)
  - If kanji exists, UserItemProgress record is created/updated:
    - `item_type` = "kanji"
    - `item_id` = matched kanji id
    - `srs_stage` = 9 (burned)
    - `burned_at` = current timestamp
    - `source` = "wanikani" (FR36)
    - `unlocked_at` = current timestamp
    - `next_review_at` = NULL (burned items don't have reviews)
  - If kanji doesn't exist in database, it is skipped (logged but not imported)

**Given** an authenticated user without a stored WaniKani API key
**When** POST `/api/v1/me/import/wanikani` is called
**Then** response status is 400 Bad Request with error indicating API key not configured

**Given** an authenticated user with invalid WaniKani API key
**When** POST `/api/v1/me/import/wanikani` is called
**Then** response status is 401 Unauthorized (WaniKani API rejects the key)
**And** error message indicates invalid API key

**Given** WaniKani API is unavailable (network error, timeout)
**When** POST `/api/v1/me/import/wanikani` is called
**Then** response status is 502 Bad Gateway or 503 Service Unavailable
**And** error message indicates WaniKani API is unavailable (NFR6)

**Given** WaniKani API returns rate limit exceeded
**When** POST `/api/v1/me/import/wanikani` is called
**Then** service waits appropriately and retries, or returns 429 Too Many Requests with retry-after header (NFR5)

**Given** an authenticated user imports kanji that already exists in their UserItemProgress
**When** POST `/api/v1/me/import/wanikani` is called
**Then** existing UserItemProgress record is updated (not duplicated)
**And** `source` field is updated to "wanikani" if it was "manual"
**And** `srs_stage` is set to 9 (burned) if not already burned

**Given** an authenticated user
**When** POST `/api/v1/me/import/wanikani` is called successfully
**Then** response includes:
  - `imported_count` (number of kanji imported)
  - `skipped_count` (number of kanji not found in database)
  - `total_burned` (total burned kanji from WaniKani)

**Given** an unauthenticated request
**When** POST `/api/v1/me/import/wanikani` is called
**Then** response status is 401 Unauthorized

**And** `src/wanikani/router.py` mounts at `/api/v1/me/import/wanikani`
**And** `src/wanikani/service.py` uses `httpx` or similar for HTTP requests
**And** import process is idempotent (safe to run multiple times)
**And** WaniKani API key is retrieved from User model `wk_api_key` field (stored in Epic 1 Story 1.4)
