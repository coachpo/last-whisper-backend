"""Pytest tests for the TTS API using FastAPI TestClient."""
import json
import os
import tempfile
import time
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api import app, get_database, get_task_manager, get_tts_service
from database import Base, DatabaseManager, Task
from models import TTSConvertRequest, TTSConvertResponse, TTSTaskResponse


class TestDatabaseManager(DatabaseManager):
    """Test database manager using in-memory SQLite."""
    
    def __init__(self):
        # Use in-memory SQLite for testing
        super().__init__("sqlite:///:memory:")


@pytest.fixture
def test_db():
    """Create a test database."""
    db = TestDatabaseManager()
    return db


@pytest.fixture
def mock_tts_service():
    """Create a mock TTS service."""
    service = Mock()
    service.submit_request.return_value = "test_task_id_123"
    service.start_service.return_value = None
    service.stop_service.return_value = None
    service.get_task_queue.return_value = Mock()
    return service


@pytest.fixture
def mock_task_manager(mock_tts_service):
    """Create a mock task manager."""
    manager = Mock()
    manager.submit_task.return_value = "test_task_id_123"
    manager.start_monitoring.return_value = None
    manager.stop_monitoring.return_value = None
    manager.tts_service = mock_tts_service
    return manager


@pytest.fixture
def client(test_db, mock_task_manager, mock_tts_service):
    """Create a test client with mocked dependencies."""
    
    # Override dependencies
    app.dependency_overrides[get_database] = lambda: test_db
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_tts_service] = lambda: mock_tts_service
    
    client = TestClient(app)
    
    yield client
    
    # Clean up
    app.dependency_overrides.clear()


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "TTS API"
        assert data["version"] == "1.0.0"


class TestTTSConvert:
    """Test TTS conversion endpoint."""
    
    def test_convert_text_success(self, client, test_db, mock_task_manager):
        """Test successful text conversion submission."""
        # Create a task in the database
        with test_db.get_session() as session:
            task = Task(
                task_id="test_task_id_123",
                original_text="Hello world",
                text_hash="test_hash",
                status="queued",
                submitted_at=None
            )
            session.add(task)
            session.commit()
        
        # Make request
        request_data = {
            "text": "Hello world",
            "custom_filename": "test_file"
        }
        
        response = client.post("/api/v1/tts/convert", json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["conversion_id"] == "test_task_id_123"
        assert data["text"] == "Hello world"
        assert data["status"] == "queued"
        assert "submitted_at" in data
        
        # Verify task manager was called
        mock_task_manager.submit_task.assert_called_once_with(
            text="Hello world",
            custom_filename="test_file"
        )
    
    def test_convert_text_empty_text(self, client):
        """Test conversion with empty text."""
        request_data = {"text": ""}
        
        response = client.post("/api/v1/tts/convert", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_convert_text_missing_text(self, client):
        """Test conversion with missing text field."""
        request_data = {"custom_filename": "test"}
        
        response = client.post("/api/v1/tts/convert", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_convert_text_task_manager_failure(self, client, mock_task_manager):
        """Test when task manager fails to submit task."""
        mock_task_manager.submit_task.return_value = None
        
        request_data = {"text": "Hello world"}
        
        response = client.post("/api/v1/tts/convert", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to submit TTS task" in data["detail"]
    
    def test_convert_text_task_not_found_in_db(self, client, mock_task_manager):
        """Test when task is submitted but not found in database."""
        request_data = {"text": "Hello world"}
        
        response = client.post("/api/v1/tts/convert", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Task created but not found in database" in data["detail"]


class TestGetConversionStatus:
    """Test get conversion status endpoint."""
    
    def test_get_status_success(self, client, test_db):
        """Test successful status retrieval."""
        # Create a task in the database
        with test_db.get_session() as session:
            task = Task(
                task_id="test_task_id_123",
                original_text="Hello world",
                text_hash="test_hash",
                status="completed",
                output_file_path="/path/to/output.wav",
                custom_filename="test_file",
                file_size=12345,
                sampling_rate=22050,
                device="cpu"
            )
            session.add(task)
            session.commit()
        
        response = client.get("/api/v1/tts/test_task_id_123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["conversion_id"] == "test_task_id_123"
        assert data["text"] == "Hello world"
        assert data["status"] == "completed"
        assert data["output_file_path"] == "/path/to/output.wav"
        assert data["custom_filename"] == "test_file"
        assert data["file_size"] == 12345
        assert data["sampling_rate"] == 22050
        assert data["device"] == "cpu"
    
    def test_get_status_not_found(self, client):
        """Test status retrieval for non-existent task."""
        response = client.get("/api/v1/tts/nonexistent_task")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_get_status_with_duration_calculation(self, client, test_db):
        """Test status retrieval with duration calculation."""
        with test_db.get_session() as session:
            task = Task(
                task_id="test_task_id_123",
                original_text="Hello world",
                text_hash="test_hash",
                status="completed",
                output_file_path="/nonexistent/path.wav",  # File doesn't exist
                file_size=44100,  # 1 second of audio at 22050 Hz
                sampling_rate=22050,
                device="cpu"
            )
            session.add(task)
            session.commit()
        
        response = client.get("/api/v1/tts/test_task_id_123")
        
        assert response.status_code == 200
        data = response.json()
        
        # Duration should be calculated: 44100 / (22050 * 2) = 1.0 second
        assert data["duration"] == pytest.approx(1.0, rel=0.01)


class TestListConversions:
    """Test list conversions endpoint."""
    
    def test_list_all_conversions(self, client, test_db):
        """Test listing all conversions."""
        # Create multiple tasks
        with test_db.get_session() as session:
            for i in range(3):
                task = Task(
                    task_id=f"task_{i}",
                    original_text=f"Text {i}",
                    text_hash=f"hash_{i}",
                    status="completed" if i % 2 == 0 else "queued"
                )
                session.add(task)
            session.commit()
        
        response = client.get("/api/v1/tts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 3
        assert all(item["conversion_id"].startswith("task_") for item in data)
    
    def test_list_conversions_by_status(self, client, test_db):
        """Test listing conversions filtered by status."""
        # Create tasks with different statuses
        with test_db.get_session() as session:
            for i in range(4):
                status = "completed" if i < 2 else "queued"
                task = Task(
                    task_id=f"task_{i}",
                    original_text=f"Text {i}",
                    text_hash=f"hash_{i}",
                    status=status
                )
                session.add(task)
            session.commit()
        
        response = client.get("/api/v1/tts?status=completed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 2
        assert all(item["status"] == "completed" for item in data)
    
    def test_list_conversions_invalid_status(self, client):
        """Test listing with invalid status parameter."""
        response = client.get("/api/v1/tts?status=invalid")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid status" in data["detail"]
    
    def test_list_conversions_invalid_limit(self, client):
        """Test listing with invalid limit parameter."""
        response = client.get("/api/v1/tts?limit=0")
        
        assert response.status_code == 400
        data = response.json()
        assert "Limit must be between 1 and 1000" in data["detail"]
        
        response = client.get("/api/v1/tts?limit=1001")
        
        assert response.status_code == 400
        data = response.json()
        assert "Limit must be between 1 and 1000" in data["detail"]
    
    def test_list_conversions_with_limit(self, client, test_db):
        """Test listing with limit parameter."""
        # Create 5 tasks
        with test_db.get_session() as session:
            for i in range(5):
                task = Task(
                    task_id=f"task_{i}",
                    original_text=f"Text {i}",
                    text_hash=f"hash_{i}",
                    status="completed"
                )
                session.add(task)
            session.commit()
        
        response = client.get("/api/v1/tts?limit=3")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 3


class TestServiceDependencies:
    """Test service dependency failures."""
    
    def test_missing_task_manager(self, test_db, mock_tts_service):
        """Test API when task manager is not available."""
        app.dependency_overrides[get_database] = lambda: test_db
        app.dependency_overrides[get_tts_service] = lambda: mock_tts_service
        # Don't override task manager - it will be None
        
        client = TestClient(app)
        
        request_data = {"text": "Hello world"}
        response = client.post("/api/v1/tts/convert", json=request_data)
        
        assert response.status_code == 503
        data = response.json()
        assert "TTS service not initialized" in data["detail"]
        
        app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
