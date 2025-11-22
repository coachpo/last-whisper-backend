# Repository Guidelines

## Project Structure & Module Organization
Core FastAPI code lives in `app/`, split into clearly defined layers: `api/routes` exposes versioned endpoints, `core` holds config/logging, `models` mixes SQLAlchemy + Pydantic schemas, `services` contains domain logic, and `tts_engine` wraps the Google Cloud provider. `run_api.py` boots uvicorn with project defaults, while `pyproject.toml` owns dependencies and tool configs. Generated artifacts stay outside source: SQLite data in `data/dictation.db`, cached audio in `audio/`, and credentials in `keys/`. Tests mirror the package layout under `tests/` so every module has a matching suite.

## Build, Test, and Development Commands
- `conda activate last_whisper`: enter the shared conda environment configured for this project.
- `pip install -e .[dev]`: install the app plus lint/test extras from `pyproject.toml`.
- `python run_api.py` (or `uvicorn app.main:app --reload`): launch the API locally with live reload.
- `ruff check app tests` and `black app tests`: enforce linting and formatting before commits.
- `pytest` or `pytest --cov=app --cov-report=term-missing`: run the suite and display coverage expectations.

## Coding Style & Naming Conventions
Follow the strict `black` + `ruff` profile (Python 3.11 target, 88-char lines, 4-space indents). Keep modules small and prefer dependency injection through FastAPI `Depends`. Name modules and files using lowercase with underscores (`items_service.py`), keep Pydantic models in `PascalCase`, and reserve ALL_CAPS for constants/settings. Surface env-driven settings via `app/core/config.py`; never hardcode secrets.

## Testing Guidelines
All new behavior requires pytest coverage beside existing tests (e.g., place API tests in `tests/api/test_items.py`). Name tests `test_<function>_<scenario>` and group fixtures in `tests/conftest.py`. Use `pytest-asyncio` for async endpoints and `httpx.AsyncClient` for FastAPI clients. Maintain ≥85% coverage for `app/`; run `pytest --cov` locally before opening PRs.

## Commit & Pull Request Guidelines
Git history favors Conventional Commit syntax (`feat(api): add scoring hook`, `test: expand stats coverage`) with optional emojis. Write imperative, present-tense summaries under 72 chars and include scopes when touching multiple layers. PRs should link GitHub issues, describe behavior changes, call out migrations/config updates, and attach screenshots or sample `curl` calls for new endpoints. Confirm CI lint/test success and note any follow-up tasks before requesting review.

## Security & Configuration Tips
Use `.env` or shell exports to provide `GCP_*` credentials and database paths consumed by `app/core/config.py`. Keep `keys/` and `data/` out of commits—add redactions or git-crypt if sharing logs. When testing TTS locally, rotate API keys regularly and verify quota usage in provider dashboards.
