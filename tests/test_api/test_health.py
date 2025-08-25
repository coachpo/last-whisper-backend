"""Tests for health API endpoints."""

import pytest
from unittest.mock import Mock, patch


class TestHealthAPI:
    """Test cases for health API endpoints."""

    def test_health_check_success(self, test_client, db_manager):
        """Test successful health check."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "checks" in data
        assert isinstance(data["checks"], dict)
        
        # Check required health check fields
        required_checks = ["database", "audio_directory", "tts_service", "task_manager", "service", "version", "timestamp"]
        for check in required_checks:
            assert check in data["checks"]

    def test_health_check_database_healthy(self, test_client, db_manager):
        """Test health check with healthy database."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Database should be healthy
        assert data["checks"]["database"] == "healthy"
        assert data["status"] == "healthy"

    def test_health_check_database_unhealthy(self, test_client, db_manager):
        """Test health check with unhealthy database."""
        # Mock database health check to return False
        with patch.object(db_manager, 'health_check', return_value=False):
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Database should be unhealthy
            assert data["checks"]["database"] == "unhealthy"
            assert data["status"] == "unhealthy"

    def test_health_check_database_error(self, test_client, db_manager):
        """Test health check with database error."""
        # Mock database health check to raise exception
        with patch.object(db_manager, 'health_check', side_effect=Exception("Database connection failed")):
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Database should show error
            assert "error:" in data["checks"]["database"]
            assert data["status"] == "unhealthy"

    def test_health_check_audio_directory_healthy(self, test_client, db_manager):
        """Test health check with healthy audio directory."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Audio directory should be healthy
        assert data["checks"]["audio_directory"] == "healthy"

    def test_health_check_audio_directory_unhealthy(self, test_client, db_manager):
        """Test health check with unhealthy audio directory."""
        # Mock audio directory check to return False
        with patch.object(db_manager, 'check_audio_directory', return_value=False):
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Audio directory should be unhealthy
            assert data["checks"]["audio_directory"] == "unhealthy"
            assert data["status"] == "unhealthy"

    def test_health_check_audio_directory_error(self, test_client, db_manager):
        """Test health check with audio directory error."""
        # Mock audio directory check to raise exception
        with patch.object(db_manager, 'check_audio_directory', side_effect=Exception("Permission denied")):
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Audio directory should show error
            assert "error:" in data["checks"]["audio_directory"]
            assert data["status"] == "unhealthy"

    def test_health_check_tts_service_initialized(self, test_client, mock_tts_service):
        """Test health check with initialized TTS service."""
        mock_tts_service.is_initialized = True
        
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # TTS service should be healthy
        assert data["checks"]["tts_service"] == "healthy"

    def test_health_check_tts_service_not_initialized(self, test_client, mock_tts_service):
        """Test health check with uninitialized TTS service."""
        mock_tts_service.is_initialized = False
        
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # TTS service should show not initialized
        assert data["checks"]["tts_service"] == "not_initialized"

    def test_health_check_tts_service_error(self, test_client, mock_tts_service):
        """Test health check with TTS service error."""
        # Mock get_tts_service to raise exception
        with patch('app.api.routes.health.get_tts_service', side_effect=Exception("TTS service error")):
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # TTS service should show error
            assert "error:" in data["checks"]["tts_service"]

    def test_health_check_task_manager_initialized(self, test_client, mock_task_manager):
        """Test health check with initialized task manager."""
        mock_task_manager.is_initialized = True
        
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Task manager should be healthy
        assert data["checks"]["task_manager"] == "healthy"

    def test_health_check_task_manager_not_initialized(self, test_client, mock_task_manager):
        """Test health check with uninitialized task manager."""
        mock_task_manager.is_initialized = False
        
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Task manager should show not initialized
        assert data["checks"]["task_manager"] == "not_initialized"

    def test_health_check_task_manager_error(self, test_client, mock_task_manager):
        """Test health check with task manager error."""
        # Mock get_task_manager to raise exception
        with patch('app.api.routes.health.get_task_manager', side_effect=Exception("Task manager error")):
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Task manager should show error
            assert "error:" in data["checks"]["task_manager"]

    def test_health_check_service_info(self, test_client):
        """Test health check service information."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Service info should be present
        assert "service" in data["checks"]
        assert "version" in data["checks"]
        assert "timestamp" in data["checks"]
        
        # Service name should match expected value
        assert data["checks"]["service"] == "Dictation Backend API"
        
        # Version should be present
        assert data["checks"]["version"] is not None
        assert len(data["checks"]["version"]) > 0
        
        # Timestamp should be valid ISO format
        import re
        timestamp_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        assert re.match(timestamp_pattern, data["checks"]["timestamp"])

    def test_health_check_overall_status_healthy(self, test_client, db_manager):
        """Test health check overall status when all services are healthy."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Overall status should be healthy when all services are healthy
        assert data["status"] == "healthy"

    def test_health_check_overall_status_unhealthy(self, test_client, db_manager):
        """Test health check overall status when some services are unhealthy."""
        # Mock database to be unhealthy
        with patch.object(db_manager, 'health_check', return_value=False):
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Overall status should be unhealthy when any service is unhealthy
            assert data["status"] == "unhealthy"

    def test_health_check_overall_status_mixed(self, test_client, db_manager):
        """Test health check overall status with mixed service health."""
        # Mock database to be unhealthy but TTS service to be healthy
        with patch.object(db_manager, 'health_check', return_value=False):
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Overall status should be unhealthy when any service is unhealthy
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"] == "unhealthy"

    def test_health_check_response_structure(self, test_client):
        """Test health check response structure."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert isinstance(data, dict)
        assert "status" in data
        assert "checks" in data
        
        # Status should be a string
        assert isinstance(data["status"], str)
        assert data["status"] in ["healthy", "unhealthy"]
        
        # Checks should be a dictionary
        assert isinstance(data["checks"], dict)
        
        # All check values should be strings
        for check_name, check_value in data["checks"].items():
            assert isinstance(check_value, str)

    def test_health_check_required_fields(self, test_client):
        """Test that all required health check fields are present."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required checks
        required_checks = [
            "database",
            "audio_directory", 
            "tts_service",
            "task_manager",
            "service",
            "version",
            "timestamp"
        ]
        
        for check in required_checks:
            assert check in data["checks"], f"Missing required check: {check}"
            assert data["checks"][check] is not None, f"Check {check} value is None"

    def test_health_check_error_handling(self, test_client, db_manager):
        """Test health check error handling for all services."""
        # Mock all services to raise exceptions
        with patch.object(db_manager, 'health_check', side_effect=Exception("DB error")), \
             patch.object(db_manager, 'check_audio_directory', side_effect=Exception("Audio error")), \
             patch('app.api.routes.health.get_tts_service', side_effect=Exception("TTS error")), \
             patch('app.api.routes.health.get_task_manager', side_effect=Exception("Task error")):
            
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # All services should show errors
            assert "error:" in data["checks"]["database"]
            assert "error:" in data["checks"]["audio_directory"]
            assert "error:" in data["checks"]["tts_service"]
            assert "error:" in data["checks"]["task_manager"]
            
            # Overall status should be unhealthy
            assert data["status"] == "unhealthy"

    def test_health_check_timestamp_format(self, test_client):
        """Test that timestamp is in correct format."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        timestamp = data["checks"]["timestamp"]
        
        # Should be ISO format
        assert "T" in timestamp
        assert len(timestamp) >= 19  # YYYY-MM-DDTHH:MM:SS
        
        # Try to parse as datetime
        from datetime import datetime
        try:
            parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            assert parsed_time is not None
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {timestamp}")

    def test_health_check_service_name_consistency(self, test_client):
        """Test that service name is consistent."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Service name should match expected value
        expected_service_name = "Dictation Backend API"
        assert data["checks"]["service"] == expected_service_name

    def test_health_check_version_format(self, test_client):
        """Test that version is in correct format."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        version = data["checks"]["version"]
        
        # Version should be a string
        assert isinstance(version, str)
        
        # Version should not be empty
        assert len(version) > 0
        
        # Version should follow semantic versioning pattern (e.g., "1.0.0")
        import re
        version_pattern = r'^\d+\.\d+\.\d+'
        assert re.match(version_pattern, version), f"Invalid version format: {version}"

    def test_health_check_database_connection(self, test_client, db_manager):
        """Test that database connection is actually tested."""
        # This test verifies that the health check actually calls the database
        with patch.object(db_manager, 'health_check') as mock_health_check:
            mock_health_check.return_value = True
            
            response = test_client.get("/health")
            
            assert response.status_code == 200
            
            # Verify that health_check was called
            mock_health_check.assert_called_once()

    def test_health_check_audio_directory_permissions(self, test_client, db_manager):
        """Test that audio directory permissions are actually tested."""
        # This test verifies that the health check actually tests audio directory
        with patch.object(db_manager, 'check_audio_directory') as mock_check_audio:
            mock_check_audio.return_value = True
            
            response = test_client.get("/health")
            
            assert response.status_code == 200
            
            # Verify that check_audio_directory was called
            mock_check_audio.assert_called_once()

    def test_health_check_tts_service_availability(self, test_client, mock_tts_service):
        """Test that TTS service availability is actually tested."""
        # This test verifies that the health check actually checks TTS service
        mock_tts_service.is_initialized = True
        
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # TTS service should be marked as healthy
        assert data["checks"]["tts_service"] == "healthy"

    def test_health_check_task_manager_availability(self, test_client, mock_task_manager):
        """Test that task manager availability is actually tested."""
        # This test verifies that the health check actually checks task manager
        mock_task_manager.is_initialized = True
        
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Task manager should be marked as healthy
        assert data["checks"]["task_manager"] == "healthy"
