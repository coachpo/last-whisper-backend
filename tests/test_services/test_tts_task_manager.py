"""Tests for TTSTaskManager."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC, timedelta

from app.services.outer.tts_task_manager import TTSTaskManager
from app.models.database import Task, Item


class TestTTSTaskManager:
    """Test cases for TTSTaskManager."""

    @pytest.fixture
    def mock_tts_service(self):
        """Create a mock TTS service."""
        mock_service = Mock()
        mock_service.submit_request.return_value = "test_task_123"
        return mock_service

    @pytest.fixture
    def task_manager(self, db_manager, mock_tts_service):
        """Create a task manager instance for testing."""
        return TTSTaskManager(
            database_url=db_manager.database_url,
            tts_service=mock_tts_service
        )

    def test_init(self, db_manager, mock_tts_service):
        """Test task manager initialization."""
        manager = TTSTaskManager(
            database_url=db_manager.database_url,
            tts_service=mock_tts_service
        )
        
        assert manager.db_manager is not None
        assert manager.tts_service == mock_tts_service
        assert manager.is_running is False
        assert manager.monitor_thread is None

    def test_calculate_text_hash(self, task_manager):
        """Test text hash calculation."""
        text = "Test text for hashing"
        hash1 = task_manager._calculate_text_hash(text)
        hash2 = task_manager._calculate_text_hash(text)
        
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length
        assert isinstance(hash1, str)

    def test_submit_task_success(self, task_manager, db_manager):
        """Test successful task submission."""
        text = "Test text for TTS"
        custom_filename = "test_audio"
        
        task_id = task_manager.submit_task(text, custom_filename)
        
        assert task_id == "test_task_123"
        
        # Check database record
        with db_manager.get_session() as session:
            task = session.query(Task).filter(Task.task_id == task_id).first()
            assert task is not None
            assert task.original_text == text
            assert task.custom_filename == custom_filename
            assert task.status == "queued"

    def test_submit_task_empty_text(self, task_manager):
        """Test task submission with empty text."""
        result = task_manager.submit_task("", "test")
        assert result is None

    def test_submit_task_whitespace_text(self, task_manager):
        """Test task submission with whitespace-only text."""
        result = task_manager.submit_task("   ", "test")
        assert result is None

    def test_submit_task_no_tts_service(self, db_manager):
        """Test task submission without TTS service."""
        manager = TTSTaskManager(database_url=db_manager.database_url, tts_service=None)
        
        result = manager.submit_task("Test text")
        assert result is None

    def test_submit_task_duplicate_text(self, task_manager, db_manager):
        """Test task submission with duplicate text."""
        text = "Duplicate text"
        
        # Submit first task
        task_id1 = task_manager.submit_task(text)
        assert task_id1 == "test_task_123"
        
        # Submit duplicate text
        task_id2 = task_manager.submit_task(text)
        assert task_id2 == task_id1  # Should return existing task ID

    def test_submit_task_for_item(self, task_manager, db_manager):
        """Test task submission specifically for an item."""
        # Create an item first
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item text",
                tts_status="pending"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Submit task for item
        task_id = task_manager.submit_task_for_item(item_id, "Test text", "item_audio")
        
        assert task_id == "test_task_123"
        
        # Check that task is linked to item
        with db_manager.get_session() as session:
            task = session.query(Task).filter(Task.task_id == task_id).first()
            assert task.item_id == item_id

    def test_get_task_status(self, task_manager, db_manager):
        """Test getting task status."""
        # Create a task first
        with db_manager.get_session() as session:
            task = Task(
                task_id="test_task_456",
                original_text="Test text",
                text_hash="hash123",
                status="queued",
                created_at=datetime.now(UTC)
            )
            session.add(task)
            session.commit()
        
        # Get task status
        status = task_manager.get_task_status("test_task_456")
        
        assert status is not None
        assert status["task_id"] == "test_task_456"
        assert status["status"] == "queued"

    def test_get_task_status_not_found(self, task_manager):
        """Test getting status for non-existent task."""
        status = task_manager.get_task_status("non_existent")
        assert status is None

    def test_get_all_tasks(self, task_manager, db_manager):
        """Test getting all tasks."""
        # Create some tasks
        with db_manager.get_session() as session:
            for i in range(3):
                task = Task(
                    task_id=f"task_{i}",
                    original_text=f"Text {i}",
                    text_hash=f"hash{i}",
                    status="queued",
                    created_at=datetime.now(UTC)
                )
                session.add(task)
            session.commit()
        
        # Get all tasks
        tasks = task_manager.get_all_tasks()
        assert len(tasks) == 3
        
        # Get tasks with status filter
        queued_tasks = task_manager.get_all_tasks(status="queued")
        assert len(queued_tasks) == 3

    def test_get_tasks_by_text_hash(self, task_manager, db_manager):
        """Test getting tasks by text hash."""
        text_hash = "test_hash_123"
        
        # Create tasks with same hash
        with db_manager.get_session() as session:
            for i in range(2):
                task = Task(
                    task_id=f"task_{i}",
                    original_text=f"Text {i}",
                    text_hash=text_hash,
                    status="queued",
                    created_at=datetime.now(UTC)
                )
                session.add(task)
            session.commit()
        
        # Get tasks by hash
        tasks = task_manager.get_tasks_by_text_hash(text_hash)
        assert len(tasks) == 2
        assert all(task["text_hash"] == text_hash for task in tasks)

    def test_start_stop_monitoring(self, task_manager):
        """Test starting and stopping monitoring."""
        # Start monitoring
        task_manager.start_monitoring()
        assert task_manager.is_running is True
        assert task_manager.monitor_thread is not None
        assert task_manager.monitor_thread.is_alive()
        
        # Stop monitoring
        task_manager.stop_monitoring()
        assert task_manager.is_running is False

    def test_get_statistics(self, task_manager, db_manager):
        """Test getting task statistics."""
        # Create tasks with different statuses
        with db_manager.get_session() as session:
            for i in range(5):
                status = "queued" if i < 3 else "completed"
                task = Task(
                    task_id=f"task_{i}",
                    original_text=f"Text {i}",
                    text_hash=f"hash{i}",
                    status=status,
                    file_size=1024 if status == "completed" else None,
                    created_at=datetime.now(UTC)
                )
                session.add(task)
            session.commit()
        
        # Get statistics
        stats = task_manager.get_statistics()
        
        assert stats["total_tasks"] == 5
        assert stats["status_counts"]["queued"] == 3
        assert stats["status_counts"]["completed"] == 2

    def test_cleanup_failed_tasks(self, task_manager, db_manager):
        """Test cleaning up old failed tasks."""
        # Create old failed task
        old_date = datetime.now(UTC) - timedelta(days=10)
        with db_manager.get_session() as session:
            task = Task(
                task_id="old_failed_task",
                original_text="Old text",
                text_hash="old_hash",
                status="failed",
                failed_at=old_date,
                created_at=old_date
            )
            session.add(task)
            session.commit()
        
        # Clean up tasks older than 7 days
        deleted_count = task_manager.cleanup_failed_tasks(days=7)
        assert deleted_count == 1
        
        # Verify task was deleted
        with db_manager.get_session() as session:
            task = session.query(Task).filter(Task.task_id == "old_failed_task").first()
            assert task is None

    def test_get_tts_worker_health(self, task_manager):
        """Test getting TTS worker health information."""
        health = task_manager.get_tts_worker_health()
        
        assert "worker_running" in health
        assert "queue_size" in health
        assert "pending_items" in health
        assert "tts_service_available" in health

    def test_submit_multiple_tasks(self, task_manager):
        """Test submitting multiple tasks."""
        texts = ["Text 1", "Text 2", "Text 3"]
        
        task_ids = task_manager.submit_multiple_tasks(texts)
        
        assert len(task_ids) == 3
        assert all(task_id == "test_task_123" for task_id in task_ids)

    def test_is_initialized_property(self, task_manager, db_manager):
        """Test the is_initialized property."""
        # With TTS service
        assert task_manager.is_initialized is True
        
        # Without TTS service
        manager = TTSTaskManager(database_url=db_manager.database_url, tts_service=None)
        assert manager.is_initialized is False

    @patch('app.services.outer.tts_task_manager.os.path.exists')
    @patch('app.services.outer.tts_task_manager.os.makedirs')
    @patch('app.services.outer.tts_task_manager.shutil.copy2')
    def test_update_item_from_task_status_completed(self, mock_copy2, mock_makedirs, mock_exists, task_manager, db_manager):
        """Test updating item when task is completed."""
        mock_exists.return_value = True
        
        # Create item and task
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item",
                tts_status="pending"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            task = Task(
                task_id="test_task",
                original_text="Test text",
                text_hash="hash123",
                status="queued",
                item_id=item.id,
                created_at=datetime.now(UTC)
            )
            session.add(task)
            session.commit()
        
        # Update task status to completed
        task_manager._update_item_from_task_status(
            task, "completed", "/tmp/output.wav", {"file_size": 1024}, session
        )
        
        # Verify item was updated
        with db_manager.get_session() as session:
            updated_item = session.query(Item).filter(Item.id == item.id).first()
            assert updated_item.tts_status == "ready"
            assert updated_item.audio_url is not None

    def test_retry_failed_item_tts(self, task_manager, db_manager):
        """Test retrying TTS for failed item."""
        # Create failed item
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item",
                tts_status="failed"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
        
        # Retry TTS
        task_id = task_manager.retry_failed_item_tts(item.id)
        
        assert task_id == "test_task_123"
        
        # Verify item status was reset
        with db_manager.get_session() as session:
            updated_item = session.query(Item).filter(Item.id == item.id).first()
            assert updated_item.tts_status == "pending"

    def test_retry_failed_item_tts_not_failed(self, task_manager, db_manager):
        """Test retrying TTS for non-failed item."""
        # Create non-failed item
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
        
        # Try to retry TTS
        task_id = task_manager.retry_failed_item_tts(item.id)
        
        assert task_id is None  # Should not retry non-failed items

    def test_cleanup_orphaned_tasks(self, task_manager, db_manager):
        """Test cleaning up orphaned tasks."""
        # Create orphaned completed task
        old_date = datetime.now(UTC) - timedelta(hours=25)
        with db_manager.get_session() as session:
            task = Task(
                task_id="orphaned_task",
                original_text="Orphaned text",
                text_hash="orphaned_hash",
                status="completed",
                completed_at=old_date,
                created_at=old_date,
                item_id=None  # No item link
            )
            session.add(task)
            session.commit()
        
        # Clean up orphaned tasks
        deleted_count = task_manager.cleanup_orphaned_tasks()
        assert deleted_count == 1
        
        # Verify task was deleted
        with db_manager.get_session() as session:
            task = session.query(Task).filter(Task.task_id == "orphaned_task").first()
            assert task is None
