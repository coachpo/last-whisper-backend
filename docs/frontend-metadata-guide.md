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

## Frontend Upgrade Guide

Use this checklist whenever the backend bumps `service.schema_version`, introduces new sections, or retires existing fields. Treat metadata as a versioned contract and stage upgrades the same way you would for any other API change.

### 1. Detect and assess the change

- Record the current schema version inside your frontend release notes. During app bootstrap, compare the freshly fetched `service.schema_version` to the version your bundle expects.
- Use the `fields` parameter in lower environments to probe newly added sections without impacting production users.
- Review backend release notes for deprecations—fields will remain optional for at least one release cycle, so plan to maintain backward compatibility until you confirm the new version is everywhere.

### 2. Prepare the client

1. Update TypeScript/PropTypes interfaces so optional fields are guarded (e.g., `metadata.features?.tts_languages ?? []`).
2. Add feature toggles that key off either the schema version (`>= 2025-11-22`) or an explicit capability flag returned in the payload.
3. Refresh local fixtures/mocks used by Storybook and unit tests so they reflect both the old and new schema, ensuring components render gracefully in either case.

### 3. Roll out safely

- **Development**: Point your local build at the newest backend, verifying console warnings are absent and that fallbacks render when sections are missing.
- **Staging**: Deploy the frontend behind an environment flag. Enable verbose logging around the metadata fetch (timing, schema version, feature flags) to catch mismatches early.
- **Production**: Ship the bundle with the new logic still tolerant of older schemas. Keep caches short (≤30s) during the rollout so clients observe backend upgrades quickly.

### 4. Validate and monitor

- Track a synthetic check that periodically fetches `/metadata` with `detail=full` and asserts the schema version your frontend expects. Alert if it drifts.
- Add runtime assertions (only in non-production builds) that warn developers when an unknown field appears—handy for future upgrades.
- After release, confirm that UI elements tied to new metadata (e.g., new feature flags) behave correctly while legacy environments continue to function.

### 5. Rollback + support plan

- If the backend rollout lags, set the frontend feature toggle off and rely on the older rendering paths; because the client treats new fields as optional, this is instant.
- Keep the previous metadata schema fixture around until every environment reports the new `service.schema_version` for at least one full day.
- Document any consumer-visible changes (new footer info, feature gates) in your frontend changelog so other teams know when they can depend on them.
