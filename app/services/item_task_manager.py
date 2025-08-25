"""Item-specific task manager with TTS integration."""

import os
from datetime import UTC, datetime
from typing import Optional, Dict, Any

from app.core.config import settings
from app.models.database import Task, Item
from app.services.outer.tts_task_manager import TTSTaskManager


class ItemTaskManager(TTSTaskManager):
    """Task manager that integrates TTS tasks with Item entities."""

    def __init__(self, database_url: str = settings.database_url, tts_service=None):
        super().__init__(database_url, tts_service)
        # We inherit the database manager from parent

    def _update_task_from_message(self, message: Dict[str, Any]):
        """Update task status and related item from task queue message."""
        # Call parent implementation first
        super()._update_task_from_message(message)

        # Now handle item updates
        task_id = message.get("request_id")
        status = message.get("status")
        output_file_path = message.get("output_file_path")
        metadata = message.get("metadata", {})

        if not task_id:
            return

        with self.db_manager.get_session() as session:
            # Get the task
            task = session.query(Task).filter(Task.task_id == task_id).first()
            if not task or not task.item_id:
                return

            # Get the related item
            item = session.query(Item).filter(Item.id == task.item_id).first()
            if not item:
                return

            # Update item based on task status
            if status == "completed":
                # TTS completed successfully
                item.tts_status = "ready"

                # Build audio URL from output file
                if output_file_path and os.path.exists(output_file_path):
                    # Move file to audio directory with proper naming
                    audio_filename = f"item_{item.id}.wav"
                    audio_path = os.path.join(settings.audio_dir, audio_filename)

                    try:
                        # Ensure audio directory exists
                        os.makedirs(settings.audio_dir, exist_ok=True)

                        # Copy or move the file
                        if output_file_path != audio_path:
                            import shutil
                            shutil.copy2(output_file_path, audio_path)

                        # Set the audio URL
                        item.audio_url = f"{settings.base_url}/v1/audio/{audio_filename}"

                        print(f"Audio file ready for item {item.id}: {audio_filename}")

                    except Exception as e:
                        print(f"Error handling audio file for item {item.id}: {e}")
                        item.tts_status = "failed"

            elif status == "failed":
                # TTS failed
                item.tts_status = "failed"
                print(f"TTS failed for item {item.id}: {metadata.get('error', 'Unknown error')}")

            # Update timestamp
            item.updated_at = datetime.now(UTC)
            session.commit()

    def submit_task_for_item(self, item_id: int, text: str, custom_filename: Optional[str] = None) -> Optional[str]:
        """Submit a TTS task specifically for an item."""
        # Submit the task using parent method
        task_id = self.submit_task(text, custom_filename)

        if task_id:
            # Link the task to the item
            with self.db_manager.get_session() as session:
                task = session.query(Task).filter(Task.task_id == task_id).first()
                if task:
                    task.item_id = item_id
                    session.commit()
                    print(f"Linked task {task_id} to item {item_id}")

        return task_id

    def get_item_tts_status(self, item_id: int) -> Optional[str]:
        """Get TTS status for a specific item."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if item:
                return item.tts_status
            return None

    def retry_failed_item_tts(self, item_id: int) -> Optional[str]:
        """Retry TTS for a failed item."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None

            if item.tts_status != "failed":
                return None  # Only retry failed items

            # Reset status to pending
            item.tts_status = "pending"
            item.updated_at = datetime.now(UTC)
            session.commit()

            # Submit new TTS task
            custom_filename = f"item_{item.id}"
            return self.submit_task_for_item(item.id, item.text, custom_filename)

    def get_items_by_tts_status(self, status: str = "pending") -> list[Dict[str, Any]]:
        """Get items by TTS status."""
        with self.db_manager.get_session() as session:
            items = session.query(Item).filter(Item.tts_status == status).all()

            return [
                {
                    "id": item.id,
                    "text": item.text[:100] + "..." if len(item.text) > 100 else item.text,
                    "locale": item.locale,
                    "tts_status": item.tts_status,
                    "audio_url": item.audio_url,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                }
                for item in items
            ]

    def cleanup_orphaned_tasks(self) -> int:
        """Clean up tasks that are not linked to any item."""
        with self.db_manager.get_session() as session:
            # Delete completed tasks older than 24 hours that have no item link
            cutoff_date = datetime.now(UTC) - datetime.timedelta(hours=24)

            deleted_count = (
                session.query(Task)
                .filter(
                    Task.item_id.is_(None),
                    Task.status == "completed",
                    Task.completed_at < cutoff_date
                )
                .delete()
            )
            session.commit()

            print(f"Cleaned up {deleted_count} orphaned completed tasks")
            return deleted_count

    def get_tts_worker_health(self) -> Dict[str, Any]:
        """Check TTS worker health."""
        is_running = self.is_running

        # Get queue status if available
        queue_size = 0
        try:
            if self.tts_service and hasattr(self.tts_service, 'get_task_queue'):
                task_queue = self.tts_service.get_task_queue()
                queue_size = task_queue.qsize() if hasattr(task_queue, 'qsize') else 0
        except Exception:
            pass

        # Get pending items count
        pending_items = 0
        try:
            with self.db_manager.get_session() as session:
                pending_items = session.query(Item).filter(Item.tts_status == "pending").count()
        except Exception:
            pass

        return {
            "worker_running": is_running,
            "queue_size": queue_size,
            "pending_items": pending_items,
            "tts_service_available": self.tts_service is not None,
        }
