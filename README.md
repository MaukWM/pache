# pache

> *If WaniKani is so good, why is there no WaniKani 2?*

A self-hostable, social spaced-repetition (SRS) platform for learning kanji and
vocabulary. WaniKani-style lessons, reviews, SRS stage progression, and
burn & resurrect — built around a **shared item pool** so users can contribute
and study community vocabulary, not just a fixed deck.

The whole app (FastAPI backend + React frontend) ships as a **single container**.

## Run it (released image)

Requires Docker. Pulls the published image and runs it alongside MySQL:

```bash
docker compose -f docker-compose.release.yml up -d
```

Then open **http://localhost:8000** — the API and the web UI are served from the
same origin. Migrations run automatically on startup, and the kanji table
(~12,500 entries) is seeded on first boot.

Pin a specific version with `APP_TAG` (note: container tags drop the `v`):

```bash
APP_TAG=1.5.0 docker compose -f docker-compose.release.yml up -d
```

Image: [`ghcr.io/maukwm/pache`](https://github.com/MaukWM/pache/pkgs/container/pache)
(tags: `latest`, `1.5.0`, `1.5`).

## Features

- **Lessons & reviews** with the WaniKani SRS algorithm (Apprentice → Guru →
  Master → Enlightened → Burned), hour-batched review scheduling.
- **Burn & resurrect** — bring burned items back for more review.
- **Shared item pool** — community vocabulary with readings, meanings, tags,
  and example sentences that can be linked across multiple items.
- **WaniKani integration** — import your Guru+ kanji to seed what you already
  know, and see a live count of reviews due on WaniKani right on the dashboard
  (with a one-click link to do them there). Reviews you do *here* stay local;
  imported items are reviewed on WaniKani.

## Development

The dev stack builds locally and hot-reloads the backend:

```bash
docker compose up -d          # MySQL + API on :8000 (runs migrations, seeds kanji)
```

Frontend dev server (Vite, proxies `/api` to the backend):

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Run the test suite:

```bash
uv run --extra dev pytest
```

## API

The backend is the source of truth for the API contract. With the app running,
the interactive OpenAPI docs are at **http://localhost:8000/docs**.

- Base prefix: `/api/v1`
- Auth: `Authorization: Bearer <token>`
- Health check: `GET /health`

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), MySQL 8, Pydantic v2,
  Alembic, structlog. Managed with `uv`.
- **Frontend:** React 19 + TypeScript, Vite, Tailwind CSS, TanStack Query,
  React Router.
- **Packaging:** multi-stage Dockerfile (Node builds the SPA → FastAPI serves it),
  published to GHCR via GitHub Actions.

## Project structure

| Path | What |
|------|------|
| `src/` | FastAPI backend — one package per domain (`auth`, `kanji`, `vocab`, `lessons`, `reviews`, `progress`, `wanikani`) plus `core`, `database.py`, `main.py`. |
| `frontend/` | React + TS + Vite single-page app. |
| `alembic/` | Database migrations. |
| `scripts/` | `seed_kanji.py` — seeds kanji from jamdict. |
| `_bmad-output/` | Planning & design artifacts (PRD, architecture, epics). |

## Releases

Pushing a `v*` tag triggers `.github/workflows/release.yml`, which builds the
container, pushes it to GHCR (`latest` + semver tags), and creates a GitHub
Release:

```bash
git tag -a v1.5.0 -m "v1.5.0"
git push origin v1.5.0
```

## AI Development Disclosure,
Yes, AI was heavily employed in the creation of this project. When I started, I used this as a bit of a learning project to see how development with the BMAD method would go (see the `_bmad_output/` folder).

## License

Licensed under the **GNU Affero General Public License v3.0** — see [`LICENSE`](LICENSE).