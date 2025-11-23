"""Tests for task-message upsert logic in TTSEngineManager._update_task_from_message."""

from datetime import datetime

from app.models.database_manager import Base
from app.models.enums import TaskStatus
from app.models.models import Task
from app.tts_engine.tts_engine_manager import TTSEngineManager


def _reset_schema(db_manager):
    Base.metadata.drop_all(bind=db_manager.engine)
    Base.metadata.create_all(bind=db_manager.engine)


def test_inserts_missing_task_from_message(test_db_url):
    manager = TTSEngineManager(test_db_url, tts_service=None)
    _reset_schema(manager.db_manager)

    message = {
        "request_id": "task-123",
        "status": TaskStatus.COMPLETED,
        "output_file_path": "/tmp/audio.wav",
        "metadata": {
            "text": "hello world",
            "completed_at": datetime.now().isoformat(),
            "file_size": 321,
            "sampling_rate": 24000,
            "device": "test-device",
        },
    }

    manager._update_task_from_message(message)

    with manager.db_manager.get_session() as session:
        task = session.query(Task).filter(Task.task_id == "task-123").first()

        assert task is not None
        assert task.status == TaskStatus.COMPLETED
        assert task.output_file_path == "/tmp/audio.wav"
        assert task.file_size == 321
        assert task.sampling_rate == 24000
        assert task.device == "test-device"


def test_updates_existing_task_from_message(test_db_url):
    manager = TTSEngineManager(test_db_url, tts_service=None)
    _reset_schema(manager.db_manager)

    # Seed a queued task
    with manager.db_manager.get_session() as session:
        seeded = Task(
            task_id="task-queued",
            original_text="hello",
            text_hash="hash",
            status=TaskStatus.QUEUED,
            created_at=datetime.now(),
            submitted_at=datetime.now(),
        )
        session.add(seeded)
        session.commit()

    message = {
        "request_id": "task-queued",
        "status": TaskStatus.FAILED,
        "output_file_path": None,
        "metadata": {
            "text": "hello",
            "failed_at": datetime.now().isoformat(),
            "error": "boom",
            "device": "test-device",
        },
    }

    manager._update_task_from_message(message)

    with manager.db_manager.get_session() as session:
        task = session.query(Task).filter(Task.task_id == "task-queued").first()

        assert task is not None
        assert task.status == TaskStatus.FAILED
        assert task.error_message == "boom"
        assert task.device == "test-device"
