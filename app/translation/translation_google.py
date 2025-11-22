"""Google Cloud Translation provider (v2)."""

from typing import Tuple, Dict, Any

from google.api_core.exceptions import GoogleAPIError
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account

from app.core.config import settings
from app.core.logging import get_logger
from .base import TranslationProvider

logger = get_logger(__name__)


class GoogleTranslateProvider(TranslationProvider):
    def __init__(self):
        logger.info("Translation: initializing Google Translate client")
        self.client = self._build_client()
        logger.info("Translation: Google Translate client ready")

    def _build_client(self) -> translate.Client:
        credentials_path = settings.google_application_credentials
        if not credentials_path:
            raise RuntimeError(
                "Translation: google_application_credentials must be configured via app.core.config settings."
            )

        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        logger.info("Translation: using Google credentials from %s", credentials_path)
        return translate.Client(credentials=credentials)

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
            logger.error(
                "Translation: Google API error",
                exc_info=exc,
            )
            raise
