"""Service for managing preset tags."""

from app.core.exceptions import DatabaseException, ValidationException
from app.models.database_manager import DatabaseManager
from app.models.models import Tag
from app.models.schemas import TagCreateRequest, TagResponse, TagListResponse


class TagsService:
    """Service for managing preset tags."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def create_tag(self, tag_data: TagCreateRequest) -> TagResponse:
        """Create a new preset tag."""
        try:
            with self.db_manager.get_session() as session:
                # Check if tag name already exists
                existing_tag = (
                    session.query(Tag).filter(Tag.name == tag_data.name).first()
                )
                if existing_tag:
                    raise ValidationException(
                        f"Tag with name '{tag_data.name}' already exists"
                    )

                # Create new tag
                tag = Tag(name=tag_data.name)

                session.add(tag)
                session.commit()
                session.refresh(tag)

                return TagResponse(**tag.to_dict())

        except ValidationException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to create tag: {str(e)}")

    def get_tags(self, limit: int = 100, offset: int = 0) -> TagListResponse:
        """Get list of preset tags."""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(Tag)

                # Get total count
                total = query.count()

                # Get paginated results
                tags = query.order_by(Tag.name.asc()).offset(offset).limit(limit).all()

                tag_responses = [TagResponse(**tag.to_dict()) for tag in tags]

                return TagListResponse(tags=tag_responses, total=total)

        except Exception as e:
            raise DatabaseException(f"Failed to get tags: {str(e)}")

    def delete_tag(self, tag_id: int) -> bool:
        """Delete a preset tag."""
        try:
            with self.db_manager.get_session() as session:
                tag = session.query(Tag).filter(Tag.id == tag_id).first()
                if not tag:
                    raise ValidationException(f"Tag with ID {tag_id} not found")

                session.delete(tag)
                session.commit()

                return True

        except ValidationException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to delete tag: {str(e)}")
