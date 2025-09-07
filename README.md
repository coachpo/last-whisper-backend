# Last Whisper - Backend Service 🎯

A production-grade FastAPI service for comprehensive dictation training with automatic TTS audio generation. Built with clean architecture, robust task management, and intelligent scoring systems.

## ✨ Core Features

### 🎙️ Internal TTS Engine
- **Multiple Providers**: Azure Speech and Google Cloud Text-to-Speech
- **High-Quality Audio**: Neural voice synthesis with customizable parameters
- **Automatic Processing**: Background TTS generation for dictation items
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
├── pyproject.toml                 # Python project configuration and dependencies
├── run_api.py                     # Server startup script
├── data/                          # Database storage
│   └── dictation.db               # SQLite database
└── README.md                      # This documentation file
```

## 🎙️ TTS Engine (Internal)

The backend includes a robust TTS engine that automatically generates audio files for dictation items:

### 🔵 Azure Speech TTS
- **Provider**: Microsoft Azure Cognitive Services Speech
- **Voice Options**: Multiple Finnish neural voices with natural intonation
- **Output Format**: High-quality WAV audio files (24kHz, 16-bit mono)
- **Features**: SSML support, prosody controls, advanced neural voices
- **Use Cases**: Automatic audio generation for dictation practice items

### 🟢 Google Cloud Text-to-Speech
- **Provider**: Google Cloud Platform Text-to-Speech API
- **Voice Options**: Premium WaveNet voices (fi-FI-Wavenet-B)
- **Output Format**: High-fidelity WAV audio files (24kHz, 16-bit mono)
- **Features**: Advanced neural voice synthesis, comprehensive SSML support
- **Use Cases**: High-quality audio generation for dictation practice items

### ⚡ Internal Features
- **Automatic Processing**: TTS generation happens automatically when dictation items are created
- **Task Management**: Comprehensive task lifecycle tracking with deduplication
- **Provider Switching**: Seamless configuration-based provider selection
- **Error Handling**: Robust error handling with intelligent retry mechanisms
- **Background Processing**: Non-blocking audio generation for optimal performance

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

### 📚 Dictation Endpoints

#### `POST /v1/items`
Create a new dictation item with automatic TTS generation.

**Request Body:** JSON object with locale, text content, difficulty level, and tags array

#### `GET /v1/items`
List items with advanced filtering options:
- **Locale filtering**: Filter by language/locale
- **Tag filtering**: Filter by one or more tags
- **Difficulty filtering**: Filter by difficulty level
- **Text search**: Search within item text content
- **Practice status**: Filter by practiced/unpracticed items

#### `POST /v1/attempts`
Submit and automatically score a practice attempt.

**Request Body:** JSON object with item ID and practice text

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

1. **Clone the repository** and navigate to the backend directory
2. **Create a Python virtual environment** for dependency isolation:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies** using pip with pyproject.toml:
   ```bash
   pip install -e ".[dev]"
   ```
4. **Initialize database** - SQLite database is created automatically on first run

## 🏃‍♂️ Running the Application

### 🛠️ Development Server
For development and testing, use the provided run script.

### 🚀 Production Server
For production deployment, use Uvicorn ASGI server with specified host and port configuration.

### 📚 Access Points
- **API Base URL**: `http://localhost:8000`
- **Interactive Documentation**: `http://localhost:8000/docs`
- **Alternative Documentation**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## ⚙️ Configuration

Configuration is managed through environment variables or `.env` file for maximum flexibility:

### 🔧 Core Application Settings

**Application Identity Configuration:**
- Application name and version settings
- Host and port configuration for server binding
- Reload settings for development mode
- Log level configuration for debugging

**Database Configuration:**
- SQLite database URL for data persistence

### 🎙️ TTS Provider Configuration

**Provider Selection:**
- TTS provider choice (Azure or Google Cloud)
- Thread count for concurrent processing
- Supported languages configuration

**Azure Speech TTS Settings:**
- Azure Speech service key and region
- Language code and sample rate configuration

**Google Cloud TTS Settings:**
- Google Cloud credentials configuration
- Voice name and language settings
- Sample rate configuration

### 📁 Storage & Media Configuration

**Audio Storage:**
- Audio directory configuration
- Base URL for API endpoints

**API Documentation:**
- Documentation endpoint URLs
- OpenAPI schema configuration

## 🧪 Testing

### Running Tests

**Test Execution Options:**
- Run the complete test suite with pytest
- Execute tests with verbose output for detailed information
- Run specific test modules (API tests, service tests)
- Generate coverage reports for code quality assessment

### Test Structure
- **API Tests**: Endpoint testing with request/response validation
- **Service Tests**: Business logic testing with mocking
- **Integration Tests**: End-to-end workflow testing
- **Unit Tests**: Individual component testing

## 🔍 Code Quality

### Code Formatting

**Black Code Formatter:**
- Format code with Black for consistent style: `black .`
- Check formatting without making changes: `black --check .`

### Code Linting

**Ruff Linter:**
- Run comprehensive linting checks: `ruff check .`
- Auto-fix common linting issues: `ruff check --fix .`
- Run with specific rule sets for targeted checks

### Development Workflow
1. **Write tests** for new functionality
2. **Format code** with Black: `black .`
3. **Lint code** with Ruff: `ruff check .`
4. **Run tests** to ensure everything works: `pytest`
5. **Commit changes** with descriptive messages

### Using pyproject.toml

The project uses `pyproject.toml` for configuration, which provides:
- **Unified configuration** for all tools (Black, Ruff, pytest)
- **Modern Python packaging** with PEP 621 compliance
- **Development dependencies** managed through optional dependencies
- **Build system** configuration for packaging and distribution

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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Community

- 🐛 **Bug Reports**: Open an issue with detailed reproduction steps
- 💡 **Feature Requests**: Share your ideas and use cases
- 📖 **Documentation**: Check our comprehensive docs for detailed guides
- 💬 **Discussions**: Join our community discussions for questions and ideas

---

**Ready to build amazing TTS applications?** 🚀 [Get started now](#-installation--setup) with Last Whisper Backend!

