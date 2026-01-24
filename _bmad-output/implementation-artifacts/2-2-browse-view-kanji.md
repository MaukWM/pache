# Story 2.2: Browse & View Kanji Endpoints

Status: review

## Story

As a **user**,
I want **to browse and view kanji in the database**,
So that **I can see which kanji are available and their details**.

## Acceptance Criteria

**Given** kanji have been seeded in the database
**When** GET `/api/v1/kanji` is called
**Then** response returns a list of kanji
**And** by default, only active kanji are returned (empty list initially)
**And** query param `?include_inactive=true` includes dormant kanji

**Given** a kanji with id=42 or character="日" exists
**When** GET `/api/v1/kanji/42` or GET `/api/v1/kanji/日` is called
**Then** response returns the full kanji details including meanings and readings
**And** response status is 200

**Given** no kanji matches the id or character
**When** GET `/api/v1/kanji/{id_or_char}` is called
**Then** response status is 404

**And** `src/kanji/router.py` mounts at `/api/v1/kanji`
**And** endpoints do NOT require authentication (kanji pool is public)

## Tasks / Subtasks

- [x] Task 1: Create kanji router
  - [x] Create `src/kanji/router.py`
  - [x] Mount router at `/api/v1/kanji`
  - [x] Implement GET `/api/v1/kanji` endpoint (list kanji)
  - [x] Implement GET `/api/v1/kanji/{id_or_char}` endpoint (get single kanji)
  - [x] Add query parameter `include_inactive` for list endpoint
  - [x] Handle both ID and character lookup for single kanji endpoint
  - [x] Return 404 for not found

- [x] Task 2: Mount router in main app
  - [x] Import kanji router in `src/main.py`
  - [x] Mount router with prefix `/api/v1/kanji`

- [x] Task 3: Write tests for endpoints
  - [x] Test GET `/api/v1/kanji` returns active kanji only by default
  - [x] Test GET `/api/v1/kanji?include_inactive=true` returns all kanji
  - [x] Test GET `/api/v1/kanji/{id}` returns kanji by ID
  - [x] Test GET `/api/v1/kanji/{character}` returns kanji by character
  - [x] Test GET `/api/v1/kanji/{id}` returns 404 for non-existent kanji
  - [x] Test endpoints do not require authentication

## Dev Notes

### Architecture Requirements
- Follow project structure exactly as defined in architecture.md
- Use service layer pattern: thin routes, business logic in services
- Absolute imports from `src`
- Endpoints are public (no authentication required)

### Router Pattern
- Routes should be thin, delegate to KanjiService
- Use Pydantic schemas for request/response
- Return proper HTTP status codes (200, 404)

### ID vs Character Lookup
- Endpoint should accept both integer ID and single character string
- Try parsing as integer first, if fails treat as character
- Use appropriate service method based on type

### References
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2: Kanji Database Foundation]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2: Browse & View Kanji Endpoints]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

✅ **Story 2.2 Implementation Complete**

**Router Implementation:**
- Created `src/kanji/router.py` with FastAPI router
- Implemented GET `/api/v1/kanji` endpoint for listing kanji
- Implemented GET `/api/v1/kanji/{id_or_char}` endpoint for getting single kanji
- List endpoint supports `include_inactive` query parameter (defaults to False)
- Single kanji endpoint accepts both integer ID and single character string
- Returns 404 for not found kanji
- Returns 400 for invalid identifier format
- Endpoints are public (no authentication required)

**Router Mounting:**
- Mounted kanji router in `src/main.py` with prefix `/api/v1/kanji`
- Router properly integrated with FastAPI app

**Testing:**
- Created comprehensive test suite in `tests/kanji/test_router.py`
- Tests cover all acceptance criteria:
  - Empty database returns empty list
  - Default behavior returns only active kanji
  - `include_inactive=true` returns all kanji
  - Get by ID works correctly
  - Get by character works correctly
  - 404 returned for non-existent kanji
  - 400 returned for invalid identifier
  - Endpoints work without authentication
- Updated `tests/conftest.py` to add `async_client` fixture for async testing
- Tests use dependency override to inject test database session

**Implementation Details:**
- Router uses service layer pattern (delegates to KanjiService)
- Uses Pydantic schemas for request/response validation
- Proper HTTP status codes (200, 404, 400)
- ID vs character lookup: tries parsing as integer first, falls back to character
- All endpoints properly typed and documented

### File List

**Created Files:**
- `src/kanji/router.py` - Kanji API routes
- `tests/kanji/test_router.py` - Router endpoint tests

**Modified Files:**
- `src/main.py` - Mounted kanji router
- `tests/conftest.py` - Added async_client fixture

## Change Log

- 2026-01-23: Story 2.2 implementation completed
  - Created kanji router with list and get endpoints
  - Mounted router in main app
  - Implemented comprehensive test suite
  - All acceptance criteria satisfied
