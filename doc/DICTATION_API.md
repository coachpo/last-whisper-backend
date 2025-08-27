# Whisper TTS - Dictation Backend API

This document describes the comprehensive dictation backend functionality with multiple TTS provider support.

## Overview

The project provides a comprehensive dictation practice backend with multiple TTS provider support and the following
features:

- **Items Management**: Create, read, update, delete dictation items with automatic TTS generation
- **Attempts Scoring**: Submit user attempts and get automatic scoring using Word Error Rate (WER)
- **Statistics**: Get aggregated statistics and practice logs
- **Tags Management**: Create and manage preset tags for item categorization
- **Multiple TTS Providers**: Support for Local (Facebook MMS-TTS-Fin), Azure Speech, and Google Cloud TTS
- **Provider Flexibility**: Easy switching between TTS providers via configuration
- **SQLite Database**: Local database for persistence
- **Session-less**: No authentication or user sessions required
- **Backward Compatibility**: Maintains existing TTS API endpoints

## Architecture Components

### Database Models

- **Item**: Dictation items with text, locale, difficulty, tags, and TTS status
- **Attempt**: User practice attempts with scoring metrics
- **Task**: TTS processing tasks with lifecycle tracking
- **Tag**: Preset tags for item categorization

### Services

- **ItemsService**: CRUD operations for dictation items and TTS job management
- **AttemptsService**: Scoring and persistence of practice attempts
- **StatsService**: Aggregated statistics and practice logs
- **TagsService**: Management of preset tags for item categorization
- **TaskService**: Database operations for TTS tasks
- **TTSEngineManager**: TTS workflow management with Items integration across all providers
- **TTSEngineWrapper**: Provider selection and unified TTS interface

### API Endpoints

#### Items (`/v1/items`)

- `POST /v1/items` - Create new dictation item
- `GET /v1/items` - List items with filtering (locale, tags, difficulty, practiced status)
- `GET /v1/items/{id}` - Get specific item
- `DELETE /v1/items/{id}` - Delete item and associated files
- `GET /v1/items/{id}/audio` - Download audio file
- `POST /v1/items/bulk` - Create multiple items in batch
- `PATCH /v1/items/{id}/tags` - Update item tags
- `PATCH /v1/items/{id}/difficulty` - Update item difficulty

#### Attempts (`/v1/attempts`)

- `POST /v1/attempts` - Submit and score practice attempt
- `GET /v1/attempts` - List attempts with filtering
- `GET /v1/attempts/{id}` - Get specific attempt

#### Stats (`/v1/stats`)

- `GET /v1/stats/summary` - Get summary statistics
- `GET /v1/stats/practice-log` - Get per-audio practice log
- `GET /v1/stats/items/{item_id}` - Get detailed statistics for a specific item
- `GET /v1/stats/progress` - Get progress over time

#### Tags (`/v1/tags`)

- `POST /v1/tags/` - Create a new preset tag
- `GET /v1/tags/` - Get list of preset tags
- `DELETE /v1/tags/{tag_id}` - Delete a preset tag

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

- Filter by locale, difficulty, tags
- Practice status filtering (practiced/unpracticed)
- Date range filtering for attempts and stats
- Pagination support for large result sets
- Sorting options for items and attempts

### Statistics and Analytics

- Summary stats: total attempts, unique items practiced, averages
- Practice log: per-item statistics with attempt counts and scores
- Progress tracking over time
- Best/worst/average scores per item
- Time-window based filtering for trend analysis
- Individual item statistics and detailed metrics

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
# azure_service_region: str (from environment)
# azure_language_code: str = "fi-FI"
# azure_sample_rate_hz: int = 24000

# GCP TTS Settings (when tts_provider="gcp")
# google_application_credentials: str (from environment)
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
- **Advanced tag management**: Tag hierarchies, tag-based filtering, and tag analytics
- **Batch operations**: Bulk item updates, bulk tag assignments, and batch processing
- **Audio format support**: Support for additional audio formats and quality options
