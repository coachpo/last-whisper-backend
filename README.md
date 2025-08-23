# Whisper TTS API

A production-grade FastAPI service for Text-to-Speech conversion using Facebook's MMS-TTS-Fin model with clean architecture, comprehensive testing, and robust task management.

## Features

- **Advanced TTS Engine**: Powered by Facebook's MMS-TTS-Fin model for high-quality speech synthesis
- **Clean Architecture**: Organized with proper separation of concerns and modular design
- **FastAPI Framework**: Modern, fast web framework with automatic OpenAPI documentation
- **SQLAlchemy 2.x**: Modern ORM with type hints and async support
- **Comprehensive Testing**: Full test suite with pytest and mocking
- **Service Layer**: Clean abstraction over TTS infrastructure with task management
- **Configuration Management**: Centralized settings with environment variable support
- **Error Handling**: Custom exceptions and proper HTTP status codes
- **Task Queue Management**: Robust task processing with status tracking
- **Multi-device Support**: Automatic GPU/CPU detection with manual override options

## Project Structure

```
whisper-tts/
├── app/
│   ├── api/
│   │   ├── routes/          # API route definitions
│   │   │   ├── health.py    # Health check endpoints
│   │   │   └── tts.py       # TTS conversion endpoints
│   │   └── dependencies.py  # FastAPI dependencies
│   ├── core/
│   │   ├── config.py        # Application configuration
│   │   └── exceptions.py    # Custom exceptions
│   ├── models/
│   │   ├── schemas.py       # Pydantic models and schemas
│   │   └── database.py      # SQLAlchemy models
│   ├── services/
│   │   ├── database.py      # Database operations
│   │   ├── outer/           # External service integrations
│   │   │   ├── tts_service.py      # TTS service wrapper
│   │   │   └── tts_task_manager.py # Task management service
│   │   ├── task_manager.py  # Core task management
│   │   └── tts_fb_service.py # Facebook TTS service implementation
│   └── main.py              # FastAPI application entry point
├── tests/                   # Comprehensive test suite
│   ├── test_api/           # API endpoint tests
│   └── test_services/      # Service layer tests
├── requirements.txt         # Python dependencies
├── run_api.py              # Server startup script
└── README.md               # This file
```

## TTS Capabilities

This API provides high-quality text-to-speech conversion using:

- **Model**: Facebook's MMS-TTS-Fin (Multilingual TTS model)
- **Output Format**: WAV audio files
- **Language Support**: Finnish and multilingual capabilities
- **Device Optimization**: Automatic GPU/CPU detection with manual override
- **Batch Processing**: Queue-based request handling for scalability

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

1. Clone the repository and navigate to the project directory:

```bash
git clone <repository-url>
cd whisper-tts
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Initialize database (optional):

```bash
# The database will be created automatically on first run
```

## Running the Application

### Development Server

```bash
python run_api.py
```

### Production Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

## Configuration

Configuration is managed through environment variables or `.env` file:

```bash
# API Settings
APP_NAME="Whisper TTS API"
APP_VERSION="1.0.0"
HOST="0.0.0.0"
PORT=8000
RELOAD=true
LOG_LEVEL="info"

# Database
DATABASE_URL="sqlite:///tts_tasks.db"

# TTS Settings
TTS_OUTPUT_DIR="output"
TTS_DEVICE="cpu"  # or "cuda" for GPU, None for auto-detection

# API Documentation
DOCS_URL="/docs"
REDOC_URL="/redoc"
OPENAPI_URL="/openapi.json"
```

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

### Key Components

- **TTSServiceWrapper**: High-level interface for TTS operations
- **FBTTSService**: Facebook TTS model integration with queue management
- **TaskManager**: Centralized task processing and status tracking
- **Database Services**: Persistent storage for conversion tasks

This design provides:

- **Testability**: Easy to mock and test individual components
- **Maintainability**: Clear separation of concerns
- **Scalability**: Modular design allows easy extension
- **Reliability**: Comprehensive error handling and logging
- **Performance**: GPU acceleration support and efficient queue processing

## Dependencies

- **FastAPI**: Modern web framework for building APIs
- **Transformers**: Hugging Face transformers for TTS models
- **PyTorch**: Deep learning framework for model inference
- **SQLAlchemy**: Database ORM and management
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server for production deployment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions, please open an issue in the repository.
