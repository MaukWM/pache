# Story 5.1: SRS Core Logic & Review Log Model

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want **the SRS interval calculation logic and ReviewLog model**,
So that **review submissions can calculate next review times and track review history**.

## Acceptance Criteria

**AC1: SRS Constants**
**Given** the existing constants file
**When** SRS constants are defined
**Then** `src/core/constants.py` defines:
- `SRS_STAGES`: 1-9 (1-4=Apprentice, 5-6=Guru, 7=Master, 8=Enlightened, 9=Burned)
- Note: `SRS_INTERVALS` dict already exists from Story 4.3

**AC2: SRS Calculation Module**
**Given** the reviews module
**When** SRS calculation logic is created
**Then** `src/reviews/srs.py` provides:
- `calculate_next_review(current_stage: int, correct: bool) -> tuple[int, datetime | None]` function
- When `correct=True`: advances to next stage, calculates `next_review_at` using SRS_INTERVALS
- When `correct=False`: drops ~2 stages (minimum stage 1), recalculates `next_review_at`
- Handles stage 9 (burned) - cannot advance further, returns None for next_review_at
- Returns (new_stage, next_review_at) tuple

**AC3: ReviewType Enum**
**Given** the constants file
**When** review types are defined
**Then** `src/core/constants.py` defines `ReviewType` enum with values: `reading`, `meaning`

**AC4: ReviewLog Model**
**Given** the database from Epic 4
**When** the ReviewLog model is created
**Then** `src/reviews/models.py` defines:

**ReviewLog model:**
- `id` (primary key)
- `user_id` (FK to users, indexed)
- `item_type` (enum: kanji | vocab)
- `item_id` (FK to kanji or vocab)
- `review_type` (enum: reading | meaning)
- `correct` (boolean)
- `srs_stage_before` (integer, stage before review)
- `srs_stage_after` (integer, stage after review)
- `reviewed_at` (datetime, indexed for querying)

**AC5:** Alembic migration creates `review_log` table with proper indexes

**AC6:** `src/reviews/schemas.py` defines `ReviewCreateRequest`, `ReviewResponse`, `ReviewLogResponse`

## Tasks / Subtasks

- [x] Task 1: Add SRS stage constants (AC: 1)
  - [x] Add SRS_STAGES dict to `src/core/constants.py` mapping stage numbers to names
  - [x] Verify SRS_INTERVALS already exists (from story 4.3)
  - [x] Add docstring explaining WaniKani SRS system

- [x] Task 2: Add ReviewType enum (AC: 3)
  - [x] Add ReviewType enum to `src/core/constants.py` with values: reading, meaning

- [x] Task 3: Create SRS calculation module (AC: 2)
  - [x] Create `src/reviews/srs.py`
  - [x] Implement `calculate_next_review(current_stage: int, correct: bool) -> tuple[int, datetime | None]`:
    - If correct and stage < 9: new_stage = current_stage + 1, next_review = now + SRS_INTERVALS[current_stage]
    - If correct and stage == 9: return (9, None) - already burned
    - If incorrect: new_stage = max(1, current_stage - 2), next_review = now + SRS_INTERVALS[new_stage]
    - Stage 9 has no next_review (burned)
  - [x] Add comprehensive docstrings explaining WaniKani SRS logic

- [x] Task 4: Create ReviewLog model (AC: 4)
  - [x] Create `src/reviews/models.py`
  - [x] Add ReviewLog model with all required fields:
    - id (Integer, primary key, autoincrement)
    - user_id (Integer, FK to users.id, indexed, not null)
    - item_type (Enum using ItemType, not null)
    - item_id (Integer, not null)
    - review_type (Enum using ReviewType, not null)
    - correct (Boolean, not null)
    - srs_stage_before (Integer, not null)
    - srs_stage_after (Integer, not null)
    - reviewed_at (DateTime with timezone, default UTC now, indexed)
  - [x] Add relationship to User model

- [x] Task 5: Create Alembic migration (AC: 5)
  - [x] Generate migration for review_log table
  - [x] Add foreign key constraint to users table
  - [x] Add index on user_id
  - [x] Add index on reviewed_at for query performance

- [x] Task 6: Create Pydantic schemas (AC: 6)
  - [x] Create `src/reviews/schemas.py`
  - [x] Add ReviewCreateRequest schema:
    - item_type: ItemType
    - item_id: int
    - review_type: ReviewType
    - correct: bool
  - [x] Add ReviewResponse schema (for submit review response)
  - [x] Add ReviewLogResponse schema (for viewing review history)

- [x] Task 7: Write comprehensive tests
  - [x] Create `tests/reviews/test_srs.py`:
    - Test correct answer advances stage
    - Test correct answer at stage 8 goes to burned (9)
    - Test correct answer at stage 9 stays burned
    - Test incorrect answer drops 2 stages
    - Test incorrect answer at stage 2 drops to 1 (minimum)
    - Test incorrect answer at stage 1 stays at 1
    - Test next_review_at calculation for each stage
    - Test burned items have no next_review_at
  - [x] Create `tests/reviews/test_models.py`:
    - Test ReviewLog model creation
    - Test relationships and constraints

### Review Follow-ups (AI)

- [x] [AI-Review][High] H1: Fix SRS interval calculation - use `SRS_INTERVALS[current_stage]` not `new_stage` per story spec [src/reviews/srs.py:59]
- [x] [AI-Review][High] H2: Add input validation to `calculate_next_review()` - validate current_stage is 1-9, raise ValueError otherwise [src/reviews/srs.py:17]
- [x] [AI-Review][High] H3a: Refactor ReviewLog model - replace `review_type` + `correct` fields with `reading_correct: bool` + `meaning_correct: bool` [src/reviews/models.py]
- [x] [AI-Review][High] H3b: Remove `ReviewType` enum from constants.py (no longer needed after consolidation) [src/core/constants.py]
- [x] [AI-Review][High] H3c: Update schemas - `ReviewCreateRequest` takes `reading_correct` + `meaning_correct` instead of `review_type` + `correct` [src/reviews/schemas.py]
- [x] [AI-Review][High] H3d: Update migration 006 - remove `reviewtype` enum, add `reading_correct` + `meaning_correct` columns [alembic/versions/006_create_review_log.py]
- [x] [AI-Review][High] H3e: Update tests to use new consolidated model structure [tests/reviews/]
- [x] [AI-Review][Med] M1: Add composite index for user+item queries [alembic/versions/006_create_review_log.py]
- [x] [AI-Review][Med] M2: Add ON DELETE CASCADE to FK constraint [alembic/versions/006_create_review_log.py:42]
- [x] [AI-Review][Med] M3: Add `gt=0` validation to `item_id` in `ReviewLogResponse` [src/reviews/schemas.py]
- [x] [AI-Review][Low] L1: Remove unused `SRS_STAGES` dict [src/core/constants.py]
- [x] [AI-Review][Low] L2: Remove unnecessary async markers from synchronous SRS tests [tests/reviews/test_srs.py]

## Dev Notes

### Architecture Requirements

- Follow service layer pattern: routers → services → models
- Use async SQLAlchemy 2.0 patterns
- SRS logic in dedicated `srs.py` module for testability
- This story creates foundation - no endpoints yet (Story 5.2 and 5.3 add endpoints)

### SRS Algorithm Details (WaniKani)

**Stages:**
- Stage 1-4: Apprentice (learning phase)
- Stage 5-6: Guru (short-term memory)
- Stage 7: Master (medium-term memory)
- Stage 8: Enlightened (long-term memory)
- Stage 9: Burned (permanent memory - no more reviews)

**Intervals (already in SRS_INTERVALS from Story 4.3):**
- Stage 1 → 2: 4 hours
- Stage 2 → 3: 8 hours
- Stage 3 → 4: 1 day
- Stage 4 → 5: 2 days
- Stage 5 → 6: 1 week
- Stage 6 → 7: 2 weeks
- Stage 7 → 8: 30 days
- Stage 8 → 9: 120 days
- Stage 9: No review (burned)

**Incorrect Answer Penalty:**
- Drop approximately 2 stages (minimum stage 1)
- Recalculate next_review_at based on new stage

### Previous Story Context (Story 4.3)

Story 4.3 established:
- UserItemProgress model with srs_stage field (1-9)
- SRS_INTERVALS dict in `src/core/constants.py`
- ItemType enum (kanji, vocab)
- Lesson completion sets srs_stage=1 and next_review_at=4 hours

This story builds on that by:
- Adding SRS stage name constants
- Adding ReviewType enum
- Creating the calculation function used by submit_review
- Creating ReviewLog model for tracking review history

### File Organization

```
src/reviews/
├── __init__.py       # Module docstring
├── models.py         # ReviewLog model (new)
├── srs.py            # SRS calculation logic (new)
├── schemas.py        # Request/Response schemas (new)
├── service.py        # Will be created in Story 5.2
└── router.py         # Will be created in Story 5.2
```

### Project Structure Notes

- `src/reviews/srs.py` is specifically called out in architecture document
- SRS calculations are critical business logic - test thoroughly
- ReviewLog tracks history separately from UserItemProgress (which tracks current state)

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Key Implementation Files - src/reviews/srs.py]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure - reviews module]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1]
- [Source: src/core/constants.py - SRS_INTERVALS dict from Story 4.3]
- [Source: src/progress/models.py - UserItemProgress model for srs_stage reference]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None

### Completion Notes List

- Implemented SRS_STAGES constant mapping stage numbers (1-9) to descriptive names (Apprentice 1-4, Guru 1-2, Master, Enlightened, Burned)
- Added comprehensive module docstring to constants.py explaining the WaniKani SRS system
- Added ReviewType enum with READING and MEANING values
- Created calculate_next_review() function with correct stage advancement logic:
  - Correct answers advance to next stage (max 9)
  - Incorrect answers drop ~2 stages (min 1)
  - Burned items (stage 9) return None for next_review_at
- Created ReviewLog model with all required fields and proper indexes
- Added bidirectional relationship between User and ReviewLog with cascade delete
- Created Alembic migration 006 for review_log table with reviewtype enum
- Created Pydantic schemas: ReviewCreateRequest, ReviewResponse, ReviewLogResponse
- Wrote 24 comprehensive tests covering all SRS calculation edge cases and model operations
- All 156 tests pass, ruff and mypy checks pass

**Code Review Follow-ups Resolved (2026-01-24):**
- [H1] Fixed SRS interval calculation to use `SRS_INTERVALS[current_stage]` per story spec
- [H2] Added input validation to `calculate_next_review()` - raises ValueError for stages outside 1-9
- [H3] Refactored ReviewLog model to consolidate reading/meaning reviews:
  - Replaced `review_type` + `correct` with `reading_correct` + `meaning_correct` fields
  - Removed `ReviewType` enum from constants.py (no longer needed)
  - Updated schemas to use new consolidated structure
  - Updated migration 006 to remove reviewtype enum, add boolean columns
  - Updated all tests to use new model structure
- [M1] Added composite index `ix_review_log_user_item` for user+item queries
- [M2] Added ON DELETE CASCADE to user_id foreign key constraint
- [M3] Added `gt=0` validation to `item_id` in ReviewResponse and ReviewLogResponse schemas
- [L1] Removed unused `SRS_STAGES` dict from constants.py
- [L2] Verified SRS tests are already synchronous (no async markers to remove)
- All 161 tests pass, ruff and mypy checks pass

### File List

**New Files:**
- src/reviews/srs.py
- src/reviews/models.py
- src/reviews/schemas.py
- alembic/versions/006_create_review_log.py
- tests/reviews/test_srs.py
- tests/reviews/test_models.py

**Modified Files:**
- src/core/constants.py (added SRS_STAGES dict, ReviewType enum, module docstring)
- src/auth/models.py (added review_logs relationship to User model)
- tests/conftest.py (registered ReviewLog model)

**Files Modified During Code Review Follow-ups:**
- src/reviews/srs.py (fixed interval calculation, added input validation)
- src/reviews/models.py (refactored to use reading_correct/meaning_correct, added ON DELETE CASCADE)
- src/reviews/schemas.py (refactored to use reading_correct/meaning_correct, added item_id validation)
- src/core/constants.py (removed ReviewType enum, removed unused SRS_STAGES dict)
- alembic/versions/006_create_review_log.py (removed reviewtype enum, added boolean columns, composite index, CASCADE)
- tests/reviews/test_srs.py (fixed interval tests for current_stage, added input validation tests)
- tests/reviews/test_models.py (updated to use new reading_correct/meaning_correct fields)

## Senior Developer Review (AI)

**Review Date:** 2026-01-24
**Outcome:** Changes Requested
**Reviewer:** Claude Opus 4.5

### Action Items

- [x] [High] H1: Fix SRS interval calculation - use current_stage not new_stage
- [x] [High] H2: Add input validation (stage 1-9) to calculate_next_review()
- [x] [High] H3: Refactor model to consolidate reading/meaning into single review record (5 subtasks)
- [x] [Med] M1: Add composite index for user+item queries
- [x] [Med] M2: Add ON DELETE CASCADE to FK constraint
- [x] [Med] M3: Add item_id validation to ReviewLogResponse
- [x] [Low] L1: Remove unused SRS_STAGES dict
- [x] [Low] L2: Remove async markers from sync tests

**Summary:** Implementation meets original ACs but user requested design simplification - consolidate separate reading/meaning reviews into single record with both fields. This better matches intended frontend simplicity (one endpoint per item review).

## Change Log

- 2026-01-24: Story 5.1 implemented - SRS core logic and ReviewLog model complete
- 2026-01-24: Code review completed - 12 action items created (3 High, 4 Medium refactoring design per user feedback, 2 Low)
- 2026-01-24: Addressed code review findings - 12 items resolved (7 High, 3 Medium, 2 Low). Major changes: fixed SRS interval calculation, added input validation, refactored ReviewLog to consolidate reading/meaning into single record.
