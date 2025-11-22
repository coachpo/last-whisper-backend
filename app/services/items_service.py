"""Items service for managing dictation items."""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import and_, func, true

from app.core.config import settings
from app.core.logging import get_logger
from app.models.database_manager import DatabaseManager
from app.models.models import Item, ItemTTS
from app.models.enums import ItemTTSStatus
from app.services.exceptions import NotFoundError, ServiceError, ValidationError
from app.services.item_audio_manager import ItemAudioManager

# Setup logger for this module
logger = get_logger(__name__)


class ItemsService:
    """Service for managing dictation items."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        task_manager=None,
        audio_manager: Optional[ItemAudioManager] = None,
    ):
        self.db_manager = db_manager
        self.task_manager = task_manager
        self.audio_manager = audio_manager or ItemAudioManager(
            db_manager, task_manager
        )

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

    def _validate_locale(self, locale: str) -> None:
        if locale not in settings.tts_supported_languages:
            raise ValidationError(
                f"Locale '{locale}' is not supported for TTS."
            )

    def create_item(
        self,
        locale: str,
        text: str,
        difficulty: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new dictation item and enqueue TTS job in background."""
        self._validate_locale(locale)
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
            )

            if tags:
                item.tags = tags

            session.add(item)
            session.commit()
            session.refresh(item)

            # Create ItemTTS record
            tts_record = ItemTTS(
                item_id=item.id,
                status=ItemTTSStatus.PENDING,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            session.add(tts_record)
            session.commit()

            if self.audio_manager:
                self.audio_manager.schedule_generation(item.id, text, locale)

            # Return clean data structure to avoid session binding issues
            return self._item_to_dict(item)

    def bulk_create_items(self, items_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple dictation items and enqueue TTS jobs in background."""
        created_items = []
        failed_items = []

        with self.db_manager.get_session() as session:
            for item_data in items_data:
                try:
                    self._validate_locale(item_data["locale"])
                    item = Item(
                        locale=item_data["locale"],
                        text=item_data["text"],
                        difficulty=item_data.get("difficulty"),
                        tags_json=None,
                    )

                    if item.difficulty is None:
                        item.difficulty = self._calculate_difficulty_from_text(
                            item_data["text"]
                        )

                    if item_data.get("tags"):
                        item.tags = item_data["tags"]

                    session.add(item)
                    session.flush()
                    session.refresh(item)

                    session.add(
                        ItemTTS(
                            item_id=item.id,
                            status=ItemTTSStatus.PENDING,
                            created_at=item.created_at,
                            updated_at=item.updated_at,
                        )
                    )
                    session.commit()

                    created_items.append(self._item_to_dict(item))

                    if self.audio_manager:
                        self.audio_manager.schedule_generation(
                            item.id, item.text, item.locale
                        )

                except ValidationError as exc:
                    session.rollback()
                    failed_items.append({"data": item_data, "error": exc.message})
                except Exception as exc:  # pragma: no cover - logged for ops
                    session.rollback()
                    logger.error("Failed to create item: %s", exc)
                    failed_items.append({"data": item_data, "error": str(exc)})

        return {"created_items": created_items, "failed_items": failed_items}

    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Get an item by ID."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                raise NotFoundError(f"Item {item_id} not found")

            # Return clean data structure to avoid session binding issues
            return self._item_to_dict(item)

    def delete_item(self, item_id: int) -> bool:
        """Delete an item and its associated audio file."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                raise NotFoundError(f"Item {item_id} not found")

            # Delete associated audio file if it exists
            # Check if audio file exists using predictable naming convention
            audio_filename = f"item_{item_id}.wav"
            file_path = os.path.join(settings.audio_dir, audio_filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(
                        f"Failed to delete audio file for item {item_id}: {e}"
                    )

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
                dialect = self.db_manager.engine.dialect.name
                if dialect == "sqlite":
                    for idx, tag in enumerate(tags):
                        tag_alias = (
                            func.json_each(Item.tags_json)
                            .table_valued("value")
                            .alias(f"tag_filter_{idx}")
                        )
                        query = query.join(tag_alias, true(), isouter=True)
                        query = query.filter(tag_alias.c.value == tag)
                else:
                    for tag in tags:
                        query = query.filter(Item.tags_json.like(f'%"{tag}"%'))

            if difficulty:
                if ".." in difficulty:
                    # Range query: "1..5"
                    try:
                        min_diff, max_diff = map(int, difficulty.split(".."))
                        query = query.filter(
                            and_(
                                Item.difficulty >= min_diff, Item.difficulty <= max_diff
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

    def update_item_tts_status(self, item_id: int, status: str) -> bool:
        """Update the TTS status for an item."""
        with self.db_manager.get_session() as session:
            tts = (
                session.query(ItemTTS).filter(ItemTTS.item_id == item_id).first()
            )
            if not tts:
                return False

            tts.status = status
            tts.updated_at = datetime.now()
            session.commit()
            return True

    def refresh_item_audio(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Force refresh/generate audio for an item."""
        if not self.audio_manager:
            raise ServiceError("TTS refresh unavailable", status_code=503)

        return self.audio_manager.refresh_item_audio(item_id)

    def update_item_tags(
        self, item_id: int, tags: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Update tags for an item by replacing all existing tags with new ones."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                raise NotFoundError(f"Item {item_id} not found")

            previous_tags = item.tags.copy() if item.tags else []

            # Simply replace all tags with the new ones
            item.tags = tags
            item.updated_at = datetime.now()
            session.commit()

            return {
                "item_id": item.id,
                "operation": "replace",
                "previous_tags": previous_tags,
                "current_tags": tags,
                "updated_at": item.updated_at,
                "message": f"Replaced all tags with: {', '.join(tags) if tags else 'none'}",
            }

    def update_item_difficulty(
        self, item_id: int, difficulty: int
    ) -> Optional[Dict[str, Any]]:
        """Update the difficulty level for an item."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                raise NotFoundError(f"Item {item_id} not found")

            previous_difficulty = item.difficulty

            # Update the difficulty
            item.difficulty = difficulty
            item.updated_at = datetime.now()
            session.commit()

            # Create message based on whether difficulty was previously set
            if previous_difficulty is None:
                message = f"Set difficulty to {difficulty}"
            else:
                message = (
                    f"Updated difficulty from {previous_difficulty} to {difficulty}"
                )

            return {
                "item_id": item.id,
                "previous_difficulty": previous_difficulty,
                "current_difficulty": difficulty,
                "updated_at": item.updated_at,
                "message": message,
            }

    def get_items_tts_status(self, item_ids: List[int]) -> Dict[str, Any]:
        """Get TTS status for multiple items."""
        with self.db_manager.get_session() as session:
            items = (
                session.query(Item)
                .filter(Item.id.in_(item_ids))
                .outerjoin(ItemTTS, Item.id == ItemTTS.item_id)
                .add_entity(ItemTTS)
                .all()
            )

            status_info = {}
            for item, tts in items:
                status_info[item.id] = {
                    "id": item.id,
                    "text": (
                        item.text[:100] + "..." if len(item.text) > 100 else item.text
                    ),
                    "tts_status": tts.status if tts else None,
                    "created_at": (
                        item.created_at.isoformat() if item.created_at else None
                    ),
                    "updated_at": (
                        item.updated_at.isoformat() if item.updated_at else None
                    ),
                }

            return status_info

    def _item_to_dict(self, item: Item) -> Dict[str, Any]:
        """Convert Item model to dictionary."""
        tts_status = None
        if item.tts_record:
            tts_status = item.tts_record.status
        return {
            "id": item.id,
            "locale": item.locale,
            "text": item.text,
            "difficulty": item.difficulty,
            "tags": item.tags,
            "tts_status": tts_status,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "practiced": item.has_attempts,
        }
