# Story 5.4: Resurrect Burned Items

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to resurrect burned items**,
So that **I can review items I've forgotten**.

## Acceptance Criteria

**AC1: Resurrect burned item**
**Given** an authenticated user with an item at stage 9 (burned) in UserItemProgress
**When** POST `/api/v1/me/progress/{item_type}/{item_id}/resurrect` is called
**Then** response status is 200
**And** UserItemProgress is updated:
  - `srs_stage` is reset to 1 (Apprentice 1)
  - `burned_at` is set to NULL
  - `next_review_at` is recalculated based on stage 1 (4 hours from now)
  - `unlocked_at` remains unchanged
**And** response includes updated progress item

**AC2: Item not burned**
**Given** an authenticated user with an item not at stage 9
**When** POST `/api/v1/me/progress/{item_type}/{item_id}/resurrect` is called
**Then** response status is 400 Bad Request with error indicating item is not burned

**AC3: Item not found**
**Given** an authenticated user attempting to resurrect an item not in their UserItemProgress
**When** POST `/api/v1/me/progress/{item_type}/{item_id}/resurrect` is called
**Then** response status is 404 Not Found

**AC4: Authentication required**
**Given** an unauthenticated request
**When** POST `/api/v1/me/progress/{item_type}/{item_id}/resurrect` is called
**Then** response status is 401 Unauthorized

**AC5:** Resurrection endpoint is added to `src/progress/router.py`

**AC6:** `src/progress/service.py` contains `resurrect_item` method

**AC7:** Resurrection creates a ReviewLog entry indicating the resurrection action

## Tasks / Subtasks

- [ ] Task 1: Add resurrect_item to ProgressService (AC: 1, 6, 7)
  - [ ] Add `resurrect_item(user_id: int, item_type: ItemType, item_id: int) -> ProgressResponse` method to `src/progress/service.py`
  - [ ] Query UserItemProgress for (user_id, item_type, item_id)
  - [ ] If not found: raise 404 Not Found
  - [ ] If srs_stage != 9: raise 400 Bad Request "Item is not burned"
  - [ ] Update UserItemProgress:
    - srs_stage = 1
    - burned_at = None
    - next_review_at = now + 4 hours (SRS_INTERVALS[1])
    - Keep unlocked_at unchanged
  - [ ] Create ReviewLog entry to track resurrection:
    - review_type could be a special value or use existing enum
    - Alternative: Create separate ResurrectionLog model or use metadata
    - Recommended: Create ReviewLog with srs_stage_before=9, srs_stage_after=1, and special marker
  - [ ] Return updated ProgressResponse

- [ ] Task 2: Handle resurrection tracking (AC: 7)
  - [ ] Option A: Add `resurrection` to ReviewType enum
  - [ ] Option B: Create separate log/audit mechanism
  - [ ] Option C: Use ReviewLog with null review_type or special flag
  - [ ] **Recommended: Option A** - Add ReviewType.resurrection enum value
  - [ ] Create ReviewLog with:
    - user_id, item_type, item_id
    - review_type = ReviewType.resurrection
    - correct = True (or None if nullable)
    - srs_stage_before = 9
    - srs_stage_after = 1
    - reviewed_at = current timestamp

- [ ] Task 3: Add ReviewType.resurrection enum (AC: 7)
  - [ ] Update `src/core/constants.py`:
    - Add `resurrection` to ReviewType enum
  - [ ] Update ReviewLog model if needed for nullable correct field

- [ ] Task 4: Create response schema (AC: 1)
  - [ ] Add ResurrectResponse schema to `src/progress/schemas.py` (or reuse ProgressResponse):
    - item_type: ItemType
    - item_id: int
    - srs_stage: int (will be 1)
    - next_review_at: datetime
    - unlocked_at: datetime
    - message: str (e.g., "Item resurrected successfully")

- [ ] Task 5: Create router endpoint (AC: 1, 2, 3, 4, 5)
  - [ ] Add POST `/api/v1/me/progress/{item_type}/{item_id}/resurrect` endpoint to `src/progress/router.py`:
    - Requires authentication (Depends(get_current_user))
    - Path params: item_type (ItemType enum), item_id (int)
    - Calls ProgressService.resurrect_item
    - Returns ResurrectResponse
    - Handles 400 (not burned)
    - Handles 404 (not found)
    - Handles 401 (unauthenticated)

- [ ] Task 6: Write comprehensive tests
  - [ ] Add to `tests/progress/test_service.py`:
    - Test resurrect_item resets stage to 1
    - Test resurrect_item clears burned_at
    - Test resurrect_item sets next_review_at to 4 hours
    - Test resurrect_item keeps unlocked_at unchanged
    - Test resurrect_item creates ReviewLog
    - Test resurrect_item not burned (400)
    - Test resurrect_item not found (404)
  - [ ] Add to `tests/progress/test_router.py`:
    - Test POST resurrect endpoint success
    - Test POST resurrect not burned (400)
    - Test POST resurrect not found (404)
    - Test POST resurrect unauthenticated (401)
    - Test POST resurrect invalid item_type (400/422)

## Dev Notes

### Architecture Requirements

- Follow service layer pattern: routers → services → models
- Use async SQLAlchemy 2.0 patterns
- Transaction for atomic update + log creation

### Resurrection Logic

When an item is resurrected:
1. Verify item exists in UserItemProgress
2. Verify srs_stage == 9 (burned)
3. Reset to starting SRS state:
   - `srs_stage = 1` (Apprentice 1)
   - `burned_at = None`
   - `next_review_at = now + 4 hours`
   - `unlocked_at` stays the same (original lesson date preserved)
4. Create audit trail via ReviewLog

### Tracking Resurrection (AC7)

**Why track?**
- Audit trail for user activity
- Analytics on which items users forget
- Debugging/support purposes

**Implementation Decision:**
Add `resurrection` to ReviewType enum. This keeps the system simple:
- Single ReviewLog table for all review-related events
- Consistent querying for review history
- No additional tables needed

```python
class ReviewType(str, Enum):
    reading = "reading"
    meaning = "meaning"
    resurrection = "resurrection"  # NEW
```

For resurrection ReviewLog:
- `review_type = "resurrection"`
- `correct = True` (resurrection is always "successful")
- `srs_stage_before = 9`
- `srs_stage_after = 1`

### Endpoint Path Design

Path: `/api/v1/me/progress/{item_type}/{item_id}/resurrect`

Why this structure:
- Under `/me/progress/` since it modifies user progress
- Path params identify the specific item
- `resurrect` action as trailing path segment
- Consistent with REST conventions for actions on resources

### Error Messages

- 404: "Item not found in your progress"
- 400 (not burned): "Item is not burned (current stage: {stage})"
- 401: Standard authentication error

### Dependencies

- Story 5.1: ReviewLog model, ReviewType enum (extend it)
- Story 4.3: UserItemProgress model, SRS_INTERVALS

### Previous Story Patterns

From Story 4.2 (remove from queue):
- Similar path pattern: `/api/v1/me/queue/{item_type}/{item_id}`
- Similar error handling approach
- Reference for endpoint structure

### Project Structure Notes

- Endpoint added to `src/progress/router.py` (existing router)
- Method added to `src/progress/service.py` (ProgressService)
- This is the simplest story in Epic 5

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.4]
- [Source: _bmad-output/planning-artifacts/epics.md#FR29 - Resurrect burned items]
- [Source: _bmad-output/planning-artifacts/architecture.md#Service Layer Pattern]
- [Source: src/progress/models.py - UserItemProgress.burned_at field]
- [Source: src/progress/router.py - existing progress endpoints pattern]
- [Source: src/core/constants.py - SRS_INTERVALS for stage 1 interval]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
