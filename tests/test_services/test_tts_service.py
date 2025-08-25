"""Tests for TTSServiceWrapper."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.outer.tts_service import TTSServiceWrapper
from app.core.exceptions import TTSServiceException


class TestTTSServiceWrapper:
    """Test cases for TTSServiceWrapper."""

    def test_init(self):
        """Test service initialization."""
        service = TTSServiceWrapper()
        assert service._service is None
        assert service._is_initialized is False

    @patch('app.services.outer.tts_service.FBTTSService')
    def test_initialize_success(self, mock_fb_tts):
        """Test successful service initialization."""
        mock_service = Mock()
        mock_fb_tts.return_value = mock_service
        
        service = TTSServiceWrapper()
        service.initialize()
        
        assert service._is_initialized is True
        assert service._service == mock_service
        mock_service.start_service.assert_called_once()

    @patch('app.services.outer.tts_service.FBTTSService')
    def test_initialize_failure(self, mock_fb_tts):
        """Test service initialization failure."""
        mock_fb_tts.side_effect = Exception("Model loading failed")
        
        service = TTSServiceWrapper()
        
        with pytest.raises(TTSServiceException) as exc_info:
            service.initialize()
        
        assert "Failed to initialize TTS service" in str(exc_info.value)
        assert service._is_initialized is False

    def test_shutdown_with_service(self):
        """Test service shutdown with active service."""
        mock_service = Mock()
        service = TTSServiceWrapper()
        service._service = mock_service
        service._is_initialized = True
        
        service.shutdown()
        
        mock_service.stop_service.assert_called_once()
        assert service._service is None
        assert service._is_initialized is False

    def test_shutdown_without_service(self):
        """Test service shutdown without active service."""
        service = TTSServiceWrapper()
        service._service = None
        service._is_initialized = False
        
        # Should not raise any exceptions
        service.shutdown()
        
        assert service._service is None
        assert service._is_initialized is False

    def test_shutdown_ignores_errors(self):
        """Test that shutdown ignores service errors."""
        mock_service = Mock()
        mock_service.stop_service.side_effect = Exception("Service error")
        
        service = TTSServiceWrapper()
        service._service = mock_service
        service._is_initialized = True
        
        # Should not raise exceptions
        service.shutdown()
        
        assert service._service is None
        assert service._is_initialized is False

    def test_submit_request_success(self):
        """Test successful request submission."""
        mock_service = Mock()
        mock_service.submit_request.return_value = "task_123"
        
        service = TTSServiceWrapper()
        service._service = mock_service
        service._is_initialized = True
        
        result = service.submit_request("Test text", "custom_name")
        
        assert result == "task_123"
        mock_service.submit_request.assert_called_once_with("Test text", "custom_name")

    def test_submit_request_not_initialized(self):
        """Test request submission when service not initialized."""
        service = TTSServiceWrapper()
        service._is_initialized = False
        
        with pytest.raises(TTSServiceException) as exc_info:
            service.submit_request("Test text")
        
        assert "TTS service not initialized" in str(exc_info.value)

    def test_submit_request_service_error(self):
        """Test request submission when service raises error."""
        mock_service = Mock()
        mock_service.submit_request.side_effect = Exception("Service error")
        
        service = TTSServiceWrapper()
        service._service = mock_service
        service._is_initialized = True
        
        with pytest.raises(TTSServiceException) as exc_info:
            service.submit_request("Test text")
        
        assert "Failed to submit TTS request" in str(exc_info.value)

    def test_get_task_queue_success(self):
        """Test successful task queue retrieval."""
        mock_queue = Mock()
        mock_service = Mock()
        mock_service.get_task_queue.return_value = mock_queue
        
        service = TTSServiceWrapper()
        service._service = mock_service
        service._is_initialized = True
        
        result = service.get_task_queue()
        
        assert result == mock_queue
        mock_service.get_task_queue.assert_called_once()

    def test_get_task_queue_not_initialized(self):
        """Test task queue retrieval when service not initialized."""
        service = TTSServiceWrapper()
        service._is_initialized = False
        
        with pytest.raises(TTSServiceException) as exc_info:
            service.get_task_queue()
        
        assert "TTS service not initialized" in str(exc_info.value)

    def test_is_initialized_property(self):
        """Test the is_initialized property."""
        service = TTSServiceWrapper()
        assert service.is_initialized is False
        
        service._is_initialized = True
        assert service.is_initialized is True
        
        service._is_initialized = False
        assert service.is_initialized is False

    def test_context_manager_behavior(self):
        """Test service behaves correctly in context manager scenarios."""
        service = TTSServiceWrapper()
        
        # Initial state
        assert not service.is_initialized
        
        # After initialization
        with patch('app.services.outer.tts_service.FBTTSService') as mock_fb_tts:
            mock_service = Mock()
            mock_fb_tts.return_value = mock_service
            
            service.initialize()
            assert service.is_initialized
        
        # After shutdown
        service.shutdown()
        assert not service.is_initialized
