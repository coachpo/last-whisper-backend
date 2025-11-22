"""Google Cloud Translation provider (v2)."""

import os
from typing import Tuple, Dict, Any

from google.cloud import translate_v2 as translate
from google.api_core.exceptions import GoogleAPIError

from app.core.config import settings
from app.core.logging import get_logger
from .base import TranslationProvider

logger = get_logger(__name__)


class GoogleTranslateProvider(TranslationProvider):
    def __init__(self):
        self._configure_credentials()
        self.client = translate.Client()

    def _configure_credentials(self):
        if getattr(settings, "google_application_credentials", None):
            os.environ.setdefault(
                "GOOGLE_APPLICATION_CREDENTIALS", settings.google_application_credentials
            )
            logger.info(
                "Translation: Using Google credentials from %s",
                settings.google_application_credentials,
            )
        else:
            if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                logger.info("Translation: Using GOOGLE_APPLICATION_CREDENTIALS from env")
            else:
                logger.warning(
                    "Translation: No Google credentials provided. Set GOOGLE_APPLICATION_CREDENTIALS or settings.google_application_credentials."
                )

    def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> Tuple[str, Dict[str, Any]]:
        try:
            response = self.client.translate(
                text,
                source_language=source_lang,
                target_language=target_lang,
                format_="text",
            )
            translated_text = response.get("translatedText")
            metadata = {
                "detected_source_language": response.get("detectedSourceLanguage"),
                "model": response.get("model"),
            }
            return translated_text, metadata
        except GoogleAPIError as exc:
            logger.error("Google Translate API error: %s", exc)
            raise
