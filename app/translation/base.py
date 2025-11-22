"""Translation provider interface."""

from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any


class TranslationProvider(ABC):
    """Abstract translation provider."""

    @abstractmethod
    def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Translate text and return translated string plus metadata."""
        raise NotImplementedError
