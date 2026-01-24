# Story 5.2: View Items Due for Review

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to see items that are due for review**,
So that **I know what to study next**.

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

**AC3: Limit parameter**
**Given** an authenticated user
**When** GET `/api/v1/me/reviews?limit=10` is called with optional limit parameter
**Then** response returns at most 10 items
**And** items are ordered by next_review_at (oldest first)

**AC4: Authentication required**
**Given** an unauthenticated request
**When** GET `/api/v1/me/reviews` is called
**Then** response status is 401 Unauthorized

**AC5:** `src/reviews/router.py` mounts at `/api/v1/me/reviews`

**AC6:** `src/reviews/service.py` contains `ReviewService` with `get_due_reviews` method

**AC7:** Hour-batching logic truncates timestamps to hour precision before comparison

## Tasks / Subtasks

- [ ] Task 1: Create ReviewService (AC: 6, 7)
  - [ ] Create `src/reviews/service.py`
  - [ ] Add ReviewService class with `__init__(self, db: AsyncSession)`
  - [ ] Implement `get_due_reviews(user_id: int, limit: int | None = None) -> list[ReviewItemResponse]`:
    - Query UserItemProgress for user
    - Filter where srs_stage < 9 (not burned)
    - Filter where next_review_at is not None
    - Truncate current time to hour precision
    - Filter where next_review_at (truncated to hour) <= current_hour
    - Order by next_review_at ascending (oldest first)
    - Apply limit if provided
    - Eagerly load item details (kanji or vocab)
    - Return formatted response with item details

- [ ] Task 2: Add hour truncation helper (AC: 7)
  - [ ] Add `truncate_to_hour(dt: datetime) -> datetime` function to `src/reviews/srs.py`
  - [ ] Function should set minute, second, microsecond to 0
  - [ ] Use for both query filter and timestamp comparison

- [ ] Task 3: Create response schemas (AC: 1)
  - [ ] Add to `src/reviews/schemas.py`:
    - ReviewItemResponse schema:
      - item_type: ItemType
      - item_id: int
      - srs_stage: int
      - next_review_at: datetime
      - item_details: KanjiItemDetails | VocabItemDetails (union type)
    - DueReviewsResponse schema:
      - items: list[ReviewItemResponse]
      - count: int
  - [ ] Import KanjiItemDetails and VocabItemDetails from progress schemas

- [ ] Task 4: Create router endpoint (AC: 1, 2, 3, 4, 5)
  - [ ] Create `src/reviews/router.py`
  - [ ] Add GET `/api/v1/me/reviews` endpoint:
    - Requires authentication (Depends(get_current_user))
    - Optional query param: limit (int, default None)
    - Calls ReviewService.get_due_reviews
    - Returns DueReviewsResponse
    - Handles 401 for unauthenticated

- [ ] Task 5: Mount router in main.py
  - [ ] Import reviews router
  - [ ] Mount at `/api/v1/me/reviews`

- [ ] Task 6: Write comprehensive tests
  - [ ] Create `tests/reviews/test_service.py`:
    - Test get_due_reviews returns due items
    - Test get_due_reviews excludes burned items (srs_stage=9)
    - Test get_due_reviews excludes items with future next_review_at
    - Test get_due_reviews hour batching (items due within current hour included)
    - Test get_due_reviews respects limit parameter
    - Test get_due_reviews orders by next_review_at ascending
    - Test get_due_reviews returns empty list when no items due
    - Test get_due_reviews includes correct item details (kanji vs vocab)
  - [ ] Create `tests/reviews/test_router.py`:
    - Test GET /me/reviews returns due items
    - Test GET /me/reviews with limit parameter
    - Test GET /me/reviews empty response
    - Test GET /me/reviews unauthenticated (401)
  - [ ] Add tests to `tests/reviews/test_srs.py`:
    - Test truncate_to_hour function

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

### File List

