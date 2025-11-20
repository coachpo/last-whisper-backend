"""API routes for preset tags management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool

from app.api.dependencies import get_tags_service
from app.core.exceptions import DatabaseException, ValidationException
from app.models.schemas import TagCreateRequest, TagResponse, TagListResponse
from app.services.tags_service import TagsService

router = APIRouter(prefix="/v1/tags", tags=["Tags"])


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new preset tag",
    description="Create a new preset tag that can be used when creating dictation items.",
)
async def create_tag(
    tag_data: TagCreateRequest, tags_service: TagsService = Depends(get_tags_service)
):
    """Create a new preset tag."""
    try:
        return await run_in_threadpool(tags_service.create_tag, tag_data)
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "",
    response_model=TagListResponse,
    summary="Get list of preset tags",
    description="Get a paginated list of preset tags.",
)
async def get_tags(
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of tags to return"
    ),
    offset: int = Query(0, ge=0, description="Number of tags to skip"),
    tags_service: TagsService = Depends(get_tags_service),
):
    """Get list of preset tags."""
    try:
        return await run_in_threadpool(tags_service.get_tags, limit, offset)
    except DatabaseException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a preset tag",
    description="Delete a preset tag. This will not affect existing items that use this tag.",
)
async def delete_tag(
    tag_id: int, tags_service: TagsService = Depends(get_tags_service)
):
    """Delete a preset tag."""
    try:
        await run_in_threadpool(tags_service.delete_tag, tag_id)
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
