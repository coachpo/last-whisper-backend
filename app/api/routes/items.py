"""Items API endpoints."""

import os
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.security import rate_limit_dependency
from app.models.enums import ItemTTSStatus
from app.models.schemas import (
    ErrorResponse,
    ItemCreateRequest,
    ItemResponse,
    ItemListResponse,
    BulkItemCreateRequest,
    BulkItemCreateResponse,
    TagUpdateRequest,
    TagUpdateResponse,
    DifficultyUpdateRequest,
    DifficultyUpdateResponse,
    ItemTTSStatusResponse,
    AudioRefreshResponse,
)
from app.services.items_service import ItemsService
from app.services.exceptions import ServiceError

router = APIRouter(
    prefix="/v1/items",
    tags=["Items"],
    dependencies=[Depends(rate_limit_dependency("items"))],
)


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
    description="Create a new dictation item. The item is immediately created in the database with 'pending' TTS status, and TTS processing happens in the background. The API response is returned immediately without waiting for TTS completion. Difficulty will be auto-calculated based on text length if not provided.",
    responses={
        202: {
            "description": "Item created successfully. TTS processing started in background."
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_item(
    request: ItemCreateRequest,
    items_service: ItemsService = Depends(get_items_service),
):
    """Create a new dictation item."""
    try:
        item_data = await run_in_threadpool(
            items_service.create_item,
            request.locale,
            request.text,
            request.difficulty,
            request.tags or [],
        )

        return ItemResponse(**item_data)

    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create item: {str(e)}",
        )


@router.post(
    "/bulk",
    response_model=BulkItemCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create multiple dictation items",
    description="Create multiple new dictation items. All items are immediately created in the database with 'pending' TTS status, and TTS processing for all items happens in the background. The API response is returned immediately without waiting for TTS completion. Difficulty will be auto-calculated based on text length if not provided.",
    responses={
        202: {
            "description": "Items created successfully. TTS processing started in background for all items."
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def bulk_create_items(
    request: BulkItemCreateRequest,
    items_service: ItemsService = Depends(get_items_service),
):
    """Create multiple new dictation items."""
    try:
        # Prepare items data for the service
        items_data = []
        for item_request in request.items:
            items_data.append(
                {
                    "locale": item_request.locale,
                    "text": item_request.text,
                    "difficulty": item_request.difficulty,
                    "tags": item_request.tags or [],
                }
            )

        result = await run_in_threadpool(items_service.bulk_create_items, items_data)

        # Convert created items to response format
        created_items_response = []
        for item_data in result["created_items"]:
            created_items_response.append(ItemResponse(**item_data))

        return BulkItemCreateResponse(
            created_items=created_items_response,
            total_created=len(result["created_items"]),
            failed_items=result["failed_items"],
            total_failed=len(result["failed_items"]),
            submitted_at=datetime.now(),
        )

    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create items: {str(e)}",
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
    tag: Optional[List[str]] = Query(
        None, description="Filter by tags (repeat for multiple)"
    ),
    difficulty: Optional[str] = Query(
        None, description="Filter by difficulty (single value or 'min..max')"
    ),
    practiced: Optional[bool] = Query(None, description="Filter by practice status"),
    sort: str = Query("created_at.desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    items_service: ItemsService = Depends(get_items_service),
):
    """List dictation items with filtering."""
    try:
        # Validate sort parameter
        valid_sorts = [
            "created_at.asc",
            "created_at.desc",
            "difficulty.asc",
            "difficulty.desc",
        ]
        if sort not in valid_sorts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort parameter. Must be one of: {', '.join(valid_sorts)}",
            )

        result = await run_in_threadpool(
            items_service.list_items,
            locale,
            tag,
            difficulty,
            practiced,
            sort,
            page,
            per_page,
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
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
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
        item_data = await run_in_threadpool(items_service.get_item, item_id)

        return ItemResponse(**item_data)

    except HTTPException:
        raise
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve item: {str(e)}",
        )


@router.get(
    "/{item_id}/tts-status",
    response_model=ItemTTSStatusResponse,
    summary="Get item TTS status",
    description="Get the latest TTS processing status for a dictation item.",
    responses={
        200: {"description": "TTS status retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
)
async def get_item_tts_status(
    item_id: int,
    items_service: ItemsService = Depends(get_items_service),
):
    """Return the TTS processing status for a specific dictation item."""

    try:
        status_map = await run_in_threadpool(
            items_service.get_items_tts_status, [item_id]
        )
        status_info = status_map.get(item_id)

        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )

        return ItemTTSStatusResponse(
            item_id=status_info["id"],
            text=status_info["text"],
            tts_status=status_info["tts_status"],
            created_at=status_info["created_at"],
            updated_at=status_info["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve TTS status: {str(e)}",
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
        await run_in_threadpool(items_service.delete_item, item_id)

    except HTTPException:
        raise
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete item: {str(e)}",
        )


@router.patch(
    "/{item_id}/tags",
    response_model=TagUpdateResponse,
    summary="Update item tags",
    description="Update tags for a dictation item by replacing all existing tags with new ones.",
    responses={
        200: {"description": "Tags updated successfully"},
        404: {"model": ErrorResponse, "description": "Item not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_item_tags(
    item_id: int,
    request: TagUpdateRequest,
    items_service: ItemsService = Depends(get_items_service),
):
    """Update tags for a dictation item."""
    try:
        result = await run_in_threadpool(
            items_service.update_item_tags,
            item_id,
            request.tags,
        )

        return TagUpdateResponse(
            item_id=result["item_id"],
            operation=result["operation"],
            previous_tags=result["previous_tags"],
            current_tags=result["current_tags"],
            updated_at=result["updated_at"],
            message=result["message"],
        )

    except HTTPException:
        raise
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tags: {str(e)}",
        )


@router.patch(
    "/{item_id}/difficulty",
    response_model=DifficultyUpdateResponse,
    summary="Update item difficulty",
    description="Update the difficulty level for a dictation item. Difficulty must be an integer between 1-5.",
    responses={
        200: {"description": "Difficulty updated successfully"},
        404: {"model": ErrorResponse, "description": "Item not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_item_difficulty(
    item_id: int,
    request: DifficultyUpdateRequest,
    items_service: ItemsService = Depends(get_items_service),
):
    """Update the difficulty level for a dictation item."""
    try:
        result = await run_in_threadpool(
            items_service.update_item_difficulty,
            item_id,
            request.difficulty,
        )

        return DifficultyUpdateResponse(
            item_id=result["item_id"],
            previous_difficulty=result["previous_difficulty"],
            current_difficulty=result["current_difficulty"],
            updated_at=result["updated_at"],
            message=result["message"],
        )

    except HTTPException:
        raise
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update difficulty: {str(e)}",
        )


# Audio serving endpoint
@router.get(
    "/{item_id}/audio",
    summary="Get item audio",
    description="Stream the audio file for a dictation item.",
    responses={
        200: {"description": "Audio file stream", "content": {"audio/wav": {}}},
        404: {"model": ErrorResponse, "description": "Item or audio not found"},
        400: {"model": ErrorResponse, "description": "Audio not ready"},
    },
)
async def get_item_audio(
    item_id: int,
    items_service: ItemsService = Depends(get_items_service),
):
    """Stream the audio file for a dictation item."""
    try:
        item_data = await run_in_threadpool(items_service.get_item, item_id)

        if item_data["tts_status"] != ItemTTSStatus.READY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio not ready. Current status: {item_data['tts_status']}",
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
            audio_path,
            media_type="audio/wav",
            filename=audio_filename,
            headers={"Cache-Control": "public, max-age=3600"},
        )

    except HTTPException:
        raise
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audio: {str(e)}",
        )


@router.post(
    "/{item_id}/audio/refresh",
    response_model=AudioRefreshResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Force refresh/generate audio for an item",
    responses={
        202: {
            "description": "TTS refresh enqueued",
        },
        404: {"model": ErrorResponse, "description": "Item not found"},
        409: {"model": ErrorResponse, "description": "Unsupported locale"},
    },
)
async def refresh_item_audio(
    item_id: int,
    items_service: ItemsService = Depends(get_items_service),
):
    """Enqueue TTS regeneration even if audio exists/missing."""
    try:
        result = await run_in_threadpool(items_service.refresh_item_audio, item_id)

        return AudioRefreshResponse(**result)

    except HTTPException:
        raise
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh audio: {str(e)}",
        )
