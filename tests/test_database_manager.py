"""Tests for the DatabaseManager helpers."""

from app.core.config import settings
from app.models.database_manager import DatabaseManager


def test_database_manager_creates_sqlite_parent_dir(tmp_path, monkeypatch):
    db_file = tmp_path / "nested" / "dictation.db"
    db_url = f"sqlite:///{db_file}"
    audio_dir = tmp_path / "audio"
    monkeypatch.setattr(settings, "audio_dir", str(audio_dir))

    manager = DatabaseManager(database_url=db_url)

    try:
        assert db_file.parent.exists()
        assert db_file.exists()
    finally:
        manager.close()
