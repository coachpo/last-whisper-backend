"""Pytest configuration and fixtures."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.database import DatabaseManager, Base


@pytest.fixture
def test_db():
    """Create a test database."""
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    # Create session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield ":memory:", TestingSessionLocal


@pytest.fixture
def db_manager(test_db):
    """Create a database manager for testing."""
    db_path, _ = test_db
    return DatabaseManager(f"sqlite:///{db_path}")


@pytest.fixture
def mock_tts_service():
    """Create a mock TTS service."""
    mock_service = Mock()
    mock_service.is_initialized = True
    mock_service.submit_request.return_value = "test_task_123"
    mock_service.get_task_queue.return_value = Mock()
    return mock_service


@pytest.fixture
def mock_task_manager(mock_tts_service):
    """Create a mock task manager."""
    mock_manager = Mock()
    mock_manager.is_initialized = True
    mock_manager.submit_task.return_value = "test_task_123"
    mock_manager.submit_task_for_item.return_value = "test_task_123"
    mock_manager.get_task_status.return_value = {
        "task_id": "test_task_123",
        "status": "completed",
        "original_text": "Test text",
        "output_file_path": "/tmp/test.wav",
        "custom_filename": "test",
        "created_at": "2024-01-01T00:00:00",
        "submitted_at": "2024-01-01T00:00:00",
        "started_at": "2024-01-01T00:00:01",
        "completed_at": "2024-01-01T00:00:02",
        "failed_at": None,
        "file_size": 1024,
        "sampling_rate": 22050,
        "device": "cpu",
        "error_message": None,
        "item_id": None,
    }
    return mock_manager


@pytest.fixture
def test_client(test_db, mock_tts_service, mock_task_manager):
    """Create a test client with mocked dependencies."""
    # Override dependencies
    from app.api.dependencies import get_database_manager, get_tts_service, get_task_manager

    def override_get_database_manager():
        db_path, _ = test_db
        return DatabaseManager(f"sqlite:///{db_path}")

    def override_get_tts_service():
        return mock_tts_service

    def override_get_task_manager():
        return mock_task_manager

    app.dependency_overrides[get_database_manager] = override_get_database_manager
    app.dependency_overrides[get_tts_service] = override_get_tts_service
    app.dependency_overrides[get_task_manager] = override_get_task_manager

    with TestClient(app) as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def sample_item_data():
    """Sample item data for testing."""
    return {
        "locale": "fi",
        "text": "Hei, tämä on testi!",
        "difficulty": 3,
        "tags": ["test", "basic"]
    }


@pytest.fixture
def sample_attempt_data():
    """Sample attempt data for testing."""
    return {
        "item_id": 1,
        "text": "Hei, tämä on testi!"
    }


@pytest.fixture
def sample_tts_request():
    """Sample TTS request data for testing."""
    return {
        "text": "Test text for TTS conversion",
        "custom_filename": "test_audio"
    }


@pytest.fixture
def sample_tts_multiple_request():
    """Sample multiple TTS request data for testing."""
    return {
        "texts": [
            "First test text",
            "Second test text",
            "Third test text"
        ]
    }
