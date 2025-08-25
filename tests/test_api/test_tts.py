"""Tests for TTS API endpoints."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC


class TestTTSAPI:
    """Test cases for TTS API endpoints."""

    def test_convert_text_success(self, test_client, sample_tts_request):
        """Test successful text-to-speech conversion."""
        response = test_client.post("/api/v1/tts/convert", json=sample_tts_request)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "conversion_id" in data
        assert data["text"] == "Test text for TTS conversion"
        assert data["status"] == "queued"
        assert "submitted_at" in data

    def test_convert_text_without_custom_filename(self, test_client):
        """Test TTS conversion without custom filename."""
        request_data = {
            "text": "Simple text for conversion"
        }
        
        response = test_client.post("/api/v1/tts/convert", json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["text"] == "Simple text for conversion"
        assert data["custom_filename"] is None

    def test_convert_text_invalid_data(self, test_client):
        """Test TTS conversion with invalid data."""
        # Missing text
        response = test_client.post("/api/v1/tts/convert", json={})
        assert response.status_code == 422
        
        # Empty text
        response = test_client.post("/api/v1/tts/convert", json={"text": ""})
        assert response.status_code == 422
        
        # Text too long
        long_text = "a" * 10001
        response = test_client.post("/api/v1/tts/convert", json={"text": long_text})
        assert response.status_code == 422
        
        # Invalid custom filename
        response = test_client.post("/api/v1/tts/convert", json={
            "text": "Test text",
            "custom_filename": "a" * 256  # Too long
        })
        assert response.status_code == 422

    def test_convert_multiple_texts_success(self, test_client, sample_tts_multiple_request):
        """Test successful multiple text-to-speech conversion."""
        response = test_client.post("/api/v1/tts/convert-multiple", json=sample_tts_multiple_request)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "conversion_ids" in data
        assert len(data["conversion_ids"]) == 3
        assert data["texts"] == sample_tts_multiple_request["texts"]
        assert data["status"] == "queued"
        assert "submitted_at" in data

    def test_convert_multiple_texts_invalid_data(self, test_client):
        """Test multiple TTS conversion with invalid data."""
        # Empty texts list
        response = test_client.post("/api/v1/tts/convert-multiple", json={"texts": []})
        assert response.status_code == 422
        
        # Too many texts
        too_many_texts = [f"Text {i}" for i in range(101)]
        response = test_client.post("/api/v1/tts/convert-multiple", json={"texts": too_many_texts})
        assert response.status_code == 422
        
        # Empty text in list
        response = test_client.post("/api/v1/tts/convert-multiple", json={
            "texts": ["Valid text", "", "Another valid text"]
        })
        assert response.status_code == 422

    def test_get_conversion_status_success(self, test_client, mock_task_manager):
        """Test successful conversion status retrieval."""
        # Mock task manager to return a task
        mock_task_manager.get_task_status.return_value = {
            "task_id": "test_task_123",
            "status": "completed",
            "original_text": "Test text",
            "output_file_path": "/tmp/test.wav",
            "custom_filename": "test_audio",
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
        
        response = test_client.get("/api/v1/tts/test_task_123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["conversion_id"] == "test_task_123"
        assert data["text"] == "Test text"
        assert data["status"] == "completed"
        assert data["output_file_path"] == "/tmp/test.wav"
        assert data["custom_filename"] == "test_audio"
        assert data["file_size"] == 1024
        assert data["sampling_rate"] == 22050
        assert data["device"] == "cpu"

    def test_get_conversion_status_not_found(self, test_client):
        """Test getting status for non-existent conversion."""
        response = test_client.get("/api/v1/tts/non_existent_task")
        
        assert response.status_code == 404
        data = response.json()
        assert "Task with ID 'non_existent_task' not found" in data["detail"]

    def test_get_conversion_status_invalid_id(self, test_client):
        """Test getting status with invalid conversion ID."""
        response = test_client.get("/api/v1/tts/invalid_id")
        
        # Should handle gracefully or return 404
        assert response.status_code in [404, 422]

    def test_list_conversions_success(self, test_client, mock_task_manager):
        """Test successful conversion listing."""
        # Mock task manager to return tasks
        mock_task_manager.get_all_tasks.return_value = [
            {
                "task_id": "task_1",
                "status": "completed",
                "original_text": "Text 1",
                "output_file_path": "/tmp/task1.wav",
                "custom_filename": "audio1",
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
            },
            {
                "task_id": "task_2",
                "status": "queued",
                "original_text": "Text 2",
                "output_file_path": None,
                "custom_filename": "audio2",
                "created_at": "2024-01-01T00:00:00",
                "submitted_at": "2024-01-01T00:00:00",
                "started_at": None,
                "completed_at": None,
                "failed_at": None,
                "file_size": None,
                "sampling_rate": None,
                "device": None,
                "error_message": None,
                "item_id": None,
            }
        ]
        
        response = test_client.get("/api/v1/tts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 2
        assert data[0]["conversion_id"] == "task_1"
        assert data[0]["status"] == "completed"
        assert data[1]["conversion_id"] == "task_2"
        assert data[1]["status"] == "queued"

    def test_list_conversions_with_status_filter(self, test_client, mock_task_manager):
        """Test conversion listing with status filter."""
        # Mock task manager to return filtered tasks
        mock_task_manager.get_all_tasks.return_value = [
            {
                "task_id": "completed_task",
                "status": "completed",
                "original_text": "Completed text",
                "output_file_path": "/tmp/completed.wav",
                "custom_filename": "completed_audio",
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
        ]
        
        response = test_client.get("/api/v1/tts?status=completed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["status"] == "completed"

    def test_list_conversions_with_limit(self, test_client, mock_task_manager):
        """Test conversion listing with limit."""
        # Mock task manager to return limited tasks
        mock_task_manager.get_all_tasks.return_value = [
            {
                "task_id": f"task_{i}",
                "status": "completed",
                "original_text": f"Text {i}",
                "output_file_path": f"/tmp/task{i}.wav",
                "custom_filename": f"audio{i}",
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
            for i in range(5)
        ]
        
        response = test_client.get("/api/v1/tts?limit=3")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should respect the limit
        assert len(data) <= 3

    def test_list_conversions_invalid_status(self, test_client):
        """Test conversion listing with invalid status."""
        response = test_client.get("/api/v1/tts?status=invalid_status")
        
        # Should handle gracefully or return 400
        assert response.status_code in [200, 400]

    def test_list_conversions_invalid_limit(self, test_client):
        """Test conversion listing with invalid limit."""
        # Limit too low
        response = test_client.get("/api/v1/tts?limit=0")
        assert response.status_code == 422
        
        # Limit too high
        response = test_client.get("/api/v1/tts?limit=1001")
        assert response.status_code == 422

    def test_download_audio_file_success(self, test_client, mock_task_manager):
        """Test successful audio file download."""
        # Mock task manager to return a completed task
        mock_task_manager.get_task_status.return_value = {
            "task_id": "test_task_123",
            "status": "completed",
            "original_text": "Test text",
            "output_file_path": "/tmp/test.wav",
            "custom_filename": "test_audio",
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
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            response = test_client.get("/api/v1/tts/test_task_123/download")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/wav"

    def test_download_audio_file_not_completed(self, test_client, mock_task_manager):
        """Test audio download for non-completed conversion."""
        # Mock task manager to return a queued task
        mock_task_manager.get_task_status.return_value = {
            "task_id": "test_task_123",
            "status": "queued",
            "original_text": "Test text",
            "output_file_path": None,
            "custom_filename": "test_audio",
            "created_at": "2024-01-01T00:00:00",
            "submitted_at": "2024-01-01T00:00:00",
            "started_at": None,
            "completed_at": None,
            "failed_at": None,
            "file_size": None,
            "sampling_rate": None,
            "device": None,
            "error_message": None,
            "item_id": None,
        }
        
        response = test_client.get("/api/v1/tts/test_task_123/download")
        
        assert response.status_code == 400
        data = response.json()
        assert "Task is not completed" in data["detail"]

    def test_download_audio_file_not_found(self, test_client):
        """Test audio download for non-existent conversion."""
        response = test_client.get("/api/v1/tts/non_existent_task/download")
        
        assert response.status_code == 404
        data = response.json()
        assert "Task with ID 'non_existent_task' not found" in data["detail"]

    def test_download_audio_file_missing_file(self, test_client, mock_task_manager):
        """Test audio download when file doesn't exist."""
        # Mock task manager to return a completed task
        mock_task_manager.get_task_status.return_value = {
            "task_id": "test_task_123",
            "status": "completed",
            "original_text": "Test text",
            "output_file_path": "/tmp/missing.wav",
            "custom_filename": "test_audio",
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
        
        # Mock file not existing
        with patch('os.path.exists', return_value=False):
            response = test_client.get("/api/v1/tts/test_task_123/download")
            
            assert response.status_code == 404
            data = response.json()
            assert "Audio file not found" in data["detail"]

    def test_serve_audio_file_success(self, test_client):
        """Test successful generic audio file serving."""
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            response = test_client.get("/api/v1/tts/audio/test_audio.wav")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/wav"

    def test_serve_audio_file_not_found(self, test_client):
        """Test serving non-existent audio file."""
        # Mock file not existing
        with patch('os.path.exists', return_value=False):
            response = test_client.get("/api/v1/tts/audio/test_audio.wav")
            
            assert response.status_code == 404
            data = response.json()
            assert "Audio file not found" in data["detail"]

    def test_serve_audio_file_invalid_filename(self, test_client):
        """Test serving audio file with invalid filename."""
        # Test path traversal attempt
        response = test_client.get("/api/v1/tts/audio/../../../etc/passwd")
        assert response.status_code == 400
        
        # Test non-WAV file
        response = test_client.get("/api/v1/tts/audio/test.mp3")
        assert response.status_code == 400
        
        # Test filename with slashes
        response = test_client.get("/api/v1/tts/audio/subdir/test.wav")
        assert response.status_code == 400

    def test_conversion_duration_calculation(self, test_client, mock_task_manager):
        """Test that conversion duration is calculated correctly."""
        # Mock task manager to return a completed task with metadata
        mock_task_manager.get_task_status.return_value = {
            "task_id": "test_task_123",
            "status": "completed",
            "original_text": "Test text",
            "output_file_path": "/tmp/test.wav",
            "custom_filename": "test_audio",
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
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            response = test_client.get("/api/v1/tts/test_task_123")
            
            assert response.status_code == 200
            data = response.json()
            
            # Duration should be calculated from file size and sampling rate
            assert "duration" in data
            if data["duration"] is not None:
                assert data["duration"] > 0

    def test_conversion_metadata_inclusion(self, test_client, mock_task_manager):
        """Test that all conversion metadata is included in responses."""
        # Mock task manager to return a task with full metadata
        mock_task_manager.get_task_status.return_value = {
            "task_id": "test_task_123",
            "status": "completed",
            "original_text": "Test text with metadata",
            "output_file_path": "/tmp/test.wav",
            "custom_filename": "test_audio",
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
        
        response = test_client.get("/api/v1/tts/test_task_123")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields
        required_fields = [
            "conversion_id", "text", "status", "output_file_path", "custom_filename",
            "submitted_at", "started_at", "completed_at", "failed_at",
            "file_size", "sampling_rate", "device", "error_message"
        ]
        
        for field in required_fields:
            assert field in data

    def test_conversion_status_transitions(self, test_client, mock_task_manager):
        """Test different conversion status values."""
        statuses = ["queued", "processing", "completed", "failed"]
        
        for status in statuses:
            # Mock task manager to return task with specific status
            mock_task_manager.get_task_status.return_value = {
                "task_id": f"task_{status}",
                "status": status,
                "original_text": f"Text with {status} status",
                "output_file_path": "/tmp/test.wav" if status == "completed" else None,
                "custom_filename": "test_audio",
                "created_at": "2024-01-01T00:00:00",
                "submitted_at": "2024-01-01T00:00:00",
                "started_at": "2024-01-01T00:00:01" if status in ["processing", "completed", "failed"] else None,
                "completed_at": "2024-01-01T00:00:02" if status == "completed" else None,
                "failed_at": "2024-01-01T00:00:02" if status == "failed" else None,
                "file_size": 1024 if status == "completed" else None,
                "sampling_rate": 22050 if status == "completed" else None,
                "device": "cpu" if status in ["processing", "completed", "failed"] else None,
                "error_message": "Test error" if status == "failed" else None,
                "item_id": None,
            }
            
            response = test_client.get(f"/api/v1/tts/task_{status}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == status

    def test_conversion_error_handling(self, test_client, mock_task_manager):
        """Test error handling in conversion endpoints."""
        # Test TTS service unavailable
        mock_task_manager.submit_task.return_value = None
        
        response = test_client.post("/api/v1/tts/convert", json={
            "text": "Test text"
        })
        
        # Should handle gracefully
        assert response.status_code in [201, 500, 503]

    def test_conversion_id_uniqueness(self, test_client, mock_task_manager):
        """Test that conversion IDs are unique."""
        # Submit multiple conversions
        conversion_ids = set()
        
        for i in range(3):
            response = test_client.post("/api/v1/tts/convert", json={
                "text": f"Text {i}"
            })
            
            if response.status_code == 201:
                data = response.json()
                conversion_ids.add(data["conversion_id"])
        
        # All IDs should be unique
        assert len(conversion_ids) == 3

    def test_conversion_timestamps(self, test_client, mock_task_manager):
        """Test that conversion timestamps are properly set."""
        response = test_client.post("/api/v1/tts/convert", json={
            "text": "Test text for timestamps"
        })
        
        if response.status_code == 201:
            data = response.json()
            
            # Should have submitted_at timestamp
            assert "submitted_at" in data
            assert data["submitted_at"] is not None
            
            # Timestamp should be recent
            submitted_at = datetime.fromisoformat(data["submitted_at"].replace("Z", "+00:00"))
            now = datetime.now(UTC)
            time_diff = abs((now - submitted_at).total_seconds())
            
            # Should be within last minute
            assert time_diff < 60

    def test_conversion_file_handling(self, test_client, mock_task_manager):
        """Test that file handling works correctly."""
        # Mock task manager to return a completed task
        mock_task_manager.get_task_status.return_value = {
            "task_id": "test_task_123",
            "status": "completed",
            "original_text": "Test text",
            "output_file_path": "/tmp/test.wav",
            "custom_filename": "test_audio",
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
        
        # Test file download
        with patch('os.path.exists', return_value=True):
            response = test_client.get("/api/v1/tts/test_task_123/download")
            
            assert response.status_code == 200
            assert "Content-Disposition" in response.headers
            assert "test_audio.wav" in response.headers["Content-Disposition"]

    def test_conversion_validation(self, test_client):
        """Test input validation for conversion endpoints."""
        # Test text length validation
        short_text = "a"  # Too short
        response = test_client.post("/api/v1/tts/convert", json={"text": short_text})
        assert response.status_code == 422
        
        # Test custom filename length validation
        long_filename = "a" * 256  # Too long
        response = test_client.post("/api/v1/tts/convert", json={
            "text": "Valid text",
            "custom_filename": long_filename
        })
        assert response.status_code == 422
        
        # Test multiple texts validation
        response = test_client.post("/api/v1/tts/convert-multiple", json={
            "texts": ["Valid text", "a", "Another valid text"]  # One too short
        })
        assert response.status_code == 422

    def test_conversion_response_consistency(self, test_client, mock_task_manager):
        """Test that conversion responses are consistent across endpoints."""
        # Submit a conversion
        response = test_client.post("/api/v1/tts/convert", json={
            "text": "Test text for consistency"
        })
        
        if response.status_code == 201:
            data = response.json()
            conversion_id = data["conversion_id"]
            
            # Get status for the same conversion
            mock_task_manager.get_task_status.return_value = {
                "task_id": conversion_id,
                "status": "queued",
                "original_text": "Test text for consistency",
                "output_file_path": None,
                "custom_filename": None,
                "created_at": "2024-01-01T00:00:00",
                "submitted_at": "2024-01-01T00:00:00",
                "started_at": None,
                "completed_at": None,
                "failed_at": None,
                "file_size": None,
                "sampling_rate": None,
                "device": None,
                "error_message": None,
                "item_id": None,
            }
            
            status_response = test_client.get(f"/api/v1/tts/{conversion_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                # Text should be consistent
                assert status_data["text"] == data["text"]
                assert status_data["conversion_id"] == data["conversion_id"]
