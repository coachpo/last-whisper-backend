# Whisper TTS - Dictation Backend API

This document describes the comprehensive dictation backend functionality with multiple TTS provider support.

## Overview

The project provides a comprehensive dictation practice backend with multiple TTS provider support and the following
features:

- **Items Management**: Create, read, update, delete dictation items with automatic TTS generation
- **Attempts Scoring**: Submit user attempts and get automatic scoring using Word Error Rate (WER)
- **Statistics**: Get aggregated statistics and practice logs
- **Multiple TTS Providers**: Support for Local (Facebook MMS-TTS-Fin), Azure Speech, and Google Cloud TTS
- **Provider Flexibility**: Easy switching between TTS providers via configuration
- **SQLite Database**: Local database for persistence
- **Session-less**: No authentication or user sessions required
- **Backward Compatibility**: Maintains existing TTS API endpoints

## Architecture Components

### Database Models

- **Item**: Dictation items with text, locale, difficulty, tags, and TTS status
- **Attempt**: User practice attempts with scoring metrics
- **Task**: TTS processing tasks (item from original)

### Services

- **ItemsService**: CRUD operations for dictation items and TTS job management
- **AttemptsService**: Scoring and persistence of practice attempts
- **StatsService**: Aggregated statistics and practice logs
- **TTSEngineManager**: TTS workflow management with Items integration across all providers
- **TTSEngineWrapper**: Provider selection and unified TTS interface

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

- **Multiple Provider Support**: Automatic TTS generation using configured provider (Local/Azure/GCP)
- **Provider Selection**: Easy switching between TTS providers via `TTS_PROVIDER` configuration
- **Local TTS**: Facebook MMS-TTS-Fin model with GPU/CPU support
- **Azure TTS**: Microsoft Azure Speech with neural voices and SSML support
- **GCP TTS**: Google Cloud Text-to-Speech with WaveNet voices
- **Support for different locales**: Configurable language support per provider
- **Audio files stored locally**: Stable URLs with proper file management
- **Background processing**: Status tracking across all providers
- **Task deduplication**: Avoid redundant TTS generation regardless of provider

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

# TTS Provider Selection
tts_provider: str = "local"  # Options: "local", "azure", "gcp"
tts_supported_languages: list[str] = ["fi"]

# Local TTS Settings (when tts_provider="local")
tts_device: Optional[str] = None  # None for auto-detection
tts_thread_count: int = 1

# Azure TTS Settings (when tts_provider="azure")
# azure_speech_key: str (from environment)
# azure_speech_region: str (from environment)
# azure_language_code: str = "fi-FI"
# azure_sample_rate_hz: int = 24000

# GCP TTS Settings (when tts_provider="gcp")
# gcp_voice_name: str = "fi-FI-Wavenet-B"
# gcp_language_code: str = "fi-FI"
# gcp_sample_rate_hz: int = 24000

# API Settings
app_name: str = "Dictation Training Backend"
app_version: str = "1.0.0"
```

## Dependencies

Dependencies in `requirements.txt`:

### Core Framework
- `fastapi` - Web framework
- `sqlalchemy` - Database ORM
- `pydantic` - Data validation
- `pydantic-settings` - Configuration management

### TTS Engines
- `transformers` - Hugging Face TTS models (Local)
- `torch` - PyTorch for model inference (Local)
- `azure-cognitiveservices-speech` - Azure Speech TTS
- `google-cloud-texttospeech` - Google Cloud TTS

### Dictation Features
- `jiwer` - Word Error Rate calculation
- `unidecode` - Unicode normalization

### Development Tools
- `alembic` - Database migrations
- `pytest` - Testing framework
- `black` - Code formatting
- `ruff` - Code linting

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

The original TTS API endpoints remain functional and work with all TTS providers:

- `POST /api/v1/tts/convert` - TTS conversion (works with all providers)
- `GET /api/v1/tts/{id}` - Task status (works with all providers)
- `POST /api/v1/tts/convert-multiple` - Batch TTS conversion (works with all providers)
- All existing functionality preserved across provider changes

## Health Monitoring

The system provides comprehensive health monitoring:

- Database connectivity and health
- Audio directory accessibility and permissions
- TTS service initialization status (all providers)
- Task manager monitoring status
- TTS worker health and queue status
- Provider-specific health checks (Local/Azure/GCP)
- Overall system health aggregation

## Future Enhancements

Potential areas for expansion:

- **Additional TTS Providers**: Support for Amazon Polly, IBM Watson, or other TTS services
- **User authentication and multi-tenant support**: User management and data isolation
- **Advanced analytics and learning metrics**: Detailed progress tracking and insights
- **Export/import functionality for items**: Bulk operations and data portability
- **Audio quality analysis**: Quality metrics and optimization suggestions
- **Real-time pronunciation feedback**: Live feedback during practice sessions
- **Integration with speech recognition**: Auto-transcription for practice attempts
- **Multi-language support expansion**: Support for additional languages across all providers
- **Performance optimization**: Caching, CDN integration, and scalability improvements
- **API rate limiting and usage quotas**: Usage monitoring and limits
- **Provider-specific features**: Advanced voice customization, SSML templates, etc.
