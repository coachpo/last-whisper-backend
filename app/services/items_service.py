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

    def _calculate_difficulty_from_text(self, text: str) -> int:
        """Calculate difficulty level based on text length rules."""
        # Count words and letters
        words = len(text.split())
        letters = len(text.replace(" ", ""))
        
        # Apply difficulty rules
        if words <= 6 or letters <= 50:
            return 1
        elif 7 <= words <= 9 or 51 <= letters <= 80:
            return 2
        elif 10 <= words <= 12 or 81 <= letters <= 110:
            return 3
        elif 13 <= words <= 15 or 111 <= letters <= 140:
            return 4
        else:  # words >= 16 or letters >= 141
            return 5

    def create_item(
            self,
            locale: str,
            text: str,
            difficulty: Optional[int] = None,
            tags: Optional[List[str]] = None,
    ) -> Item:
        """Create a new dictation item and enqueue TTS job."""
        # Auto-calculate difficulty if not provided
        if difficulty is None:
            difficulty = self._calculate_difficulty_from_text(text)
        
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

    def bulk_create_items(
            self,
            items_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create multiple dictation items and enqueue TTS jobs."""
        created_items = []
        failed_items = []
        
        with self.db_manager.get_session() as session:
            for item_data in items_data:
                try:
                    # Create item with pending TTS status
                    item = Item(
                        locale=item_data["locale"],
                        text=item_data["text"],
                        difficulty=item_data.get("difficulty"),
                        tags_json=None,
                        tts_status="pending",
                        audio_url=None,
                    )

                    # Auto-calculate difficulty if not provided
                    if item.difficulty is None:
                        item.difficulty = self._calculate_difficulty_from_text(item_data["text"])

                    if item_data.get("tags"):
                        item.tags = item_data["tags"]

                    session.add(item)
                    session.flush()  # Get the ID without committing
                    session.refresh(item)

                    # Enqueue TTS job if task manager is available
                    if self.task_manager:
                        try:
                            # Create a custom filename based on item ID
                            custom_filename = f"item_{item.id}"
                            task_id = self.task_manager.submit_task_for_item(item.id, item.text, custom_filename)

                            if not task_id:
                                # Mark TTS as failed if we couldn't submit
                                item.tts_status = "failed"

                        except Exception as e:
                            logger.warning(f"Failed to enqueue TTS job for item {item.id}: {e}")
                            item.tts_status = "failed"

                    created_items.append(item)

                except Exception as e:
                    logger.error(f"Failed to create item: {e}")
                    failed_items.append({
                        "data": item_data,
                        "error": str(e)
                    })

            # Commit all successful creations
            session.commit()
            
            return {
                "created_items": created_items,
                "failed_items": failed_items
            }

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

    def update_item_tags(
            self,
            item_id: int,
            operation: str,
            **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Update tags for an item based on the specified operation."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None

            previous_tags = item.tags.copy() if item.tags else []
            current_tags = previous_tags.copy()
            message = ""

            if operation == "replace":
                # Replace all tags
                new_tags = kwargs.get("tags", [])
                current_tags = new_tags
                message = f"Replaced all tags with: {', '.join(new_tags) if new_tags else 'none'}"

            elif operation == "add":
                # Add new tags
                add_tags = kwargs.get("add_tags", [])
                for tag in add_tags:
                    if tag not in current_tags:
                        current_tags.append(tag)
                message = f"Added tags: {', '.join(add_tags)}"

            elif operation == "remove":
                # Remove specific tags
                remove_tags = kwargs.get("remove_tags", [])
                for tag in remove_tags:
                    if tag in current_tags:
                        current_tags.remove(tag)
                message = f"Removed tags: {', '.join(remove_tags)}"

            elif operation == "modify":
                # Modify specific tags
                tag_modifications = kwargs.get("tag_modifications", [])
                for mod in tag_modifications:
                    old_tag = mod.get("old")
                    new_tag = mod.get("new")
                    if old_tag in current_tags:
                        index = current_tags.index(old_tag)
                        current_tags[index] = new_tag
                message = f"Modified {len(tag_modifications)} tag(s)"

            # Update the item
            item.tags = current_tags
            item.updated_at = datetime.now()
            session.commit()

            return {
                "item_id": item.id,
                "operation": operation,
                "previous_tags": previous_tags,
                "current_tags": current_tags,
                "updated_at": item.updated_at,
                "message": message
            }

    def update_item_difficulty(
            self,
            item_id: int,
            difficulty: int
    ) -> Optional[Dict[str, Any]]:
        """Update the difficulty level for an item."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None

            previous_difficulty = item.difficulty
            
            # Update the difficulty
            item.difficulty = difficulty
            item.updated_at = datetime.now()
            session.commit()

            # Create message based on whether difficulty was previously set
            if previous_difficulty is None:
                message = f"Set difficulty to {difficulty}"
            else:
                message = f"Updated difficulty from {previous_difficulty} to {difficulty}"

            return {
                "item_id": item.id,
                "previous_difficulty": previous_difficulty,
                "current_difficulty": difficulty,
                "updated_at": item.updated_at,
                "message": message
            }

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
