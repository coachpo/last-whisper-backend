"""Tests for health check endpoints."""

from fastapi import status


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_health_check(self, client):
        """Test root health check endpoint."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "TTS API"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data

    def test_detailed_health_check(self, client):
        """Test detailed health check endpoint."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "TTS API"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data
