# Last Whisper Backend
FastAPI service for dictation training: TTS generation (Google Cloud), WER-based scoring, tagging, and analytics APIs.

## Overview
- REST + OpenAPI docs, background TTS queues, health checks, typed models.
- Defaults: SQLite at `data/dictation.db`, audio in `audio/`, port 8000.
- Production image: Gunicorn + Uvicorn on Python 3.12-slim.

## Prerequisites
- Python 3.11+ (3.12 supported) and `pip`
- Google Cloud Text-to-Speech credentials JSON at `keys/google-credentials.json`
- Optional: Docker for container runs; `ruff`/`black`/`pytest` for quality checks

## Quickstart (local)
```bash
cd last-whisper-backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e ".[dev]"
export TTS_PROVIDER=google
export GOOGLE_APPLICATION_CREDENTIALS=keys/google-credentials.json
python run_api.py    # http://localhost:8000, docs at /docs
```
Alternate: `uvicorn app.main:app --reload --port 8000`.

## Environment variables (common)
- `TTS_PROVIDER` (default `google`)
- `GOOGLE_APPLICATION_CREDENTIALS` (default `keys/google-credentials.json`)
- `DATABASE_URL` (default `sqlite:///data/dictation.db`)
- `CORS_ORIGINS`, `API_KEYS_CSV` / `API_KEYS`, `PORT` (default 8000), `ENVIRONMENT`
Settings load from `.env` via `pydantic-settings` (`app/core/config.py`).

## Testing & quality
```bash
pytest
pytest --cov=app --cov-report=term-missing
ruff check app tests
black app tests
```

## Docker
```bash
docker build -t last-whisper-backend .
docker run -p 8000:8000 \
  -v $(pwd)/keys:/app/keys:ro \
  -v $(pwd)/audio:/app/audio \
  last-whisper-backend
```
Image entrypoint: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`.

## Project layout
```
app/               # FastAPI routes, services, models, config
run_api.py         # Local dev entrypoint (uvicorn)
audio/             # Generated audio (gitignored)
data/              # SQLite DB (gitignored)
tests/             # Pytest suite mirroring app/
AGENTS.md          # Contributor conventions
Dockerfile         # Production build
```

## Deployment
- Staging/dev: from repo root `docker compose -f ../staging/docker-compose.staging.yml up --build`
- Production: `docker compose -f ../deploy/docker-compose.prod.yml up -d` (uses GHCR image `ghcr.io/coachpo/last-whisper-backend:latest`; mount `deploy/keys` for Google creds)
