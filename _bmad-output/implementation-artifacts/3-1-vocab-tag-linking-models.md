# Story 3.1: Vocab, Tag & Linking Models

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want **the Vocab, Tag, and linking models**,
So that **vocabulary creation and browsing can be implemented**.

## Acceptance Criteria

**Given** the database from Epic 2
**When** the Vocab models are created
**Then** `src/vocab/models.py` defines:

**AC1: Vocab model with all required fields:**
- `id` (primary key)
- `word` (the vocabulary term, indexed)
- `reading` (hiragana/katakana reading)
- `meanings` (JSON array of English meanings)
- `creator_id` (FK to users)
- `creator_comment` (nullable text)
- `created_at`

**AC2: Tag model:**
- `id` (primary key)
- `name` (unique, indexed)

**AC3: VocabTag junction table:**
- `vocab_id` (FK)
- `tag_id` (FK)
- Composite primary key

**AC4: VocabKanji junction table:**
- `vocab_id` (FK)
- `kanji_id` (FK)
- Composite primary key

**AC5:** Alembic migration creates `vocab`, `tags`, `vocab_tags`, `vocab_kanji` tables

**AC6:** `src/vocab/schemas.py` defines `VocabCreateRequest`, `VocabResponse`, `TagResponse`

## Tasks / Subtasks

- [x] Task 1: Create User and Session models (AC: prerequisite for creator_id FK)
  - [x] Create `src/auth/models.py` with User model (id, username unique, wk_api_key nullable, created_at)
  - [x] Create Session model (id, user_id FK, token unique indexed, created_at)
  - [x] Create Alembic migration for users and sessions tables

- [x] Task 2: Create Vocab model (AC: 1)
  - [x] Create `src/vocab/models.py`
  - [x] Define Vocab model with all required columns:
    - id (Integer, primary key, autoincrement)
    - word (String, indexed, not null)
    - reading (String, not null)
    - meanings (JSON array, not null)
    - creator_id (Integer, FK to users.id, not null)
    - creator_comment (Text, nullable)
    - created_at (DateTime with timezone, default UTC now)
  - [x] Add relationship to User model (creator)

- [x] Task 3: Create Tag model (AC: 2)
  - [x] Add Tag model to `src/vocab/models.py`
  - [x] Define columns:
    - id (Integer, primary key, autoincrement)
    - name (String, unique, indexed, not null)

- [x] Task 4: Create VocabTag junction table (AC: 3)
  - [x] Add VocabTag association table to `src/vocab/models.py`
  - [x] Define columns:
    - vocab_id (Integer, FK to vocab.id, primary key)
    - tag_id (Integer, FK to tags.id, primary key)
  - [x] Add relationship on Vocab model to access tags

- [x] Task 5: Create VocabKanji junction table (AC: 4)
  - [x] Add VocabKanji association table to `src/vocab/models.py`
  - [x] Define columns:
    - vocab_id (Integer, FK to vocab.id, primary key)
    - kanji_id (Integer, FK to kanji.id, primary key)
  - [x] Add relationship on Vocab model to access linked kanji

- [x] Task 6: Create Alembic migration (AC: 5)
  - [x] Generate migration for users, sessions tables (if not exists)
  - [x] Generate migration for vocab, tags, vocab_tags, vocab_kanji tables
  - [x] Ensure foreign key constraints are properly defined
  - [x] Test migration upgrade and downgrade

- [x] Task 7: Create Pydantic schemas (AC: 6)
  - [x] Create `src/vocab/schemas.py`
  - [x] Define VocabCreateRequest schema:
    - word: str
    - reading: str
    - meanings: list[str]
    - kanji_ids: list[int] (optional, for linking kanji)
    - tags: list[str] (optional, tag names to create/link)
    - creator_comment: str | None
  - [x] Define VocabResponse schema:
    - id: int
    - word: str
    - reading: str
    - meanings: list[str]
    - creator_id: int
    - creator_comment: str | None
    - created_at: datetime
    - tags: list[TagResponse]
    - kanji: list[KanjiResponse] (linked kanji)
  - [x] Define TagResponse schema:
    - id: int
    - name: str

- [x] Task 8: Write tests for models
  - [x] Create `tests/vocab/test_models.py`
  - [x] Test Vocab model creation and field types
  - [x] Test Tag model uniqueness constraint
  - [x] Test VocabTag relationship (many-to-many)
  - [x] Test VocabKanji relationship (many-to-many)
  - [x] Test Vocab.creator relationship to User

## Dev Notes

### Architecture Requirements

Follow these patterns from `architecture.md`:

**Service Layer Pattern:**
- Routes are thin, business logic lives in services
- Models define data structure only, no business logic

**Naming Conventions:**
- Tables: snake_case, plural (`vocab`, `tags`, `vocab_tags`, `vocab_kanji`)
- Columns: snake_case (`creator_id`, `created_at`)
- Foreign Keys: `{referenced_table}_id`
- Classes: PascalCase (`Vocab`, `VocabTag`)

**Import Style:**
```python
# Absolute imports from src
from src.database import Base
from src.kanji.models import Kanji
from src.auth.models import User
```

### Model Patterns (follow existing Kanji model)

```python
from datetime import datetime, timezone
from sqlalchemy import JSON, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

# Junction tables use Table construct
vocab_tags = Table(
    "vocab_tags",
    Base.metadata,
    Column("vocab_id", Integer, ForeignKey("vocab.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

class Vocab(Base):
    __tablename__ = "vocab"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # ... other fields follow Kanji pattern

    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="vocab_items")
    tags: Mapped[list["Tag"]] = relationship(secondary=vocab_tags)
    kanji: Mapped[list["Kanji"]] = relationship(secondary=vocab_kanji)
```

### Schema Patterns (follow existing KanjiResponse)

```python
from pydantic import BaseModel, ConfigDict

class VocabResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    word: str
    # ... enable SQLAlchemy model conversion
```

### User Model Required First

Story 3.1 requires the User model for the `creator_id` foreign key. The architecture specifies:

```python
# src/auth/models.py
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    wk_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Reverse relationship
    vocab_items: Mapped[list["Vocab"]] = relationship("Vocab", back_populates="creator")
```

### VocabResponse Needs Nested Schemas

VocabResponse should include:
- `tags: list[TagResponse]` - nested tag objects
- `kanji: list[KanjiResponse]` - reuse existing schema from `src/kanji/schemas.py`
- `creator_username: str` - denormalized for display (FR18)

### Key Business Rules

1. **Vocab requires creator** - creator_id is NOT NULL, FK to users
2. **Tags are shared** - same tag can be on multiple vocab items
3. **Kanji linking** - vocab links to existing kanji (dormant activation in Story 3.2)
4. **Word not unique** - same word can have multiple entries with different readings/meanings

### Previous Story Intelligence

From Story 2.2:
- Router pattern: use `Depends(get_db)` for database session
- Schema pattern: use `ConfigDict(from_attributes=True)` for SQLAlchemy conversion
- Test pattern: use `tests/conftest.py` fixtures, async testing with `pytest-asyncio`
- File created: `tests/kanji/test_router.py` - follow similar structure for vocab tests

### Project Structure Notes

**Files to create:**
- `src/auth/models.py` - User, Session models (prerequisite)
- `src/vocab/models.py` - Vocab, Tag, VocabTag, VocabKanji
- `src/vocab/schemas.py` - VocabCreateRequest, VocabResponse, TagResponse
- `tests/vocab/test_models.py` - Model tests

**Migrations to create:**
- `alembic/versions/xxx_create_users_sessions.py`
- `alembic/versions/xxx_create_vocab_tags_tables.py`

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1: Vocab, Tag & Linking Models]
- [Source: src/kanji/models.py - existing model pattern]
- [Source: src/kanji/schemas.py - existing schema pattern]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

**Story 3.1 Implementation Complete**

**User/Session Models (Task 1):**
- Created `src/auth/models.py` with User and Session models
- User model: id, username (unique, indexed), wk_api_key (nullable), created_at
- Session model: id, user_id (FK), token (unique, indexed), created_at
- Created migration `alembic/versions/002_create_users_sessions.py`

**Vocab Model (Task 2):**
- Created `src/vocab/models.py` with Vocab model
- All required columns: id, word (indexed), reading, meanings (JSON), creator_id (FK), creator_comment, created_at
- Relationship to User via `creator` backref

**Tag Model (Task 3):**
- Added Tag model with id and name (unique, indexed)
- Bidirectional relationship with Vocab via `vocab_items` backref

**VocabTag Junction (Task 4):**
- Created `vocab_tags` Table construct with composite PK (vocab_id, tag_id)
- Many-to-many relationship properly configured

**VocabKanji Junction (Task 5):**
- Created `vocab_kanji` Table construct with composite PK (vocab_id, kanji_id)
- Links Vocab to Kanji for vocabulary-kanji associations

**Alembic Migration (Task 6):**
- Created `alembic/versions/003_create_vocab_tags_tables.py`
- Creates: tags, vocab, vocab_tags, vocab_kanji tables
- All FK constraints properly defined

**Pydantic Schemas (Task 7):**
- Created `src/vocab/schemas.py`
- TagResponse: id, name
- VocabCreateRequest: word, reading, meanings, kanji_ids, tags, creator_comment
- VocabResponse: all fields + nested tags and kanji
- VocabDetailResponse: extends VocabResponse with creator_username

**Tests (Task 8):**
- Created `tests/vocab/test_models.py` with 8 comprehensive tests
- Tests: model creation, field constraints, uniqueness, many-to-many relationships
- Updated `tests/conftest.py` to import all models for proper Base.metadata registration
- All 30 tests pass (no regressions)

**Pre-commit Checks:**
- All hooks pass: ruff, ruff-format, mypy, gitleaks

**Code Review Fixes:**
- Removed VocabDetailResponse (YAGNI - consolidated)
- Added created_at timestamp to Tag model for consistency
- Added tests/auth/test_models.py with 7 tests for User/Session models
- Added tests/vocab/test_schemas.py with 8 schema validation tests
- Updated migration 003 to include tags.created_at column
- Updated TagResponse schema with created_at field
- Total tests: 45 (up from 30)

### File List

**Created Files:**
- `src/auth/models.py` - User, Session SQLAlchemy models
- `src/vocab/models.py` - Vocab, Tag models + junction tables
- `src/vocab/schemas.py` - VocabCreateRequest, VocabResponse, TagResponse
- `alembic/versions/002_create_users_sessions.py` - Users/Sessions migration
- `alembic/versions/003_create_vocab_tags_tables.py` - Vocab/Tags migration
- `tests/vocab/test_models.py` - Vocab model tests
- `tests/auth/test_models.py` - User/Session model tests
- `tests/vocab/test_schemas.py` - Schema validation tests

**Modified Files:**
- `tests/conftest.py` - Added model imports for Base.metadata registration, fixed Generator type hint
- `alembic/versions/001_create_kanji_table.py` - Added type ignore for mypy

## Change Log

- 2026-01-24: Story 3.1 implementation completed
  - Created User/Session models with migration
  - Created Vocab, Tag models with junction tables
  - Created Pydantic schemas for API
  - All 8 tests pass, full suite of 30 tests pass
  - Pre-commit checks pass
  - All acceptance criteria satisfied
- 2026-01-24: Code review fixes applied
  - Removed VocabDetailResponse (YAGNI)
  - Added created_at to Tag model + migration
  - Added tests/auth/test_models.py (7 tests)
  - Added tests/vocab/test_schemas.py (8 tests)
  - Total: 45 tests pass, pre-commit pass
