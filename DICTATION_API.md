# Dictation Backend API

This document describes the extended dictation backend functionality that has been added to the TTS project.

## Overview

The project has been extended from a simple TTS API to a comprehensive dictation practice backend with the following
features:

- **Items Management**: Create, read, update, delete dictation items with automatic TTS generation
- **Attempts Scoring**: Submit user attempts and get automatic scoring using Word Error Rate (WER)
- **Statistics**: Get aggregated statistics and practice logs
- **Local TTS**: Uses existing local TTS models (no cloud dependencies)
- **SQLite with WAL**: High-performance local database with Write-Ahead Logging
- **Session-less**: No authentication or user sessions required

## Architecture Components

### Database Models

- **Item**: Dictation items with text, locale, difficulty, tags, and TTS status
- **Attempt**: User practice attempts with scoring metrics
- **Task**: TTS processing tasks (item from original)

### Services

- **ItemsService**: CRUD operations for dictation items and TTS job management
- **AttemptsService**: Scoring and persistence of practice attempts
- **StatsService**: Aggregated statistics and practice logs
- **ItemTaskManager**: TTS workflow management with Items integration

### API Endpoints

#### Items (`/v1/items`)

- `POST /v1/items` - Create new dictation item
- `GET /v1/items` - List items with filtering (locale, tags, difficulty, search, practiced status)
- `GET /v1/items/{id}` - Get specific item
- `DELETE /v1/items/{id}` - Delete item and associated files
- `GET /v1/items/{id}/audio` - Download audio file

#### Attempts (`/v1/attempts`)

- `POST /v1/attempts` - Submit and score practice attempt
- `GET /v1/attempts` - List attempts with filtering
- `GET /v1/attempts/{id}` - Get specific attempt

#### Stats (`/v1/stats`)

- `GET /v1/stats/summary` - Get summary statistics
- `GET /v1/stats/practice-log` - Get per-audio practice log
- `GET /v1/stats/items/{id}` - Get item-specific statistics
- `GET /v1/stats/progress/{id}` - Get progress over time

#### Health (`/healthz`)

- Item health checks for database, audio directory, and TTS worker

## Features

### Text-to-Speech Integration

- Automatic TTS generation when items are created
- Support for different locales
- Audio files stored locally with stable URLs
- Background processing with status tracking

### Scoring System

- Word Error Rate (WER) calculation
- Unicode normalization for fair comparison
- Punctuation and case-insensitive scoring
- Percentage scores (0-100)

### Filtering and Search

- Full-text search using SQLite FTS5
- Filter by locale, difficulty, tags
- Practice status filtering (practiced/unpracticed)
- Date range filtering for attempts and stats

### Statistics and Analytics

- Summary stats: total attempts, unique items practiced, averages
- Practice log: per-item statistics with attempt counts and scores
- Progress tracking over time
- Best/worst/average scores per item

## Configuration

New configuration options in `app/core/config.py`:

```python
# Database
database_url: str = "sqlite:///dictation.db"
db_path: str = "dictation.db"

# Audio Storage
audio_dir: str = "audio"
base_url: str = "http://localhost:8000"

# TTS Settings
tts_thread_count: int = 1
```

## Dependencies

Added dependencies in `requirements.txt`:

- `jiwer` - Word Error Rate calculation
- `unidecode` - Unicode normalization
- `alembic` - Database migrations (future use)

## Database Schema

### Items Table

```sql
CREATE TABLE items
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    locale     VARCHAR(10) NOT NULL,
    text       TEXT        NOT NULL,
    difficulty INTEGER,
    tags_json  TEXT,
    tts_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    audio_url  TEXT,
    created_at DATETIME    NOT NULL,
    updated_at DATETIME    NOT NULL
);
```

### Attempts Table

```sql
CREATE TABLE attempts
(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id       INTEGER  NOT NULL REFERENCES items (id) ON DELETE CASCADE,
    text          TEXT     NOT NULL,
    percentage    INTEGER  NOT NULL,
    wer           REAL     NOT NULL,
    words_ref     INTEGER  NOT NULL,
    words_correct INTEGER  NOT NULL,
    created_at    DATETIME NOT NULL
);
```

### FTS5 Virtual Table

```sql
CREATE VIRTUAL TABLE items_fts USING fts5
(
    id UNINDEXED,
    text,
    content='items',
    content_rowid='id'
);
```

## Usage Examples

### Create a dictation item

```bash
curl -X POST "http://localhost:8000/v1/items" \
     -H "Content-Type: application/json" \
     -d '{
       "locale": "en",
       "text": "The quick brown fox jumps over the lazy dog",
       "difficulty": 3,
       "tags": ["animals", "classic"]
     }'
```

### Submit a practice attempt

```bash
curl -X POST "http://localhost:8000/v1/attempts" \
     -H "Content-Type: application/json" \
     -d '{
       "item_id": 1,
       "text": "The quick brown fox jumps over lazy dog"
     }'
```

### Get practice statistics

```bash
curl "http://localhost:8000/v1/stats/summary"
curl "http://localhost:8000/v1/stats/practice-log"
```

## Testing

Comprehensive test suites have been added:

- `tests/test_services/test_items_service.py` - Items service tests
- `tests/test_services/test_attempts_service.py` - Attempts service tests
- `tests/test_api/test_items.py` - API endpoint tests

Run tests with:

```bash
pytest tests/
```

## Backward Compatibility

The original TTS API endpoints remain functional:

- `POST /api/v1/tts/convert` - Legacy TTS conversion
- `GET /api/v1/tts/{id}` - Legacy task status
- All existing functionality preserved

## Future Enhancements

Potential areas for expansion:

- User authentication and multi-tenant support
- Advanced analytics and learning metrics
- Export/import functionality for items
- Audio quality analysis
- Real-time pronunciation feedback
- Integration with speech recognition for auto-transcription
