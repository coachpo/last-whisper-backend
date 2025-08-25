## Whisper TTS API – Architecture Overview

This document explains the system design, major components, data flows, and key decisions of the Whisper TTS API
project.

### Goals and Constraints

- Provide a clean, production-grade HTTP API for Text-to-Speech (TTS)
- Orchestrate model inference, task lifecycle, persistence, and delivery
- Remain modular and testable with clear separation of concerns
- Support CPU/GPU execution and horizontal scalability patterns

### High-level Architecture

- **API Layer (FastAPI)**: HTTP endpoints, request/response validation, error translation.
- **Service Layer**: Business logic orchestration and integration with external systems.
    - `TTSServiceWrapper` encapsulates the concrete TTS engine implementation (`FBTTSService`).
    - `TaskManagerWrapper` encapsulates the background `TTSTaskManager` that synchronizes task statuses.
    - `DatabaseService` provides a thin façade over the persistence layer.
- **Data Layer**:
    - SQLAlchemy models (`Task`) and a `DatabaseManager` that owns the engine/session lifecycle.
- **Core**: Configuration (`Settings`) and domain-level exceptions.

Directory layout (key parts):

```
app/
  api/
    routes/           # HTTP routes (health, tts)
    dependencies.py   # DI providers for services
  core/
    config.py         # Settings (env/.env driven)
    exceptions.py     # Domain exceptions mapped to HTTP
  models/
    database.py       # SQLAlchemy ORM model and DB manager
    schemas.py        # Pydantic request/response models
  services/
    database.py       # DatabaseService façade
    task_manager.py   # TaskManagerWrapper façade
    tts_fb_service.py # FBTTSService (Hugging Face model + queues)
    outer/
      tts_service.py       # TTSServiceWrapper (lifecycle + API)
      tts_task_manager.py  # TTSTaskManager (queue monitor + DB sync)
  main.py             # FastAPI app, lifespan startup/shutdown
run_api.py            # Uvicorn runner
```

### Component Responsibilities

- **FastAPI app (`app/main.py`)**
    - Initializes services on startup (`lifespan`): `TTSServiceWrapper.initialize()` then
      `TaskManagerWrapper.initialize()`.
    - Registers exception handlers to consistently return `ErrorResponse`.
    - Mounts routers from `app/api/routes`.

- **API routes (`app/api/routes/tts.py`, `health.py`)**
    - Validate inputs using Pydantic schemas (`TTSConvertRequest`, etc.).
    - Delegate to `TaskManagerWrapper` for submitting work and to `DatabaseService` for reads.
    - Return typed responses (`TTSConvertResponse`, `TTSTaskResponse`, etc.).

- **Service façades**
    - `TTSServiceWrapper` (outer/tts_service.py)
        - Owns `FBTTSService` instance, ensures correct lifecycle (start/stop), and exposes a minimal API (
          `submit_request`, `get_task_queue`).
        - Guards usage via `is_initialized` and raises `TTSServiceException` on misuse.
    - `TaskManagerWrapper` (services/task_manager.py)
        - Wraps `TTSTaskManager` and starts a monitoring thread to watch the TTS service task queue.
        - Provides `submit_task`, `submit_multiple_tasks`, `get_task_status` for API usage.
    - `DatabaseService` (services/database.py)
        - Thin typed layer to retrieve tasks and translate DB errors to `DatabaseException`/`TaskNotFoundException`.

- **Concrete TTS implementation (`services/tts_fb_service.py`)**
    - Loads the Hugging Face model `facebook/mms-tts-fin` and tokenizer.
    - Supports device selection (auto CPU/GPU) and switching.
    - Uses two queues:
        - An internal `request_queue` for inbound synthesis jobs.
        - A public `task_queue` for publishing task lifecycle events to observers.
    - A worker thread processes requests: tokenizes, runs inference, writes a WAV file, and emits `queued` →
      `processing` → `completed` → `done` (or `failed`) messages.

- **Task manager (`services/outer/tts_task_manager.py`)**
    - Persists new tasks in the DB on submission and deduplicates by `text_hash` (MD5 of original text).
    - Monitors the TTS service `task_queue` in a background thread and updates persisted task records as statuses
      change.
    - Provides reporting (status counts, averages, duplicates) and cleanup utilities.

- **Persistence layer (`models/database.py`)**
    - SQLAlchemy model `Task` with fields for lifecycle timestamps, output location, audio metadata and device.
    - `DatabaseManager` encapsulates engine and session factory and ensures tables exist.

- **Core (`core/config.py`, `core/exceptions.py`)**
    - `Settings` uses `pydantic-settings` with `.env` support for host/port, database URL, docs URLs, TTS device, and
      output dir.
    - Exception hierarchy (`TTSAPIException` and specializations) standardizes error propagation and HTTP mapping.

### Request Lifecycle and Data Flow

1) Client calls `POST /api/v1/tts/convert` with text.
2) Route validates input and calls `TaskManagerWrapper.submit_task(text, custom_filename)`.
3) `TTSTaskManager.submit_task` checks for duplicates by `text_hash`. If a prior non-failed task exists, returns its
   `task_id` to avoid redundant synthesis.
4) Otherwise, it forwards to `TTSServiceWrapper._service.submit_request`, which enqueues the job and immediately emits a
   `queued` message to the public `task_queue`.
5) `TTSTaskManager` writes a `Task` row with `status='queued'` and timestamps.
6) The `FBTTSService` worker processes the job, writes the WAV file to the configured output directory, and emits
   `processing` → `completed` → `done` messages with metadata (timestamps, file size, sampling rate, device).
7) The `TTSTaskManager` monitoring thread consumes these messages and updates the `Task` row accordingly (status and
   metadata fields).
8) Clients poll `GET /api/v1/tts/{conversion_id}` or list via `GET /api/v1/tts`.
9) When complete, clients download audio with `GET /api/v1/tts/{conversion_id}/download`.

### Data Model (Task)

- Identity: `id` (PK), `task_id` (external ID), `text_hash` (dedupe key)
- Content: `original_text`, `custom_filename`, `output_file_path`
- Lifecycle: `status`, `submitted_at`, `started_at`, `completed_at`, `failed_at`, `created_at`
- Metadata: `file_size`, `sampling_rate`, `device`, `metadata` (JSON), derived `duration`

### Error Handling

- Route layer translates domain exceptions to HTTP responses using FastAPI exception handlers.
- `TTSServiceException`, `TaskNotFoundException`, `ValidationException`, `DatabaseException` ensure consistent status
  codes and payloads (`ErrorResponse`).

### Concurrency and Threads

- `FBTTSService` runs a worker thread for synthesis.
- `TTSTaskManager` runs a monitor thread that consumes the public `task_queue` and updates the database.
- API requests are handled by the ASGI server (Uvicorn) independently.

### Configuration

- Centralized via `Settings` with environment variables (`.env`). Key options: host, port, log level, database URL, docs
  URLs, TTS device, output directory.

### Observability and Operations

- Health endpoints: `/` and `/health` return `HealthResponse` with version and timestamp.
- File outputs are stored under the configured output directory; filenames allow deterministic overrides via
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
- Components are factored to allow mocking (`TTSServiceWrapper`, `DatabaseService`).

### Security Notes

- Input validation via Pydantic schemas with bounds on text size and list cardinality.
- Filename sanitization: `custom_filename` is accepted without path components; server enforces `.wav` extension on
  download.
- Consider rate limiting and authentication for production deployments.

### Key Trade-offs

- Simplicity of in-process queues/threads vs. robustness of external job systems.
- Immediate DB writes and status updates vs. eventual consistency across threads.


