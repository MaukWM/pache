# Story 4.3: Complete Lessons with Prerequisite Enforcement

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to complete lessons for any learnable item (single or batch)**,
So that **I can move items into SRS rotation with one action, without requiring queue membership**.

## Acceptance Criteria

**AC1: UserItemProgress model**
**Given** the database from Story 4.1
**When** the UserItemProgress model is created
**Then** `src/progress/models.py` defines:

**UserItemProgress model:**
- `id` (primary key)
- `user_id` (FK to users, indexed)
- `item_type` (enum: kanji | vocab, discriminator)
- `item_id` (FK to kanji or vocab)
- `srs_stage` (integer, 1-9: 1-4=apprentice, 5-6=guru, 7=master, 8=enlightened, 9=burned)
- `next_review_at` (nullable datetime, set when item enters SRS)
- `unlocked_at` (datetime, when lesson was completed)
- `burned_at` (nullable datetime)
- `meaning_note` (nullable text, user's custom explanation)
- `reading_mnemonic` (nullable text, user's custom mnemonic)
- `source` (enum: manual | wanikani, default: manual)
- Composite unique constraint on `(user_id, item_type, item_id)`

**AC2:** Alembic migration creates `user_item_progress` table

**AC3:** `src/progress/schemas.py` defines `LessonCompleteRequest`, `LessonCompleteResponse`, `LessonItemResponse`, `SelectedItem`

**AC4: Lesson completion (queue NOT required)**
**Given** an authenticated user
**When** POST `/api/v1/me/lessons` is called with:
```json
{
  "item_ids": [
    {"item_type": "kanji", "item_id": 42},
    {"item_type": "vocab", "item_id": 123}
  ]
}
```
**Then** response status is 200
**And** UserItemProgress records are created for each specified item
**And** for each completed item:
  - A UserItemProgress record is created with `srs_stage=1` (Apprentice 1)
  - `unlocked_at` is set to current timestamp
  - `next_review_at` is set to 4 hours from now (WaniKani interval)
  - If item was in user's LessonQueue, it is auto-removed
**And** response includes list of completed lesson items with srs_stage and next_review_at

**AC5: Prerequisite enforcement for vocab**
**Given** an authenticated user attempting to lesson a vocab item
**When** the vocab item has constituent kanji that are NOT in the user's UserItemProgress at GURU stage (srs_stage >= 5)
**Then** response status is 400 Bad Request
**And** error message indicates which kanji prerequisites are missing (FR22 - prerequisite enforcement)

**AC6: Prerequisite satisfied**
**Given** an authenticated user attempting to lesson a vocab item
**When** all constituent kanji are in the user's UserItemProgress with `srs_stage >= 5` (GURU stage)
**Then** the vocab lesson completes successfully
**And** UserItemProgress record is created for the vocab item

**AC7: Already learned item**
**Given** an authenticated user attempting to lesson an item already in UserItemProgress
**When** POST `/api/v1/me/lessons` is called with that item
**Then** response status is 400 Bad Request
**And** error message indicates item already learned

**AC8: Authentication required**
**Given** an unauthenticated request
**When** POST `/api/v1/me/lessons` is called
**Then** response status is 401 Unauthorized

**AC9:** `src/lessons/router.py` mounts at `/api/v1/me/lessons`
**AC10:** `src/lessons/service.py` contains `LessonService` with batch completion and prerequisite checking logic
**AC11:** Prerequisite checking queries UserItemProgress to verify all constituent kanji are at GURU stage (srs_stage >= 5) before allowing vocab lessons

## Tasks / Subtasks

- [x] Task 1: Create UserItemProgress model (AC: 1)
  - [x] Add UserItemProgress model to `src/progress/models.py`:
    - id (Integer, primary key, autoincrement)
    - user_id (Integer, FK to users.id, indexed, not null)
    - item_type (Enum using ItemType from src.core.constants, not null)
    - item_id (Integer, not null)
    - srs_stage (Integer, 1-9, default 1, not null)
    - next_review_at (DateTime with timezone, nullable)
    - unlocked_at (DateTime with timezone, default UTC now, not null)
    - burned_at (DateTime with timezone, nullable)
    - meaning_note (Text, nullable)
    - reading_mnemonic (Text, nullable)
    - source (Enum: manual | wanikani, default manual, not null)
    - Composite unique constraint on (user_id, item_type, item_id)
    - Relationship to User model

- [x] Task 2: Create Alembic migration (AC: 2)
  - [x] Generate migration for user_item_progress table
  - [x] Ensure foreign key constraint to users table
  - [x] Ensure composite unique constraint
  - [x] Ensure indexes on user_id
  - [x] Add source enum type

- [x] Task 3: Create Pydantic schemas (AC: 3)
  - [x] Add SelectedItem schema to `src/progress/schemas.py`:
    - item_type: ItemType
    - item_id: int
  - [x] Add LessonCompleteRequest schema:
    - item_ids: list[SelectedItem] (required list of items to complete)
  - [x] Add LessonItemResponse schema:
    - item_type, item_id, srs_stage, next_review_at, item_details
  - [x] Add LessonCompleteResponse schema:
    - items: list[LessonItemResponse] (completed items)
    - count: int (actual count processed)
  - [x] Updated KanjiItemDetails to include readings_on and readings_kun for consistency

- [x] Task 4: Create LessonService (AC: 4, 5, 6, 7, 9, 10, 11)
  - [x] Create `src/lessons/service.py` with LessonService class
  - [x] Implement `complete_lessons` method:
    - Process specified item_ids from request
    - For each item:
      - Verify item exists (kanji/vocab)
      - Check if item already in UserItemProgress (already learned)
      - For vocab items: check prerequisite kanji (all must have srs_stage >= 5, GURU stage)
      - Create UserItemProgress record with srs_stage=1, unlocked_at=now, next_review_at=4 hours
      - Auto-remove item from LessonQueue if present
    - Return list of completed items
  - [x] Implement prerequisite checking helper method:
    - Query vocab.kanji relationship
    - Check each kanji exists in UserItemProgress with srs_stage >= 5 (GURU stage)
    - Return list of missing kanji if any

- [x] Task 5: Create router endpoints (AC: 4, 5, 8, 9)
  - [x] Create `src/lessons/router.py`
  - [x] Add POST `/api/v1/me/lessons` endpoint:
    - Requires authentication (Depends(get_current_user))
    - Accepts LessonCompleteRequest
    - Calls LessonService.complete_lessons
    - Returns LessonCompleteResponse
    - Handles 400 errors (already learned, prerequisites, item not found)
    - Handles 401 for unauthenticated

- [x] Task 6: Mount router in main.py
  - [x] Import lessons router
  - [x] Mount at `/api/v1/me/lessons`

- [x] Task 7: Write comprehensive tests
  - [x] Create tests in `tests/progress/test_models.py`:
    - Test UserItemProgress model creation
    - Test composite unique constraint
    - Test relationships
  - [x] Create tests in `tests/lessons/test_service.py`:
    - Test complete_lessons direct without queue
    - Test complete_lessons auto-removes from queue
    - Test complete_lessons sets next_review_at
    - Test prerequisite enforcement (vocab with unlearned kanji)
    - Test prerequisite satisfied (vocab with learned kanji)
    - Test already learned items
    - Test atomic failure on mixed batch
  - [x] Create tests in `tests/lessons/test_router.py`:
    - Test POST /me/lessons direct without queue
    - Test POST /me/lessons auto-removes from queue
    - Test POST /me/lessons already learned (400)
    - Test POST /me/lessons prerequisite failure (400)
    - Test POST /me/lessons prerequisite satisfied
    - Test POST /me/lessons unauthenticated (401)

## Dev Notes

### Architecture Requirements

- Follow service layer pattern: routers → services → models
- Use async SQLAlchemy 2.0 patterns
- Error handling with HTTPException for API errors
- Transaction handling to ensure data consistency

### Simplified Lesson Flow (2026-01-24 Update)

**Key Design Decision**: Queue membership is NOT required for lesson completion.

The lesson queue (`/api/v1/me/queue`) serves as an optional "want to learn later" wishlist/bookmark feature, but users can complete lessons for any item directly from the pool.

**Endpoint**: `POST /api/v1/me/lessons`
- Request: `{"item_ids": [{"item_type": "vocab", "item_id": 123}, ...]}`
- Items enter SRS at stage 1 (Apprentice 1), not stage 0
- `next_review_at` is set to 4 hours from completion (WaniKani stage 1 interval)
- If item was in user's queue, it's auto-removed

### Prerequisite Checking Logic

- For vocab items, query the vocab.kanji relationship to get constituent kanji
- Check each kanji exists in UserItemProgress for the user
- Verify srs_stage >= 5 (GURU stage) - in WaniKani, kanji must be at GURU level before vocab can be learned
- Return clear error message listing missing kanji characters

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Change Log - Simplified Lesson Flow]
- [Source: _bmad-output/planning-artifacts/prd.md#FR21 - Lesson completion without queue requirement]
- [Source: _bmad-output/planning-artifacts/architecture.md#Service Layer Pattern]
- [Source: src/progress/service.py - ProgressService pattern]
- [Source: src/vocab/models.py - Vocab.kanji relationship]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Debug Log References

### Completion Notes List

✅ **Task 1 Complete**: Created UserItemProgress model in `src/progress/models.py` with all required fields including srs_stage, next_review_at, unlocked_at, burned_at, meaning_note, reading_mnemonic, and source enum. Added composite unique constraint and relationship to User model.

✅ **Task 2 Complete**: Created Alembic migration `005_create_user_item_progress.py` with user_item_progress table, foreign key constraints, composite unique constraint, indexes, and ProgressSource enum type.

✅ **Task 3 Complete**: Added schemas to `src/progress/schemas.py`: SelectedItem, LessonCompleteRequest, LessonItemResponse, and LessonCompleteResponse. Added readings_on and readings_kun to KanjiItemDetails for consistency.

✅ **Task 4 Complete**: Created LessonService in `src/lessons/service.py` with complete_lessons method. **SIMPLIFIED FLOW**: Items can be completed directly without queue membership. Sets srs_stage=1 (Apprentice 1) and next_review_at=4 hours. Auto-removes from queue if present. Implements prerequisite checking for vocab items (verifies all constituent kanji have srs_stage >= 5, GURU stage).

✅ **Task 5 Complete**: Created router in `src/lessons/router.py` with POST `/api/v1/me/lessons` endpoint. Handles authentication, request validation, and error responses.

✅ **Task 6 Complete**: Mounted lessons router in `src/main.py` at `/api/v1/me/lessons`.

✅ **Task 7 Complete**: Added comprehensive tests:
- UserItemProgress model tests (creation, constraints, relationships, SRS stages, optional fields)
- LessonService tests (direct completion without queue, auto-removal from queue, next_review_at, prerequisites, validation)
- Router tests (all endpoints, error cases, authentication)

## File List

- `src/core/constants.py` - Added ProgressSource enum
- `src/progress/models.py` - Added UserItemProgress model
- `src/auth/models.py` - Added item_progress relationship to User model
- `alembic/versions/005_create_user_item_progress.py` - Migration for user_item_progress table
- `src/progress/schemas.py` - Added SelectedItem, LessonCompleteRequest, LessonItemResponse, LessonCompleteResponse schemas
- `src/progress/service.py` - Fixed missing readings_on/readings_kun in kanji item details
- `src/lessons/service.py` - Created LessonService with simplified lesson completion (no queue requirement)
- `src/lessons/router.py` - Created lessons router with POST endpoint
- `src/main.py` - Mounted lessons router
- `tests/progress/test_models.py` - Added UserItemProgress model tests
- `tests/lessons/test_service.py` - Created comprehensive LessonService tests (simplified flow)
- `tests/lessons/test_router.py` - Created comprehensive router tests (simplified flow)
- `tests/conftest.py` - Added UserItemProgress import

## Change Log

- 2026-01-24: **SIMPLIFIED LESSON FLOW** - Story 4.3 updated
  - **Key change**: Queue membership NO LONGER required for lesson completion
  - Items can be completed directly from the pool with one action
  - Items enter SRS at stage 1 (Apprentice 1), not stage 0
  - next_review_at set to 4 hours from lesson completion
  - Auto-cleanup: items in queue are auto-removed when lesson completed
  - Prerequisite enforcement unchanged (vocab requires kanji at GURU stage)
  - All tests updated to reflect simplified flow (131 tests pass)

- 2026-01-24: Initial Implementation - Batch Complete Lessons with Prerequisite Enforcement
  - Created UserItemProgress model for tracking SRS progress
  - Implemented batch lesson completion
  - Added prerequisite enforcement for vocab items (requires learned kanji)
  - Created comprehensive test suite
