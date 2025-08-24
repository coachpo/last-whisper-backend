"""Pytest configuration and fixtures."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_database_service, get_task_manager, get_tts_service
from app.core.exceptions import TaskNotFoundException
from app.main import app
from app.models.database import DatabaseManager, Task


class TestDatabaseService:
    """Test database service using in-memory SQLite."""

    def __init__(self):
        self.db_manager = DatabaseManager("sqlite:///:memory:")
        # Ensure tables are created by accessing the engine
        self.db_manager.engine

    def get_task_by_id(self, task_id: str):
        """Mock get task by ID."""
        if task_id == "test_task_id_123":
            # Return a mock task for testing
            task = Task(
                task_id="test_task_id_123",
                original_text="Hello world",
                text_hash="test_hash",
                status="queued",
                created_at=datetime.now(UTC),
                submitted_at=datetime.now(UTC),
            )
            return task
        elif task_id in ["task_1", "task_2", "task_3"]:
            # Return mock tasks for multiple text conversion testing
            task = Task(
                task_id=task_id,
                original_text=f"Text for {task_id}",
                text_hash=f"hash_{task_id}",
                status="queued",
                created_at=datetime.now(UTC),
                submitted_at=datetime.now(UTC),
            )
            return task
        # For any other task ID, raise TaskNotFoundException to simulate not found
        raise TaskNotFoundException(task_id)

    def get_all_tasks(self, status=None, limit=100):
        """Mock get all tasks."""
        # Return a list with the sample task
        task = Task(
            task_id="test_task_id_123",
            original_text="Hello world",
            text_hash="test_hash",
            status="queued",
            created_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )
        return [task]

    def get_database_manager(self):
        """Get the underlying database manager."""
        return self.db_manager


@pytest.fixture
def test_db_service():
    """Create a test database service."""
    return TestDatabaseService()


@pytest.fixture
def mock_tts_service():
    """Create a mock TTS service."""
    service = Mock()
    service.is_initialized = True
    service.submit_request.return_value = "test_task_id_123"
    service.initialize.return_value = None
    service.shutdown.return_value = None
    return service


@pytest.fixture
def mock_task_manager():
    """Create a mock task manager."""
    manager = Mock()
    manager.is_initialized = True
    manager.initialize.return_value = None
    manager.shutdown.return_value = None

    # Mock the task manager methods that the API actually calls
    manager.submit_task = Mock(return_value="test_task_id_123")
    manager.submit_multiple_tasks = Mock(return_value=["task_1", "task_2", "task_3"])

    return manager


@pytest.fixture
def client(test_db_service, mock_task_manager, mock_tts_service):
    """Create a test client with mocked dependencies."""

    # Override dependencies
    app.dependency_overrides[get_database_service] = lambda: test_db_service
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_tts_service] = lambda: mock_tts_service

    client = TestClient(app=app)

    yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_task(test_db_service):
    """Create a sample task in the test database."""
    with test_db_service.db_manager.get_session() as session:
        task = Task(
            task_id="test_task_id_123",
            original_text="Hello world",
            text_hash="test_hash",
            status="queued",
            created_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        return task
