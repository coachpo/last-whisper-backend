"""Tests for TTS service wrapper."""
from unittest.mock import Mock, patch

import pytest
from app.services.tts_service import TTSServiceWrapper

from app.core.exceptions import TTSServiceException


class TestTTSServiceWrapper:
    """Test TTS service wrapper."""

    def test_initialization_success(self):
        """Test successful service initialization."""
        service = TTSServiceWrapper()

        with patch('app.services.tts_service.FBTTSService') as mock_service_class:
            mock_service_instance = Mock()
            mock_service_class.return_value = mock_service_instance

            service.initialize()

            assert service.is_initialized
            mock_service_class.assert_called_once_with(device=None)
            mock_service_instance.start_service.assert_called_once()

    def test_initialization_failure(self):
        """Test failed service initialization."""
        service = TTSServiceWrapper()

        with patch('app.services.tts_service.FBTTSService') as mock_service_class:
            mock_service_class.side_effect = Exception("Initialization failed")

            with pytest.raises(TTSServiceException):
                service.initialize()

            assert not service.is_initialized

    def test_submit_request_success(self):
        """Test successful request submission."""
        service = TTSServiceWrapper()

        with patch('app.services.tts_service.FBTTSService') as mock_service_class:
            mock_service_instance = Mock()
            mock_service_instance.submit_request.return_value = "task_123"
            mock_service_class.return_value = mock_service_instance

            service.initialize()
            result = service.submit_request("Hello world", "test_file")

            assert result == "task_123"
            mock_service_instance.submit_request.assert_called_once_with("Hello world", "test_file")

    def test_submit_request_not_initialized(self):
        """Test request submission when service not initialized."""
        service = TTSServiceWrapper()

        with pytest.raises(TTSServiceException, match="not initialized"):
            service.submit_request("Hello world")

    def test_shutdown(self):
        """Test service shutdown."""
        service = TTSServiceWrapper()

        with patch('app.services.tts_service.FBTTSService') as mock_service_class:
            mock_service_instance = Mock()
            mock_service_class.return_value = mock_service_instance

            service.initialize()
            service.shutdown()

            assert not service.is_initialized
            mock_service_instance.stop_service.assert_called_once()
