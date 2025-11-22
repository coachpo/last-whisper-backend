"""Lightweight runtime state helpers for metadata and diagnostics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


_app_started_at: datetime = datetime.now(timezone.utc)


def set_app_started_at(value: Optional[datetime] = None) -> None:
    """Persist the moment the API finished bootstrapping."""

    global _app_started_at
    _app_started_at = value or datetime.now(timezone.utc)


def get_app_started_at() -> datetime:
    """Return the stored startup timestamp."""

    return _app_started_at


def get_uptime_seconds(now: Optional[datetime] = None) -> float:
    """Calculate process uptime in seconds."""

    current_time = now or datetime.now(timezone.utc)
    delta = current_time - _app_started_at
    return max(delta.total_seconds(), 0.0)
