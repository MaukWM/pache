# Story 4.1: Lesson Queue Model & Add Items to Queue

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to add vocabulary and kanji items to my personal lesson queue**,
So that **I can prepare them for batch lesson completion**.

## Acceptance Criteria

**AC1: LessonQueue model**
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

**AC2:** Alembic migration creates `lesson_queue` table

**AC3:** `src/progress/schemas.py` defines `QueueItemRequest`, `QueueItemResponse`, `QueueListResponse`

**AC4: Add item to queue (success)**
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

**AC5: Duplicate item handling**
**Given** an authenticated user with vocab id=123 already in their queue
**When** POST `/api/v1/me/queue` is called with the same item
**Then** response status is 409 Conflict with error message indicating item already in queue

**AC6: Invalid item_id handling**
**Given** an authenticated user
**When** POST `/api/v1/me/queue` is called with invalid item_id (e.g., vocab id=99999 doesn't exist)
**Then** response status is 400 with error message indicating item not found

**AC7: Get queue items**
**Given** an authenticated user
**When** GET `/api/v1/me/queue` is called
**Then** response status is 200
**And** response returns a list of all items in the user's lesson queue
**And** each item includes item_type, item_id, and item details (kanji character or vocab word)

**AC8: Authentication required**
**Given** an unauthenticated request
**When** POST `/api/v1/me/queue` or GET `/api/v1/me/queue` is called
**Then** response status is 401 Unauthorized

**AC9:** `src/progress/router.py` mounts queue endpoints at `/api/v1/me/queue`

**AC10:** `src/progress/service.py` contains `ProgressService` with queue management logic

## Tasks / Subtasks

- [x] Task 1: Create LessonQueue model (AC: 1)
  - [x] Create `src/progress/models.py`
  - [x] Define LessonQueue model with all required columns:
    - id (Integer, primary key, autoincrement)
    - user_id (Integer, FK to users.id, indexed, not null)
    - item_type (Enum using ItemType from src.core.constants, not null)
    - item_id (Integer, not null)
    - added_at (DateTime with timezone, default UTC now)
  - [x] Add composite unique constraint on (user_id, item_type, item_id)
  - [x] Add relationship to User model

- [x] Task 2: Create Alembic migration (AC: 2)
  - [x] Generate migration for lesson_queue table
  - [x] Ensure foreign key constraint to users table
  - [x] Ensure composite unique constraint
  - [x] Ensure indexes on user_id
  - [x] Test migration upgrade and downgrade

- [x] Task 3: Create Pydantic schemas (AC: 3)
  - [x] Create `src/progress/schemas.py`
  - [x] Define QueueItemRequest schema:
    - item_type: ItemType (kanji | vocab)
    - item_id: int
  - [x] Define QueueItemResponse schema:
    - id: int
    - item_type: ItemType
    - item_id: int
    - added_at: datetime
    - item_details: dict (kanji character or vocab word/reading)
  - [x] Define QueueListResponse schema:
    - items: list[QueueItemResponse]

- [x] Task 4: Create ProgressService with queue management (AC: 10)
  - [x] Create `src/progress/service.py`
  - [x] Implement `ProgressService` class
  - [x] Implement `add_to_queue` method:
    - Validate item exists (kanji or vocab)
    - Check for duplicate (user_id, item_type, item_id)
    - Create LessonQueue record
    - Return QueueItemResponse
  - [x] Implement `get_queue` method:
    - Query user's queue items
    - Eager load item details (kanji or vocab)
    - Return list of QueueItemResponse

- [x] Task 5: Create queue router endpoints (AC: 4, 5, 6, 7, 8, 9)
  - [x] Create `src/progress/router.py`
  - [x] Implement POST `/api/v1/me/queue` endpoint:
    - Requires authentication (Depends(get_current_user))
    - Accepts QueueItemRequest
    - Calls ProgressService.add_to_queue
    - Returns 201 with QueueItemResponse on success
    - Returns 409 on duplicate
    - Returns 400 on invalid item_id
  - [x] Implement GET `/api/v1/me/queue` endpoint:
    - Requires authentication
    - Calls ProgressService.get_queue
    - Returns 200 with QueueListResponse
  - [x] Mount router in `src/main.py` at `/api/v1/me/queue`

- [x] Task 6: Write comprehensive tests
  - [x] Create `tests/progress/test_models.py`
    - Test LessonQueue model creation
    - Test composite unique constraint
    - Test relationships
  - [x] Create `tests/progress/test_service.py`
    - Test add_to_queue success
    - Test add_to_queue duplicate (409)
    - Test add_to_queue invalid item_id (400)
    - Test get_queue returns user's items
    - Test get_queue includes item details
  - [x] Create `tests/progress/test_router.py`
    - Test POST /me/queue success (201)
    - Test POST /me/queue duplicate (409)
    - Test POST /me/queue invalid item_id (400)
    - Test POST /me/queue unauthenticated (401)
    - Test GET /me/queue success (200)
    - Test GET /me/queue unauthenticated (401)
    - Test GET /me/queue returns item details

## Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Fix N+1 query problem in `get_queue` method [src/progress/service.py:99-146]
  - Current: Individual `db.get()` calls for each queue item causes N+1 queries
  - Fix: Use bulk queries with `IN` clauses - separate queries for kanji_ids and vocab_ids
  - Example pattern from VocabService: Use `select(Kanji).where(Kanji.id.in_(kanji_ids))` for bulk loading
  - Impact: With 100 queue items, reduces from 101 queries to 3 queries (1 queue + 1 kanji bulk + 1 vocab bulk)
  - ✅ Fixed: Implemented bulk loading with separate queries for kanji and vocab items

- [x] [AI-Review][HIGH] Add input validation for `item_id` [src/progress/schemas.py:13]
  - Current: `item_id: int` accepts negative, zero, or invalid values
  - Fix: Add `item_id: int = Field(..., gt=0, description="Positive item ID")`
  - Impact: Prevents invalid IDs from reaching database, better error messages
  - ✅ Fixed: Added Field validation with gt=0 constraint

- [x] [AI-Review][HIGH] Clean up orphaned queue entries when items are deleted [src/progress/service.py:119-121, 130-132]
  - Current: Silently skips deleted items, leaving orphaned queue entries
  - Fix: When item not found, delete the queue entry: `await self.db.delete(queue_item)` then `continue`
  - Also: Add cleanup method or background task to periodically remove orphaned entries
  - Impact: Prevents accumulation of orphaned data
  - ✅ Fixed: Implemented cleanup in get_queue method, deletes orphaned entries and commits changes

- [x] [AI-Review][HIGH] Add foreign key handling strategy for `item_id` [src/progress/models.py:29, alembic/versions/004_create_lesson_queue.py:29]
  - Current: `item_id` has no FK constraint (polymorphic reference issue)
  - Suggestion: Since `item_id` references different tables based on `item_type`, use application-level cleanup:
    - Add database triggers OR application-level cleanup on kanji/vocab delete
    - Consider adding `ON DELETE CASCADE` if using polymorphic association pattern
    - Alternative: Add check constraint validation at application level (already done in service)
  - Note: This is acceptable for polymorphic references, but document the decision
  - ✅ Fixed: Added comprehensive documentation in LessonQueue model docstring explaining polymorphic FK pattern

- [ ] [AI-Review][HIGH] Add check for already-learned items (when UserItemProgress exists) [src/progress/service.py:22-97]
  - Current: No validation if item already in UserItemProgress
  - Fix: After Story 4.3 (UserItemProgress exists), add check:
    ```python
    progress = await self.db.execute(
        select(UserItemProgress).where(
            UserItemProgress.user_id == user_id,
            UserItemProgress.item_type == item_type,
            UserItemProgress.item_id == item_id
        )
    )
    if progress.scalar_one_or_none():
        raise HTTPException(400, "Item already learned")
    ```
  - Impact: Prevents users from queuing items they've already learned
  - ⏸️ Deferred: Waiting for Story 4.3 (UserItemProgress model) to be implemented

- [x] [AI-Review][MEDIUM] Improve type safety for `item_details` using TypedDict [src/progress/schemas.py:26]
  - Current: `item_details: dict[str, str | list[str]]` is too generic
  - Fix: Create TypedDict classes:
    ```python
    class KanjiItemDetails(TypedDict):
        character: str
        meanings: list[str]

    class VocabItemDetails(TypedDict):
        word: str
        readings: list[str]
        meanings: list[str]
    ```
  - Then: `item_details: KanjiItemDetails | VocabItemDetails`
  - Impact: Better IDE support and type checking
  - ✅ Fixed: Created KanjiItemDetails and VocabItemDetails TypedDict classes

- [x] [AI-Review][MEDIUM] Make composite index explicit in migration [alembic/versions/004_create_lesson_queue.py:33]
  - Current: Unique constraint creates index implicitly
  - Fix: Add explicit index after unique constraint:
    ```python
    op.create_index("ix_lesson_queue_user_item", "lesson_queue", ["user_id", "item_type", "item_id"], unique=False)
    ```
  - Note: The unique constraint already creates an index, but explicit is clearer for query optimization
  - Impact: Better query plan visibility
  - ✅ Fixed: Added explicit composite index in migration

- [x] [AI-Review][LOW] Add docstring examples to service methods [src/progress/service.py:22, 99]
  - Current: Basic docstrings without examples
  - Fix: Add usage examples:
    ```python
    """Add an item to the user's lesson queue.

    Example:
        response = await service.add_to_queue(
            user_id=1,
            item_type=ItemType.KANJI,
            item_id=42
        )
    """
    ```
  - Impact: Better developer experience
  - ✅ Fixed: Added example docstrings to both add_to_queue and get_queue methods

## Dev Notes

### Architecture Requirements

Follow these patterns from `architecture.md` and `project-context.md`:

**Service Layer Pattern:**
- Routes are thin, business logic lives in services
- Service handles all validation and business rules

**URL Pattern:**
- `/api/v1/me/queue` - user's personal queue endpoints
- Requires authentication (use `get_current_user` dependency)

**Naming Conventions:**
- Tables: snake_case, plural (`lesson_queue`)
- Columns: snake_case (`user_id`, `item_type`, `item_id`, `added_at`)
- Classes: PascalCase (`LessonQueue`, `ProgressService`)

**Import Style:**
```python
# Absolute imports from src
from src.database import Base
from src.auth.models import User
from src.core.constants import ItemType
```

### Model Patterns

```python
from datetime import datetime, timezone
from sqlalchemy import Integer, Enum, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base
from src.core.constants import ItemType

class LessonQueue(Base):
    __tablename__ = "lesson_queue"
    __table_args__ = (
        UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_item"),
        Index("ix_lesson_queue_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="lesson_queue_items")
```

### Item Validation Logic

The service must validate that the item exists before adding to queue:

```python
# For kanji items
kanji = await db.get(Kanji, item_id)
if not kanji:
    raise ValueError(f"Kanji with id={item_id} not found")

# For vocab items
vocab = await db.get(Vocab, item_id)
if not vocab:
    raise ValueError(f"Vocab with id={item_id} not found")
```

### Item Details in Response

QueueItemResponse should include item details:
- For kanji: `{"character": "漢", "meanings": [...]}`
- For vocab: `{"word": "漢字", "reading": "かんじ", "meanings": [...]}`

### Previous Story Intelligence

From Story 3.1:
- Router pattern: use `Depends(get_db)` and `Depends(get_current_user)` for authentication
- Schema pattern: use `ConfigDict(from_attributes=True)` for SQLAlchemy conversion
- Test pattern: use `tests/conftest.py` fixtures, async testing with `pytest-asyncio`
- Error handling: use HTTPException with appropriate status codes

### Project Structure Notes

**Files to create:**
- `src/progress/models.py` - LessonQueue model
- `src/progress/schemas.py` - QueueItemRequest, QueueItemResponse, QueueListResponse
- `src/progress/service.py` - ProgressService with queue management
- `src/progress/router.py` - Queue endpoints
- `tests/progress/test_models.py` - Model tests
- `tests/progress/test_service.py` - Service tests
- `tests/progress/test_router.py` - Router tests

**Migrations to create:**
- `alembic/versions/xxx_create_lesson_queue.py`

**Files to modify:**
- `src/main.py` - Mount progress router
- `src/auth/models.py` - Add back_populates relationship to User

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/project-context.md]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1: Lesson Queue Model & Add Items to Queue]
- [Source: src/core/constants.py - ItemType enum]
- [Source: src/vocab/models.py - existing model pattern]
- [Source: src/vocab/router.py - existing router pattern]

## Senior Developer Review (AI)

**Review Date:** 2026-01-24
**Reviewer:** AI Code Reviewer (Adversarial)
**Review Outcome:** Changes Requested

### Summary

**Total Issues Found:** 10 (6 High, 2 Medium, 2 Low)
**Git vs Story Discrepancies:** 0 (all files match)
**Acceptance Criteria:** All implemented ✓
**Code Quality:** Good foundation, but performance and data integrity improvements needed

### Action Items

- [x] [AI-Review][HIGH] Fix N+1 query problem in `get_queue` method [src/progress/service.py:99-146]
- [x] [AI-Review][HIGH] Add input validation for `item_id` [src/progress/schemas.py:13]
- [x] [AI-Review][HIGH] Clean up orphaned queue entries when items are deleted [src/progress/service.py:119-121, 130-132]
- [x] [AI-Review][HIGH] Add foreign key handling strategy for `item_id` [src/progress/models.py:29]
- [ ] [AI-Review][HIGH] Add check for already-learned items (when UserItemProgress exists) [src/progress/service.py:22-97] - Deferred until Story 4.3
- [x] [AI-Review][MEDIUM] Improve type safety for `item_details` using TypedDict [src/progress/schemas.py:26]
- [x] [AI-Review][MEDIUM] Make composite index explicit in migration [alembic/versions/004_create_lesson_queue.py:33]
- [x] [AI-Review][LOW] Add docstring examples to service methods [src/progress/service.py:22, 99]

### Review Notes

**Key Findings:**
1. **Performance:** N+1 query issue will impact scalability - fix before production
2. **Data Integrity:** Missing validation and orphaned data handling need attention
3. **Type Safety:** Can be improved with TypedDict for better IDE support
4. **Architecture:** Polymorphic FK handling is acceptable but should be documented

**Positive Aspects:**
- Clean service layer pattern
- Good test coverage (20 tests)
- Proper error handling with HTTPException
- Follows project conventions

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

**Story 4.1 Implementation Complete**

**Review Feedback Implementation (2026-01-24):**
- ✅ Fixed N+1 query problem: Implemented bulk loading with separate queries for kanji_ids and vocab_ids using `IN` clauses, reducing queries from O(n) to O(1) for item loading
- ✅ Added input validation: Added `Field(gt=0)` constraint to `item_id` in QueueItemRequest schema
- ✅ Cleaned up orphaned entries: Implemented automatic cleanup in `get_queue` method that deletes orphaned queue entries when referenced items are deleted
- ✅ Documented FK strategy: Added comprehensive documentation in LessonQueue model explaining polymorphic foreign key pattern and cleanup approach
- ✅ Improved type safety: Created KanjiItemDetails and VocabItemDetails TypedDict classes for better IDE support and type checking
- ✅ Added explicit composite index: Added `ix_lesson_queue_user_item` index in migration for better query plan visibility
- ✅ Added docstring examples: Added usage examples to both `add_to_queue` and `get_queue` methods
- ⏸️ Deferred: Check for already-learned items (waiting for Story 4.3 UserItemProgress model)

**LessonQueue Model (Task 1):**
- Created `src/progress/models.py` with LessonQueue model
- All required columns: id, user_id (FK, indexed), item_type (ItemType enum), item_id, added_at
- Composite unique constraint on (user_id, item_type, item_id)
- Relationship to User model with back_populates
- Updated User model to include lesson_queue_items relationship

**Alembic Migration (Task 2):**
- Created `alembic/versions/004_create_lesson_queue.py`
- Creates lesson_queue table with all constraints
- Foreign key to users table
- Composite unique constraint
- Index on user_id

**Pydantic Schemas (Task 3):**
- Created `src/progress/schemas.py`
- QueueItemRequest: item_type (ItemType), item_id (int)
- QueueItemResponse: id, item_type, item_id, added_at, item_details (dict)
- QueueListResponse: items (list[QueueItemResponse])

**ProgressService (Task 4):**
- Created `src/progress/service.py` with ProgressService class
- `add_to_queue`: Validates item exists, checks duplicates, creates record, returns response with item details
- `get_queue`: Queries user's queue, loads item details (kanji/vocab), returns list of responses
- Proper error handling with HTTPException (400 for invalid items, 409 for duplicates)

**Router Endpoints (Task 5):**
- Created `src/progress/router.py` with queue endpoints
- POST `/api/v1/me/queue`: Requires auth, accepts QueueItemRequest, returns 201/409/400
- GET `/api/v1/me/queue`: Requires auth, returns QueueListResponse
- Mounted router in `src/main.py` at `/api/v1/me/queue`

**Tests (Task 6):**
- Created `tests/progress/test_models.py` with 5 model tests
- Created `tests/progress/test_service.py` with 8 service tests
- Created `tests/progress/test_router.py` with 7 router tests
- Total: 20 new tests, all passing
- Full test suite: 100 tests pass (no regressions)

**Pre-commit Checks:**
- All hooks pass: ruff, ruff-format, mypy, gitleaks

**All Acceptance Criteria Satisfied:**
- AC1: LessonQueue model created ✓
- AC2: Alembic migration created ✓
- AC3: Pydantic schemas created ✓
- AC4: POST endpoint returns 201 on success ✓
- AC5: POST endpoint returns 409 on duplicate ✓
- AC6: POST endpoint returns 400 on invalid item_id ✓
- AC7: GET endpoint returns queue items with details ✓
- AC8: Endpoints require authentication (401) ✓
- AC9: Router mounted at correct path ✓
- AC10: ProgressService contains queue management logic ✓

**Review Feedback Implementation (2026-01-24):**
- ✅ Fixed N+1 query problem: Implemented bulk loading with separate queries for kanji_ids and vocab_ids using `IN` clauses, reducing queries from O(n) to O(1) for item loading
- ✅ Added input validation: Added `Field(gt=0)` constraint to `item_id` in QueueItemRequest schema
- ✅ Cleaned up orphaned entries: Implemented automatic cleanup in `get_queue` method that deletes orphaned queue entries when referenced items are deleted
- ✅ Documented FK strategy: Added comprehensive documentation in LessonQueue model explaining polymorphic foreign key pattern and cleanup approach
- ✅ Improved type safety: Created KanjiItemDetails and VocabItemDetails TypedDict classes for better IDE support and type checking
- ✅ Added explicit composite index: Added `ix_lesson_queue_user_item` index in migration for better query plan visibility
- ✅ Added docstring examples: Added usage examples to both `add_to_queue` and `get_queue` methods
- ✅ Added test: Added test_get_queue_cleans_up_orphaned_entries test to verify cleanup functionality
- ⏸️ Deferred: Check for already-learned items (waiting for Story 4.3 UserItemProgress model)

## File List

**Created Files:**
- `src/progress/models.py` - LessonQueue SQLAlchemy model
- `src/progress/schemas.py` - QueueItemRequest, QueueItemResponse, QueueListResponse
- `src/progress/service.py` - ProgressService with queue management
- `src/progress/router.py` - Queue endpoints (POST, GET)
- `alembic/versions/004_create_lesson_queue.py` - LessonQueue migration
- `tests/progress/test_models.py` - LessonQueue model tests (5 tests)
- `tests/progress/test_service.py` - ProgressService tests (8 tests)
- `tests/progress/test_router.py` - Queue router tests (7 tests)

**Modified Files:**
- `src/auth/models.py` - Added lesson_queue_items relationship to User model
- `src/main.py` - Mounted progress router at `/api/v1/me/queue`
- `tests/conftest.py` - Added LessonQueue import for Base.metadata registration
- `src/progress/service.py` - Fixed N+1 queries, added orphaned cleanup, added docstring examples
- `src/progress/schemas.py` - Added input validation, improved type safety with TypedDict
- `src/progress/models.py` - Added FK handling strategy documentation
- `alembic/versions/004_create_lesson_queue.py` - Added explicit composite index
- `tests/progress/test_service.py` - Added test for orphaned entry cleanup

## Change Log

- 2026-01-24: Story 4.1 implementation completed
  - Created LessonQueue model with composite unique constraint
  - Created Alembic migration for lesson_queue table
  - Created Pydantic schemas for queue API
  - Implemented ProgressService with add_to_queue and get_queue methods
  - Created queue router endpoints (POST, GET) with authentication
  - Added comprehensive tests (20 tests)
  - All 100 tests pass, no regressions
  - Pre-commit checks pass
  - All acceptance criteria satisfied
