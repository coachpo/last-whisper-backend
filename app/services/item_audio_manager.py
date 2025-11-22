"""Background coordination for item audio generation."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Lock
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.logging import get_logger
from app.models.database_manager import DatabaseManager
from app.models.enums import ItemTTSStatus, TaskStatus
from app.models.models import Item, ItemTTS
from app.services.exceptions import NotFoundError, ServiceError

logger = get_logger(__name__)


class ItemAudioManager:
    """Encapsulates TTS submission and ItemTTS bookkeeping."""

    def __init__(self, db_manager: DatabaseManager, task_manager=None):
        self.db_manager = db_manager
        self.task_manager = task_manager
        self._executor = ThreadPoolExecutor(
            max_workers=settings.tts_submission_workers,
            thread_name_prefix="tts-submitter",
        )
        self._shutdown_lock = Lock()
        self._is_shutdown = False

    def schedule_generation(
        self, item_id: int, text: str, locale: Optional[str]
    ) -> None:
        """Queue a TTS submission for later processing."""

        if not self.task_manager:
            logger.warning("Cannot schedule TTS without task manager")
            return

        self._executor.submit(self._submit_request, item_id, text, locale)

    def _submit_request(self, item_id: int, text: str, locale: Optional[str]):
        language = locale or settings.tts_supported_languages[0]
        try:
            task_id = self.task_manager.submit_task_for_item(
                item_id, text, f"item_{item_id}", language
            )
            if not task_id:
                logger.warning("Task submission failed for item %s", item_id)
                self._mark_tts_failed(item_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error submitting TTS for item %s: %s", item_id, exc)
            self._mark_tts_failed(item_id)

    def _mark_tts_failed(self, item_id: int):
        try:
            with self.db_manager.get_session() as session:
                tts = (
                    session.query(ItemTTS)
                    .filter(ItemTTS.item_id == item_id)
                    .first()
                )
                if tts:
                    tts.status = ItemTTSStatus.FAILED
                    tts.updated_at = datetime.now()
                    session.commit()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to flag TTS failure for item %s: %s", item_id, exc)

    def refresh_item_audio(self, item_id: int) -> Dict[str, Any]:
        """Force TTS regeneration and update item state."""

        if not self.task_manager:
            raise ServiceError("TTS task manager unavailable", status_code=503)

        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                raise NotFoundError(f"Item {item_id} not found")

            language = item.locale or settings.tts_supported_languages[0]
            task_id = self.task_manager.submit_task_for_item(
                item.id, item.text, f"item_{item.id}", language, force_refresh=True
            )
            if not task_id:
                raise ServiceError("Unable to enqueue audio refresh", status_code=502)

            tts = (
                session.query(ItemTTS)
                .filter(ItemTTS.item_id == item.id)
                .first()
            )
            if not tts:
                tts = ItemTTS(
                    item_id=item.id,
                    status=ItemTTSStatus.PENDING,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                session.add(tts)

            tts.status = ItemTTSStatus.PENDING
            tts.updated_at = datetime.now()
            session.commit()
            response = {
                "item_id": item.id,
                "task_id": task_id,
                "status": TaskStatus.QUEUED,
                "tts_status": tts.status,
                "audio_path": os.path.join(
                    settings.audio_dir, f"item_{item.id}.wav"
                ),
                "provider": getattr(settings, "tts_provider", "google"),
                "voice": None,
                "cached": False,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "metadata": None,
            }

        return response

    def shutdown(self):
        with self._shutdown_lock:
            if self._is_shutdown:
                return
            self._executor.shutdown(wait=False)
            self._is_shutdown = True

    def __del__(self):  # pragma: no cover - best-effort cleanup
        self.shutdown()
