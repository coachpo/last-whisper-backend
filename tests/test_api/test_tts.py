"""Tests for TTS conversion endpoints."""

from fastapi import status


class TestTTSConvert:
    """Test TTS conversion endpoint."""

    def test_convert_text_success(self, client, sample_task, mock_task_manager):
        """Test successful text conversion submission."""
        request_data = {"text": "Hello world", "custom_filename": "test_file"}

        response = client.post("/api/v1/tts/convert", json=request_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["conversion_id"] == "test_task_id_123"
        assert data["text"] == "Hello world"
        assert data["status"] == "queued"
        assert "submitted_at" in data

        # Verify task manager was called
        mock_task_manager.submit_task.assert_called_once_with(
            text="Hello world", custom_filename="test_file"
        )

    def test_convert_text_empty_text(self, client):
        """Test conversion with empty text."""
        request_data = {"text": ""}

        response = client.post("/api/v1/tts/convert", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_convert_text_missing_text(self, client):
        """Test conversion with missing text field."""
        request_data = {"custom_filename": "test"}

        response = client.post("/api/v1/tts/convert", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_convert_text_task_manager_failure(self, client, mock_task_manager):
        """Test when task manager fails to submit task."""
        mock_task_manager.submit_task.return_value = None

        request_data = {"text": "Hello world"}

        response = client.post("/api/v1/tts/convert", json=request_data)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


class TestGetConversionStatus:
    """Test get conversion status endpoint."""

    def test_get_status_success(self, client, sample_task):
        """Test successful status retrieval."""
        response = client.get("/api/v1/tts/test_task_id_123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["conversion_id"] == "test_task_id_123"
        assert data["text"] == "Hello world"
        assert data["status"] == "queued"

    def test_get_status_not_found(self, client):
        """Test status retrieval for non-existent task."""
        response = client.get("/api/v1/tts/nonexistent_task")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"]


class TestListConversions:
    """Test list conversions endpoint."""

    def test_list_all_conversions(self, client, sample_task):
        """Test listing all conversions."""
        response = client.get("/api/v1/tts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) >= 1
        assert any(item["conversion_id"] == "test_task_id_123" for item in data)

    def test_list_conversions_invalid_status(self, client):
        """Test listing with invalid status parameter."""
        response = client.get("/api/v1/tts?status=invalid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "Invalid status" in data["detail"]

    def test_list_conversions_invalid_limit(self, client):
        """Test listing with invalid limit parameter."""
        response = client.get("/api/v1/tts?limit=0")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "Limit must be between 1 and 1000" in data["detail"]
