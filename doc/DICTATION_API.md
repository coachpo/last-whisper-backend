# Dictation Backend API

This document describes the extended dictation backend functionality that has been added to the TTS project.

## Overview

The project has been extended from a simple TTS API to a comprehensive dictation practice backend with the following
features:

- **Items Management**: Create, read, update, delete dictation items with automatic TTS generation
- **Attempts Scoring**: Submit user attempts and get automatic scoring using Word Error Rate (WER)
- **Statistics**: Get aggregated statistics and practice logs
- **Local TTS**: Uses existing local TTS models (no cloud dependencies)
- **SQLite Database**: Local database for persistence
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
- **TTSEngineManager**: TTS workflow management with Items integration

### API Endpoints

#### Items (`/v1/items`)

- `POST /v1/items` - Create new dictation item
- `GET /v1/items` - List items with filtering (locale, tags, difficulty, text search, practiced status)
- `GET /v1/items/{id}` - Get specific item
- `DELETE /v1/items/{id}` - Delete item and associated files
- `GET /v1/items/{id}/audio` - Download audio file
- `POST /v1/items/bulk` - Create multiple items in batch
- `PATCH /v1/items/{id}/tags` - Update item tags
- `PATCH /v1/items/{id}/difficulty` - Update item difficulty

#### Attempts (`/v1/attempts`)

- `POST /v1/attempts` - Submit and score practice attempt
- `GET /v1/attempts` - List attempts with filtering

#### Stats (`/v1/stats`)

- `GET /v1/stats/summary` - Get summary statistics
- `GET /v1/stats/practice-log` - Get per-audio practice log

#### Health (`/health`)

- Comprehensive health checks for database, audio directory, and TTS worker

## Features

### Text-to-Speech Integration

- Automatic TTS generation when items are created
- Support for different locales
- Audio files stored locally with stable URLs
- Background processing with status tracking
- Task deduplication to avoid redundant TTS generation

### Scoring System

- Word Error Rate (WER) calculation using `jiwer` library
- Unicode normalization for fair comparison
- Punctuation and case-insensitive scoring
- Percentage scores (0-100)
- Word-level accuracy tracking

### Filtering and Search

- Simple text search using SQL LIKE
- Filter by locale, difficulty, tags
- Practice status filtering (practiced/unpracticed)
- Date range filtering for attempts and stats
- Pagination support for large result sets

### Statistics and Analytics

- Summary stats: total attempts, unique items practiced, averages
- Practice log: per-item statistics with attempt counts and scores
- Progress tracking over time
- Best/worst/average scores per item
- Time-window based filtering for trend analysis

## Configuration

Configuration options in `app/core/config.py`:

```python
# Database
database_url: str = "sqlite:///dictation.db"
db_path: str = "dictation.db"

# Audio Storage
audio_dir: str = "audio"
base_url: str = "http://localhost:8000"

# TTS Settings
tts_device: Optional[str] = None  # None for auto-detection
tts_thread_count: int = 1

# API Settings
app_name: str = "Dictation Backend API"
app_version: str = "1.0.0"
```

## Dependencies

Dependencies in `requirements.txt`:

- `jiwer` - Word Error Rate calculation
- `unidecode` - Unicode normalization
- `alembic` - Database migrations (future use)
- `transformers` - Hugging Face TTS models
- `torch` - PyTorch for model inference
- `fastapi` - Web framework
- `sqlalchemy` - Database ORM
- `pydantic` - Data validation

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

### Tasks Table

```sql
CREATE TABLE tasks
(
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id           VARCHAR NOT NULL UNIQUE,
    original_text     TEXT    NOT NULL,
    text_hash         VARCHAR NOT NULL,
    status            VARCHAR NOT NULL DEFAULT 'pending',
    output_file_path  TEXT,
    custom_filename   TEXT,
    created_at        DATETIME NOT NULL,
    submitted_at      DATETIME,
    started_at        DATETIME,
    completed_at      DATETIME,
    failed_at         DATETIME,
    error_message     TEXT,
    file_size         INTEGER,
    sampling_rate     INTEGER,
    device            VARCHAR,
    metadata          TEXT,
    item_id           INTEGER REFERENCES items (id) ON DELETE SET NULL
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

### Create multiple items in batch

```bash
curl -X POST "http://localhost:8000/v1/items/bulk" \
     -H "Content-Type: application/json" \
     -d '{
       "items": [
         {
           "locale": "en",
           "text": "First dictation text",
           "difficulty": 2,
           "tags": ["beginner"]
         },
         {
           "locale": "en", 
           "text": "Second dictation text",
           "difficulty": 4,
           "tags": ["intermediate"]
         }
       ]
     }'
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
- `POST /api/v1/tts/convert-multiple` - Batch TTS conversion
- All existing functionality preserved

## Health Monitoring

The system provides comprehensive health monitoring:

- Database connectivity and health
- Audio directory accessibility and permissions
- TTS service initialization status
- Task manager monitoring status
- Overall system health aggregation

## Future Enhancements

Potential areas for expansion:

- User authentication and multi-tenant support
- Advanced analytics and learning metrics
- Export/import functionality for items
- Audio quality analysis
- Real-time pronunciation feedback
- Integration with speech recognition for auto-transcription
- Multi-language support expansion
- Performance optimization for large datasets
- API rate limiting and usage quotas
