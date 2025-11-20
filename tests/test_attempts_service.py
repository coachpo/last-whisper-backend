"""Tests for AttemptsService scoring and filtering behavior."""

from datetime import datetime, timedelta, timezone

import app.services.attempts_service as attempts_module
from app.models.models import Attempt, Item


def _naive_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _create_item(db_manager, *, locale="en-US", text="hello world", difficulty=1) -> Item:
    with db_manager.get_session() as session:
        item = Item(locale=locale, text=text, difficulty=difficulty)
        session.add(item)
        session.commit()
        session.refresh(item)
        return item


def test_create_attempt_normalizes_text(db_manager, attempts_service, monkeypatch):
    """Ensure scoring ignores accents/punctuation and persists attempts."""

    monkeypatch.setattr(attempts_module, "HAS_JIWER", False)
    item = _create_item(db_manager, text="Café, world!")

    attempt = attempts_service.create_attempt(item.id, "Cafe world")

    assert attempt is not None
    assert attempt.item_id == item.id
    assert attempt.words_ref == 2
    assert attempt.words_correct == 2
    assert attempt.percentage == 100


def test_create_attempt_returns_none_when_item_missing(attempts_service):
    """Missing source items should short-circuit and return None."""

    result = attempts_service.create_attempt(item_id=9999, user_text="anything")

    assert result is None


def test_list_attempts_filters_by_item_and_since(
    db_manager, attempts_service, monkeypatch
):
    """Verify list_attempts honors item filter, since window, and pagination metadata."""

    monkeypatch.setattr(attempts_module, "HAS_JIWER", False)
    item_a = _create_item(db_manager, text="alpha beta")
    item_b = _create_item(db_manager, text="gamma delta")

    first_attempt = attempts_service.create_attempt(item_a.id, "alpha beta")
    attempts_service.create_attempt(item_a.id, "alpha beta alpha")
    attempts_service.create_attempt(item_b.id, "gamma delta")

    cutoff = _naive_utc_now() - timedelta(hours=1)
    with db_manager.get_session() as session:
        attempt_model = session.get(Attempt, first_attempt.id)
        attempt_model.created_at = cutoff - timedelta(days=1)
        session.commit()

    result = attempts_service.list_attempts(
        item_id=item_a.id, since=cutoff, page=1, per_page=5
    )

    assert result["total"] == 1
    assert result["total_pages"] == 1
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["item_id"] == item_a.id
    assert result["attempts"][0]["created_at"] is not None
