# CLAUDE.md — pache

Agent onboarding. Read this first, then the linked BMAD docs before writing code.

## What this is

**pache** — a social SRS (spaced-repetition) kanji learning platform with a shared item pool. WaniKani-style lessons, reviews, SRS stage progression, burn & resurrect. Backend is mature (Epics 1–5). Frontend is a real React app (lessons, reviews, dashboard with forecast/spreads, kanji/vocab browsing, account/admin, light+dark themes).

> Named after Patchouli Knowledge's nickname パチェ ("The Unmoving Great Library"). The DB is still named `kanji_srs` — that's plumbing, intentionally not renamed.

## Repo layout

| Path | What |
|------|------|
| `src/` | FastAPI backend. One package per domain: `auth`, `kanji`, `vocab`, `lessons`, `reviews`, `progress`, `wanikani`, plus `core`, `database.py`, `settings.py`, `main.py`. |
| `frontend/` | React 19 + TS + Vite SPA (committed). `src/pages/`, `src/components/` (+ `ui/` primitives), `src/lib/`. See **Frontend** below. |
| `_bmad-output/planning-artifacts/` | Design source of truth: `prd.md`, `architecture.md`, `epics.md`, `project-context.md`. **Do not edit BMAD docs.** |
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

## Frontend

React 19 + TS + Vite SPA under `frontend/`.

- **Routing:** `react-router-dom` v7.
- **Data:** TanStack Query v5; all HTTP through `src/lib/api.ts` helpers.
- **Auth:** token in `localStorage`, sent as `Authorization: Bearer <token>`. Auth context in `src/lib/auth.tsx`. Login at `POST /api/v1/auth/login`.
- **Styling:** Tailwind CSS v4 (`@tailwindcss/vite`). Design tokens (incl. light/dark) live in `src/index.css` (`:root` + `.dark`). shadcn-style primitives in `src/components/ui/` over Radix; `lucide-react` icons; `sonner` toasts; `cn()` from `src/lib/utils.ts`.
- **Aesthetic:** "washed" palette, **sharp corners globally** (all radii forced to 0 in `index.css`), mincho serif (`--font-mincho`) for Japanese glyphs. Soften strong colors rather than using vivid defaults; keep it theme-aware (verify both light & dark).
- **Pages:** Dashboard, Login, Kanji/KanjiDetail, Vocab/VocabDetail, Lessons, Review, Progress, Account. **Key components:** `QuizCard`/`QuizShell`/`LessonQuiz` (review/lesson flow), `ReviewForecast`, `ActiveItemSpread`/`SrsSpread`. **lib:** `forecast`, `quiz`, `srs`, `spread`, `romaji`.
- After TS/UI changes, typecheck before a Docker rebuild (`tsc -b` / `npm run build`).

## Run it

```bash
docker compose up -d                 # MySQL + API
DATABASE_URL="mysql+asyncmy://kanji_user:kanji_password@localhost/kanji_srs" uv run alembic upgrade head
DATABASE_URL="mysql+asyncmy://kanji_user:kanji_password@localhost/kanji_srs" uv run python -m scripts.seed_kanji
# API: http://localhost:8000  · docs: http://localhost:8000/docs
```

Frontend (dev):
```bash
cd frontend && npm install && npm run dev   # Vite dev server; CORS is enabled for it
```

**Prod serving:** when `frontend_dist/` exists (the production image bakes the built SPA there), the API serves it — `/assets` static mount + SPA fallback to `index.html` (`main.py`). No `frontend_dist/` → API-only mode. So a frontend change needs an image rebuild to show in a deployed env; the backend hot-reloads.

## API contract (for the frontend)

- Base prefix: **`/api/v1`** (`settings.api_prefix`). Health: `GET /health`. CORS middleware is mounted.
- Auth: **`Authorization: Bearer <token>`** (`HTTPBearer`, `auth/dependencies.py::get_current_user`).
- Routers mounted in `main.py`: `auth`, `kanji`, `vocab`, `progress`, progress-actions, `lessons`, `reviews`, `wanikani`, wanikani-status.
  - `POST /auth/login`, `GET/POST /auth/users`, `POST /auth/password`, `GET/POST /auth/settings`, admin user actions
  - `GET /kanji`, `GET /kanji/{id_or_char}`
  - `POST /vocab`, `GET /vocab`, `GET /vocab/{id}`
  - `POST /lessons` (batch complete), lesson queue under progress
  - `GET /reviews` (items due), `POST /reviews` (submit → SRS stage progression)
  - Progress + progress-actions (queue add/list/remove, resurrect burned)
  - WaniKani sync + status/forecast
- Confirm live shapes at `/docs` (OpenAPI) — it's the authoritative contract.

## Workflow

BMAD method, greenfield. Status tracked in `_bmad-output/planning-artifacts/bmm-workflow-status.yaml`. Commands under `.claude/commands/bmad/`. Commits use gitmoji (`:sparkles:`, `:memo:`, `:art:`).
