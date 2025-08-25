"""Items API endpoints."""

import os
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse

from app.core.config import settings
from app.models.schemas import (
    ErrorResponse,
    ItemCreateRequest,
    ItemResponse,
    ItemListResponse,
)
from app.services.items_service import ItemsService

router = APIRouter(prefix="/v1/items", tags=["Items"])


# We'll need dependency injection for services
def get_items_service() -> ItemsService:
    """Get items service instance."""
    # This will be implemented in dependencies.py
    from app.api.dependencies import get_items_service as _get_items_service
    return _get_items_service()


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create dictation item",
    description="Create a new dictation item and enqueue TTS job.",
    responses={
        202: {"description": "Item created and TTS job queued"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_item(
        request: ItemCreateRequest,
        items_service: ItemsService = Depends(get_items_service),
):
    """Create a new dictation item."""
    try:
        item = items_service.create_item(
            locale=request.locale,
            text=request.text,
            difficulty=request.difficulty,
            tags=request.tags or [],
        )

        return ItemResponse(
            id=item.id,
            locale=item.locale,
            text=item.text,
            difficulty=item.difficulty,
            tags=item.tags,
            tts_status=item.tts_status,
            audio_url=item.audio_url,
            created_at=item.created_at,
            updated_at=item.updated_at,
            practiced=item.has_attempts,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create item: {str(e)}",
        )


@router.get(
    "",
    response_model=ItemListResponse,
    summary="List dictation items",
    description="List dictation items with filtering and pagination.",
    responses={
        200: {"description": "Items retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
    },
)
async def list_items(
        locale: Optional[str] = Query(None, description="Filter by locale"),
        tag: Optional[List[str]] = Query(None, description="Filter by tags (repeat for multiple)"),
        difficulty: Optional[str] = Query(None, description="Filter by difficulty (single value or 'min..max')"),
        q: Optional[str] = Query(None, description="Full-text search query"),
        practiced: Optional[bool] = Query(None, description="Filter by practice status"),
        sort: str = Query("created_at.desc", description="Sort order"),
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        items_service: ItemsService = Depends(get_items_service),
):
    """List dictation items with filtering."""
    try:
        # Validate sort parameter
        valid_sorts = ["created_at.asc", "created_at.desc", "difficulty.asc", "difficulty.desc"]
        if sort not in valid_sorts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort parameter. Must be one of: {', '.join(valid_sorts)}",
            )

        result = items_service.list_items(
            locale=locale,
            tags=tag,
            difficulty=difficulty,
            q=q,
            practiced=practiced,
            sort=sort,
            page=page,
            per_page=per_page,
        )

        # Convert to response format
        items = []
        for item_dict in result["items"]:
            items.append(ItemResponse(**item_dict))

        return ItemListResponse(
            items=items,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=result["total_pages"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list items: {str(e)}",
        )


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get dictation item",
    description="Get a specific dictation item by ID.",
    responses={
        200: {"description": "Item retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
)
async def get_item(
        item_id: int,
        items_service: ItemsService = Depends(get_items_service),
):
    """Get a specific dictation item."""
    try:
        item = items_service.get_item(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )

        return ItemResponse(
            id=item.id,
            locale=item.locale,
            text=item.text,
            difficulty=item.difficulty,
            tags=item.tags,
            tts_status=item.tts_status,
            audio_url=item.audio_url,
            created_at=item.created_at,
            updated_at=item.updated_at,
            practiced=item.has_attempts,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve item: {str(e)}",
        )


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete dictation item",
    description="Delete a dictation item and its associated audio file and attempts.",
    responses={
        204: {"description": "Item deleted successfully"},
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
)
async def delete_item(
        item_id: int,
        items_service: ItemsService = Depends(get_items_service),
):
    """Delete a dictation item."""
    try:
        success = items_service.delete_item(item_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete item: {str(e)}",
        )


# Audio serving endpoint
@router.get(
    "/{item_id}/audio",
    summary="Get item audio",
    description="Download the audio file for a dictation item.",
    responses={
        200: {"description": "Audio file", "content": {"audio/wav": {}}},
        404: {"model": ErrorResponse, "description": "Item or audio not found"},
        400: {"model": ErrorResponse, "description": "Audio not ready"},
    },
)
async def get_item_audio(
        item_id: int,
        items_service: ItemsService = Depends(get_items_service),
):
    """Get the audio file for a dictation item."""
    try:
        item = items_service.get_item(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )

        if item.tts_status != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio not ready. Current status: {item.tts_status}",
            )

        # Build audio file path
        audio_filename = f"item_{item_id}.wav"
        audio_path = os.path.join(settings.audio_dir, audio_filename)

        if not os.path.exists(audio_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file not found",
            )

        return FileResponse(
            path=audio_path,
            media_type="audio/wav",
            filename=audio_filename,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audio: {str(e)}",
        )
