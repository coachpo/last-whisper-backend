# Frontend Integration Guide: `/metadata` API

## Overview
The metadata endpoint exposes non-sensitive diagnostics that help the frontend display environment labels, build identifiers, feature availability, and lightweight runtime state. It replaces ad-hoc env flags in the UI with a single source of truth straight from FastAPI.

| Method | Path        | Auth | Cache hint |
| ------ | ----------- | ---- | ---------- |
| GET    | `/metadata` | none | safe to cache for ~30s client-side |

## Query Parameters

| Name   | Type   | Default | Description |
| ------ | ------ | ------- | ----------- |
| `detail` | `core`, `runtime`, `full` | `full` | Controls which optional sections are returned (service info is always included). |
| `fields` | comma-separated string | `None` | Explicitly list sections to include (`service`, `build`, `runtime`, `providers`, `features`, `limits`, `links`). Overrides `detail` when provided. |

## Example Requests

### Full payload
```bash
curl http://localhost:8000/metadata
```

```json
{
  "service": {
    "name": "Last Whisper Backend (Development)",
    "description": "Last Whisper's backend service - Dictation training with cloud TTS, scoring, and session-less workflow",
    "environment": "development",
    "version": "1.0.0",
    "schema_version": "2025-11-22"
  },
  "build": {
    "commit": "6f94d4f2b24f5c23e6a2c3a5b5513f7f954c1234",
    "short_commit": "6f94d4f",
    "branch": "main",
    "built_at": "2025-11-21T18:42:03Z",
    "python_version": "3.11.9",
    "fastapi_version": "0.111.0"
  },
  "runtime": {
    "started_at": "2025-11-22T12:15:00.123456+00:00",
    "uptime_seconds": 3600.12,
    "process_id": 4123,
    "host": "last-whisper-api",
    "worker": {
      "worker_running": true,
      "queue_size": 0,
      "pending_items": 0,
      "tts_service_available": true
    }
  },
  "providers": {
    "database": {"engine": "sqlite", "file": "data/dictation.db"},
    "tts": {"provider": "google", "supported_languages": ["fi"]},
    "translation": {"provider": "google", "supported_languages": ["en", "fi", "zh-CN", "zh-TW"]}
  },
  "features": {
    "tts_submission_workers": 4,
    "tts_languages": ["fi"],
    "translation_languages": ["en", "fi", "zh-CN", "zh-TW"]
  },
  "limits": {
    "max_items_per_bulk_request": 100,
    "max_tags_per_item": 20,
    "max_tag_length": 50,
    "max_text_length": 10000
  },
  "links": {
    "status": "/health",
    "metadata": "/metadata",
    "docs": "/docs",
    "redoc": "/redoc",
    "openapi": "/openapi.json"
  }
}
```

### Runtime-only view (for dashboards)
```bash
curl "http://localhost:8000/metadata?detail=runtime&fields=runtime"
```

```json
{
  "service": {
    "name": "Last Whisper Backend (Development)",
    "description": "Last Whisper's backend service - Dictation training with cloud TTS, scoring, and session-less workflow",
    "environment": "development",
    "version": "1.0.0",
    "schema_version": "2025-11-22"
  },
  "runtime": {
    "started_at": "2025-11-22T12:15:00.123456+00:00",
    "uptime_seconds": 65.4,
    "process_id": 4123,
    "host": "last-whisper-api",
    "worker": {
      "worker_running": true,
      "queue_size": 0,
      "pending_items": 0,
      "tts_service_available": true
    }
  }
}
```

## Usage Scenarios

1. **Environment badge** – Render the `service.environment` (e.g., `development`, `production`) in the UI header.
2. **Version + commit footer** – Display `service.version` and `build.short_commit`; link out to release notes using `links.docs`.
3. **Feature gating** – Use `features.translation_languages` to enable/disable language selectors dynamically.
4. **Operational toast** – If `runtime.worker.worker_running` is `false`, warn admins that the background queue is paused.
5. **Limits display** – Mirror `limits.max_items_per_bulk_request` wherever the UI collects bulk uploads so the backend and frontend stay consistent.

## Best Practices

- **Cache responsibly**: the payload is mostly static; cache for 30–60 seconds in the frontend store or SWR hook to avoid unnecessary calls.
- **Graceful fallback**: treat missing optional sections (`build`, `runtime`, etc.) as absence rather than fatal; render placeholders like `Unknown`.
- **Schema versioning**: track `service.schema_version` so the UI can detect breaking changes (upgrade if the schema version advances).
- **Security**: endpoint is intentionally free of secrets—do not log or surface sensitive env vars when extending it.
- **Error handling**: fallback to a local default (e.g., `DEV`) if the request fails; the API still returns HTTP 200 when healthy, so retries should only happen on network/server errors.

## Configuration & Assumptions

- No auth required today; if we add auth later, the frontend should attach the same bearer token it uses for other API calls.
- Running locally? Access via `http://localhost:8000/metadata`; staging/production keeps the same relative path.
- CORS is already configured for `http://localhost:3000`, so browsers may call the endpoint directly.
- CI/CD can override build info via environment variables `BUILD_COMMIT_SHA`, `BUILD_BRANCH`, and `BUILD_TIMESTAMP`; otherwise git metadata is used.

## Implementation Checklist for the Frontend

1. Fetch metadata once during app bootstrap; cache in a global store (Redux/Zustand/Context).
2. Surface key values (version, environment, feature flags) where relevant.
3. Re-request on interval only when you need runtime stats (uptime or worker health).
4. If `runtime.worker.tts_service_available` becomes `false`, surface an admin alert and disable submission-triggering UI.
5. When adding new sections to the response, prefer using the `fields` query parameter to minimize payload size in views that only need runtime data.
