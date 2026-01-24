# Project Context for AI Agents

**Project:** Kanji SRS Platform
**Generated:** 2026-01-23

_Critical rules and patterns for consistent implementation. Read this before writing any code._

---

## Technology Stack

| Component | Choice | Version |
|-----------|--------|---------|
| Language | Python | 3.12+ |
| Framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ (async) |
| DB Driver | asyncmy | Latest |
| Database | MySQL | 8.0+ |
| Migrations | Alembic | Latest |
| Validation | Pydantic | v2 |
| Logging | structlog | Latest |
| Package Manager | uv | Latest |
| Linting | ruff | Latest |
| Type Checking | mypy | Latest |
| Testing | pytest + pytest-asyncio | Latest |
| Japanese Data | jamdict + jamdict-data | Latest |

---

## Critical Rules

### 1. Async Everywhere

All database operations MUST be async:

```python
# CORRECT
async def get_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# WRONG - blocks event loop
def get_user(db: Session, user_id: int) -> User:
    return db.query(User).filter(User.id == user_id).first()
```

### 2. Service Layer Pattern

Routes are thin. Business logic lives in services:

```python
# src/reviews/router.py - THIN
@router.post("/reviews")
async def submit_review(
    request: ReviewCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReviewService(db)
    return await service.submit_review(current_user.id, request)

# src/reviews/service.py - ALL LOGIC HERE
class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit_review(self, user_id: int, request: ReviewCreateRequest) -> ReviewResponse:
        # SRS calculations, DB updates, etc.
        ...
```

### 3. Schema Naming Convention

```python
# Request schemas (incoming data)
class VocabCreateRequest(BaseModel): ...
class VocabUpdateRequest(BaseModel): ...

# Response schemas (outgoing data)
class VocabResponse(BaseModel): ...
class VocabListResponse(BaseModel): ...
```

### 4. Import Style

Always use absolute imports from `src`:

```python
# CORRECT
from src.auth.service import AuthService
from src.reviews.schemas import ReviewCreateRequest
from src.core.constants import SRS_INTERVALS

# WRONG
from .service import AuthService
from ..reviews.schemas import ReviewCreateRequest
```

### 5. Logging Pattern

```python
from src.logging import logger

# Event name first, then key-value context
logger.info("review_submitted", user_id=123, item_id=456, new_stage=3)
logger.error("wanikani_import_failed", user_id=123, error=str(e))
```

---

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| DB Tables | snake_case, plural | `users`, `vocab_items` |
| DB Columns | snake_case | `user_id`, `srs_stage` |
| API Endpoints | plural, lowercase | `/api/v1/vocab` |
| JSON Fields | snake_case | `{"next_review_at": "..."}` |
| Files | snake_case.py | `review_service.py` |
| Classes | PascalCase | `ReviewService` |
| Functions | snake_case | `calculate_next_review()` |
| Constants | SCREAMING_SNAKE | `SRS_INTERVALS` |

---

## Project Structure

```
src/
├── main.py              # FastAPI app entry
├── settings.py          # Pydantic Settings
├── logging.py           # structlog setup
├── database.py          # Async engine, get_db
├── auth/                # Authentication
├── kanji/               # Kanji browsing
├── vocab/               # Vocab CRUD + shared pool
├── reviews/             # SRS review system
├── lessons/             # Lesson completion
├── progress/            # User progress + queue
├── wanikani/            # WK import
└── core/                # Constants, exceptions
```

Each module contains:
- `router.py` - FastAPI routes
- `service.py` - Business logic
- `schemas.py` - Pydantic models
- `models.py` - SQLAlchemy models (if needed)

---

## SRS System

WaniKani intervals - DO NOT MODIFY:

```python
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
```

- Stage 0 = Lesson (not yet started)
- Stage 9 = Burned (complete)
- Wrong answer drops ~2 stages
- Reviews batched by hour, not exact timestamp

---

## Authentication

- Username-only login (no password - trusted users)
- Session tokens stored in DB
- Long-lived sessions (no auto-expiry)
- Header: `Authorization: Bearer <token>`
- Use `get_current_user` dependency for all `/me/*` routes

---

## Key Business Rules

1. **Kanji are dormant** until vocabulary links to them
2. **Vocab requires kanji** - can't lesson vocab until constituent kanji are learned
3. **Both reading + meaning** must pass to advance SRS stage
4. **Frontend validates** correctness, backend records outcome
5. **WK API keys** stored plaintext (trusted environment)

---

## Anti-Patterns to Avoid

```python
# DON'T put business logic in routes
@router.post("/reviews")
async def submit_review(...):
    # NO: calculating SRS here
    new_stage = current_stage + 1 if correct else max(1, current_stage - 2)
    # Use service layer instead

# DON'T use sync database calls
user = db.query(User).first()  # WRONG
user = await db.execute(select(User))  # CORRECT

# DON'T mix naming conventions
class vocab_create_request: ...  # WRONG
class VocabCreateRequest: ...    # CORRECT

# DON'T forget type hints
def get_user(db, user_id):  # WRONG
async def get_user(db: AsyncSession, user_id: int) -> User | None:  # CORRECT
```

---

## Testing

- Tests live in `tests/` mirroring `src/` structure
- Use pytest-asyncio for async tests
- Test fixtures in `conftest.py`
- SRS calculations are critical - test thoroughly

```python
# tests/reviews/test_srs.py
@pytest.mark.asyncio
async def test_correct_answer_advances_stage():
    ...

@pytest.mark.asyncio
async def test_wrong_answer_drops_two_stages():
    ...
```

---

## Quick Reference

**API Base:** `/api/v1/`

**Key Endpoints:**
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/kanji` - Browse kanji
- `GET/POST /api/v1/vocab` - Browse/create vocab
- `GET /api/v1/me/reviews` - Get due reviews
- `POST /api/v1/me/reviews` - Submit review
- `POST /api/v1/me/lessons` - Complete lessons
- `GET/POST/DELETE /api/v1/me/queue` - Lesson queue
- `POST /api/v1/me/import/wanikani` - WK import

**Date Format:** ISO 8601 UTC (`"2026-01-23T14:30:00Z"`)
