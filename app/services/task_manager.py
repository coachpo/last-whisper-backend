"""Task manager service wrapper."""

from typing import Optional

from app.core.exceptions import TTSServiceException
from app.services.outer.tts_service import tts_service
from app.services.outer.tts_task_manager import TTSTaskManager


class TaskManagerWrapper:
    """Wrapper for the task manager that provides a clean interface."""

    def __init__(self):
        self._manager: Optional[object] = None
        self._is_initialized = False

    def initialize(self):
        """Initialize the task manager."""
        try:
            # Import here to avoid circular dependencies

            if not tts_service.is_initialized:
                raise TTSServiceException("TTS service must be initialized first")

            self._manager = TTSTaskManager(tts_service=tts_service._service)
            self._manager.start_monitoring()
            self._is_initialized = True
        except Exception as e:
            raise TTSServiceException(f"Failed to initialize task manager: {str(e)}")

    def shutdown(self):
        """Shutdown the task manager."""
        if self._manager:
            try:
                self._manager.stop_monitoring()
            except Exception:
                pass  # Ignore shutdown errors
            finally:
                self._manager = None
                self._is_initialized = False

    def submit_task(self, text: str, custom_filename: Optional[str] = None) -> Optional[str]:
        """Submit a task for processing."""
        if not self._is_initialized or not self._manager:
            raise TTSServiceException("Task manager not initialized")

        try:
            return self._manager.submit_task(text, custom_filename)
        except Exception as e:
            raise TTSServiceException(f"Failed to submit task: {str(e)}")

    def submit_multiple_tasks(self, texts: list[str]) -> list[str]:
        """Submit multiple tasks for processing."""
        if not self._is_initialized or not self._manager:
            raise TTSServiceException("Task manager not initialized")

        try:
            task_ids = []
            for text in texts:
                task_id = self._manager.submit_task(text)
                if task_id:
                    task_ids.append(task_id)
            return task_ids
        except Exception as e:
            raise TTSServiceException(f"Failed to submit multiple tasks: {str(e)}")

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get task status."""
        if not self._is_initialized or not self._manager:
            raise TTSServiceException("Task manager not initialized")

        try:
            return self._manager.get_task_status(task_id)
        except Exception as e:
            raise TTSServiceException(f"Failed to get task status: {str(e)}")

    @property
    def is_initialized(self) -> bool:
        """Check if the manager is initialized."""
        return self._is_initialized


# Global task manager instance
task_manager = TaskManagerWrapper()
