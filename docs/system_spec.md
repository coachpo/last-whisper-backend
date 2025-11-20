# Last Whisper Backend – Comprehensive Specification

## 1. System Overview
- **Purpose:** Provide a production-ready FastAPI backend that powers a dictation training workflow with automated TTS (Text-To-Speech), scoring, analytics, and tag management.
- **Key Capabilities:** Dictation item CRUD with background audio generation, practice attempt ingestion & scoring, stats reporting, preset tag management, health monitoring, and multi-provider TTS orchestration (Azure + Google Cloud).
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
- **`tts_engine_wrapper.py`:** Encapsulates provider selection (`azure` vs `gcp`), credential loading, lifecycle management, and bridge to DummyTTSEngine for tests.
- **Provider Implementations:** `tts_engine_gcp.py` and `tts_engine_azure.py` integrate official SDKs, normalize voice parameters, and push completion messages into queues consumed by the manager.

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
- Key settings: environment flags, host/port/log level, doc URLs, SQLite `database_url`, `audio_dir`, TTS provider choice, submission workers, Google/Azure credentials, comma-separated CORS policies.
- `DatabaseManager` auto-creates tables and audio dir; `run_api.py` uses settings to configure Uvicorn.

## 7. API Surface (Highlights)
| Endpoint | Description | Key Validation |
| --- | --- | --- |
| `GET /health` | Returns system + dependency status map. | None. |
| `POST /v1/items` | Creates item, auto-calculates difficulty, enqueues TTS (202). | Requires locale & text. |
| `POST /v1/items/bulk` | Batch insert items with background TTS scheduling. | Handles partial failures. |
| `GET /v1/items` | Paginated/filterable item listing (locale, tags, difficulty, practiced). | Validates sort + pagination. |
| `GET /v1/items/{id}` | Fetches single item plus TTS metadata. | 404 on missing. |
| `PATCH /v1/items/{id}/difficulty` & `/tags` | Update difficulty or tags arrays. | Range & list validation. |
| `GET /v1/items/{id}/tts-status` | Returns TTS status snapshots. | Valid IDs. |
| `POST /v1/attempts` | Scores dictation attempt (WER). | 404 if item missing. |
| `GET /v1/attempts` | Paginated attempts filterable by item/time. | Pagination bounds. |
| `GET /v1/attempts/{id}` | Retrieves single attempt. | 404 on missing. |
| `GET /v1/stats/summary` | Aggregated totals/averages. | Since < until validation. |
| `GET /v1/stats/practice-log` | Paginated per-item aggregates with tags/time. | Same window validation. |
| `GET /v1/stats/items/{id}` | Detailed per-item stats. | 404 on missing. |
| `GET /v1/stats/progress` | Daily time series for attempts/score trends. | Optional `item_id`. |
| `POST/GET/DELETE /v1/tags` | Tag creation, listing, deletion. | Duplicate validation, async wrappers. |

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
- **Credentials:** `keys/google-credentials.json` placeholder; Azure keys via env variables.
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
