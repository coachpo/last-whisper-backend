"""Tests for ItemsService TTS scheduling helpers."""

import pytest

from app.models.enums import ItemTTSStatus
from app.models.models import Item
from app.services.items_service import ItemsService


class ImmediateExecutor:
    def __init__(self):
        self.calls = []

    def submit(self, fn, *args, **kwargs):
        self.calls.append((fn, args, kwargs))
        return fn(*args, **kwargs)


@pytest.fixture()
def immediate_executor(monkeypatch):
    executor = ImmediateExecutor()
    monkeypatch.setattr(ItemsService, "_tts_executor", executor)
    monkeypatch.setattr(
        ItemsService,
        "_get_executor",
        classmethod(lambda cls: executor),
    )
    return executor


def test_create_item_submits_tts_with_locale(
    items_service, task_manager, immediate_executor
):
    payload = items_service.create_item(locale="en-US", text="hello world example text")

    assert payload["tts_status"] == ItemTTSStatus.PENDING
    assert len(task_manager.submissions) == 1

    submission_args, _ = task_manager.submissions[0]
    assert submission_args[3] == "en-US"
    assert payload["difficulty"] is not None


def test_bulk_create_marks_failed_when_submission_missing(
    items_service, task_manager, db_manager, immediate_executor, monkeypatch
):
    monkeypatch.setattr(
        task_manager,
        "submit_task_for_item",
        lambda *args, **kwargs: None,
    )

    result = items_service.bulk_create_items(
        [
            {"locale": "fi", "text": "Hei maailma"},
            {"locale": "sv", "text": "Hej världen"},
        ]
    )

    assert len(result["created_items"]) == 2

    with db_manager.get_session() as session:
        statuses = {item.tts_record.status for item in session.query(Item).all()}
        assert statuses == {ItemTTSStatus.FAILED}
