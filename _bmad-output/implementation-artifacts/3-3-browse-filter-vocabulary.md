# Story 3.3: Browse & Filter Vocabulary

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to browse the shared vocabulary pool with filters**,
So that **I can discover interesting terms added by friends**.

## Acceptance Criteria

**AC1: Browse all vocabulary**
**Given** vocabulary exists in the database
**When** GET `/api/v1/vocab` is called
**Then** response returns a list of all vocabulary
**And** each vocab item includes creator username (FR18)
**And** each vocab item includes linked kanji characters
**And** each vocab item includes tags

**AC2: Filter by tag**
**Given** vocabulary with tag "slang" exists
**When** GET `/api/v1/vocab?tag=slang` is called
**Then** response returns only vocabulary with that tag

**AC3: Filter by creator**
**Given** vocabulary created by user "floppa" exists
**When** GET `/api/v1/vocab?creator=floppa` is called
**Then** response returns only vocabulary created by that user

**AC4: Multiple filters (AND logic)**
**Given** multiple filters are provided
**When** GET `/api/v1/vocab?tag=slang&creator=floppa` is called
**Then** response returns vocabulary matching ALL filters (AND logic)

**AC5: Get single vocab by ID**
**Given** a vocab with id=123 exists
**When** GET `/api/v1/vocab/123` is called
**Then** response returns full vocab details including meanings, readings, kanji, tags, creator

**AC6: Handle vocab not found**
**Given** no vocab with that id exists
**When** GET `/api/v1/vocab/999` is called
**Then** response status is 404

**AC7: No authentication required**
**And** browse endpoint does NOT require authentication (pool is shared/public)

**Note:** FR17 (not_in_queue filter) will be added in Epic 4 when LessonQueue exists

## Tasks / Subtasks

- [ ] Task 1: Add browse methods to VocabService (AC: 1, 2, 3, 4)
  - [ ] Implement `get_all` method with optional filters:
    - `tag: str | None` - filter by tag name
    - `creator: str | None` - filter by creator username
  - [ ] Implement query joining for filter conditions
  - [ ] Ensure eager loading of relationships (tags, kanji, creator)
  - [ ] Write tests for filtering logic

- [ ] Task 2: Add get_by_id method to VocabService (AC: 5)
  - [ ] Implement `get_by_id` method
  - [ ] Eager load relationships (tags, kanji, creator)
  - [ ] Return None if not found
  - [ ] Write tests

- [ ] Task 3: Add GET endpoints to vocab router (AC: 1-7)
  - [ ] Implement GET `/vocab` endpoint:
    - Query params: `tag`, `creator` (both optional)
    - No authentication required
    - Return list of VocabResponse
  - [ ] Implement GET `/vocab/{vocab_id}` endpoint:
    - Path param: vocab_id (int)
    - Return VocabResponse or 404
  - [ ] Write integration tests

- [ ] Task 4: Write comprehensive tests
  - [ ] Test browse returns all vocab
  - [ ] Test filter by tag
  - [ ] Test filter by creator
  - [ ] Test combined filters (AND logic)
  - [ ] Test get by ID success
  - [ ] Test get by ID 404
  - [ ] Test no auth required for browse

## Dev Notes

### Architecture Requirements

Follow these patterns from `architecture.md`:

**Service Layer Pattern:**
- Routes are thin, business logic lives in services
- Service handles all query construction and filtering

**URL Pattern:**
- `/api/v1/vocab` - list with optional filters
- `/api/v1/vocab/{vocab_id}` - single item by ID

**Query Params:**
- snake_case: `?tag=slang&creator=floppa`

### VocabService Query Methods

```python
# src/vocab/service.py
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.vocab.models import Vocab, Tag

class VocabService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        tag: str | None = None,
        creator: str | None = None,
    ) -> list[Vocab]:
        """Get all vocabulary with optional filters."""
        query = (
            select(Vocab)
            .options(
                selectinload(Vocab.tags),
                selectinload(Vocab.kanji),
                selectinload(Vocab.creator),
            )
        )

        # Filter by tag
        if tag:
            query = query.join(Vocab.tags).where(Tag.name == tag)

        # Filter by creator username
        if creator:
            query = query.join(Vocab.creator).where(User.username == creator)

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def get_by_id(self, vocab_id: int) -> Vocab | None:
        """Get vocabulary by ID with all relationships."""
        query = (
            select(Vocab)
            .where(Vocab.id == vocab_id)
            .options(
                selectinload(Vocab.tags),
                selectinload(Vocab.kanji),
                selectinload(Vocab.creator),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
```

### Router Implementation

```python
# src/vocab/router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.vocab.schemas import VocabResponse
from src.vocab.service import VocabService

router = APIRouter(prefix="/vocab", tags=["vocab"])

@router.get("", response_model=list[VocabResponse])
async def list_vocab(
    tag: str | None = Query(default=None, description="Filter by tag name"),
    creator: str | None = Query(default=None, description="Filter by creator username"),
    db: AsyncSession = Depends(get_db),
) -> list[VocabResponse]:
    """List all vocabulary with optional filters."""
    service = VocabService(db)
    vocab_list = await service.get_all(tag=tag, creator=creator)
    return [VocabResponse.from_orm_with_creator(v) for v in vocab_list]

@router.get("/{vocab_id}", response_model=VocabResponse)
async def get_vocab(
    vocab_id: int,
    db: AsyncSession = Depends(get_db),
) -> VocabResponse:
    """Get a single vocabulary item by ID."""
    service = VocabService(db)
    vocab = await service.get_by_id(vocab_id)
    if vocab is None:
        raise HTTPException(status_code=404, detail="Vocabulary not found")
    return VocabResponse.from_orm_with_creator(vocab)
```

### Eager Loading for Performance

Use `selectinload` for many-to-many relationships to avoid N+1 queries:
- `selectinload(Vocab.tags)` - load all tags in one query
- `selectinload(Vocab.kanji)` - load all kanji in one query
- `selectinload(Vocab.creator)` - load creator user

### Query with Multiple Joins

When filtering by both tag and creator:
```python
query = (
    select(Vocab)
    .join(Vocab.tags)
    .join(Vocab.creator)
    .where(Tag.name == tag)
    .where(User.username == creator)
    .options(
        selectinload(Vocab.tags),
        selectinload(Vocab.kanji),
        selectinload(Vocab.creator),
    )
)
# Use .unique() to dedupe results from joins
result = await self.db.execute(query)
return list(result.scalars().unique().all())
```

### Project Structure Notes

**Files to modify:**
- `src/vocab/service.py` - add get_all and get_by_id methods
- `src/vocab/router.py` - add GET endpoints
- `tests/vocab/test_service.py` - add filter tests
- `tests/vocab/test_router.py` - add endpoint tests

**Note:** Story 3.2 creates the service and router files. This story extends them.

### Previous Story Intelligence

From Story 3.2 (planned):
- VocabService will exist with create_vocab method
- vocab router will exist with POST endpoint
- Auth dependency created
- VocabResponse includes creator_username

This story adds the read/browse functionality.

### Test Data Setup

```python
# In conftest.py or test fixtures
@pytest.fixture
async def sample_vocab(db: AsyncSession, sample_user, sample_kanji):
    """Create sample vocabulary for testing."""
    vocab = Vocab(
        word="日本語",
        reading="にほんご",
        meanings=["Japanese language"],
        creator_id=sample_user.id,
    )
    vocab.kanji = sample_kanji
    tag = Tag(name="N5")
    vocab.tags = [tag]
    db.add(vocab)
    await db.commit()
    return vocab
```

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication]
- [Source: _bmad-output/planning-artifacts/architecture.md#Service Layer Pattern]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3: Browse & Filter Vocabulary]
- [Source: src/kanji/router.py - GET endpoint pattern]
- [Source: src/kanji/service.py - query pattern]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
