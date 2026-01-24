# Story 3.2: Create Vocabulary

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to create vocabulary with kanji links and tags**,
So that **I can add terms I encounter to the shared pool**.

## Acceptance Criteria

**AC1: Create vocabulary with all required fields**
**Given** an authenticated user
**When** POST `/api/v1/vocab` is called with:
```json
{
  "word": "日本語",
  "reading": "にほんご",
  "meanings": ["Japanese language"],
  "kanji_ids": [42, 55, 78],
  "tags": ["language", "N5"],
  "creator_comment": "Found in my textbook"
}
```
**Then** response status is 201
**And** a new Vocab record is created with creator_id set to current user
**And** VocabKanji links are created for each kanji_id
**And** Tags are created if they don't exist, VocabTag links are created
**And** response includes the created vocab with all details

**AC2: Auto-activate linked kanji (FR6)**
**Given** kanji with id 42 exists and has `active=False`
**When** vocabulary is created linking to kanji id 42
**Then** kanji 42 is set to `active=True` (auto-activation)

**AC3: Handle invalid kanji IDs**
**Given** kanji_ids contains an invalid kanji id (e.g., 99999)
**When** POST `/api/v1/vocab` is called
**Then** response status is 400 with error message indicating invalid kanji ID

**AC4: Require authentication**
**Given** an unauthenticated request (missing or invalid token)
**When** POST `/api/v1/vocab` is called
**Then** response status is 401 Unauthorized

**AC5: Creator username in response**
**Given** vocabulary is created successfully
**When** response is returned
**Then** response includes `creator_username` field (FR18 - see who created)

## Tasks / Subtasks

- [x] Task 1: Create auth dependencies (AC: 4)
  - [x] Create `src/auth/dependencies.py`
  - [x] Implement `get_current_user` dependency that:
    - Extracts Bearer token from `Authorization` header
    - Looks up Session by token
    - Returns User or raises 401
  - [x] Write tests for `get_current_user` dependency

- [x] Task 2: Create VocabService (AC: 1, 2)
  - [x] Create `src/vocab/service.py`
  - [x] Implement `VocabService` class with `create_vocab` method:
    - Validate all kanji_ids exist
    - Create or get-existing tags
    - Create Vocab record with creator_id
    - Create VocabKanji links
    - Create VocabTag links
    - Activate linked kanji (`active=True`)
    - Return created Vocab with relationships loaded
  - [x] Write tests for `VocabService.create_vocab`

- [x] Task 3: Create vocab router (AC: 1, 3, 4, 5)
  - [x] Create `src/vocab/router.py`
  - [x] Implement POST `/vocab` endpoint:
    - Use `Depends(get_current_user)` for authentication
    - Use `Depends(get_db)` for database session
    - Call `VocabService.create_vocab`
    - Return 201 with `VocabResponse`
    - Handle validation errors with 400 status
  - [x] Write integration tests for endpoint

- [x] Task 4: Update schemas for creator_username (AC: 5)
  - [x] Update `VocabResponse` to include `creator_username: str`
  - [x] Ensure schema can populate from ORM relationship

- [x] Task 5: Mount vocab router in main.py
  - [x] Import vocab router
  - [x] Add `app.include_router(vocab_router, prefix=settings.api_prefix)`

- [x] Task 6: Write comprehensive tests
  - [x] Test vocab creation with all fields
  - [x] Test kanji auto-activation
  - [x] Test tag creation (new tags)
  - [x] Test tag reuse (existing tags)
  - [x] Test invalid kanji ID error
  - [x] Test authentication required

## Dev Notes

### Architecture Requirements

Follow these patterns from `architecture.md`:

**Service Layer Pattern:**
- Routes are thin, business logic lives in services
- Service receives Pydantic request, returns model with relationships

**Auth Dependency Pattern:**
```python
# src/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.auth.models import Session, User
from src.database import get_db

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from the session token."""
    token = credentials.credentials
    result = await db.execute(
        select(Session).where(Session.token == token)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    result = await db.execute(
        select(User).where(User.id == session.user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
```

**Naming Conventions:**
- Endpoints: lowercase, plural `/api/v1/vocab`
- JSON fields: snake_case

**Import Style:**
```python
from src.auth.dependencies import get_current_user
from src.vocab.service import VocabService
from src.vocab.schemas import VocabCreateRequest, VocabResponse
```

### Kanji Auto-Activation Logic

When vocabulary is created with linked kanji:
1. Validate all kanji_ids exist
2. For each kanji with `active=False`, set `active=True`
3. Commit within same transaction as vocab creation

```python
# In VocabService.create_vocab
async def create_vocab(
    self,
    request: VocabCreateRequest,
    creator_id: int
) -> Vocab:
    # Validate kanji IDs
    kanji_list = []
    for kanji_id in request.kanji_ids:
        kanji = await self.db.get(Kanji, kanji_id)
        if kanji is None:
            raise ValueError(f"Kanji with id {kanji_id} not found")
        kanji_list.append(kanji)

    # Get or create tags
    tags = []
    for tag_name in request.tags:
        result = await self.db.execute(
            select(Tag).where(Tag.name == tag_name)
        )
        tag = result.scalar_one_or_none()
        if tag is None:
            tag = Tag(name=tag_name)
            self.db.add(tag)
        tags.append(tag)

    # Create vocab
    vocab = Vocab(
        word=request.word,
        reading=request.reading,
        meanings=request.meanings,
        creator_id=creator_id,
        creator_comment=request.creator_comment,
    )
    vocab.kanji = kanji_list
    vocab.tags = tags
    self.db.add(vocab)

    # Activate linked kanji (FR6)
    for kanji in kanji_list:
        if not kanji.active:
            kanji.active = True

    await self.db.commit()
    await self.db.refresh(vocab)
    return vocab
```

### VocabResponse with creator_username

Update schema to include creator username:

```python
class VocabResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    word: str
    reading: str
    meanings: list[str]
    creator_id: int
    creator_username: str  # Added for FR18
    creator_comment: str | None
    created_at: datetime
    tags: list[TagResponse]
    kanji: list[KanjiResponse]

    @classmethod
    def from_orm_with_creator(cls, vocab: Vocab) -> "VocabResponse":
        return cls(
            id=vocab.id,
            word=vocab.word,
            reading=vocab.reading,
            meanings=vocab.meanings,
            creator_id=vocab.creator_id,
            creator_username=vocab.creator.username,
            creator_comment=vocab.creator_comment,
            created_at=vocab.created_at,
            tags=[TagResponse.model_validate(t) for t in vocab.tags],
            kanji=[KanjiResponse.model_validate(k) for k in vocab.kanji],
        )
```

### Project Structure Notes

**Files to create:**
- `src/auth/dependencies.py` - get_current_user dependency
- `src/vocab/service.py` - VocabService with create_vocab
- `src/vocab/router.py` - POST /vocab endpoint
- `tests/auth/test_dependencies.py` - auth dependency tests
- `tests/vocab/test_service.py` - service tests
- `tests/vocab/test_router.py` - integration tests

**Files to modify:**
- `src/vocab/schemas.py` - add creator_username to VocabResponse
- `src/main.py` - mount vocab router

### Previous Story Intelligence

From Story 3.1:
- Vocab, Tag, VocabTag, VocabKanji models exist
- VocabCreateRequest, VocabResponse, TagResponse schemas exist
- conftest.py has fixtures for async database testing
- All 45 tests pass, pre-commit passes

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- [Source: _bmad-output/planning-artifacts/architecture.md#Service Layer Pattern]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2: Create Vocabulary]
- [Source: src/vocab/models.py - existing models]
- [Source: src/vocab/schemas.py - existing schemas]
- [Source: src/kanji/router.py - router pattern reference]
- [Source: src/kanji/service.py - service pattern reference]

## Dev Agent Record

### Agent Model Used

Composer (Claude Sonnet 4.5)

### Debug Log References

### Completion Notes List

- ✅ Created `src/auth/dependencies.py` with `get_current_user` dependency that validates Bearer tokens and returns authenticated User
- ✅ Created `src/vocab/service.py` with `VocabService.create_vocab` method that:
  - Validates kanji IDs exist
  - Creates or reuses tags
  - Creates Vocab with kanji and tag relationships
  - Auto-activates linked kanji (FR6)
- ✅ Created `src/vocab/router.py` with POST `/api/v1/vocab` endpoint:
  - Requires authentication via `get_current_user`
  - Handles validation errors with 400 status
  - Returns 201 with VocabResponse including creator_username
- ✅ Updated `VocabResponse` schema to include `creator_username` field (FR18)
- ✅ Mounted vocab router in `src/main.py`
- ✅ Comprehensive test coverage:
  - Auth dependency tests (valid/invalid tokens, missing user)
  - Service tests (creation, kanji activation, tag reuse, invalid kanji IDs)
  - Router integration tests (success, errors, authentication)

### File List

**New Files:**
- `src/auth/dependencies.py` - Authentication dependency for FastAPI
- `src/vocab/service.py` - Vocabulary service layer
- `src/vocab/router.py` - Vocabulary API routes
- `tests/auth/test_dependencies.py` - Tests for auth dependencies
- `tests/vocab/test_service.py` - Tests for vocab service
- `tests/vocab/test_router.py` - Integration tests for vocab router

**Modified Files:**
- `src/vocab/schemas.py` - Added `creator_username` field to `VocabResponse`
- `src/main.py` - Mounted vocab router
