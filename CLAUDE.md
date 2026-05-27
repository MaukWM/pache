# CLAUDE.md — Kanji SRS Platform

Agent onboarding. Read this first, then the linked BMAD docs before writing code.

## What this is

Social SRS (spaced-repetition) kanji learning platform with a shared item pool — WaniKani-style lessons, reviews, SRS stage progression, burn & resurrect. Backend is mature (Epics 1–5 implemented). **Frontend is greenfield** (see below).

## Repo layout

| Path | What |
|------|------|
| `src/` | FastAPI backend. One package per domain: `auth`, `kanji`, `vocab`, `lessons`, `reviews`, `progress`, `wanikani`, plus `core`, `database.py`, `settings.py`, `main.py`. |
| `frontend/` | React 19 + TS + Vite. **Currently the default Vite scaffold, untracked in git.** No real UI yet. |
| `_bmad-output/planning-artifacts/` | Design source of truth: `prd.md`, `architecture.md`, `epics.md`, `project-context.md`. |
| `_bmad-output/implementation-artifacts/` | Per-story specs (1.1 → 5.4). |
| `_bmad-output/analysis/` | Brainstorm + code reviews. |
| `alembic/` | Migrations. `scripts/seed_kanji.py` seeds ~12.5k kanji. |

## Read before coding

1. `_bmad-output/planning-artifacts/project-context.md` — **critical rules** (async everywhere, thin routes / service layer, schema naming). Non-negotiable.
2. `_bmad-output/planning-artifacts/architecture.md` — component boundaries, auth model, structure mapping.
3. `_bmad-output/planning-artifacts/prd.md` + `epics.md` — feature scope, 36 FRs.

## Backend conventions (from project-context.md)

- **Async everywhere.** All DB ops `async`, `AsyncSession`. Never sync `db.query(...)`.
- **Thin routes, fat services.** Routes in `<domain>/router.py` just call `<domain>/service.py`. All logic in services.
- **Schema naming:** `XCreateRequest` / `XUpdateRequest` (incoming), `XResponse` (outgoing).
- Stack: Python 3.12+, FastAPI 0.115+, SQLAlchemy 2.0 async, asyncmy, MySQL 8, Pydantic v2, structlog, uv, ruff, mypy, pytest + pytest-asyncio.

## Run it

```bash
docker compose up -d                 # MySQL + API
DATABASE_URL="mysql+asyncmy://kanji_user:kanji_password@localhost/kanji_srs" uv run alembic upgrade head
DATABASE_URL="mysql+asyncmy://kanji_user:kanji_password@localhost/kanji_srs" uv run python -m scripts.seed_kanji
# API: http://localhost:8000  · docs: http://localhost:8000/docs
```

Frontend:
```bash
cd frontend && npm install && npm run dev   # Vite dev server
```

## API contract (for the frontend)

- Base prefix: **`/api/v1`** (`settings.api_prefix`). Health: `GET /health`.
- Auth: **`Authorization: Bearer <token>`** header (`HTTPBearer`, `auth/dependencies.py::get_current_user`). Frontend stores the token.
- Endpoints implemented:
  - `GET /kanji`, `GET /kanji/{id_or_char}`
  - `POST /vocab`, `GET /vocab`, `GET /vocab/{id}`
  - `POST /lessons` (batch complete), lesson queue under progress
  - `GET /reviews` (items due), `POST /reviews` (submit review → SRS stage progression)
  - Progress + progress-actions routers (queue add/list/remove, resurrect burned)
- Confirm live shapes at `/docs` (OpenAPI) — it's the authoritative contract.

## ⚠️ Frontend status — START HERE if doing frontend work

There is **no frontend yet** and **no UX/design decisions recorded anywhere**:

- `frontend/` is the unmodified `npm create vite` template (React 19 + TS), **not committed** to git.
- `architecture.md` explicitly defers frontend ("plugged on later").
- BMAD `create-ux-design` workflow = **pending** — never run. No wireframes, no design system, no component plan.

Before building UI, design decisions must be captured. Options:
- Run the BMAD UX workflow: `/bmad-create-ux-design` (ux-designer agent) → writes a UX doc into `_bmad-output/planning-artifacts/`.
- Or capture decisions directly here (stack additions, routing, state mgmt, styling/design system, auth flow, which API endpoints each screen hits).

Open frontend gaps to decide: styling (Tailwind? CSS modules?), routing (react-router?), data fetching (TanStack Query? fetch?), state, auth-token storage, **CORS** (backend `main.py` mounts no CORS middleware — cross-origin dev calls will fail until added), and whether an **auth/login router is mounted** (`auth_router` is *not* in `main.py:include_router` — only `get_current_user` dependency exists, so there may be no login endpoint yet).

## Workflow

BMAD method, greenfield. Status tracked in `_bmad-output/planning-artifacts/bmm-workflow-status.yaml`. Commands under `.claude/commands/bmad/`. Commits use gitmoji (`:sparkles:`, `:memo:`, `:art:`).
