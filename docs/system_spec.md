# Last Whisper Backend – Comprehensive Specification

## 1. System Overview
- **Purpose:** Provide a production-ready FastAPI backend that powers a dictation training workflow with automated TTS (Text-To-Speech), scoring, analytics, and tag management.
- **Key Capabilities:** Dictation item CRUD with background audio generation, practice attempt ingestion & scoring, stats reporting, preset tag management, health monitoring, and Google Cloud TTS orchestration.
- **Primary Use Cases:** Language/dictation learning tools that deliver audio prompts, accept user submissions, compute WER-based feedback, and surface progress analytics without session state.

## 2. Architecture Summary
| Layer | Responsibilities | Key Modules |
| --- | --- | --- |
| **Entry / Runtime** | Process startup, logging, server host/port setup | `run_api.py`, `app/main.py`, `app/core/logging.py`, `app/core/uvicorn_logging.py` |
| **API Layer** | HTTP routing, dependency resolution, validation schemas | `app/api/routes/*.py`, `app/api/dependencies.py`, `app/models/schemas.py` |
| **Service Layer** | Business logic and orchestration | `app/services/*.py` |
| **Data Layer** | DB connectivity, ORM models, enums | `app/models/database_manager.py`, `app/models/models.py`, `app/models/enums.py` |
| **TTS Engine Layer** | Provider abstraction, queue management, task lifecycle | `app/tts_engine/*.py` |
| **Core Utilities** | Configuration, exceptions, logging helpers | `app/core/*.py` |

Interactions flow from HTTP routes → dependency-provided services → data/TTS layers, with configuration and logging accessible globally via `app.core`.

## 3. Runtime & Lifecycle
1. **Startup (`run_api.py` / `app.main`):**
   - `setup_logging()` configures structured logging before boot.
   - FastAPI `app` created with custom lifespan manager to initialize DB, TTS engine, and TTS manager, and to shut them down gracefully.
   - CORS policy is derived from comma-separated config strings, enabling wildcard support.
   - Custom exception handlers:
     - `TTSAPIException` mapped to structured JSON errors.
     - Generic handler logs stack traces (development mode exposes `detail`).

2. **Dependency Injection (`app/api/dependencies.py`):**
   - Singleton caches per process for DB manager, service instances, TTSEngine wrapper, manager, and tag/task services.
   - Manager uses `settings.database_url` and lazily instantiates dependencies, making them overrideable in tests.

3. **Background TTS Monitoring:** `TTSEngineManager.start_monitoring()` spins a daemon thread that consumes provider message queues and syncs DB task rows plus linked items.

## 4. Core Modules

### 4.1 API Routes
| Route Module | Responsibilities |
| --- | --- |
| `health.py` | Aggregates DB health, audio dir write check, TTS status, manager status, version/time. |
| `items.py` | Dictation CRUD helpers, difficulty inference, filtering (locale, tags, difficulty ranges, practiced), bulk creation, tag/difficulty updates, audio download, TTS status lookups. |
| `attempts.py` | Creates attempts with auto-scoring, fetches individual attempts and paginated listings (with filtering by item & time range). |
| `stats.py` | Provides summary stats, practice log with pagination, per-item stats, and progress-over-time data. |
| `tags.py` | Async wrappers that run synchronous `TagsService` work in threadpool; supports create/list/delete. |

### 4.2 Services
- **ItemsService:** Manages dictation records, difficulty inference, and TTS job scheduling via shared executor; bulk creation handles partial failures and marks TTS failures.
- **AttemptsService:** Retrieves reference text, normalizes inputs (unicodedata + optional `unidecode`), computes WER (prefers `jiwer`, falls back to manual DP) and persists scoring metadata.
- **StatsService:** Performs SQLAlchemy aggregations for summary, practice logs (items + attempts), per-item stats, and daily progress series.
- **TagsService:** CRUD for preset tags with validation and typed responses.
- **TaskService:** Legacy helper for direct task table interactions.
- **TTSEngineManager:** Deduplicates submissions via MD5, enqueues provider requests, monitors message queues, updates tasks/items, exposes stats, and cleans failed rows.

### 4.3 TTS Engine Components
- **`tts_engine_wrapper.py`:** Encapsulates provider configuration (Google Cloud), credential loading, lifecycle management, and bridge to DummyTTSEngine for tests.
- **Provider Implementations:** `tts_engine_gcp.py` integrates the official SDK, normalizes voice parameters, and pushes completion messages into queues consumed by the manager.

## 5. Data Model Overview
- **SQLAlchemy Tables (`app/models/models.py`):**
  - `Task`: Tracks TTS lifecycle, metadata (duration, sampling rate), filenames, relationships to `Item`.
  - `Item`: Dictation text with locale, difficulty, JSON tags, TTS status, relationships to attempts/tasks; helper properties parse tags and check attempt existence.
  - `Attempt`: Stores scored submissions with WER metrics/timestamps.
  - `Tag`: Preset tag metadata with created/updated timestamps.
- **Enums (`app/models/enums.py`):** `TaskStatus`, `ItemTTSStatus`, etc., mirror DB/TTS states.
- **Pydantic Schemas (`app/models/schemas.py`):** Request/response models for items, attempts, stats, health, tags; enforce pagination bounds and validation ranges.

## 6. Configuration & Environment
- Centralized in `app/core/config.py` (pydantic-settings, `.env` support).
- Key settings: environment flags, host/port/log level, doc URLs, SQLite `database_url`, `audio_dir`, submission workers, Google credentials, comma-separated CORS policies.
- `DatabaseManager` auto-creates tables and audio dir; `run_api.py` uses settings to configure Uvicorn.

## 7. API Surface (OpenAPI-derived)
### Health
- `GET /health`
  - Returns `HealthCheckResponse` containing an overall `status` plus per-component diagnostics (DB, audio dir, TTS manager, clock skew, etc.).
  - No parameters; always 200 unless the app fails before routing.

### Items
- `POST /v1/items`
  - Body: `ItemCreateRequest` requires `locale` (2–10 chars) and `text` (1–10 000 chars) with optional `difficulty` (int 1–5) and `tags` array.
  - Response: 202 with `ItemResponse` reflecting `pending` TTS status; 422 on validation errors.
- `POST /v1/items/bulk`
  - Body: `BulkItemCreateRequest` containing 1–100 `ItemCreateRequest` payloads.
  - Response: 202 with `BulkItemCreateResponse` summarizing created vs failed items plus submission timestamp.
- `GET /v1/items`
  - Query filters: `locale`, repeated `tag`, `difficulty` (single value or `min..max` string), `practiced` (bool), `sort` (default `created_at.desc`).
  - Pagination: `page` ≥ 1 (default 1), `per_page` 1–100 (default 20).
  - Responses: 200 with `ItemListResponse`, 400 for invalid filter combos, 422 for malformed params.
- `GET /v1/items/{item_id}`
  - Path `item_id` (int) resolves a single dictation item plus metadata; 404 if missing.
- `DELETE /v1/items/{item_id}`
  - Deletes the item, its audio asset, and related attempts/tasks; returns 204 on success, 404 when the item is absent, and 422 for malformed IDs.
- `GET /v1/items/{item_id}/tts-status`
  - Reports latest TTS state via `ItemTTSStatusResponse`; 404 if the item is absent.
- `PATCH /v1/items/{item_id}/difficulty`
  - Body: `DifficultyUpdateRequest` with `difficulty` constrained to integers 1–5.
  - Response: `DifficultyUpdateResponse` echoing prior/current difficulty with timestamps; 422 on invalid range.
- `PATCH /v1/items/{item_id}/tags`
  - Body: `TagUpdateRequest` containing the complete replacement list of tags.
  - Response: `TagUpdateResponse` listing previous vs current tags; 404/422 on invalid targets or payloads.
- `GET /v1/items/{item_id}/audio`
  - Streams the generated audio (`audio/wav`); returns JSON errors when audio is not ready (400) or missing (404).

### Attempts
- `POST /v1/attempts`
  - Body: `AttemptCreateRequest` with `item_id` and attempt `text` (max 10 000 chars).
  - Response: 201 `AttemptResponse` including score, WER, and counts; 404 if the referenced item is missing.
- `GET /v1/attempts`
  - Query filters: `item_id`, `since`/`until` timestamps (ISO 8601), plus `page` ≥ 1 and `per_page` 1–100 (default 20).
  - Response: 200 `AttemptListResponse`; 400 for invalid windows, 422 for malformed params.
- `GET /v1/attempts/{attempt_id}`
  - Path `attempt_id` (int) retrieves a single attempt or returns 404.

### Stats
- `GET /v1/stats/summary`
  - Optional `since`/`until` query params bound to ISO datetimes to scope aggregations; validates that `since <= until`.
  - Returns `StatsSummaryResponse` with totals, averages, and derived practice minutes.
- `GET /v1/stats/practice-log`
  - Query `since`/`until` plus pagination (`page` ≥ 1, `per_page` 1–100) to list `PracticeLogEntry` rows.
  - Response: 200 `PracticeLogResponse`; 400/422 errors follow the same rules as other paginated endpoints.
- `GET /v1/stats/items/{item_id}`
  - Path `item_id` selects aggregated stats for a single dictation item; 404 if missing.
- `GET /v1/stats/progress`
  - Query params: optional `item_id` and `days` (1–365, default 30) to define the rolling window.
  - Returns progress-over-time series suitable for charting; 400 on invalid ranges.

### Tags
- `POST /v1/tags`
  - Body: `TagCreateRequest` with `name` length 1–50 characters.
  - Response: 201 `TagResponse`; 422 on duplicates or invalid length.
- `GET /v1/tags`
  - Pagination via `limit` 1–1000 (default 100) and `offset` ≥ 0 (default 0).
  - Response: 200 `TagListResponse` containing total count metadata.
- `DELETE /v1/tags/{tag_id}`
  - Removes a preset tag without touching existing items; returns 204 on success and 422 when the path parameter fails validation.

## 8. Background TTS Workflow
1. ItemsService persists a new item (difficulty inferred if absent) and queues `_schedule_tts_job`.
2. Shared `ThreadPoolExecutor` calls `_submit_tts_job`, which interacts with task manager or dummy stub.
3. `TTSEngineManager.submit_task_for_item` deduplicates via MD5, verifies provider availability, and records a new `Task` row.
4. Provider implementations process requests and push status messages to a queue.
5. Manager monitor loop consumes messages, updates task metadata (timestamps, file info), and cascades status changes to linked items (`PENDING` → `COMPLETED`/`FAILED`).
6. Audio assets persist under `audio/` (e.g., `item_{id}.wav`); deletions remove associated audio files.

## 9. Persistence & Storage
- **Database:** SQLite by default; `DatabaseManager` configures engine (foreign keys on) and exposes `get_session()`.
- **Audio Files:** Stored under `settings.audio_dir`; health check verifies write access.
- **Credentials:** `keys/google-credentials.json` placeholder for GCP service accounts.
- **Data Directory:** `data/dictation.db`; tables auto-created at startup.

## 10. Testing & Quality
- **Test Suite (`tests/`):** Fixtures in `conftest.py` supply SQLite DB, dummy task/TTS managers, and FastAPI TestClient with overrides for both dependency module functions and per-route wrappers.
- **Coverage:** Config flag behavior, HTTP handlers, items/attempts/stats/tags services, and attempts API integration.
- **Commands:** `pytest` (optionally via `conda run -n last_whisper pytest`), `pytest-asyncio`, `pytest-cov` ready for coverage.
- **Tooling:** `black` + `ruff` configured in `pyproject.toml` (line length 88, target Python 3.11).

## 11. Deployment & Operations
- **Local Dev:** `python run_api.py` or `uvicorn app.main:app --reload`; logging configured via `app/core/uvicorn_logging.py`.
- **Docker:** Provided `Dockerfile` for containerized deployment; env vars control settings.
- **Production:** Run with Uvicorn/Gunicorn (reload disabled automatically outside dev). Multiple workers can share DB/manager via dependency caches.
- **Monitoring:** `/health` surfaces component status; `TTSEngineManager` exposes statistics and cleanup utilities.

## 12. Extensibility Considerations
- **TTS Providers:** Add new provider in `tts_engine_*` with consistent queue contract; register in wrapper for selection.
- **Authentication:** Current API is session-less; middleware could add auth without changing services.
- **Persistence Scaling:** Switch `database_url` to Postgres/MySQL; SQLAlchemy models are backend-agnostic.
- **Observability:** Logging hooks exist across services; extend `LOGGING_CONFIG` for centralized tracing.
- **Automation:** Background TTS can scale horizontally by adjusting `tts_submission_workers` or running multiple manager instances with shared DB queueing.
