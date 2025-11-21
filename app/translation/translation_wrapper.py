"""Translation service wrapper for provider selection."""

from typing import Optional

from app.core.config import settings
from app.translation.providers.base import TranslationProvider


class TranslationServiceWrapper:
    """Selects and initializes the configured translation provider."""

    def __init__(self):
        self._provider: Optional[TranslationProvider] = None

    def initialize(self):
        provider = getattr(settings, "translation_provider", "google").lower()
        if provider == "google":
            from app.translation.providers.google_provider import GoogleTranslateProvider

            self._provider = GoogleTranslateProvider()
        else:
            raise ValueError(f"Unsupported translation provider: {provider}")

    @property
    def provider(self) -> TranslationProvider:
        if not self._provider:
            self.initialize()
        return self._provider
