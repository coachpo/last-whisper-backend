"""Unit tests for StatsService aggregations."""

from datetime import datetime, timedelta, timezone

from app.models.models import Attempt, Item


def _naive_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _create_item(db_manager, *, locale="en-US", text="hello", tags=None) -> Item:
    with db_manager.get_session() as session:
        item = Item(locale=locale, text=text, difficulty=1)
        if tags is not None:
            item.tags = tags
        session.add(item)
        session.commit()
        session.refresh(item)
        return item


def _create_attempt(
    db_manager,
    *,
    item_id: int,
    percentage: int,
    wer: float,
    created_at: datetime | None = None,
    text: str = "attempt",
):
    with db_manager.get_session() as session:
        attempt = Attempt(
            item_id=item_id,
            text=text,
            percentage=percentage,
            wer=wer,
            words_ref=4,
            words_correct=max(0, min(4, round(percentage / 25))),
            created_at=created_at or _naive_utc_now(),
        )
        session.add(attempt)
        session.commit()


def test_get_summary_stats_returns_zero_when_no_attempts(stats_service):
    summary = stats_service.get_summary_stats()

    assert summary == {
        "total_attempts": 0,
        "unique_items_practiced": 0,
        "average_score": 0.0,
        "best_score": 0,
        "worst_score": 0,
        "total_practice_time_minutes": 0,
    }


def test_get_summary_stats_calculates_values(stats_service, db_manager):
    item = _create_item(db_manager, text="Alpha")
    _create_attempt(db_manager, item_id=item.id, percentage=80, wer=0.1)
    _create_attempt(db_manager, item_id=item.id, percentage=60, wer=0.4)

    summary = stats_service.get_summary_stats()

    assert summary["total_attempts"] == 2
    assert summary["unique_items_practiced"] == 1
    assert summary["average_score"] == 70.0
    assert summary["best_score"] == 80
    assert summary["worst_score"] == 60
    assert summary["total_practice_time_minutes"] == 1.0


def test_get_practice_log_returns_paginated_entries(stats_service, db_manager):
    now = _naive_utc_now()
    newer_item = _create_item(db_manager, text="New", tags=["focus"])
    older_item = _create_item(db_manager, text="Old", tags=["review"])
    _create_attempt(
        db_manager,
        item_id=older_item.id,
        percentage=55,
        wer=0.45,
        created_at=now - timedelta(days=2),
    )
    _create_attempt(
        db_manager,
        item_id=newer_item.id,
        percentage=92,
        wer=0.08,
        created_at=now - timedelta(minutes=5),
    )

    result = stats_service.get_practice_log(page=1, per_page=1)

    assert result["total"] == 2
    assert result["total_pages"] == 2
    assert len(result["practice_log"]) == 1
    entry = result["practice_log"][0]
    assert entry["item_id"] == newer_item.id
    assert entry["attempt_count"] == 1
    assert entry["tags"] == ["focus"]
    assert entry["best_score"] == 92


def test_get_item_stats_returns_none_when_item_missing(stats_service):
    assert stats_service.get_item_stats(item_id=123456) is None
