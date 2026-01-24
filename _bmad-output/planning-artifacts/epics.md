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
