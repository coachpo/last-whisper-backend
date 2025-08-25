"""Items service for managing dictation items."""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from sqlalchemy import and_

from app.core.config import settings
from app.core.logging import get_logger
from app.models.database import DatabaseManager, Item

# Setup logger for this module
logger = get_logger(__name__)


class ItemsService:
    """Service for managing dictation items."""

    def __init__(self, db_manager: DatabaseManager, task_manager=None):
        self.db_manager = db_manager
        self.task_manager = task_manager

    def create_item(
            self,
            locale: str,
            text: str,
            difficulty: Optional[int] = None,
            tags: Optional[List[str]] = None,
    ) -> Item:
        """Create a new dictation item and enqueue TTS job."""
        with self.db_manager.get_session() as session:
            # Create item with pending TTS status
            item = Item(
                locale=locale,
                text=text,
                difficulty=difficulty,
                tags_json=None,
                tts_status="pending",
                audio_url=None,
            )

            if tags:
                item.tags = tags

            session.add(item)
            session.commit()
            session.refresh(item)

            # Enqueue TTS job if task manager is available
            if self.task_manager:
                try:
                    # Create a custom filename based on item ID
                    custom_filename = f"item_{item.id}"
                    task_id = self.task_manager.submit_task_for_item(item.id, text, custom_filename)

                    if not task_id:
                        # Mark TTS as failed if we couldn't submit
                        item.tts_status = "failed"
                        session.commit()

                except Exception as e:
                    logger.warning(f"Failed to enqueue TTS job for item {item.id}: {e}")
                    item.tts_status = "failed"
                    session.commit()

            return item

    def get_item(self, item_id: int) -> Optional[Item]:
        """Get an item by ID."""
        with self.db_manager.get_session() as session:
            return session.query(Item).filter(Item.id == item_id).first()

    def delete_item(self, item_id: int) -> bool:
        """Delete an item and its associated audio file."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return False

            # Delete associated audio file if it exists
            if item.audio_url:
                try:
                    # Extract filename from URL
                    filename = item.audio_url.split('/')[-1]
                    file_path = os.path.join(settings.audio_dir, filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete audio file for item {item_id}: {e}")

            # Delete the item (cascades to attempts and updates task)
            session.delete(item)
            session.commit()
            return True

    def list_items(
            self,
            locale: Optional[str] = None,
            tags: Optional[List[str]] = None,
            difficulty: Optional[str] = None,  # Single value or "min..max"
            q: Optional[str] = None,  # FTS search query
            practiced: Optional[bool] = None,
            sort: str = "created_at.desc",
            page: int = 1,
            per_page: int = 20,
    ) -> Dict[str, Any]:
        """List items with filtering and pagination."""
        with self.db_manager.get_session() as session:
            # Start with base query
            query = session.query(Item)

            # Apply filters
            if locale:
                query = query.filter(Item.locale == locale)

            if tags:
                # Items must have all specified tags
                for tag in tags:
                    query = query.filter(Item.tags_json.like(f'%"{tag}"%'))

            if difficulty:
                if ".." in difficulty:
                    # Range query: "1..5"
                    try:
                        min_diff, max_diff = map(int, difficulty.split(".."))
                        query = query.filter(
                            and_(
                                Item.difficulty >= min_diff,
                                Item.difficulty <= max_diff
                            )
                        )
                    except ValueError:
                        pass  # Invalid range format, ignore
                else:
                    # Single value
                    try:
                        diff_value = int(difficulty)
                        query = query.filter(Item.difficulty == diff_value)
                    except ValueError:
                        pass  # Invalid number, ignore

            if q:
                # Simple text search using LIKE
                query = query.filter(Item.text.like(f"%{q}%"))

            if practiced is not None:
                if practiced:
                    # Items with at least one attempt
                    query = query.filter(Item.attempts.any())
                else:
                    # Items with no attempts
                    query = query.filter(~Item.attempts.any())

            # Apply sorting
            if sort == "created_at.asc":
                query = query.order_by(Item.created_at.asc())
            elif sort == "created_at.desc":
                query = query.order_by(Item.created_at.desc())
            elif sort == "difficulty.asc":
                query = query.order_by(Item.difficulty.asc().nulls_last())
            elif sort == "difficulty.desc":
                query = query.order_by(Item.difficulty.desc().nulls_last())
            else:
                # Default sort
                query = query.order_by(Item.created_at.desc())

            # Get total count before pagination
            total = query.count()

            # Apply pagination
            offset = (page - 1) * per_page
            items = query.offset(offset).limit(per_page).all()

            # Build response
            return {
                "items": [self._item_to_dict(item) for item in items],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
            }

    def update_item_tts_status(
            self,
            item_id: int,
            status: str,
            audio_url: Optional[str] = None
    ) -> bool:
        """Update the TTS status and audio URL for an item."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return False

            item.tts_status = status
            if audio_url:
                item.audio_url = audio_url
            item.updated_at = datetime.now()

            session.commit()
            return True

    def build_audio_url(self, filename: str) -> str:
        """Build a full audio URL from filename."""
        return urljoin(settings.base_url, f"/api/v1/tts/audio/{filename}")

    def _item_to_dict(self, item: Item) -> Dict[str, Any]:
        """Convert Item model to dictionary."""
        return {
            "id": item.id,
            "locale": item.locale,
            "text": item.text,
            "difficulty": item.difficulty,
            "tags": item.tags,
            "tts_status": item.tts_status,
            "audio_url": item.audio_url,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "practiced": item.has_attempts,
        }
