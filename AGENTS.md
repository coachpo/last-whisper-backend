# Repository Guidelines

## Project Structure & Module Organization
The FastAPI source lives in `app/`, with `api/routes` for HTTP endpoints, `api/dependencies.py` for shared wiring, `core/` for config/logging/exception helpers, and `services/`, `translation/`, and `tts_engine/` for business logic. Persistent artifacts sit in `data/` (SQLite `dictation.db`) and `audio/`, while deployment docs and specs live under `docs/`. Place new tests in the mirrored layout inside `tests/` (e.g., `tests/api` for route tests) so fixtures in `tests/conftest.py` remain discoverable.

## Build, Test, and Development Commands
Install tooling with `python -m pip install -e .[dev]`. Run the API via `python run_api.py` (respects `app/core/config.py`), or `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` when you need manual overrides. Lint with `ruff check app tests` and auto-format using `black app tests`. Execute the suite using `pytest` or add coverage reporting with `pytest --cov=app --cov-report=term-missing`.

## Coding Style & Naming Conventions
Follow Black’s 88-character rule and keep imports sorted as Ruff expects. Prefer explicit type hints and dataclasses/Pydantic models for payloads. Modules, files, and functions use `snake_case`, classes use `PascalCase`, and constants are upper snake. Keep FastAPI router tags and path operation names descriptive (e.g., `tags_router`).

## Testing Guidelines
Pytest with `pytest-asyncio` and `httpx` drives both sync and async tests; name files `test_*.py` and mimic the package path (`tests/services/test_tts...`). Use Factory fixtures in `tests/conftest.py` instead of ad-hoc setup, and assert both HTTP status codes and payload schemas. Aim for coverage on core packages (`app/core`, `app/services`, `app/translation`) before touching integration layers.

## Commit & Pull Request Guidelines
History follows Conventional Commits such as `refactor(google-services): ...` or `feat(translation,tts): ...`; match that `type(scope): summary` style and keep scopes meaningful. Reference linked GitHub issues in the PR description, list test commands you ran, and attach API screenshots or curl transcripts when behavior changes.

## Configuration & Secrets
Settings resolve from `.env` via `pydantic-settings`. Provide `GOOGLE_APPLICATION_CREDENTIALS` pointing to `keys/google-credentials.json`, and never commit raw secrets. For new runtime knobs, add defaults to `app/core/config.py`, expose them through dependency providers, and document overrides in `docs/`.
