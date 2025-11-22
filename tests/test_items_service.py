"""Tests for ItemsService TTS scheduling helpers."""

import pytest

from app.core.config import settings
from app.models.enums import ItemTTSStatus
from app.models.models import Item

SUPPORTED_TTS_LOCALE = settings.tts_supported_languages[0]


@pytest.fixture()
def immediate_scheduler(monkeypatch, items_service):
    original = items_service.audio_manager.schedule_generation

    def _immediate(self, item_id, text, locale):
        return self._submit_request(item_id, text, locale)

    bound = _immediate.__get__(
        items_service.audio_manager, type(items_service.audio_manager)
    )
    monkeypatch.setattr(items_service.audio_manager, "schedule_generation", bound)
    return original


def test_create_item_submits_tts_with_locale(
    items_service, task_manager, immediate_scheduler
):
    payload = items_service.create_item(
        locale=SUPPORTED_TTS_LOCALE, text="hello world example text"
    )

    assert payload["tts_status"] == ItemTTSStatus.PENDING
    assert len(task_manager.submissions) == 1

    submission_args, _ = task_manager.submissions[0]
    assert submission_args[3] == SUPPORTED_TTS_LOCALE
    assert payload["difficulty"] is not None


def test_bulk_create_marks_failed_when_submission_missing(
    items_service, task_manager, db_manager, immediate_scheduler, monkeypatch
):
    monkeypatch.setattr(
        task_manager,
        "submit_task_for_item",
        lambda *args, **kwargs: None,
    )

    result = items_service.bulk_create_items(
        [
            {"locale": SUPPORTED_TTS_LOCALE, "text": "Hei maailma"},
            {"locale": SUPPORTED_TTS_LOCALE, "text": "Hello world"},
        ]
    )

    assert len(result["created_items"]) == 2

    with db_manager.get_session() as session:
        statuses = {item.tts_record.status for item in session.query(Item).all()}
        assert statuses == {ItemTTSStatus.FAILED}
