## Whisper TTS API – Architecture Overview

This document explains the system design, major components, data flows, and key decisions of the Whisper TTS API
project.

### Goals and Constraints

- Provide a clean, production-grade HTTP API for Text-to-Speech (TTS)
- Orchestrate model inference, task lifecycle, persistence, and delivery
- Remain modular and testable with clear separation of concerns
- Support CPU/GPU execution and horizontal scalability patterns
- Support dictation practice workflow with TTS integration

### High-level Architecture

- **API Layer (FastAPI)**: HTTP endpoints, request/response validation, error translation.
- **Service Layer**: Business logic orchestration and integration with external systems.
    - `TTSEngineWrapper` encapsulates the concrete TTS engine implementation (`TTSEngine`).
    - `TTSEngineManager` orchestrates TTS tasks and synchronizes task statuses with database.
    - Service classes provide business logic for items, attempts, stats, and tasks.
- **Data Layer**:
    - SQLAlchemy models (`Task`, `Item`, `Attempt`) and a `DatabaseManager` that owns the engine/session lifecycle.
- **Core**: Configuration (`Settings`) and domain-level exceptions.

Directory layout (key parts):

```
app/
  api/
    routes/           # HTTP routes (health, tts, items, attempts, stats)
    dependencies.py   # DI providers for services
  core/
    config.py         # Settings (env/.env driven)
    exceptions.py     # Domain exceptions mapped to HTTP
  models/
    database.py       # SQLAlchemy ORM models and DB manager
    schemas.py        # Pydantic request/response models
  services/
    task_service.py       # TaskService for database operations
    items_service.py      # ItemsService for dictation items
    attempts_service.py   # AttemptsService for practice tracking
    stats_service.py      # StatsService for analytics
  tts_engine/
    tts_engine.py         # Core TTS engine (Hugging Face model + queues)
    tts_engine_manager.py # TTSEngineManager (task orchestration + DB sync)
    tts_engine_wrapper.py # TTSEngineWrapper (lifecycle + API interface)
  main.py             # FastAPI app, lifespan startup/shutdown
run_api.py            # Uvicorn runner
```

### Component Responsibilities

- **FastAPI app (`app/main.py`)**
    - Initializes services on startup (`lifespan`): `TTSEngineWrapper.initialize()` then
      `TTSEngineManager.start_monitoring()`.
    - Registers exception handlers to consistently return `ErrorResponse`.
    - Mounts routers from `app/api/routes`.

- **API routes**
    - **TTS Routes** (`app/api/routes/tts.py`): TTS conversion endpoints, audio file serving
    - **Items Routes** (`app/api/routes/items.py`): Dictation item management
    - **Attempts Routes** (`app/api/routes/attempts.py`): Practice attempt tracking
    - **Stats Routes** (`app/api/routes/stats.py`): Analytics and reporting
    - **Health Routes** (`app/api/routes/health.py`): System health monitoring
    - All routes validate inputs using Pydantic schemas and delegate to appropriate services

- **Service layer**
    - **TTSEngineWrapper** (`tts_engine/tts_engine_wrapper.py`)
        - Owns `TTSEngine` instance, ensures correct lifecycle (start/stop), and exposes a minimal API (
          `submit_request`, `get_task_queue`).
        - Guards usage via `is_initialized` and raises `TTSServiceException` on misuse.
    - **TTSEngineManager** (`tts_engine/tts_engine_manager.py`)
        - Wraps `TTSEngine` and starts a monitoring thread to watch the TTS service task queue.
        - Provides `submit_task`, `submit_multiple_tasks`, `get_task_status` for API usage.
        - Handles task deduplication by `text_hash` and database synchronization.
    - **Service classes** (`services/`)
        - `TaskService`: Database operations for TTS tasks
        - `ItemsService`: Dictation item management with TTS integration
        - `AttemptsService`: User practice tracking and scoring
        - `StatsService`: Analytics and reporting

- **Concrete TTS implementation (`tts_engine/tts_engine.py`)**
    - Loads the Hugging Face model `facebook/mms-tts-fin` and tokenizer.
    - Supports device selection (auto CPU/GPU) and switching.
    - Uses two queues:
        - An internal `request_queue` for inbound synthesis jobs.
        - A public `task_queue` for publishing task lifecycle events to observers.
    - A worker thread processes requests: tokenizes, runs inference, writes a WAV file, and emits `queued` →
      `processing` → `completed` → `done` (or `failed`) messages.

- **Task manager (`tts_engine/tts_engine_manager.py`)**
    - Persists new tasks in the DB on submission and deduplicates by `text_hash` (MD5 of original text).
    - Monitors the TTS service `task_queue` in a background thread and updates persisted task records as statuses
      change.
    - Provides reporting (status counts, averages, duplicates) and cleanup utilities.
    - Integrates with `Item` model for dictation workflow.

- **Persistence layer (`models/database.py`)**
    - SQLAlchemy models:
        - `Task`: TTS task lifecycle with fields for timestamps, output location, audio metadata and device
        - `Item`: Dictation items with TTS status and audio URL
        - `Attempt`: User practice attempts with scoring
    - `DatabaseManager` encapsulates engine and session factory and ensures tables exist.

- **Core (`core/config.py`, `core/exceptions.py`)**
    - `Settings` uses `pydantic-settings` with `.env` support for host/port, database URL, docs URLs, TTS device, and
      output dir.
    - Exception hierarchy (`TTSAPIException` and specializations) standardizes error propagation and HTTP mapping.

### Request Lifecycle and Data Flow

#### TTS Conversion Flow
1) Client calls `POST /api/v1/tts/convert` with text.
2) Route validates input and calls `TTSEngineManager.submit_task(text, custom_filename)`.
3) `TTSEngineManager.submit_task` checks for duplicates by `text_hash`. If a prior non-failed task exists, returns its
   `task_id` to avoid redundant synthesis.
4) Otherwise, it forwards to `TTSEngine.submit_request`, which enqueues the job and immediately emits a
   `queued` message to the public `task_queue`.
5) `TTSEngineManager` writes a `Task` row with `status='queued'` and timestamps.
6) The `TTSEngine` worker processes the job, writes the WAV file to the configured output directory, and emits
   `processing` → `completed` → `done` messages with metadata (timestamps, file size, sampling rate, device).
7) The `TTSEngineManager` monitoring thread consumes these messages and updates the `Task` row accordingly (status and
   metadata fields).
8) Clients poll `GET /api/v1/tts/{conversion_id}` or list via `GET /api/v1/tts`.
9) When complete, clients download audio with `GET /api/v1/tts/{conversion_id}/download`.

#### Dictation Item Flow
1) Client calls `POST /api/v1/items` to create a dictation item.
2) `ItemsService.create_item` creates the item with `tts_status="pending"`.
3) If TTS manager is available, it automatically submits a TTS task for the item.
4) TTS processing follows the standard flow above.
5) When TTS completes, the item's `tts_status` is updated to `"ready"` and `audio_url` is set.
6) Users can practice with `POST /api/v1/items/{item_id}/attempts` and track progress.

### Data Models

#### Task Model
- Identity: `id` (PK), `task_id` (external ID), `text_hash` (dedupe key)
- Content: `original_text`, `custom_filename`, `output_file_path`
- Lifecycle: `status`, `submitted_at`, `started_at`, `completed_at`, `failed_at`, `created_at`
- Metadata: `file_size`, `sampling_rate`, `device`, `task_metadata` (JSON), derived `duration`
- Relationships: `item_id` (links to dictation item)

#### Item Model
- Identity: `id` (PK), `locale`, `text`
- Metadata: `difficulty`, `tags_json`, `tts_status`, `audio_url`
- Timestamps: `created_at`, `updated_at`
- Relationships: `attempts`, `task`

#### Attempt Model
- Identity: `id` (PK), `item_id` (FK), `user_id`
- Practice data: `audio_url`, `transcription`, `score`, `feedback`
- Timestamps: `created_at`

### Error Handling

- Route layer translates domain exceptions to HTTP responses using FastAPI exception handlers.
- `TTSServiceException`, `TaskNotFoundException`, `ValidationException`, `DatabaseException` ensure consistent status
  codes and payloads (`ErrorResponse`).

### Concurrency and Threads

- `TTSEngine` runs a worker thread for synthesis.
- `TTSEngineManager` runs a monitor thread that consumes the public `task_queue` and updates the database.
- API requests are handled by the ASGI server (Uvicorn) independently.

### Configuration

- Centralized via `Settings` with environment variables (`.env`). Key options: host, port, log level, database URL, docs
  URLs, TTS device, output directory, audio directory, base URL.

### Observability and Operations

- Health endpoints: `/` and `/health` return `HealthResponse` with version and timestamp.
- File outputs are stored under the configured audio directory; filenames allow deterministic overrides via
  `custom_filename` and default to timestamp+hash.
- The architecture supports external consumers of the `task_queue` if needed (e.g., metrics, notifications) without
  coupling them to the API.

### Scalability Considerations

- Stateless API layer enables horizontal scaling behind a load balancer.
- The DB ensures shared state across API instances.
- The current TTS worker and task monitor live in-process. For higher throughput or multi-instance safety:
    - Extract queues to a broker (e.g., Redis/RabbitMQ) and run the TTS workers as separate processes.
    - Use a distributed lock or job reservation to prevent duplicate processing across instances.
    - Store artifacts in shared or object storage (e.g., S3) instead of local disk.

### Testing Strategy

- API tests for health and TTS endpoints (`tests/test_api`).
- Service-level tests for task manager and TTS service (`tests/test_services`).
- Components are factored to allow mocking (`TTSEngineWrapper`, `TTSEngineManager`, service classes).

### Security Notes

- Input validation via Pydantic schemas with bounds on text size and list cardinality.
- Filename sanitization: `custom_filename` is accepted without path components; server enforces `.wav` extension on
  download.
- Consider rate limiting and authentication for production deployments.

### Key Trade-offs

- Simplicity of in-process queues/threads vs. robustness of external job systems.
- Immediate DB writes and status updates vs. eventual consistency across threads.
- Integration of TTS workflow with dictation practice vs. separation of concerns.

### Recent Changes

- **Unified TTS Engine**: Replaced separate service files with a unified `tts_engine/` module
- **Enhanced Data Models**: Added `Item` and `Attempt` models for dictation workflow
- **Service Layer Consolidation**: Consolidated business logic into focused service classes
- **TTS Integration**: Seamless integration between TTS processing and dictation items
- **Audio Management**: Centralized audio file handling with proper URL generation


