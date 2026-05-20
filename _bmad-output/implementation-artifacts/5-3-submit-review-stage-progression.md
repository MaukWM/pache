# Story 5.3: Submit Review with Stage Progression

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to submit review results for an item**,
So that **items progress through SRS stages based on my performance**.

## Acceptance Criteria

**AC1: Submit review with both reading and meaning**
**Given** an authenticated user with an item in UserItemProgress at stage 3
**When** POST `/api/v1/me/reviews` is called with:
```json
{
  "item_type": "vocab",
  "item_id": 123,
  "reading_correct": true,
  "meaning_correct": true
}
```
**Then** response status is 200
**And** a ReviewLog record is created with:
  - `reading_correct: true`, `meaning_correct: true`
  - `srs_stage_before: 3`, `srs_stage_after: 4`
  - `reviewed_at` set to current timestamp
**And** UserItemProgress is updated:
  - `srs_stage` advances from 3 to 4 (both reading and meaning passed - FR26)
  - `next_review_at` is calculated using `calculate_next_review(3, correct=True)` which uses SRS_INTERVALS[3] = 1 day from now
**And** response includes ReviewResponse with new stage and next_review_at

**AC2: Incorrect answer handling (both incorrect)**
**Given** an authenticated user with an item at stage 5
**When** POST `/api/v1/me/reviews` is called with:
```json
{
  "item_type": "vocab",
  "item_id": 123,
  "reading_correct": false,
  "meaning_correct": false
}
```
**Then** response status is 200
**And** ReviewLog record is created with:
  - `reading_correct: false`, `meaning_correct: false`
  - `srs_stage_before: 5`, `srs_stage_after: 3` (drops ~2 stages, minimum 1 - FR27)
**And** UserItemProgress is updated:
  - `srs_stage` drops from 5 to 3
  - `next_review_at` is recalculated using `calculate_next_review(5, correct=False)` which uses SRS_INTERVALS[3]

**AC3: Mixed result (one correct, one incorrect)**
**Given** an authenticated user with an item at stage 4
**When** POST `/api/v1/me/reviews` is called with:
```json
{
  "item_type": "vocab",
  "item_id": 123,
  "reading_correct": false,
  "meaning_correct": true
}
```
**Then** response status is 200
**And** ReviewLog record is created with both correctness values
**And** UserItemProgress stage drops (because reading failed - FR26: both must pass)
**And** `srs_stage` drops from 4 to 2 (max(1, 4-2))
**And** `next_review_at` is recalculated for the new stage

**AC4: Burn item (advance to stage 9)**
**Given** an authenticated user with an item at stage 8
**When** POST `/api/v1/me/reviews` is called with both correct:
```json
{
  "item_type": "vocab",
  "item_id": 123,
  "reading_correct": true,
  "meaning_correct": true
}
```
**Then** response status is 200
**And** ReviewLog record is created with `srs_stage_after: 9`
**And** UserItemProgress is updated:
  - `srs_stage` advances to 9 (burned)
  - `burned_at` is set to current timestamp
  - `next_review_at` is set to None (no more reviews)
**And** response indicates item is burned

**AC5: Item not in progress**
**Given** an authenticated user submits review for item not in their UserItemProgress
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 400 Bad Request with error message indicating item not in progress

**AC6: Burned item rejection**
**Given** an authenticated user submits review for item at stage 9 (burned)
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 400 Bad Request with error indicating item is burned

**AC6b: Item not yet due for review**
**Given** an authenticated user submits review for item where `next_review_at` is in the future
**When** POST `/api/v1/me/reviews` is called (e.g., reviewing a stage 8 item with 4 month wait after only 1 day)
**Then** response status is 400 Bad Request with error indicating item is not yet due for review

**AC7: Invalid request validation**
**Given** an authenticated user submits review with invalid fields
**When** POST `/api/v1/me/reviews` is called with:
  - Missing `reading_correct` or `meaning_correct`
  - Invalid `item_type` (not "kanji" or "vocab")
  - Invalid `item_id` (non-positive)
**Then** response status is 400 Bad Request with validation error

**AC8: Authentication required**
**Given** an unauthenticated request
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 401 Unauthorized

**AC9:** Review submission responds within 500ms under normal conditions (NFR1)

**AC10:** `src/reviews/service.py` contains `submit_review` method with:
  - ReviewLog creation logic (single record with both reading_correct and meaning_correct)
  - Stage progression logic (immediate evaluation based on both correctness values)
  - SRS interval calculation using `src/reviews/srs.py::calculate_next_review`
  - Transaction handling to ensure data consistency

## Tasks / Subtasks

- [x] Task 1: Add submit_review to ReviewService (AC: 1, 2, 3, 4, 10)
  - [x] Add `submit_review(user_id: int, request: ReviewCreateRequest) -> ReviewResponse` method
  - [x] Verify item exists in UserItemProgress for user
  - [x] Verify item is not burned (srs_stage < 9)
  - [x] Verify item is due for review (next_review_at is None, in the past, or current hour)
  - [x] Determine correctness: `correct = reading_correct and meaning_correct` (FR26: both must pass)
  - [x] Get current stage from UserItemProgress
  - [x] Calculate new stage and next_review_at using `calculate_next_review(current_stage, correct)`
  - [x] Create ReviewLog entry with:
    - user_id, item_type, item_id
    - reading_correct, meaning_correct (both stored in single record)
    - srs_stage_before = current srs_stage
    - srs_stage_after = calculated new_stage
    - reviewed_at = current timestamp
  - [x] Update UserItemProgress with new srs_stage and next_review_at
  - [x] If stage becomes 9, set burned_at timestamp and next_review_at = None
  - [x] Return ReviewResponse with all details

- [x] Task 2: Create response schema (AC: 1)
  - [x] Verify `ReviewResponse` schema exists in `src/reviews/schemas.py`:
    - item_type: ItemType
    - item_id: int
    - reading_correct: bool
    - meaning_correct: bool
    - srs_stage_before: int
    - srs_stage_after: int
    - next_review_at: datetime | None
  - [x] Schema should match ReviewLog model structure

- [x] Task 3: Create router endpoint (AC: 1, 5, 6, 7, 8)
  - [x] Add POST `/api/v1/me/reviews` endpoint to `src/reviews/router.py`:
    - Requires authentication (Depends(get_current_user))
    - Accepts ReviewCreateRequest
    - Calls ReviewService.submit_review
    - Returns ReviewResponse
    - Handles 400 errors (not in progress, burned, validation)
    - Handles 401 for unauthenticated

- [x] Task 4: Ensure transaction safety (AC: 10)
  - [x] Wrap submit_review logic in database transaction
  - [x] Ensure ReviewLog creation and UserItemProgress update are atomic
  - [x] Handle concurrent submission edge cases (database constraints prevent duplicates)

- [x] Task 5: Write comprehensive tests
  - [x] Add to `tests/reviews/test_service.py`:
    - Test submit_review creates ReviewLog with both reading_correct and meaning_correct
    - Test submit_review advances stage when both correct
    - Test submit_review drops stage when both incorrect
    - Test submit_review drops stage when reading incorrect (meaning correct)
    - Test submit_review drops stage when meaning incorrect (reading correct)
    - Test submit_review burns item at stage 8 with both correct
    - Test submit_review sets burned_at when reaching stage 9
    - Test submit_review sets next_review_at to None when burned
    - Test submit_review item not in progress (400)
    - Test submit_review burned item (400)
    - Test submit_review item not yet due for review (400) - including stage 8 with 4 month wait
    - Test submit_review calculates correct next_review_at using SRS_INTERVALS
    - Test submit_review transaction atomicity
  - [x] Add to `tests/reviews/test_router.py`:
    - Test POST /me/reviews successful submission
    - Test POST /me/reviews not in progress (400)
    - Test POST /me/reviews burned (400)
    - Test POST /me/reviews not yet due for review (400)
    - Test POST /me/reviews missing fields (400)
    - Test POST /me/reviews invalid item_type (400)
    - Test POST /me/reviews unauthenticated (401)

## Dev Notes

### Architecture Requirements

- Follow service layer pattern: routers → services → models
- Use async SQLAlchemy 2.0 patterns
- Transaction handling for atomic operations
- Performance target: 500ms response time (NFR1)

### Simplified Review Flow (FR26)

**Critical Rule:** Both reading AND meaning must pass to advance stage.

The frontend validates correctness (user types answer, frontend checks). Backend receives both `reading_correct` and `meaning_correct` in a single request.

**Simplified Flow:**
1. User submits review with both reading and meaning results in one request
2. Backend evaluates: `correct = reading_correct and meaning_correct`
3. Backend immediately updates stage based on correctness
4. Single ReviewLog record created with both correctness values

**No Session Tracking Needed:**
- Previous design required tracking separate reading/meaning submissions
- Simplified design: both submitted together, immediate evaluation
- No need to query recent ReviewLogs or track session state

### Stage Progression Logic

The `calculate_next_review` function in `src/reviews/srs.py` handles stage progression:

```python
def calculate_next_review(current_stage: int, correct: bool) -> tuple[int, datetime | None]:
    if correct:
        # Advance to next stage (max 9)
        new_stage = min(9, current_stage + 1)
        if new_stage == 9:
            return (9, None)  # Burned - no more reviews
        next_review_at = datetime.now(UTC) + SRS_INTERVALS[current_stage]
        return (new_stage, next_review_at)
    else:
        # Drop ~2 stages (minimum 1)
        new_stage = max(1, current_stage - 2)
        next_review_at = datetime.now(UTC) + SRS_INTERVALS[new_stage]
        return (new_stage, next_review_at)
```

**Usage in submit_review:**
```python
correct = request.reading_correct and request.meaning_correct
new_stage, next_review_at = calculate_next_review(current_stage, correct)
```

### Burning Items

When an item reaches stage 9:
- Set `srs_stage = 9`
- Set `burned_at = datetime.now(UTC)`
- Set `next_review_at = None` (no more reviews needed)

### Performance Considerations (NFR1)

Target: 500ms response time

Optimizations:
- Single query for UserItemProgress lookup
- Single ReviewLog insert
- Single UserItemProgress update
- Minimal database round-trips
- Transaction scope kept minimal

### Concurrency Edge Case

If user rapidly submits multiple reviews simultaneously:
- Database constraints prevent duplicate ReviewLog entries
- Transaction isolation ensures consistent state
- Worst case: one submission processes first, second sees updated state

### Dependencies

- Story 5.1: ReviewLog model, SRS calculation function (`calculate_next_review`)
- Story 5.2: ReviewService class (extend it), router structure
- Story 4.3: UserItemProgress model

### Project Structure Notes

- POST endpoint same path as GET: `/api/v1/me/reviews`
- Router handles both GET (due reviews) and POST (submit review)
- Service methods: `get_due_reviews` (5.2) and `submit_review` (this story)
- ReviewLog model stores both `reading_correct` and `meaning_correct` in single record (from Story 5.1, but simplified)

### Key Implementation Details

**ReviewCreateRequest Schema:**
- `item_type: ItemType` (kanji or vocab)
- `item_id: int` (must be > 0)
- `reading_correct: bool` (required)
- `meaning_correct: bool` (required)

**ReviewLog Model:**
- Stores both `reading_correct` and `meaning_correct` in single record
- No `review_type` field (simplified design)
- Single record per review submission

**Stage Evaluation:**
- `correct = reading_correct and meaning_correct` (both must pass - FR26)
- If correct: advance stage
- If incorrect: drop ~2 stages (minimum 1 - FR27)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3]
- [Source: _bmad-output/planning-artifacts/epics.md#FR26 - Both reading and meaning must pass]
- [Source: _bmad-output/planning-artifacts/epics.md#FR27 - Incorrect drops ~2 stages]
- [Source: _bmad-output/planning-artifacts/epics.md#NFR1 - 500ms response time]
- [Source: _bmad-output/planning-artifacts/architecture.md#Service Layer Pattern]
- [Source: src/reviews/srs.py - calculate_next_review function (from Story 5.1)]
- [Source: src/reviews/models.py - ReviewLog model (from Story 5.1, simplified)]
- [Source: src/reviews/schemas.py - ReviewCreateRequest and ReviewResponse schemas]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- ✅ Implemented `submit_review` method in ReviewService with full SRS stage progression logic
- ✅ Added POST `/api/v1/me/reviews` endpoint with authentication and error handling
- ✅ Verified ReviewResponse schema already exists and matches requirements
- ✅ Implemented transaction safety with commit/rollback for atomic operations
- ✅ Added validation to prevent reviewing items before they're due (checks next_review_at)
- ✅ Added comprehensive test coverage for all acceptance criteria:
  - Service tests: stage advancement, stage dropping, burning items, edge cases, transaction atomicity
  - Service tests: item not yet due validation (including stage 8 with 4 month wait)
  - Router tests: successful submission, validation errors, authentication, error handling
  - Router tests: item not yet due for review error handling
- ✅ All tests follow red-green-refactor cycle and cover all acceptance criteria

### File List

- `src/reviews/service.py` - Added `submit_review` method
- `src/reviews/router.py` - Added POST `/api/v1/me/reviews` endpoint
- `tests/reviews/test_service.py` - Added comprehensive service tests for submit_review
- `tests/reviews/test_router.py` - Added router tests for POST endpoint
