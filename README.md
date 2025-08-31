# Last Whisper - Backend Service 🎯

A production-grade FastAPI service for advanced Text-to-Speech conversion with multiple TTS providers and comprehensive dictation training capabilities. Built with clean architecture, robust task management, and intelligent scoring systems.

## ✨ Core Features

### 🎙️ Advanced TTS Engine
- **Multiple Providers**: Azure Speech, Google Cloud Text-to-Speech, and Local TTS engines
- **High-Quality Audio**: Neural voice synthesis with customizable parameters
- **Batch Processing**: Efficient queue-based conversion for multiple texts
- **Task Management**: Comprehensive lifecycle tracking with deduplication
- **Provider Switching**: Easy configuration-based provider selection

### 📚 Dictation Training System
- **Interactive Practice**: Real-time dictation exercises with immediate feedback
- **Automatic Scoring**: Word Error Rate (WER) calculation for accurate assessment
- **Progress Analytics**: Comprehensive practice tracking and performance monitoring
- **Tag Management**: Flexible categorization with preset and custom tags
- **Difficulty Levels**: Customizable difficulty settings for progressive learning

### 🏗️ Production-Ready Architecture
- **Clean Architecture**: Proper separation of concerns with modular design
- **FastAPI Framework**: Modern, fast web framework with automatic OpenAPI docs
- **SQLAlchemy 2.x**: Advanced ORM with type hints and async support
- **Comprehensive Testing**: Full test suite with pytest and mocking
- **Error Handling**: Custom exceptions with proper HTTP status codes
- **Configuration Management**: Centralized settings with environment variables
- **Cloud Integration**: Scalable cloud TTS services with high availability

## 📁 Project Structure

```
last-whisper-backend/
├── app/                           # Main application package
│   ├── api/                       # API layer
│   │   ├── routes/                # Route definitions
│   │   │   ├── health.py          # Health check endpoints
│   │   │   ├── tts.py             # TTS conversion endpoints
│   │   │   ├── items.py           # Dictation items management
│   │   │   ├── attempts.py        # Practice attempts and scoring
│   │   │   ├── stats.py           # Statistics and analytics
│   │   │   └── tags.py            # Preset tag management
│   │   └── dependencies.py        # FastAPI dependencies
│   ├── core/                      # Core application components
│   │   ├── config.py              # Application configuration
│   │   ├── exceptions.py          # Custom exceptions
│   │   ├── logging.py             # Logging configuration
│   │   └── uvicorn_logging.py     # Uvicorn logging setup
│   ├── models/                    # Data models and schemas
│   │   ├── schemas.py             # Pydantic models and schemas
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── database_manager.py    # Database management
│   │   └── enums.py               # Enumeration definitions
│   ├── services/                  # Business logic layer
│   │   ├── task_service.py        # Task management service
│   │   ├── items_service.py       # Dictation items service
│   │   ├── attempts_service.py    # Practice attempts service
│   │   ├── stats_service.py       # Statistics service
│   │   └── tags_service.py        # Preset tag service
│   ├── tts_engine/                # TTS engine implementations
│   │   ├── tts_engine_azure.py    # Azure Speech TTS engine
│   │   ├── tts_engine_gcp.py      # Google Cloud TTS engine
│   │   ├── tts_engine_manager.py  # Task orchestration and monitoring
│   │   └── tts_engine_wrapper.py  # TTS service wrapper and provider selection
│   └── main.py                    # FastAPI application entry point
├── Dockerfile                     # Backend container configuration
├── keys/                          # API keys and credentials
│   └── google-credentials.json    # Google Cloud service account keys
├── audio/                         # Generated audio files (item_*.wav)
├── requirements.txt               # Python dependencies with comments
├── run_api.py                     # Server startup script
├── data/                          # Database storage
│   └── dictation.db               # SQLite database
└── README.md                      # This documentation file
```

## 🎙️ TTS Capabilities

This API provides enterprise-grade text-to-speech conversion with multiple provider options:

### 🔵 Azure Speech TTS
- **Provider**: Microsoft Azure Cognitive Services Speech
- **Voice Options**: Multiple Finnish neural voices with natural intonation
- **Output Format**: High-quality WAV audio files (24kHz, 16-bit mono)
- **Features**: SSML support, prosody controls, advanced neural voices
- **Scalability**: Cloud-based processing with enterprise-grade availability
- **Use Cases**: Production applications requiring reliable, high-quality speech synthesis

### 🟢 Google Cloud Text-to-Speech
- **Provider**: Google Cloud Platform Text-to-Speech API
- **Voice Options**: Premium WaveNet voices (fi-FI-Wavenet-B)
- **Output Format**: High-fidelity WAV audio files (24kHz, 16-bit mono)
- **Features**: Advanced neural voice synthesis, comprehensive SSML support
- **Quality**: State-of-the-art WaveNet voices for natural, human-like speech
- **Use Cases**: Applications requiring the highest quality speech synthesis

### ⚡ Common Features
- **Batch Processing**: Efficient queue-based request handling for scalability
- **Task Management**: Comprehensive task lifecycle tracking with deduplication
- **Provider Switching**: Seamless configuration-based provider selection
- **Error Handling**: Robust error handling with intelligent retry mechanisms
- **Performance**: Optimized for high-throughput production environments

## 📚 Dictation Practice Features

The backend provides a comprehensive dictation training workflow designed for language learning and pronunciation practice:

### 📝 Item Management
- **CRUD Operations**: Create, read, update, delete dictation items with automatic TTS generation
- **Content Organization**: Flexible text management with difficulty levels and categorization
- **Automatic Audio**: Seamless TTS generation for all dictation items
- **Bulk Operations**: Efficient handling of multiple items and batch processing

### 🎯 Practice & Scoring
- **Real-time Practice**: Submit attempts and receive immediate feedback
- **Automatic Scoring**: Advanced Word Error Rate (WER) calculation for accurate assessment
- **Progress Tracking**: Comprehensive attempt history and performance monitoring
- **Session-less Design**: No authentication required - perfect for educational environments

### 📊 Analytics & Insights
- **Comprehensive Statistics**: Detailed analytics and progress monitoring
- **Performance Metrics**: Track improvement over time with visual progress indicators
- **Practice Logs**: Complete history of practice sessions and attempts
- **Item-specific Analytics**: Detailed statistics for individual dictation items

### 🏷️ Organization System
- **Tag Management**: Create and manage preset tags for item categorization
- **Flexible Filtering**: Advanced search and filter capabilities
- **Content Discovery**: Easy navigation through organized content libraries

## 🔌 API Endpoints

### 🎙️ TTS Endpoints

#### `POST /api/v1/tts/convert`
Submit text for TTS conversion with automatic audio generation.

**Request Body:**
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

#### `GET /api/v1/tts/{id}`
Retrieve conversion status and metadata for a specific task.

#### `GET /api/v1/tts`
List all conversions with optional status filtering and pagination.

#### `POST /api/v1/tts/convert-multiple`
Submit multiple texts for efficient batch TTS conversion.

### 📚 Dictation Endpoints

#### `POST /v1/items`
Create a new dictation item with automatic TTS generation.

**Request Body:**
```json
{
  "locale": "en",
  "text": "The quick brown fox jumps over the lazy dog",
  "difficulty": 3,
  "tags": ["animals", "classic"]
}
```

#### `GET /v1/items`
List items with advanced filtering options:
- **Locale filtering**: Filter by language/locale
- **Tag filtering**: Filter by one or more tags
- **Difficulty filtering**: Filter by difficulty level
- **Text search**: Search within item text content
- **Practice status**: Filter by practiced/unpracticed items

#### `POST /v1/attempts`
Submit and automatically score a practice attempt.

**Request Body:**
```json
{
  "item_id": 1,
  "text": "The quick brown fox jumps over lazy dog"
}
```

### 📊 Statistics Endpoints

#### `GET /v1/stats/summary`
Get comprehensive summary statistics for all practice sessions.

#### `GET /v1/stats/practice-log`
Retrieve detailed practice log with per-item statistics and performance metrics.

#### `GET /v1/stats/items/{item_id}`
Get detailed statistics and analytics for a specific dictation item.

#### `GET /v1/stats/progress`
Retrieve progress over time data for practice sessions and performance trends.

### 🏷️ Tag Management Endpoints

#### `POST /v1/tags/`
Create a new preset tag for item categorization.

#### `GET /v1/tags/`
Retrieve list of all available preset tags.

#### `DELETE /v1/tags/{tag_id}`
Delete a preset tag (with safety checks for existing items).

### 🏥 Health & Monitoring Endpoints

#### `GET /health`
Comprehensive health check with detailed service status and dependency monitoring.

## 🚀 Installation & Setup

### Prerequisites
- **Python 3.11+** (recommended: Python 3.11 or 3.12)
- **pip** (Python package manager)
- **Git** (for cloning the repository)

### Quick Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd last-whisper-backend
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Initialize database:**
```bash
# The SQLite database will be created automatically on first run
# No additional setup required!
```

## 🏃‍♂️ Running the Application

### 🛠️ Development Server
For development and testing:
```bash
python run_api.py
```

### 🚀 Production Server
For production deployment:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 📚 Access Points
- **API Base URL**: `http://localhost:8000`
- **Interactive Documentation**: `http://localhost:8000/docs`
- **Alternative Documentation**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## ⚙️ Configuration

Configuration is managed through environment variables or `.env` file for maximum flexibility:

### 🔧 Core Application Settings
```bash
# Application Identity
APP_NAME="Last Whisper"
APP_VERSION="1.0.0"
HOST="0.0.0.0"
PORT=8000
RELOAD=true
LOG_LEVEL="info"

# Database Configuration
DATABASE_URL="sqlite:///data/dictation.db"
```

### 🎙️ TTS Provider Configuration
```bash
# Provider Selection
TTS_PROVIDER="gcp"  # Options: "azure", "gcp"
TTS_THREAD_COUNT=1
TTS_SUPPORTED_LANGUAGES="fi,en,de"  # Comma-separated list (recommended for Docker), or JSON: '["fi"]'

# Azure Speech TTS Settings (when TTS_PROVIDER="azure")
AZURE_SPEECH_KEY="your_azure_speech_key"
AZURE_SERVICE_REGION="your_azure_region"
AZURE_LANGUAGE_CODE="fi-FI"
AZURE_SAMPLE_RATE_HZ=24000

# Google Cloud TTS Settings (when TTS_PROVIDER="gcp")
# Set GOOGLE_APPLICATION_CREDENTIALS environment variable
GCP_VOICE_NAME="fi-FI-Wavenet-B"
GCP_LANGUAGE_CODE="fi-FI"
GCP_SAMPLE_RATE_HZ=24000
```

### 📁 Storage & Media Configuration
```bash
# Audio Storage
AUDIO_DIR="audio"
BASE_URL="http://localhost:8000"

# API Documentation
DOCS_URL="/docs"
REDOC_URL="/redoc"
OPENAPI_URL="/openapi.json"
```

## 🧪 Testing

### Running Tests
```bash
# Run the complete test suite
pytest

# Run tests with verbose output
pytest -v

# Run specific test modules
pytest tests/test_api/ -v
pytest tests/test_services/ -v

# Run tests with coverage report
pytest --cov=app --cov-report=html
```

### Test Structure
- **API Tests**: Endpoint testing with request/response validation
- **Service Tests**: Business logic testing with mocking
- **Integration Tests**: End-to-end workflow testing
- **Unit Tests**: Individual component testing

## 🔍 Code Quality

### Code Formatting
```bash
# Format code with Black
black .

# Check formatting without making changes
black --check .
```

### Code Linting
```bash
# Run Ruff linter
ruff check .

# Auto-fix linting issues
ruff check . --fix

# Run with specific rules
ruff check . --select E,W,F
```

### Development Workflow
1. **Write tests** for new functionality
2. **Format code** with Black
3. **Lint code** with Ruff
4. **Run tests** to ensure everything works
5. **Commit changes** with descriptive messages

## 🏗️ Architecture

The application follows clean architecture principles with clear separation of concerns:

### 📋 Architecture Layers
- **API Layer**: FastAPI routes with request/response models and validation
- **Service Layer**: Business logic and external service integration
- **Data Layer**: Database operations, models, and data persistence
- **Core Layer**: Configuration, exceptions, logging, and utilities

### 🔧 Key Components

#### TTS Engine System
- **TTSEngine**: Core TTS engine with provider abstraction
- **TTSEngineManager**: Task orchestration, monitoring, and queue management
- **TTSEngineWrapper**: Service lifecycle management and provider selection
- **Provider Implementations**: Azure and Google Cloud TTS integrations

#### Business Services
- **ItemsService**: Dictation item management with automatic TTS integration
- **AttemptsService**: Practice attempt scoring and performance tracking
- **StatsService**: Analytics, reporting, and progress monitoring
- **TagsService**: Preset tag management and content categorization
- **TaskService**: TTS task database operations and status tracking

### 🎯 Design Benefits
- **Testability**: Easy to mock and test individual components in isolation
- **Maintainability**: Clear separation of concerns and modular design
- **Scalability**: Modular architecture allows easy extension and scaling
- **Reliability**: Comprehensive error handling, logging, and monitoring
- **Performance**: Optimized queue processing and efficient resource management

## 📦 Dependencies

### 🔧 Core Framework
- **FastAPI**: Modern, fast web framework for building APIs with automatic OpenAPI documentation
- **SQLAlchemy**: Advanced database ORM with async support and type hints
- **Pydantic**: Data validation and settings management with type safety
- **Uvicorn**: High-performance ASGI server for production deployment
- **Alembic**: Database migration management and schema versioning

### 🎙️ TTS Engines
- **Azure Cognitive Services Speech**: Enterprise-grade Azure TTS integration
- **Google Cloud Text-to-Speech**: Premium Google Cloud TTS integration

### 📚 Dictation Features
- **jiwer**: Advanced Word Error Rate calculation for accurate scoring
- **unidecode**: Unicode normalization for consistent text processing

### 🛠️ Development Tools
- **pytest**: Comprehensive testing framework with fixtures and mocking
- **black**: Opinionated code formatting for consistent style
- **ruff**: Fast Python linter with auto-fixing capabilities

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository** and create a feature branch
2. **Make your changes** following our coding standards
3. **Add tests** for new functionality
4. **Ensure all tests pass** and code is properly formatted
5. **Submit a pull request** with a clear description of your changes

### Development Guidelines
- Follow the existing code style and architecture patterns
- Add comprehensive tests for new features
- Update documentation for any API changes
- Ensure backward compatibility when possible

## 📄 License

This project is licensed under the WTFPL - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Community

- 🐛 **Bug Reports**: Open an issue with detailed reproduction steps
- 💡 **Feature Requests**: Share your ideas and use cases
- 📖 **Documentation**: Check our comprehensive docs for detailed guides
- 💬 **Discussions**: Join our community discussions for questions and ideas

---

**Ready to build amazing TTS applications?** 🚀 [Get started now](#-installation--setup) with Last Whisper Backend!
