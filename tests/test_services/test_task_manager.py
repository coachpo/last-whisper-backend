"""Tests for task manager wrapper."""
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions import TTSServiceException
from app.services.task_manager import TaskManagerWrapper


class TestTaskManagerWrapper:
    """Test task manager wrapper."""

    def test_initialization_success(self):
        """Test successful task manager initialization."""
        manager = TaskManagerWrapper()

        with patch('app.services.task_manager.tts_service') as mock_tts_service:
            mock_tts_service.is_initialized = True
            mock_tts_service._service = Mock()

            with patch('app.services.task_manager.TTSTaskManager') as mock_manager_class:
                mock_manager_instance = Mock()
                mock_manager_class.return_value = mock_manager_instance

                manager.initialize()

                assert manager.is_initialized
                mock_manager_class.assert_called_once_with(tts_service=mock_tts_service._service)
                mock_manager_instance.start_monitoring.assert_called_once()

    def test_initialization_tts_not_ready(self):
        """Test initialization when TTS service not ready."""
        manager = TaskManagerWrapper()

        with patch('app.services.task_manager.tts_service') as mock_tts_service:
            mock_tts_service.is_initialized = False

            with pytest.raises(TTSServiceException, match="TTS service must be initialized first"):
                manager.initialize()

            assert not manager.is_initialized

    def test_submit_task_success(self):
        """Test successful task submission."""
        manager = TaskManagerWrapper()

        with patch('app.services.task_manager.tts_service') as mock_tts_service:
            mock_tts_service.is_initialized = True
            mock_tts_service._service = Mock()

            with patch('app.services.task_manager.TTSTaskManager') as mock_manager_class:
                mock_manager_instance = Mock()
                mock_manager_instance.submit_task.return_value = "task_123"
                mock_manager_class.return_value = mock_manager_instance

                manager.initialize()
                result = manager.submit_task("Hello world", "test_file")

                assert result == "task_123"
                mock_manager_instance.submit_task.assert_called_once_with("Hello world", "test_file")

    def test_submit_task_not_initialized(self):
        """Test task submission when manager not initialized."""
        manager = TaskManagerWrapper()

        with pytest.raises(TTSServiceException, match="not initialized"):
            manager.submit_task("Hello world")

    def test_shutdown(self):
        """Test manager shutdown."""
        manager = TaskManagerWrapper()

        with patch('app.services.task_manager.tts_service') as mock_tts_service:
            mock_tts_service.is_initialized = True
            mock_tts_service._service = Mock()

            with patch('app.services.task_manager.TTSTaskManager') as mock_manager_class:
                mock_manager_instance = Mock()
                mock_manager_class.return_value = mock_manager_instance

                manager.initialize()
                manager.shutdown()

                assert not manager.is_initialized
                mock_manager_instance.stop_monitoring.assert_called_once()
