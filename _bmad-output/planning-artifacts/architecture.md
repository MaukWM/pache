---
stepsCompleted: ['step-01-init', 'step-02-context', 'step-03-starter', 'step-04-decisions', 'step-05-patterns', 'step-06-structure', 'step-07-validation', 'step-08-complete']
inputDocuments: ['prd.md', 'brainstorming-session-2026-01-23.md', 'product-brief-kanji-srs-2026-01-23.md']
workflowType: 'architecture'
project_name: 'Kanji SRS Platform'
user_name: 'Floppa'
date: '2026-01-23'
completedAt: '2026-01-23'
status: complete
---

# Architecture Decision Document - Kanji SRS Platform

**Author:** Floppa
**Date:** 2026-01-23

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (36 total):**
- Authentication & Users: 3 FRs (username-only auth, session management)
- Kanji Database: 5 FRs (pre-seeded, dormant activation pattern)
- Vocabulary Management: 5 FRs (CRUD with relationships, creator tracking)
- Shared Pool & Discovery: 5 FRs (filtering, browsing)
- Lesson System: 4 FRs (queue management, prerequisite enforcement)
- Review System (SRS): 7 FRs (core algorithm, intervals, stage transitions)
- Progress & Notes: 4 FRs (user-specific data)
- WaniKani Integration: 3 FRs (external API import)

**Non-Functional Requirements (8 total):**
- Performance: 500ms review submission, 1s pool browsing
- Reliability: Graceful restart recovery, daily backups
- Integration: WaniKani API rate limit handling, graceful degradation
- Security: Encrypted API key storage, session expiry

### Scale & Complexity

- **Complexity Level:** Low
- **Primary Domain:** API Backend (FastAPI + MySQL)
- **User Scale:** ~5 trusted users
- **Data Volume:** ~3000 pre-seeded kanji + user-generated vocabulary
- **Real-time Requirements:** None
- **Compliance Requirements:** None

### Technical Constraints & Dependencies

| Constraint | Impact |
|------------|--------|
| WaniKani SRS intervals must be replicated exactly | Hardcoded interval configuration |
| Reviews batched by hour, not exact timestamp | Query logic truncates to hour |
| Kanji pre-seeded via jamdict | Idempotent seed script using jamdict API, ~13000 kanji, runs on deployment |
| Self-hosted deployment | Docker-based, simple operations |
| Username-only auth (trusted users) | No password hashing, simple session tokens |
| MySQL preferred | User familiarity, SQLAlchemy abstracts differences |

### Cross-Cutting Concerns

1. **Item Type Polymorphism** - Kanji and Vocab share SRS mechanics but have different structures; UserItemProgress uses item_type discriminator
2. **User Context** - Nearly all endpoints require authenticated user context for progress/queue operations
3. **Prerequisite Resolution** - Vocab lessons blocked until constituent kanji learned; requires dependency checking
4. **Dormant Activation** - Kanji remain inactive until vocabulary links to them; state transition on vocab creation

## Starter Template Evaluation

### Primary Technology Domain

API Backend - Python/FastAPI with MySQL database

### Starter Options Considered

| Option | Verdict |
|--------|---------|
| Official Full-Stack FastAPI Template | Overkill - includes React frontend, PostgreSQL-focused, too much to strip out |
| Tobi-De/cookiecutter-fastapi | Django-inspired but still PostgreSQL-focused, opinionated |
| **Manual Setup** | **Selected** - Clean slate, MySQL from start, tailored to project domain |

### Selected Approach: Manual Setup

**Rationale:**
- Project scope is well-defined and small
- MySQL preference (not PostgreSQL)
- Backend-only focus (frontend plugged on later)
- No need to strip out unwanted boilerplate
- Structure tailored to SRS domain (kanji, vocab, reviews)

### Technology Stack

| Component | Choice | Version |
|-----------|--------|---------|
| Language | Python | 3.12+ |
| Package Manager | uv | Latest |
| Framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ (async support) |
| Validation | Pydantic | v2 (bundled with FastAPI) |
| Migrations | Alembic | Latest |
| Database | MySQL | 8.0+ |
| Japanese Data | jamdict + jamdict-data | Latest |

### What This Decision Establishes

- No cookiecutter or template generator used
- Project structure will be defined in Architecture Decisions step
- All tooling choices (linting, pre-commit, etc.) to be specified explicitly
- MySQL-native from the start, no PostgreSQL assumptions

## Core Architectural Decisions

### Data Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SQLAlchemy Pattern | Async with `asyncmy` driver | FastAPI is async-native, modern approach |
| Model Strategy | Separate SQLAlchemy models + Pydantic schemas | Clearer separation, better for learning |
| Schema Naming | `{Entity}{Action}Request` / `{Entity}Response` | Clear intent: `VocabCreateRequest`, `VocabResponse` |

### Authentication & Security

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auth Strategy | Session tokens in DB | Simple, sufficient for 5 trusted users |
| Session Lifetime | Long-lived (no auto-expiry) | Users stay logged in until explicit logout |
| Token Delivery | Header: `Authorization: Bearer <token>` | API-first, frontend stores token |
| WK API Key Storage | Plaintext | Trusted environment, encryption is overkill |

### API & Communication

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Error Handling | FastAPI default (`HTTPException`) | Simple, standard, no custom wrappers |
| Pagination | None (MVP) | Small dataset, revisit if needed |
| URL Prefix | `/api/v1/` | Cheap versioning insurance |

### Frontend Architecture

Deferred - frontend to be "plugged on later" per product brief.

### Infrastructure & Deployment

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Linting/Formatting | Ruff | Fast, replaces black+isort+flake8 |
| Type Checking | mypy | Static analysis, catches bugs early |
| Pre-commit | Full stack (see config below) | Consistent code quality |
| Containerization | Docker + Docker Compose | Flexible: API-only or full stack |
| Testing | pytest | Industry standard |

**Pre-commit Configuration:**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-ast
      - id: mixed-line-ending

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
```

**Deployment Options:**

1. **Full Compose:** `docker-compose up` - spins up API + MySQL with persistent volume
2. **API-only:** Build Dockerfile, connect to existing MySQL on host

## Implementation Patterns & Consistency Rules

### Naming Conventions

**Database:**

| Element | Convention | Example |
|---------|------------|---------|
| Tables | snake_case, plural | `users`, `vocab_items`, `review_logs` |
| Columns | snake_case | `user_id`, `created_at`, `srs_stage` |
| Foreign Keys | `{referenced_table}_id` | `user_id`, `kanji_id` |
| Indexes | `ix_{table}_{column}` | `ix_users_username` |

**API:**

| Element | Convention | Example |
|---------|------------|---------|
| Endpoints | Plural nouns, lowercase | `/api/v1/vocab`, `/api/v1/kanji` |
| Path params | `{snake_case}` | `/api/v1/vocab/{vocab_id}` |
| Query params | snake_case | `?created_by=123&not_in_queue=true` |
| JSON fields | snake_case | `{"srs_stage": 3, "next_review_at": "..."}` |

**Code (PEP 8):**

| Element | Convention | Example |
|---------|------------|---------|
| Files | snake_case.py | `review_service.py`, `vocab_schemas.py` |
| Classes | PascalCase | `VocabCreateRequest`, `ReviewService` |
| Functions/Methods | snake_case | `get_user_reviews()`, `calculate_next_review()` |
| Constants | SCREAMING_SNAKE_CASE | `SRS_INTERVALS`, `MAX_LESSONS_PER_BATCH` |
| Variables | snake_case | `current_user`, `review_count` |

### Structure Conventions

**Test Organization:** Separate `tests/` folder mirroring `src/` structure

```
tests/
├── auth/
│   └── test_service.py
├── reviews/
│   └── test_service.py
└── conftest.py
```

**Import Style:** Absolute imports from `src`

```python
# Good
from src.auth.service import AuthService
from src.reviews.schemas import ReviewCreateRequest

# Avoid
from .service import AuthService
```

### Format Conventions

| Format | Convention |
|--------|------------|
| Dates in API | ISO 8601 UTC: `"2026-01-23T14:30:00Z"` |
| Dates in DB | DATETIME columns, stored as UTC |
| Booleans | JSON native `true`/`false` |
| Nulls | Explicit `null` for absent optional fields |

### Service Layer Pattern

Business logic lives in service classes, routes stay thin:

```python
# src/reviews/service.py
class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit_review(self, user_id: int, request: ReviewCreateRequest) -> ReviewResponse:
        # All business logic here
        ...

# src/reviews/router.py
@router.post("/reviews")
async def submit_review(
    request: ReviewCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReviewService(db)
    return await service.submit_review(current_user.id, request)
```

### Logging Pattern

Structured logging with structlog:

```python
# src/logging.py
import structlog

logger = structlog.get_logger()

# Usage anywhere:
from src.logging import logger

logger.info("review_submitted", user_id=123, item_id=456, srs_stage=3)
logger.debug("srs_calculation", current_stage=2, correct=True, new_stage=3)
logger.error("wanikani_import_failed", user_id=123, error="rate_limited")
```

| Level | Usage |
|-------|-------|
| DEBUG | Detailed debugging (SQL, calculations) |
| INFO | Normal operations (login, review submitted) |
| WARNING | Unexpected but handled (slow external API) |
| ERROR | Failures requiring attention |

### Enforcement

**All code must:**

- Pass ruff linting and formatting
- Pass mypy type checking
- Follow naming conventions above
- Use service layer for business logic
- Use absolute imports from `src`

## Project Structure & Boundaries

### Complete Project Directory Structure

```
kanji-srs/
├── .github/
│   └── workflows/
│       └── ci.yml
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── scripts/
│   └── seed_kanji.py              # Idempotent kanji seeding via jamdict
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry, lifespan, router mounting
│   ├── settings.py                # Pydantic Settings (env vars)
│   ├── logging.py                 # structlog setup
│   ├── database.py                # Async engine, session factory, get_db dependency
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── router.py              # POST /auth/login
│   │   ├── service.py             # AuthService (login, session management)
│   │   ├── schemas.py             # LoginRequest, LoginResponse, etc.
│   │   ├── models.py              # User, Session SQLAlchemy models
│   │   └── dependencies.py        # get_current_user dependency
│   │
│   ├── kanji/
│   │   ├── __init__.py
│   │   ├── router.py              # GET /kanji, GET /kanji/{id_or_char}
│   │   ├── service.py             # KanjiService
│   │   ├── schemas.py             # KanjiResponse, KanjiListResponse
│   │   └── models.py              # Kanji SQLAlchemy model
│   │
│   ├── vocab/
│   │   ├── __init__.py
│   │   ├── router.py              # GET/POST /vocab, GET /vocab/{id}
│   │   ├── service.py             # VocabService (create, browse, filter)
│   │   ├── schemas.py             # VocabCreateRequest, VocabResponse, etc.
│   │   └── models.py              # Vocab, Tag, VocabTag models
│   │
│   ├── reviews/
│   │   ├── __init__.py
│   │   ├── router.py              # GET /me/reviews, POST /me/reviews
│   │   ├── service.py             # ReviewService (SRS logic lives here)
│   │   ├── schemas.py             # ReviewCreateRequest, ReviewResponse
│   │   ├── models.py              # ReviewLog model
│   │   └── srs.py                 # SRS interval calculations, stage logic
│   │
│   ├── lessons/
│   │   ├── __init__.py
│   │   ├── router.py              # POST /me/lessons
│   │   ├── service.py             # LessonService (batch complete, prerequisites)
│   │   └── schemas.py             # LessonCompleteRequest, etc.
│   │
│   ├── progress/
│   │   ├── __init__.py
│   │   ├── router.py              # GET /me/progress, GET/POST/DELETE /me/queue
│   │   ├── service.py             # ProgressService (queue management, progress queries)
│   │   ├── schemas.py             # ProgressResponse, QueueItemRequest, etc.
│   │   └── models.py              # UserItemProgress, LessonQueue models
│   │
│   ├── wanikani/
│   │   ├── __init__.py
│   │   ├── router.py              # POST /me/import/wanikani
│   │   ├── service.py             # WaniKaniService (API client, import logic)
│   │   └── schemas.py             # ImportRequest, ImportResponse
│   │
│   └── core/
│       ├── __init__.py
│       ├── exceptions.py          # Custom exceptions if needed
│       └── constants.py           # SRS_INTERVALS, item types enum, etc.
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pytest fixtures, test DB setup
│   ├── auth/
│   │   └── test_service.py
│   ├── kanji/
│   │   └── test_service.py
│   ├── vocab/
│   │   └── test_service.py
│   ├── reviews/
│   │   ├── test_service.py
│   │   └── test_srs.py            # SRS calculation tests (critical)
│   ├── lessons/
│   │   └── test_service.py
│   ├── progress/
│   │   └── test_service.py
│   └── wanikani/
│       └── test_service.py
│
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml                 # uv/pip config, ruff config, mypy config
└── README.md
```

### Requirements to Structure Mapping

| FR Category | Primary Location | Key Files |
|-------------|------------------|-----------|
| Auth & Users (FR1-3) | `src/auth/` | `service.py`, `models.py` (User, Session) |
| Kanji Database (FR4-8) | `src/kanji/` + `scripts/` | `seed_kanji.py`, `service.py`, `models.py` |
| Vocab Management (FR9-13) | `src/vocab/` | `service.py`, `models.py` (Vocab, Tag, VocabTag) |
| Shared Pool (FR14-18) | `src/vocab/` | `service.py` (filtering logic) |
| Lesson System (FR19-22) | `src/lessons/` + `src/progress/` | `service.py`, `models.py` (LessonQueue) |
| Review System (FR23-29) | `src/reviews/` | `service.py`, `srs.py`, `models.py` (ReviewLog) |
| Progress & Notes (FR30-33) | `src/progress/` | `service.py`, `models.py` (UserItemProgress) |
| WK Integration (FR34-36) | `src/wanikani/` | `service.py` |

### Architectural Boundaries

**API Layer** (`router.py` files):
- HTTP request/response handling only
- Calls service layer, returns Pydantic schemas
- No business logic

**Service Layer** (`service.py` files):
- All business logic
- Receives Pydantic requests, returns Pydantic responses
- Interacts with database via SQLAlchemy models

**Data Layer** (`models.py` files):
- SQLAlchemy model definitions
- No business logic, just data structure

**Cross-Cutting Dependencies:**
- `src/auth/dependencies.py` → `get_current_user` used by all `/me/*` routes
- `src/core/constants.py` → `SRS_INTERVALS`, `ItemType` enum shared across modules
- `src/database.py` → `get_db` dependency used everywhere

### Key Implementation Files

**`src/reviews/srs.py`** - Core SRS logic:

```python
from datetime import timedelta

SRS_INTERVALS = {
    1: timedelta(hours=4),    # Apprentice 1 → 2
    2: timedelta(hours=8),    # Apprentice 2 → 3
    3: timedelta(days=1),     # Apprentice 3 → 4
    4: timedelta(days=2),     # Apprentice 4 → Guru 1
    5: timedelta(weeks=1),    # Guru 1 → 2
    6: timedelta(weeks=2),    # Guru 2 → Master
    7: timedelta(days=30),    # Master → Enlightened
    8: timedelta(days=120),   # Enlightened → Burned
}

def calculate_next_review(current_stage: int, correct: bool) -> tuple[int, datetime]:
    # Returns (new_stage, next_review_at)
    ...
```

**`scripts/seed_kanji.py`** - Idempotent database seeding:
- Runs on deployment, safe to run multiple times
- Checks if kanji exists before inserting
- Sources from jamdict (kanjidic2 via jamdict-data SQLite)
- Optional `--update` flag to refresh metadata for existing records

**jamdict Runtime Usage:**
- Radical decomposition: `jam.krad[kanji_char]` returns list of radicals
- Vocab lookup: `jam.lookup(word)` returns JMdict entries with readings/meanings
- Used by kanji detail views and vocab creation autocomplete

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices work together without conflicts:
- FastAPI + SQLAlchemy 2.0 async + MySQL + Pydantic v2 - fully compatible
- Alembic integrates seamlessly with SQLAlchemy
- structlog + pytest + ruff + mypy - all compatible, no version conflicts

**Pattern Consistency:**
- Service layer pattern aligns perfectly with FastAPI's dependency injection
- Naming conventions (snake_case throughout) consistent across DB, API, and code
- Logging pattern (structlog) supports the structured approach

**Structure Alignment:**
- Project structure supports all architectural decisions
- Clear separation: routers → services → models
- Cross-cutting concerns properly isolated in `src/core/` and `src/auth/dependencies.py`

### Requirements Coverage Validation ✅

**Functional Requirements (36 total):**
All FR categories mapped to specific implementation locations:
- Auth & Users (FR1-3) → `src/auth/`
- Kanji Database (FR4-8) → `src/kanji/` + `scripts/seed_kanji.py`
- Vocab Management (FR9-13) → `src/vocab/`
- Shared Pool (FR14-18) → `src/vocab/service.py` filtering logic
- Lesson System (FR19-22) → `src/lessons/` + `src/progress/`
- Review System (FR23-29) → `src/reviews/` + `srs.py`
- Progress & Notes (FR30-33) → `src/progress/`
- WK Integration (FR34-36) → `src/wanikani/`

**Non-Functional Requirements (8 total):**
- Performance (NFR1-2): Async SQLAlchemy, simple queries, small dataset
- Reliability (NFR3-4): Docker volumes for persistence, standard deployment
- Integration (NFR5-6): WaniKani service handles rate limits gracefully
- Security (NFR7-8): Simplified per trusted environment decision

**Cross-Cutting Concerns:**
- Item Type Polymorphism: `item_type` discriminator in `UserItemProgress`
- User Context: `get_current_user` dependency used across `/me/*` routes
- Prerequisite Resolution: `LessonService` checks kanji progress
- Dormant Activation: `VocabService` activates kanji on vocab creation

### Implementation Readiness ✅

**Decision Completeness:**
- All critical decisions documented with specific versions
- Implementation patterns comprehensive with code examples
- Consistency rules clear and enforceable via pre-commit

**Structure Completeness:**
- Complete directory structure with all files specified
- Integration points clearly defined
- Component boundaries well-established

**Pattern Completeness:**
- All naming conventions specified (DB, API, code)
- Service layer pattern with examples
- Logging pattern with structlog usage examples

### Gap Analysis

**Critical Gaps:** None identified

**Minor Gaps (non-blocking):**
- Alembic migration naming: Use default `{timestamp}_{description}.py`
- WK API rate limit details: Implement with httpx + retry logic
- Test fixture details: Standard pytest async fixtures in `conftest.py`

These are implementation details, not architectural decisions.

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed (low complexity, ~5 users)
- [x] Technical constraints identified (WK intervals, MySQL, self-hosted)
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Authentication approach decided

**✅ Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Service layer pattern documented
- [x] Logging pattern specified

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** HIGH

**Key Strengths:**
- Simple, focused architecture matching project scope
- Clear separation of concerns with service layer
- Well-documented patterns for consistency
- Complete FR coverage with explicit mappings

**Areas for Future Enhancement:**
- Add caching layer if performance becomes an issue
- Consider background job system for WK imports if they become slow
- Add API documentation generation (FastAPI provides this automatically)

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED ✅
**Total Steps Completed:** 8
**Date Completed:** 2026-01-23
**Document Location:** `_bmad-output/planning-artifacts/architecture.md`

### Final Architecture Deliverables

**Complete Architecture Document:**
- All architectural decisions documented with specific versions
- Implementation patterns ensuring AI agent consistency
- Complete project structure with all files and directories
- Requirements to architecture mapping
- Validation confirming coherence and completeness

**Implementation Ready Foundation:**
- 15+ architectural decisions made
- 10+ implementation patterns defined
- 7 architectural components (auth, kanji, vocab, reviews, lessons, progress, wanikani)
- 36 functional requirements fully supported

### Implementation Handoff

**For AI Agents:**
This architecture document is your complete guide for implementing Kanji SRS Platform. Follow all decisions, patterns, and structures exactly as documented.

**First Implementation Priority:**

```bash
# 1. Initialize project
mkdir kanji-srs && cd kanji-srs
uv init
uv add fastapi sqlalchemy[asyncio] asyncmy alembic pydantic-settings structlog uvicorn jamdict jamdict-data

# 2. Set up pre-commit
uv add --dev pre-commit pytest pytest-asyncio ruff mypy httpx
pre-commit install

# 3. Create project structure per architecture document
```

**Development Sequence:**
1. Initialize project with uv and dependencies
2. Set up pre-commit hooks
3. Create directory structure per architecture
4. Implement database models and Alembic migrations
5. Build auth module first (needed by all `/me/*` routes)
6. Implement core SRS logic (`src/reviews/srs.py`)
7. Build remaining modules following service layer pattern
8. Create kanji seed script
9. Add tests alongside implementation

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅
