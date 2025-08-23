"""TTS service wrapper."""

from typing import Optional

from app.core.config import settings
from app.core.exceptions import TTSServiceException
from app.services.tts_fb_service import FBTTSService


class TTSServiceWrapper:
    """Wrapper for the TTS service that provides a clean interface."""

    def __init__(self):
        self._service: Optional[object] = None
        self._is_initialized = False

    def initialize(self):
        """Initialize the TTS service."""
        try:
            # Import here to avoid circular dependencies

            self._service = FBTTSService(device=settings.tts_device)
            self._service.start_service()
            self._is_initialized = True
        except Exception as e:
            raise TTSServiceException(f"Failed to initialize TTS service: {str(e)}")

    def shutdown(self):
        """Shutdown the TTS service."""
        if self._service:
            try:
                self._service.stop_service()
            except Exception:
                pass  # Ignore shutdown errors
            finally:
                self._service = None
                self._is_initialized = False

    def submit_request(self, text: str, custom_filename: Optional[str] = None) -> Optional[str]:
        """Submit a TTS request."""
        if not self._is_initialized or not self._service:
            raise TTSServiceException("TTS service not initialized")

        try:
            return self._service.submit_request(text, custom_filename)
        except Exception as e:
            raise TTSServiceException(f"Failed to submit TTS request: {str(e)}")

    def get_task_queue(self):
        """Get the task queue for monitoring."""
        if not self._is_initialized or not self._service:
            raise TTSServiceException("TTS service not initialized")

        return self._service.get_task_queue()

    @property
    def is_initialized(self) -> bool:
        """Check if the service is initialized."""
        return self._is_initialized


# Global TTS service instance
tts_service = TTSServiceWrapper()
