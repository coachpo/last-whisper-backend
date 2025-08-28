# Last Whisper - Backend Service – Architecture Overview

This document explains the system design, major components, data flows, and key decisions of the Last Whisper Backend
Service project.

### Goals and Constraints

- Provide a clean, production-grade HTTP API for Text-to-Speech (TTS) with multiple provider support
- Orchestrate model inference, task lifecycle, persistence, and delivery across different TTS providers
- Remain modular and testable with clear separation of concerns
- Support multiple TTS providers (Local, Azure, Google Cloud) with easy switching
- Support CPU/GPU execution and horizontal scalability patterns (Local TTS)
- Support dictation practice workflow with TTS integration
- Maintain backward compatibility with existing TTS API endpoints

### High-level Architecture

- **API Layer (FastAPI)**: HTTP endpoints, request/response validation, error translation.
- **Service Layer**: Business logic orchestration and integration with external systems.
    - `TTSEngineWrapper` provides unified interface and provider selection logic.
    - Multiple TTS engines: `TTSEngine` (Local), `TTSEngine` (Azure), `TTSEngine` (GCP).
    - `TTSEngineManager` orchestrates TTS tasks and synchronizes task statuses with database.
    - Service classes provide business logic for items, attempts, stats, tags, and tasks.
- **Data Layer**:
    - SQLAlchemy models (`Task`, `Item`, `Attempt`, `Tag`) and a `DatabaseManager` that owns the engine/session
      lifecycle.
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
    logging.py        # Logging configuration
    uvicorn_logging.py # Uvicorn-specific logging setup
  models/
    database.py       # SQLAlchemy ORM models and DB manager
    schemas.py        # Pydantic request/response models
  services/
    task_service.py       # TaskService for database operations
    items_service.py      # ItemsService for dictation items
    attempts_service.py   # AttemptsService for practice tracking
    stats_service.py      # StatsService for analytics
    tags_service.py       # TagsService for preset tag management
  tts_engine/
    tts_engine_local.py     # Local TTS engine (Facebook MMS-TTS-Fin)
    tts_engine_azure.py     # Azure Speech TTS engine
    tts_engine_gcp.py       # Google Cloud TTS engine
    tts_engine_manager.py   # TTSEngineManager (task orchestration + DB sync)
    tts_engine_wrapper.py   # TTSEngineWrapper (provider selection + lifecycle)
  main.py             # FastAPI app, lifespan startup/shutdown
run_api.py            # Uvicorn runner
```

### Component Responsibilities

- **FastAPI app (`app/main.py`)**
    - Initializes services on startup (`lifespan`): `TTSEngine.initialize()` then
      `TTSEngineManager.start_monitoring()`.
    - Registers exception handlers to consistently return `ErrorResponse`.
    - Mounts routers from `app/api/routes`.

- **API routes**
    - **TTS Routes** (`app/api/routes/tts.py`): TTS conversion endpoints, audio file serving
    - **Items Routes** (`app/api/routes/items.py`): Dictation item management
    - **Attempts Routes** (`app/api/routes/attempts.py`): Practice attempt tracking
    - **Stats Routes** (`app/api/routes/stats.py`): Analytics and reporting
    - **Tags Routes** (`app/api/routes/tags.py`): Preset tag management
    - **Health Routes** (`app/api/routes/health.py`): System health monitoring
    - All routes validate inputs using Pydantic schemas and delegate to appropriate services

- **Service layer**
    - **TTSEngineWrapper** (`tts_engine/tts_engine_wrapper.py`)
        - Provides unified interface for all TTS providers
        - Handles provider selection based on configuration (`TTS_PROVIDER` setting)
        - Manages lifecycle (start/stop) for the selected TTS engine
        - Guards usage via `is_initialized` and raises `TTSServiceException` on misuse
    - **TTSEngine (Local)** (`tts_engine/tts_engine_local.py`)
        - Loads the Hugging Face model `facebook/mms-tts-fin` and tokenizer
        - Supports device selection (auto CPU/GPU) and switching
        - Uses two queues for task processing and status updates
        - A worker thread processes requests: tokenizes, runs inference, writes WAV files
    - **TTSEngine (Azure)** (`tts_engine/tts_engine_azure.py`)
        - Integrates with Microsoft Azure Cognitive Services Speech
        - Supports multiple Finnish neural voices with random selection
        - Provides SSML support for prosody controls
        - Handles Azure-specific authentication and API calls
    - **TTSEngine (GCP)** (`tts_engine/tts_engine_gcp.py`)
        - Integrates with Google Cloud Text-to-Speech API
        - Uses WaveNet voices (fi-FI-Wavenet-B) for high-quality synthesis
        - Supports SSML and advanced voice configuration
        - Handles GCP authentication via service account credentials
    - **TTSEngineManager** (`tts_engine/tts_engine_manager.py`)
        - Wraps any TTS engine and starts a monitoring thread to watch the task queue
        - Provides `submit_task`, `submit_multiple_tasks`, `get_task_status` for API usage
        - Handles task deduplication by `text_hash` and database synchronization
        - Manages item-specific TTS tasks and status updates
    - **Service classes** (`services/`)
        - `TaskService`: Database operations for TTS tasks
        - `ItemsService`: Dictation item management with TTS integration
        - `AttemptsService`: User practice tracking and scoring
        - `StatsService`: Analytics and reporting
        - `TagsService`: Preset tag management and categorization

- **Task manager (`tts_engine/tts_engine_manager.py`)**
    - Persists new tasks in the DB on submission and deduplicates by `text_hash` (MD5 of original text).
    - Monitors the TTS service `task_message_queue` in a background thread and updates persisted task records as
      statuses
      change.
    - Provides reporting (status counts, averages, duplicates) and cleanup utilities.
    - Integrates with `Item` model for dictation workflow.

- **Persistence layer (`models/models.py`)**
    - SQLAlchemy models:
        - `Task`: TTS task lifecycle with fields for timestamps, output location, audio metadata and device
        - `Item`: Dictation items with TTS status and audio URL
        - `Attempt`: User practice attempts with scoring
        - `Tag`: Preset tags for item categorization
    - `DatabaseManager` encapsulates engine and session factory and ensures tables exist.

- **Core (`core/config.py`, `core/exceptions.py`, `core/logging.py`)**
    - `Settings` uses `pydantic-settings` with `.env` support for host/port, database URL, docs URLs, TTS provider
      selection, and provider-specific configurations.
    - Exception hierarchy (`TTSAPIException` and specializations) standardizes error propagation and HTTP mapping.
    - Comprehensive logging configuration with structured logging support.

### Request Lifecycle and Data Flow

#### TTS Conversion Flow

1) Client calls `POST /api/v1/tts/convert` with text.
2) Route validates input and calls `TTSEngineManager.submit_task(text, custom_filename, language)`.
3) `TTSEngineManager.submit_task` checks for duplicates by `text_hash`. If a prior non-failed task exists, returns its
   `task_id` to avoid redundant synthesis.
4) Otherwise, it forwards to `TTSEngineWrapper.submit_request`, which delegates to the configured TTS engine:
    - **Local**: Uses Hugging Face model for inference
    - **Azure**: Calls Azure Speech API with configured voice
    - **GCP**: Calls Google Cloud TTS API with WaveNet voice
5) The selected TTS engine enqueues the job and immediately emits a `queued` message to the public `task_message_queue`.
6) `TTSEngineManager` writes a `Task` row with `status='queued'` and timestamps.
7) The TTS engine worker processes the job, generates the WAV file, and emits
   `processing` → `completed` → `done` (or `failed`) messages with metadata (timestamps, file size, sampling rate,
   device).
8) The `TTSEngineManager` monitoring thread consumes these messages and updates the `Task` row accordingly (status and
   metadata fields).
9) Clients poll `GET /api/v1/tts/{conversion_id}` or list via `GET /api/v1/tts`.
10) When complete, clients download audio with `GET /api/v1/tts/{conversion_id}/download`.

#### Dictation Item Flow

1) Client calls `POST /v1/items` to create a dictation item.
2) `ItemsService.create_item` creates the item with `tts_status="pending"`.
3) If TTS manager is available, it automatically submits a TTS task for the item.
4) TTS processing follows the standard flow above.
5) When TTS completes, the item's `tts_status` is updated to `"ready"`.
6) Users can practice with `POST /v1/items/{item_id}/attempts` and track progress.

### Data Models

#### Task Model

- Identity: `id` (PK), `task_id` (external ID), `text_hash` (dedupe key)
- Content: `original_text`, `custom_filename`, `output_file_path`
- Lifecycle: `status`, `submitted_at`, `started_at`, `completed_at`, `failed_at`, `created_at`
- Metadata: `file_size`, `sampling_rate`, `device`, `task_metadata` (JSON), derived `duration`
- Relationships: `item_id` (links to dictation item)

#### Item Model

- Identity: `id` (PK), `locale`, `text`
- Metadata: `difficulty`, `tags_json`, `tts_status`, `task_id`
- Timestamps: `created_at`, `updated_at`
- Relationships: `attempts`, `task`

#### Attempt Model

- Identity: `id` (PK), `item_id` (FK)
- Practice data: `text`, `percentage`, `wer`, `words_ref`, `words_correct`
- Timestamps: `created_at`

#### Tag Model

- Identity: `id` (PK), `name` (unique)
- Timestamps: `created_at`, `updated_at`

### Error Handling

- Route layer translates domain exceptions to HTTP responses using FastAPI exception handlers.
- `TTSServiceException`, `TaskNotFoundException`, `ValidationException`, `DatabaseException` ensure consistent status
  codes and payloads (`ErrorResponse`).

### Concurrency and Threads

- `TTSEngine` runs a worker thread for synthesis.
- `TTSEngineManager` runs a monitor thread that consumes the public `task_message_queue` and updates the database.
- API requests are handled by the ASGI server (Uvicorn) independently.

### Configuration

- Centralized via `Settings` with environment variables (`.env`). Key options:
    - **API Settings**: host, port, log level, database URL, docs URLs
    - **TTS Provider Selection**: `TTS_PROVIDER` (local/azure/gcp)
    - **Local TTS**: device selection, thread count, supported languages
    - **Azure TTS**: speech key, service region, voice configuration, SSML settings
    - **GCP TTS**: voice name, language code, authentication via service account
    - **Storage**: output directory, audio directory, base URL

### Observability and Operations

- Health endpoints: `/health` returns `HealthCheckResponse` with detailed service checks.
- File outputs are stored under the configured audio directory; filenames allow deterministic overrides via
  `custom_filename` and default to timestamp+hash.
- The architecture supports external consumers of the `task_message_queue` if needed (e.g., metrics, notifications)
  without
  coupling them to the API.

### Scalability Considerations

- Stateless API layer enables horizontal scaling behind a load balancer.
- The DB ensures shared state across API instances.
- The current TTS worker and task monitor live in-process. For higher throughput or multi-instance safety:
    - Extract queues to a broker (e.g., Redis/RabbitMQ) and run the TTS workers as separate processes.
    - Use a distributed lock or job reservation to prevent duplicate processing across instances.
    - Store artifacts in shared or object storage (e.g., S3) instead of local disk.

### Testing Strategy

- API tests for all endpoints including health, TTS, items, attempts, stats, and tags.
- Service-level tests for all service classes and TTS engines.
- Components are factored to allow mocking (`TTSEngineWrapper`, `TTSEngineManager`, service classes).
- Integration tests for TTS workflows and database operations.

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

- **Multiple TTS Providers**: Added support for Local (Facebook MMS-TTS-Fin), Azure Speech, and Google Cloud TTS
- **Provider Selection**: Implemented `TTSEngineWrapper` for easy switching between TTS providers via configuration
- **Enhanced Data Models**: Added `Item`, `Attempt`, and `Tag` models for comprehensive dictation workflow
- **Service Layer Consolidation**: Consolidated business logic into focused service classes
- **TTS Integration**: Seamless integration between TTS processing and dictation items across all providers
- **Audio Management**: Centralized audio file handling with proper URL generation
- **Health Monitoring**: Enhanced health checks for all system components and TTS providers
- **Logging System**: Comprehensive logging configuration and setup
- **Configuration Management**: Extended settings to support multiple TTS provider configurations
- **Backward Compatibility**: Maintained compatibility with existing TTS API endpoints
- **Tag Management**: Added preset tag system for item categorization and management
- **Enhanced Statistics**: Extended analytics with progress tracking and detailed item statistics
- **Improved API Design**: Added comprehensive filtering, pagination, and sorting capabilities
