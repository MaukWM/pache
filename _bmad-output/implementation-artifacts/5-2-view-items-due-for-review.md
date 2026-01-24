# Story 5.2: View Items Due for Review

Status: complete

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to see items that are due for review**,
So that **I know what I have to study next**.

## Acceptance Criteria

**AC1: Due reviews endpoint**
**Given** an authenticated user with items in UserItemProgress
**When** GET `/api/v1/me/reviews` is called
**Then** response status is 200
**And** response returns a list of items where `next_review_at <= current_time` (batched by hour - FR28)
**And** query truncates `next_review_at` to hour precision for comparison (not exact timestamp)
**And** only items with `srs_stage < 9` are returned (excludes burned items)
**And** each item includes:
  - `item_type`, `item_id`
  - `srs_stage`
  - `next_review_at`
  - Item details (kanji character/meanings/readings or vocab word/reading/meanings)

**AC2: No due reviews**
**Given** an authenticated user with no items due
**When** GET `/api/v1/me/reviews` is called
**Then** response status is 200
**And** response returns empty list `[]`

**AC3: Authentication required**
**Given** an unauthenticated request
**When** GET `/api/v1/me/reviews` is called
**Then** response status is 401 Unauthorized

**AC4:** `src/reviews/router.py` mounts at `/api/v1/me/reviews`

**AC5:** `src/reviews/service.py` contains `ReviewService` with `get_due_reviews` method

**AC6:** Hour-batching logic truncates timestamps to hour precision before comparison

## Tasks / Subtasks

- [x] Task 1: Create ReviewService (AC: 5, 6)
  - [x] Create `src/reviews/service.py`
  - [x] Add ReviewService class with `__init__(self, db: AsyncSession)`
  - [x] Implement `get_due_reviews(user_id: int) -> list[ReviewItemResponse]`:
    - Query UserItemProgress for user
    - Filter where srs_stage < 9 (not burned)
    - Filter where next_review_at is not None
    - Truncate current time to hour precision
    - Filter where next_review_at (truncated to hour) <= current_hour
    - Order by next_review_at ascending (oldest first)
    - Eagerly load item details (kanji or vocab)
    - Return formatted response with item details

- [x] Task 2: Add hour truncation helper (AC: 6)
  - [x] Add `truncate_to_hour(dt: datetime) -> datetime` function to `src/reviews/srs.py`
  - [x] Function should set minute, second, microsecond to 0
  - [x] Use for both query filter and timestamp comparison

- [x] Task 3: Create response schemas (AC: 1)
  - [x] Add to `src/reviews/schemas.py`:
    - ReviewItemResponse schema:
      - item_type: ItemType
      - item_id: int
      - srs_stage: int
      - next_review_at: datetime
      - item_details: KanjiItemDetails | VocabItemDetails (union type)
    - DueReviewsResponse schema:
      - items: list[ReviewItemResponse]
      - count: int
  - [x] Import KanjiItemDetails and VocabItemDetails from progress schemas

- [x] Task 4: Create router endpoint (AC: 1, 2, 3, 4)
  - [x] Create `src/reviews/router.py`
  - [x] Add GET `/api/v1/me/reviews` endpoint:
    - Requires authentication (Depends(get_current_user))
    - Calls ReviewService.get_due_reviews
    - Returns DueReviewsResponse
    - Handles 401 for unauthenticated

- [x] Task 5: Mount router in main.py
  - [x] Import reviews router
  - [x] Mount at `/api/v1/me/reviews`

- [x] Task 6: Write comprehensive tests
  - [x] Create `tests/reviews/test_service.py`:
    - Test get_due_reviews returns due items
    - Test get_due_reviews excludes burned items (srs_stage=9)
    - Test get_due_reviews excludes items with future next_review_at
    - Test get_due_reviews hour batching (items due within current hour included)
    - Test get_due_reviews orders by next_review_at ascending
    - Test get_due_reviews returns empty list when no items due
    - Test get_due_reviews includes correct item details (kanji vs vocab)
  - [x] Create `tests/reviews/test_router.py`:
    - Test GET /me/reviews returns due items
    - Test GET /me/reviews empty response
    - Test GET /me/reviews unauthenticated (401)
  - [x] Add tests to `tests/reviews/test_srs.py`:
    - Test truncate_to_hour function

## Review Follow-ups (AI)

### [HIGH] Issue 1: Missing database index on `next_review_at`
**Location:** `alembic/versions/005_create_user_item_progress.py:34`
**Action:**
- [x] Create new Alembic migration to add index on `next_review_at` column
- [x] Consider composite index on `(user_id, next_review_at, srs_stage)` as mentioned in story line 137 for optimal query performance
- [x] Migration should add: `op.create_index("ix_user_item_progress_next_review_at", "user_item_progress", ["next_review_at"])`
- [x] Optionally add composite index: `op.create_index("ix_user_item_progress_user_review_stage", "user_item_progress", ["user_id", "next_review_at", "srs_stage"])`

### [HIGH] Issue 2: Inefficient query pattern - loads all items then filters in Python
**Location:** `src/reviews/service.py:44-65`
**Action:**
- [x] Optimize query to filter at database level when possible
- [x] For MySQL/PostgreSQL: Use database datetime truncation functions (e.g., MySQL `DATE_FORMAT` or PostgreSQL `date_trunc`)
- [x] For SQLite compatibility: Keep Python filtering but add comment explaining the trade-off
- [x] Consider adding a database abstraction layer or conditional logic based on database type
- [x] Update query to filter `next_review_at <= current_hour` at SQL level when database supports it

### [MEDIUM] Issue 3: Silent failure on orphaned progress entries
**Location:** `src/reviews/service.py:94-108`
**Action:**
- [x] Add warning log when orphaned progress entries are detected (when `kanji_map.get()` or `vocab_map.get()` returns None)
- [x] Log should include: `user_id`, `item_type`, `item_id` for debugging
- [x] Use `logger.warning()` from `src.logging`
- [x] Add TODO comment: "When Sentry is integrated, also send notification for orphaned progress entries"
- [x] Example log: `logger.warning("orphaned_progress_entry", user_id=user_id, item_type=progress.item_type, item_id=progress.item_id)`

### [MEDIUM] Issue 4: Missing File List documentation
**Location:** `_bmad-output/implementation-artifacts/5-2-view-items-due-for-review.md:211`
**Action:**
- [x] Add comment explaining why File List is empty: "File List was not populated during initial implementation due to agent interruption. Files changed in commit 102dd21:"
- [x] Add actual file list:
  - `src/main.py` - Added reviews router mount
  - `src/reviews/router.py` - Created router with GET endpoint
  - `src/reviews/schemas.py` - Added ReviewItemResponse and DueReviewsResponse schemas
  - `src/reviews/service.py` - Created ReviewService with get_due_reviews method
  - `src/reviews/srs.py` - Added truncate_to_hour function
  - `tests/reviews/test_router.py` - Created router tests
  - `tests/reviews/test_service.py` - Created service tests
  - `tests/reviews/test_srs.py` - Added truncate_to_hour tests

### [MEDIUM] Issue 5: Missing error handling for database failures
**Location:** `src/reviews/service.py:24-128`, `src/reviews/router.py:15-29`
**Action:**
- [x] Add try/except block in `ReviewService.get_due_reviews()` to catch database exceptions
- [x] Add try/except block in router endpoint `get_due_reviews()`
- [x] Handle `SQLAlchemyError` and return appropriate HTTP status codes (500 for server errors)
- [x] Log errors with context (user_id, error type) using `logger.error()`
- [x] Return meaningful error messages without exposing internal details
- [x] Consider using FastAPI's `HTTPException` for consistent error responses

### [MEDIUM] Issue 6: Test hour-batching logic is fragile
**Location:** `tests/reviews/test_service.py:138-181`, `tests/reviews/test_router.py:344-398`
**Action:**
- [x] Refactor hour-batching tests to use fixed timestamps instead of `datetime.now(UTC)`
- [x] Use `freezegun` library or mock `datetime.now()` for deterministic tests
- [x] Create test fixtures with fixed times (e.g., `2026-01-24T14:30:00Z` for item due later in hour)
- [x] Ensure tests don't depend on execution time
- [x] Test both edge cases: item due at start of hour (14:00) and end of hour (14:59)

### [LOW] Issue 7: Type safety concern with item_details access
**Location:** `tests/reviews/test_service.py:56, 295-298`
**Action:**
- [x] Use proper type narrowing in tests when accessing `item_details`
- [x] Cast to specific type: `details = cast(KanjiItemDetails, reviews[0].item_details)` or use type guards
- [x] If casting solution is janky, leave as-is (dictionary access works at runtime)
- [x] Consider adding helper function `get_kanji_details(item: ReviewItemResponse) -> KanjiItemDetails` if needed

### [LOW] Issue 8: Missing validation for empty item_ids lists
**Location:** `src/reviews/service.py:70-86`
**Action:**
- [x] Add logging when item IDs are missing from kanji_map or vocab_map
- [x] Log warning when `progress.item_id` not found in corresponding map
- [x] Include context: `user_id`, `item_type`, `item_id` in log message
- [x] This complements issue #3 logging for orphaned entries

## Dev Notes

### Architecture Requirements

- Follow service layer pattern: routers → services → models
- Use async SQLAlchemy 2.0 patterns with eager loading
- Hour-batching is FR28 requirement - critical for correct behavior

### Hour-Batching Logic (FR28)

**Why hour batching?**
- WaniKani batches reviews by hour, not exact timestamp
- An item due at 14:30 becomes reviewable at 14:00
- This prevents "drip-feeding" of reviews throughout the hour

**Implementation:**
```python
def truncate_to_hour(dt: datetime) -> datetime:
    """Truncate datetime to hour precision for review batching."""
    return dt.replace(minute=0, second=0, microsecond=0)

# Query logic:
current_hour = truncate_to_hour(datetime.now(UTC))
# Include items where truncated next_review_at <= current_hour
```

### Query Optimization

- Index on `user_item_progress.next_review_at` for efficient filtering
- Index on `user_item_progress.user_id` already exists
- Eager load kanji/vocab details to avoid N+1 queries
- Consider composite index on (user_id, next_review_at, srs_stage) for optimal query

### Response Format

Each review item includes full details for immediate use:
```json
{
  "items": [
    {
      "item_type": "kanji",
      "item_id": 42,
      "srs_stage": 3,
      "next_review_at": "2026-01-24T14:00:00Z",
      "item_details": {
        "character": "日",
        "meanings": ["day", "sun"],
        "readings_on": ["ニチ", "ジツ"],
        "readings_kun": ["ひ", "か"]
      }
    },
    {
      "item_type": "vocab",
      "item_id": 123,
      "srs_stage": 5,
      "next_review_at": "2026-01-24T14:00:00Z",
      "item_details": {
        "word": "日本語",
        "reading": "にほんご",
        "meanings": ["Japanese language"]
      }
    }
  ],
  "count": 2
}
```

### Dependency on Story 5.1

This story depends on Story 5.1 for:
- ReviewLog model (created but not used in this story - used in 5.3)
- Review schemas base
- SRS constants

### Previous Story Context (Story 4.3)

From Story 4.3:
- UserItemProgress model with srs_stage and next_review_at fields
- KanjiItemDetails and VocabItemDetails schemas in progress/schemas.py
- Pattern for loading item details (kanji or vocab)

### Project Structure Notes

- Router mounts at `/api/v1/me/reviews` (not `/api/v1/reviews`)
- Uses `/me/` prefix because it's user-specific data
- Service pattern matches ProgressService from Story 4.1

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2]
- [Source: _bmad-output/planning-artifacts/epics.md#FR28 - Batch reviews by hour]
- [Source: _bmad-output/planning-artifacts/architecture.md#Service Layer Pattern]
- [Source: src/progress/models.py - UserItemProgress.next_review_at field]
- [Source: src/progress/schemas.py - KanjiItemDetails, VocabItemDetails]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

**Story 5.2 Implementation Complete - 2026-01-24**

✅ **All Acceptance Criteria Met:**
- AC1: Due reviews endpoint implemented with hour-batching (FR28)
- AC2: Empty response handling for users with no due items
- AC3: Authentication required (401 for unauthenticated requests)
- AC4: Router mounted at `/api/v1/me/reviews` in main.py
- AC5: ReviewService with get_due_reviews method implemented
- AC6: Hour-batching logic using truncate_to_hour function

✅ **All Tasks Completed:**
- Task 1: ReviewService created with full get_due_reviews implementation
- Task 2: truncate_to_hour helper function added to srs.py
- Task 3: Response schemas (ReviewItemResponse, DueReviewsResponse) created
- Task 4: Router endpoint with authentication and error handling
- Task 5: Router mounted in main.py at correct path
- Task 6: Comprehensive test suite covering all scenarios

✅ **Code Review Follow-ups Addressed:**
- All 8 review issues resolved (HIGH, MEDIUM, LOW priority items)
- Database indexes added for query optimization
- Error handling and logging implemented
- Test improvements using freezegun for deterministic hour-batching tests

✅ **Test Coverage:**
- Service tests: 10+ test cases covering all edge cases
- Router tests: 3+ integration tests with authentication scenarios
- SRS tests: 10+ tests for truncate_to_hour function
- All tests use freezegun for deterministic time-based testing

✅ **Documentation:**
- File List complete with all changed files
- Implementation notes in Dev Notes section
- Code comments explain hour-batching logic (FR28)
- Error handling documented in docstrings

### File List

<!-- File List was not populated during initial implementation due to agent interruption. Files changed in commit 102dd21: -->
- `src/main.py` - Added reviews router mount
- `src/reviews/router.py` - Created router with GET endpoint
- `src/reviews/schemas.py` - Added ReviewItemResponse and DueReviewsResponse schemas
- `src/reviews/service.py` - Created ReviewService with get_due_reviews method
- `src/reviews/srs.py` - Added truncate_to_hour function
- `tests/reviews/test_router.py` - Created router tests
- `tests/reviews/test_service.py` - Created service tests
- `tests/reviews/test_srs.py` - Added truncate_to_hour tests

<!-- Files changed during review feedback implementation: -->
- `alembic/versions/007_add_index_next_review_at.py` - Added database indexes for query optimization
- `src/reviews/service.py` - Optimized query with MySQL DATE_FORMAT, added logging and error handling
- `src/reviews/router.py` - Added error handling for database failures
- `tests/reviews/test_service.py` - Fixed hour-batching tests using freezegun
- `tests/reviews/test_router.py` - Fixed hour-batching tests using freezegun
- `pyproject.toml` - Added freezegun to dev dependencies
