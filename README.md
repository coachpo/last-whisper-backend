# TTS API

A production-grade FastAPI service for Text-to-Speech conversion with clean architecture and comprehensive testing.

## Features

- **Clean Architecture**: Organized with proper separation of concerns
- **FastAPI Framework**: Modern, fast web framework with automatic OpenAPI documentation
- **SQLAlchemy 2.x**: Modern ORM with type hints and async support
- **Comprehensive Testing**: Full test suite with pytest and mocking
- **Service Layer**: Clean abstraction over existing TTS infrastructure
- **Configuration Management**: Centralized settings with environment variable support
- **Error Handling**: Custom exceptions and proper HTTP status codes

## Project Structure

```
tts-api/
├── app/
│   ├── api/
│   │   ├── routes/          # API route definitions
│   │   └── dependencies.py  # FastAPI dependencies
│   ├── core/
│   │   ├── config.py        # Application configuration
│   │   └── exceptions.py    # Custom exceptions
│   ├── models/
│   │   ├── schemas.py       # Pydantic models
│   │   └── database.py      # SQLAlchemy models
│   ├── services/
│   │   ├── database.py      # Database operations
│   │   ├── tts_service.py   # TTS service wrapper
│   │   └── task_manager.py  # Task management
│   ├── utils/
│   │   └── sql_queries.py   # SQL constants
│   └── main.py              # FastAPI application
├── tests/                   # Comprehensive test suite
├── scripts/                 # Utility scripts
└── requirements.txt
```

## API Endpoints

### POST /api/v1/tts/convert
Submit text for TTS conversion.

**Request:**
```json
{
  "text": "Hello world",
  "custom_filename": "optional_filename"
}
```

**Response:**
```json
{
  "conversion_id": "20231201_120000_abc123",
  "text": "Hello world", 
  "status": "queued",
  "submitted_at": "2023-12-01T12:00:00"
}
```

### GET /api/v1/tts/{id}
Get conversion status and metadata.

### GET /api/v1/tts
List conversions with optional status filtering.

### GET /health
Health check endpoint.

## Installation

1. Navigate to the project directory:
```bash
cd tts-api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize database (optional):
```bash
python scripts/init_db.py
```

## Running the Application

### Development Server
```bash
python scripts/run_api.py
```

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

## Testing

Run the full test suite:
```bash
pytest
```

Run specific test modules:
```bash
pytest tests/test_api/test_health.py -v
pytest tests/test_api/test_tts.py -v
pytest tests/test_services/ -v
```

## Configuration

Configuration is managed through environment variables or `.env` file:

```bash
# API Settings
APP_NAME="TTS API"
HOST="0.0.0.0"
PORT=8000

# Database
DATABASE_URL="sqlite:///tts_tasks.db"

# TTS Settings
TTS_OUTPUT_DIR="output"
TTS_DEVICE="cpu"  # or "cuda" for GPU
```

## Code Quality

Format code:
```bash
black .
```

Lint code:
```bash
ruff check .
```

## Architecture

The application follows clean architecture principles:

- **API Layer**: FastAPI routes with request/response models
- **Service Layer**: Business logic and external service integration  
- **Data Layer**: Database operations and models
- **Core**: Configuration, exceptions, and utilities

This design provides:
- **Testability**: Easy to mock and test individual components
- **Maintainability**: Clear separation of concerns
- **Scalability**: Modular design allows easy extension
- **Reliability**: Comprehensive error handling and logging
