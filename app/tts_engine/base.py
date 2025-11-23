"""Abstract base class for TTS engines."""

from abc import ABC, abstractmethod
from queue import Queue
from typing import Any, Dict, Optional


class BaseTTSEngine(ABC):
    """Defines the contract implemented by every concrete TTS engine."""

    @abstractmethod
    def start_service(self) -> None:
        """Start any background workers or remote connections needed by the engine."""
        raise NotImplementedError

    @abstractmethod
    def stop_service(self) -> None:
        """Stop running workers and release resources."""
        raise NotImplementedError

    @abstractmethod
    def submit_request(
        self,
        text: str,
        custom_filename: Optional[str] = None,
        language: str = "fi",
        task_kind: str = "generate",
    ) -> Optional[str]:
        """Submit a TTS request and return a task identifier if queued successfully."""
        raise NotImplementedError

    @abstractmethod
    def get_task_message_queue(self) -> Queue:
        """Expose the queue that surfaces task state updates to callers."""
        raise NotImplementedError

    @abstractmethod
    def get_queue_size(self) -> int:
        """Return the number of pending synthesis requests."""
        raise NotImplementedError

    @abstractmethod
    def get_task_message_queue_size(self) -> int:
        """Return the number of pending task messages."""
        raise NotImplementedError

    @abstractmethod
    def get_device_info(self) -> Dict[str, Any]:
        """Provide metadata about the device or backend backing the engine."""
        raise NotImplementedError

    @abstractmethod
    def switch_device(self, new_device: str) -> bool:
        """Attempt to switch to a different output device if supported."""
        raise NotImplementedError
