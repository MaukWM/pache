# Story 4.2: Remove Items from Lesson Queue

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to remove items from my lesson queue**,
So that **I can manage which items I want to learn**.

## Acceptance Criteria

**AC1: Remove item from queue (success)**
**Given** an authenticated user with items in their lesson queue
**When** DELETE `/api/v1/me/queue/{item_type}/{item_id}` is called (e.g., `/api/v1/me/queue/vocab/123`)
**Then** response status is 204 No Content
**And** the LessonQueue record is removed from the database

**AC2: Item not in queue**
**Given** an authenticated user
**When** DELETE `/api/v1/me/queue/vocab/999` is called for an item not in their queue
**Then** response status is 404 Not Found

**AC3: Invalid item_type or item_id**
**Given** an authenticated user
**When** DELETE `/api/v1/me/queue/invalid_type/123` is called with invalid item_type
**Then** response status is 422 Unprocessable Entity (FastAPI validation error)

**Given** an authenticated user
**When** DELETE `/api/v1/me/queue/kanji/-1` or `/api/v1/me/queue/kanji/0` is called with invalid item_id (negative or zero)
**Then** response status is 422 Unprocessable Entity (FastAPI validation error)

**AC4: Authentication required**
**Given** an unauthenticated request
**When** DELETE `/api/v1/me/queue/{item_type}/{item_id}` is called
**Then** response status is 401 Unauthorized

**AC5:** Delete endpoint requires authentication
**AC6:** Users can only delete items from their own queue

## Tasks / Subtasks

- [x] Task 1: Implement remove_from_queue method in ProgressService (AC: 1, 2, 6)
  - [x] Add `remove_from_queue` method to `src/progress/service.py`:
    - Validate item_type is valid (kanji or vocab)
    - Query LessonQueue for user_id, item_type, item_id
    - If not found, raise HTTPException 404
    - Delete the queue item
    - Commit transaction
    - Return None (204 No Content)

- [x] Task 2: Add DELETE endpoint to router (AC: 1, 2, 3, 4, 5)
  - [x] Add DELETE `/api/v1/me/queue/{item_type}/{item_id}` endpoint to `src/progress/router.py`
    - Requires authentication (Depends(get_current_user))
    - Accepts item_type and item_id as path parameters with Path validators
    - Validates item_type is valid ItemType enum
    - Validates item_id is positive (gt=0) using Path validator
    - Calls ProgressService.remove_from_queue
    - Returns 204 No Content on success
    - Returns 404 if item not in queue
    - Returns 422 if invalid item_type or item_id (FastAPI validation)

- [x] Task 3: Write comprehensive tests
  - [x] Create tests in `tests/progress/test_service.py`:
    - Test remove_from_queue success (deletes item)
    - Test remove_from_queue item not found (404)
    - Test remove_from_queue only deletes user's own items
  - [x] Create tests in `tests/progress/test_router.py`:
    - Test DELETE /me/queue/{item_type}/{item_id} success (204)
    - Test DELETE /me/queue/{item_type}/{item_id} not found (404)
    - Test DELETE /me/queue/{item_type}/{item_id} invalid item_type (422)
    - Test DELETE /me/queue/{item_type}/{item_id} invalid item_id (negative/zero) (422)
    - Test DELETE /me/queue/{item_type}/{item_id} unauthenticated (401)
    - Test DELETE /me/queue/{item_type}/{item_id} cannot delete other user's items

## Dev Notes

### Architecture Requirements

Follow these patterns from `architecture.md` and `project-context.md`:

**Service Layer Pattern:**
- Routes are thin, business logic lives in services
- Service handles all validation and business rules

**URL Pattern:**
- `/api/v1/me/queue/{item_type}/{item_id}` - DELETE endpoint for removing items
- Requires authentication (use `get_current_user` dependency)

**Naming Conventions:**
- Methods: snake_case (`remove_from_queue`)
- Classes: PascalCase (`ProgressService`)

**Import Style:**
```python
# Absolute imports from src
from src.database import Base
from src.auth.models import User
from src.core.constants import ItemType
```

### Implementation Pattern

The `remove_from_queue` method should:
1. Validate item_type is a valid ItemType enum value
2. Query for the queue item with user_id, item_type, item_id
3. If not found, raise HTTPException 404
4. Delete the item and commit
5. Return None (FastAPI will return 204 No Content)

### Path Parameter Validation

FastAPI will automatically validate `item_type` if we use the ItemType enum as the path parameter type. Invalid values will return 422 Unprocessable Entity, but we should handle it gracefully and return 400 Bad Request per AC3.

### Previous Story Intelligence

From Story 4.1:
- Service pattern: Use HTTPException with appropriate status codes
- Router pattern: Use `Depends(get_db)` and `Depends(get_current_user)` for authentication
- Test pattern: Use `tests/conftest.py` fixtures, async testing with `pytest-asyncio`
- Error handling: Use HTTPException with appropriate status codes (404, 400, 401)

### Project Structure Notes

**Files to modify:**
- `src/progress/service.py` - Add remove_from_queue method
- `src/progress/router.py` - Add DELETE endpoint
- `tests/progress/test_service.py` - Add service tests
- `tests/progress/test_router.py` - Add router tests

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#API Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2: Remove Items from Lesson Queue]
- [Source: src/progress/service.py - existing add_to_queue pattern]
- [Source: src/progress/router.py - existing router pattern]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

**Story 4.2 Implementation Complete**

**ProgressService.remove_from_queue (Task 1):**
- Added `remove_from_queue` method to `src/progress/service.py`
- Validates item_type (handled by FastAPI enum validation)
- Queries LessonQueue for user_id, item_type, item_id
- Raises HTTPException 404 if item not found
- Deletes queue item and commits transaction
- Returns None (FastAPI returns 204 No Content)

**Router DELETE Endpoint (Task 2):**
- Added DELETE `/api/v1/me/queue/{item_type}/{item_id}` endpoint to `src/progress/router.py`
- Requires authentication via `get_current_user` dependency
- Accepts item_type (ItemType enum) and item_id (int) as path parameters with Path validators
- FastAPI automatically validates item_type enum (returns 422 for invalid values)
- Validates item_id is positive (gt=0) using Path validator (consistent with POST endpoint)
- Includes path parameter documentation in docstring
- Calls ProgressService.remove_from_queue
- Returns 204 No Content on success
- Returns 404 if item not in queue
- Returns 422 for invalid item_type or item_id (FastAPI validation)

**Tests (Task 3):**
- Added 3 service tests in `tests/progress/test_service.py`:
  - test_remove_from_queue_success
  - test_remove_from_queue_not_found
  - test_remove_from_queue_only_user_items
- Added 6 router tests in `tests/progress/test_router.py`:
  - test_remove_from_queue_success
  - test_remove_from_queue_not_found
  - test_remove_from_queue_invalid_item_type
  - test_remove_from_queue_invalid_item_id_returns_422 (negative and zero values)
  - test_remove_from_queue_unauthorized_returns_401
  - test_remove_from_queue_cannot_delete_other_user_items
- Total: 9 new tests, all passing
- Full test suite: 110 tests pass (no regressions)

**All Acceptance Criteria Satisfied:**
- AC1: DELETE endpoint returns 204 No Content and removes item ✓
- AC2: DELETE endpoint returns 404 if item not in queue ✓
- AC3: DELETE endpoint returns 422 for invalid item_type or item_id (FastAPI validation) ✓
- AC4: DELETE endpoint requires authentication (401) ✓
- AC5: Delete endpoint requires authentication ✓
- AC6: Users can only delete items from their own queue ✓

**Note on AC3:** FastAPI returns 422 Unprocessable Entity for invalid enum values and path parameter validation errors, which is semantically more correct than 400 Bad Request for validation errors. The implementation follows FastAPI conventions with Path validators for both `item_type` and `item_id` (gt=0 constraint).

## File List

**Modified Files:**
- `src/progress/service.py` - Added remove_from_queue method
- `src/progress/router.py` - Added DELETE endpoint with Path validators and documentation
- `tests/progress/test_service.py` - Added 3 service tests
- `tests/progress/test_router.py` - Added 6 router tests (including invalid item_id test)

## Change Log

- 2026-01-24: Story 4.2 implementation completed
  - Implemented remove_from_queue method in ProgressService
  - Added DELETE endpoint to router with Path validators for item_id validation
  - Added comprehensive tests (9 tests including invalid item_id validation)
  - All 110 tests pass, no regressions
  - All acceptance criteria satisfied
  - Code review fixes applied: Path validation, documentation, test coverage