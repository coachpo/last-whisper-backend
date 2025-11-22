# Last Whisper Backend

Last Whisper is a FastAPI backend that powers a dictation-training workflow with Google Cloud text-to-speech (TTS), attempt scoring, analytics, and tag management. It exposes a fully typed REST API plus background queues that generate and monitor audio tasks.

## Key Capabilities
- Dictation item CRUD with background audio generation and locale/difficulty filtering.
- Attempt ingestion with WER-based scoring and normalized text comparison.
- Stats and practice-log endpoints for dashboards and progress charts.
- Tag presets, health monitoring, and structured logging ready for production deployments.

## Project Structure
```
app/                 # FastAPI app, routes, services, models, config
run_api.py           # Entry point that boots uvicorn with custom logging
audio/               # Generated WAV assets (gitignored)
data/dictation.db    # Default SQLite database
docs/                # Architecture and migration notes (`docs/system_spec.md`)
tests/               # Pytest suite mirroring the app layout
```
See `AGENTS.md` for contributor conventions.

## Prerequisites
- macOS/Linux/WSL with Python 3.11+
- Conda environment named `last_whisper`
- Google Cloud project with Text-to-Speech and Translation APIs enabled
- `GOOGLE_APPLICATION_CREDENTIALS` JSON stored at `keys/google-credentials.json`

## Environment Setup
```bash
conda create -n last_whisper python=3.11
conda activate last_whisper
python -m pip install --upgrade pip
pip install -e .[dev]
```
Create a `.env` file (or export env vars) to override defaults such as `DATABASE_URL`, `CORS_ORIGINS`, and `GOOGLE_APPLICATION_CREDENTIALS`. Baseline values live in `app/core/config.py` and fall back to SQLite plus local audio storage.

## Running the API
```bash
conda activate last_whisper
python run_api.py               # uses settings from app/core/config.py
# alternatively
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
OpenAPI docs are available at `/docs` when `environment=development`. The `/health` endpoint reports DB, audio directory, TTS manager, and clock diagnostics.

## Testing & Quality
```bash
conda activate last_whisper
pytest                           # full suite (sync + async)
pytest --cov=app --cov-report=term-missing
ruff check app tests             # linting
black app tests                  # formatting (88 columns)
```
Fixtures in `tests/conftest.py` supply a temporary SQLite database, dependency overrides, and dummy TTS managers—mirror the `app/` layout for new tests.

## Configuration Notes
- Update `app/core/config.py` when adding new settings; they automatically load from `.env` via `pydantic-settings`.
- Audio files save to `settings.audio_dir` (default `audio/`). Deleting items removes their audio assets.
- Background TTS jobs run through `TTSEngineManager`; ensure worker threads can write to `audio/` and reach Google Cloud.

## Deployment
- **Docker:** `docker build -t last-whisper-backend .` then `docker run -p 8000:8000 --env-file .env last-whisper-backend`.
- **Gunicorn/Uvicorn:** Use `last-whisper-api` script (declared in `pyproject.toml`) or run `uvicorn app.main:app --workers 4`. Disable `reload` in production.
- **Data Stores:** Switch `settings.database_url` to Postgres/MySQL for multi-user deployments; SQLAlchemy models are backend-agnostic.

## Further Reading
- `docs/system_spec.md` for a detailed architecture walkthrough and endpoint reference.
- GitHub Issues/Discussions for roadmap items.
