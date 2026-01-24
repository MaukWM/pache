# Story 5.3: Submit Review with Stage Progression

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to submit review results for an item**,
So that **items progress through SRS stages based on my performance**.

## Acceptance Criteria

**AC1: Submit single review (reading or meaning)**
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
**And** response includes the submitted review result

**AC2: Complete review session (both reading and meaning correct)**
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
  - `next_review_at` is calculated using SRS_INTERVALS (2 days from now for stage 3→4)
**And** response indicates session complete with new stage

**AC3: Incorrect answer handling**
**Given** an authenticated user submits a review with `correct: false`
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 200
**And** ReviewLog record is created
**And** if both reading and meaning have been submitted:
  - UserItemProgress `srs_stage` drops ~2 stages (minimum stage 1) (FR27)
  - `next_review_at` is recalculated based on new stage

**AC4: Mixed result (one correct, one incorrect)**
**Given** an authenticated user submits reading review with `correct: false`
**When** meaning review is then submitted with `correct: true`
**Then** UserItemProgress stage drops (because reading failed - FR26: both must pass)
**And** `next_review_at` is recalculated for the new (lower) stage

**AC5: Item not in progress**
**Given** an authenticated user submits review for item not in their UserItemProgress
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 400 Bad Request with error message

**AC6: Burned item rejection**
**Given** an authenticated user submits review for item at stage 9 (burned)
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 400 Bad Request with error indicating item is burned

**AC7: Invalid review type**
**Given** an authenticated user submits review with invalid `review_type`
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 400 Bad Request with validation error

**AC8: Authentication required**
**Given** an unauthenticated request
**When** POST `/api/v1/me/reviews` is called
**Then** response status is 401 Unauthorized

**AC9:** Review submission responds within 500ms under normal conditions (NFR1)

**AC10:** `src/reviews/service.py` contains `submit_review` method with:
  - ReviewLog creation logic
  - Stage progression logic (only when both reading and meaning submitted)
  - SRS interval calculation using `src/reviews/srs.py`
  - Transaction handling to ensure data consistency

## Tasks / Subtasks

- [ ] Task 1: Add review submission to ReviewService (AC: 1, 2, 3, 4, 10)
  - [ ] Add `submit_review(user_id: int, request: ReviewCreateRequest) -> ReviewSubmitResponse` method
  - [ ] Verify item exists in UserItemProgress for user
  - [ ] Verify item is not burned (srs_stage < 9)
  - [ ] Create ReviewLog entry with:
    - user_id, item_type, item_id, review_type, correct
    - srs_stage_before = current srs_stage
    - srs_stage_after = calculated (may be same if session incomplete)
    - reviewed_at = current timestamp
  - [ ] Check if review session is complete (both reading and meaning submitted)
  - [ ] If session complete, calculate new stage using `calculate_next_review`
  - [ ] Update UserItemProgress with new srs_stage and next_review_at
  - [ ] If stage becomes 9, set burned_at timestamp
  - [ ] Return response indicating session status and new stage if complete

- [ ] Task 2: Implement review session tracking (AC: 2, 3, 4)
  - [ ] Add helper method `_get_pending_reviews(user_id: int, item_type: ItemType, item_id: int) -> tuple[ReviewLog | None, ReviewLog | None]`
  - [ ] Query ReviewLog for recent reviews (reading and meaning) in current session
  - [ ] Session defined as: reviews for same item since last stage update
  - [ ] Alternative approach: track by reviewed_at timestamp within a window (e.g., 24 hours)
  - [ ] Determine if both reading and meaning submitted and their correctness

- [ ] Task 3: Add session determination logic (AC: 2, 3, 4)
  - [ ] When both reading and meaning submitted:
    - If BOTH correct: advance stage (current_stage + 1)
    - If EITHER incorrect: drop stage (max(1, current_stage - 2))
  - [ ] Calculate next_review_at using SRS_INTERVALS for new stage
  - [ ] Handle stage 9 (burned): set burned_at, next_review_at = None

- [ ] Task 4: Create response schemas (AC: 1, 2)
  - [ ] Add to `src/reviews/schemas.py`:
    - ReviewSubmitResponse schema:
      - review_id: int (the created ReviewLog id)
      - item_type: ItemType
      - item_id: int
      - review_type: ReviewType
      - correct: bool
      - session_complete: bool
      - new_srs_stage: int | None (only if session complete)
      - next_review_at: datetime | None (only if session complete)
      - burned: bool (true if item reached stage 9)

- [ ] Task 5: Create router endpoint (AC: 1, 5, 6, 7, 8)
  - [ ] Add POST `/api/v1/me/reviews` endpoint to `src/reviews/router.py`:
    - Requires authentication (Depends(get_current_user))
    - Accepts ReviewCreateRequest
    - Calls ReviewService.submit_review
    - Returns ReviewSubmitResponse
    - Handles 400 errors (not in progress, burned, validation)
    - Handles 401 for unauthenticated

- [ ] Task 6: Ensure transaction safety (AC: 10)
  - [ ] Wrap submit_review logic in transaction
  - [ ] Ensure ReviewLog and UserItemProgress updates are atomic
  - [ ] Handle concurrent submission edge cases

- [ ] Task 7: Write comprehensive tests
  - [ ] Add to `tests/reviews/test_service.py`:
    - Test submit_review creates ReviewLog
    - Test submit_review does not update stage on first submission (reading only)
    - Test submit_review does not update stage on first submission (meaning only)
    - Test submit_review advances stage when both correct
    - Test submit_review drops stage when reading incorrect
    - Test submit_review drops stage when meaning incorrect
    - Test submit_review drops stage when both incorrect
    - Test submit_review burns item at stage 8 with correct answers
    - Test submit_review item not in progress (400)
    - Test submit_review burned item (400)
    - Test submit_review calculates correct next_review_at
    - Test submit_review transaction atomicity
  - [ ] Add to `tests/reviews/test_router.py`:
    - Test POST /me/reviews first submission
    - Test POST /me/reviews session complete
    - Test POST /me/reviews not in progress (400)
    - Test POST /me/reviews burned (400)
    - Test POST /me/reviews invalid review_type (400)
    - Test POST /me/reviews unauthenticated (401)

## Dev Notes

### Architecture Requirements

- Follow service layer pattern: routers → services → models
- Use async SQLAlchemy 2.0 patterns
- Transaction handling for atomic operations
- Performance target: 500ms response time (NFR1)

### Review Session Logic (FR26)

**Critical Rule:** Both reading AND meaning must pass to advance.

The frontend validates correctness (user types answer, frontend checks). Backend receives a simple correct/incorrect result for each review type.

**Session Flow:**
1. User reviews reading → Backend records ReviewLog, stage unchanged
2. User reviews meaning → Backend records ReviewLog, checks session
3. If both submitted: evaluate and update stage

**Session Tracking Options:**

Option A: Query recent ReviewLogs
- Find ReviewLogs for this (user, item_type, item_id) since last stage change
- Session complete when both reading and meaning found

Option B: Track last review timestamp on UserItemProgress
- Add `last_review_started_at` field
- Reset when stage changes
- Session = reviews since last_review_started_at

**Recommended: Option A** - simpler, no schema changes

### Stage Progression Logic

```python
def determine_new_stage(current_stage: int, reading_correct: bool, meaning_correct: bool) -> int:
    if reading_correct and meaning_correct:
        # Advance (cap at 9)
        return min(9, current_stage + 1)
    else:
        # Drop ~2 stages (minimum 1)
        return max(1, current_stage - 2)
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
- Efficient ReviewLog queries with proper indexes
- Minimal database round-trips
- Transaction scope kept minimal

### Concurrency Edge Case

If user rapidly submits reading and meaning simultaneously:
- Database constraints prevent issues
- Transaction isolation ensures consistent state
- Worst case: one submission processes first, second sees updated state

### Dependencies

- Story 5.1: ReviewLog model, SRS calculation function
- Story 5.2: ReviewService class (extend it)
- Story 4.3: UserItemProgress model

### Project Structure Notes

- POST endpoint same path as GET: `/api/v1/me/reviews`
- Router handles both GET (due reviews) and POST (submit review)
- Service methods: `get_due_reviews` (5.2) and `submit_review` (this story)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3]
- [Source: _bmad-output/planning-artifacts/epics.md#FR26 - Both reading and meaning must pass]
- [Source: _bmad-output/planning-artifacts/epics.md#FR27 - Incorrect drops ~2 stages]
- [Source: _bmad-output/planning-artifacts/epics.md#NFR1 - 500ms response time]
- [Source: _bmad-output/planning-artifacts/architecture.md#Service Layer Pattern]
- [Source: src/reviews/srs.py - calculate_next_review function (from Story 5.1)]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

