"""Tests for health check endpoints."""

from fastapi import status


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test comprehensive health check endpoint."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "checks" in data
        
        checks = data["checks"]
        # Check that all expected health checks are present
        assert "database" in checks
        assert "audio_directory" in checks
        assert "tts_service" in checks
        assert "task_manager" in checks
        assert "service" in checks
        assert "version" in checks
        assert "timestamp" in checks
        
        # Verify service info
        assert checks["service"] == "Dictation Backend API"
        assert checks["version"] == "1.0.0"
