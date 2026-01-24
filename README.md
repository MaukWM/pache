# Kanji SRS Platform

## Quick Start

```bash
# Start the database and API
docker compose up -d

# Run migrations
DATABASE_URL="mysql+asyncmy://kanji_user:kanji_password@localhost/kanji_srs" uv run alembic upgrade head

# Seed kanji data (~12,500 kanji from jamdict)
DATABASE_URL="mysql+asyncmy://kanji_user:kanji_password@localhost/kanji_srs" uv run python -m scripts.seed_kanji
```

API available at http://localhost:8000
