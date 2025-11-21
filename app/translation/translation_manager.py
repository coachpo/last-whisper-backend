"""Manage item-bound translations with caching and refresh."""

import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.logging import get_logger
from app.models.database_manager import DatabaseManager
from app.models.models import Item, Translation
from app.models.enums import TaskStatus
from app.translation.translation_wrapper import TranslationServiceWrapper

logger = get_logger(__name__)


class TranslationManager:
    def __init__(self, db_url: str = settings.database_url, provider_wrapper=None):
        self.db_manager = DatabaseManager(db_url)
        self.provider_wrapper = provider_wrapper or TranslationServiceWrapper()

    @staticmethod
    def _text_hash(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _get_item(self, session, item_id: int) -> Optional[Item]:
        return session.query(Item).filter(Item.id == item_id).first()

    def translate_item(
        self, item_id: int, target_lang: str, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        if target_lang not in settings.translation_supported_languages:
            logger.error("Unsupported translation target_lang: %s", target_lang)
            return None

        with self.db_manager.get_session() as session:
            item = self._get_item(session, item_id)
            if not item:
                return None

            source_lang = item.locale
            text_hash = self._text_hash(item.text)

            translation = (
                session.query(Translation)
                .filter(
                    Translation.item_id == item.id,
                    Translation.target_lang == target_lang,
                )
                .first()
            )

            cached = False

            if translation and not force_refresh:
                # Cache hit
                cached = True
            else:
                # Fetch from provider
                provider = self.provider_wrapper.provider
                translated_text, metadata = provider.translate(
                    item.text, source_lang, target_lang
                )

                if not translation:
                    translation = Translation(
                        item_id=item.id,
                        target_lang=target_lang,
                        source_lang=source_lang,
                        text_hash=text_hash,
                        translated_text=translated_text,
                        provider=getattr(settings, "translation_provider", "google"),
                        status=TaskStatus.COMPLETED,
                        error=None,
                        translation_metadata=json.dumps(metadata) if metadata else None,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        last_refreshed_at=datetime.now(),
                    )
                    session.add(translation)
                else:
                    translation.translated_text = translated_text
                    translation.text_hash = text_hash
                    translation.source_lang = source_lang
                    translation.provider = getattr(
                        settings, "translation_provider", "google"
                    )
                    translation.status = TaskStatus.COMPLETED
                    translation.error = None
                    translation.translation_metadata = (
                        json.dumps(metadata) if metadata else None
                    )
                    translation.updated_at = datetime.now()
                    translation.last_refreshed_at = datetime.now()

                session.commit()

            return {
                "translation_id": translation.id,
                "item_id": translation.item_id,
                "text": item.text,
                "source_lang": translation.source_lang,
                "target_lang": translation.target_lang,
                "translated_text": translation.translated_text,
                "provider": translation.provider,
                "cached": cached,
                "status": translation.status,
                "created_at": translation.created_at,
                "updated_at": translation.updated_at,
                "last_refreshed_at": translation.last_refreshed_at,
                "metadata": translation.metadata_dict,
            }

    def get_cached_translation(
        self, item_id: int, target_lang: str
    ) -> Optional[Dict[str, Any]]:
        with self.db_manager.get_session() as session:
            translation = (
                session.query(Translation)
                .filter(
                    Translation.item_id == item_id,
                    Translation.target_lang == target_lang,
                )
                .first()
            )
            if not translation:
                return None

            item = self._get_item(session, item_id)
            if not item:
                return None

            return {
                "translation_id": translation.id,
                "item_id": translation.item_id,
                "text": item.text,
                "source_lang": translation.source_lang,
                "target_lang": translation.target_lang,
                "translated_text": translation.translated_text,
                "provider": translation.provider,
                "cached": True,
                "status": translation.status,
                "created_at": translation.created_at,
                "updated_at": translation.updated_at,
                "last_refreshed_at": translation.last_refreshed_at,
                "metadata": translation.metadata_dict,
            }

    def refresh_translation(self, translation_id: int) -> Optional[Dict[str, Any]]:
        with self.db_manager.get_session() as session:
            translation = (
                session.query(Translation)
                .filter(Translation.id == translation_id)
                .first()
            )
            if not translation:
                return None

            item = self._get_item(session, translation.item_id)
            if not item:
                return None

            provider = self.provider_wrapper.provider
            translated_text, metadata = provider.translate(
                item.text, translation.source_lang, translation.target_lang
            )

            translation.translated_text = translated_text
            translation.text_hash = self._text_hash(item.text)
            translation.status = TaskStatus.COMPLETED
            translation.error = None
            translation.translation_metadata = json.dumps(metadata) if metadata else None
            translation.updated_at = datetime.now()
            translation.last_refreshed_at = datetime.now()

            session.commit()

            return {
                "translation_id": translation.id,
                "item_id": translation.item_id,
                "text": item.text,
                "source_lang": translation.source_lang,
                "target_lang": translation.target_lang,
                "translated_text": translation.translated_text,
                "provider": translation.provider,
                "cached": False,
                "status": translation.status,
                "created_at": translation.created_at,
                "updated_at": translation.updated_at,
                "last_refreshed_at": translation.last_refreshed_at,
                "metadata": translation.metadata_dict,
            }
