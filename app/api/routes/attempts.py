"""Attempts API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.concurrency import run_in_threadpool

from app.core.security import rate_limit_dependency
from app.models.schemas import (
    ErrorResponse,
    AttemptCreateRequest,
    AttemptResponse,
    AttemptListResponse,
)
from app.services.attempts_service import AttemptsService

router = APIRouter(
    prefix="/v1/attempts",
    tags=["Attempts"],
    dependencies=[Depends(rate_limit_dependency("attempts"))],
)


# We'll need dependency injection for services
def get_attempts_service() -> AttemptsService:
    """Get attempts service instance."""
    # This will be implemented in dependencies.py
    from app.api.dependencies import get_attempts_service as _get_attempts_service

    return _get_attempts_service()


@router.post(
    "",
    response_model=AttemptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create dictation attempt",
    description="Score and persist a dictation attempt.",
    responses={
        201: {"description": "Attempt created and scored"},
        404: {"model": ErrorResponse, "description": "Item not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_attempt(
    request: AttemptCreateRequest,
    attempts_service: AttemptsService = Depends(get_attempts_service),
):
    """Create and score a new dictation attempt."""
    try:
        attempt = await run_in_threadpool(
            attempts_service.create_attempt,
            request.item_id,
            request.text,
        )

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )

        return AttemptResponse(
            id=attempt.id,
            item_id=attempt.item_id,
            text=attempt.text,
            percentage=attempt.percentage,
            wer=attempt.wer,
            words_ref=attempt.words_ref,
            words_correct=attempt.words_correct,
            created_at=attempt.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create attempt: {str(e)}",
        )


@router.get(
    "",
    response_model=AttemptListResponse,
    summary="List dictation attempts",
    description="List dictation attempts with filtering and pagination.",
    responses={
        200: {"description": "Attempts retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
    },
)
async def list_attempts(
    item_id: Optional[int] = Query(None, description="Filter by item ID"),
    since: Optional[datetime] = Query(
        None, description="Filter attempts since this timestamp"
    ),
    until: Optional[datetime] = Query(
        None, description="Filter attempts until this timestamp"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    attempts_service: AttemptsService = Depends(get_attempts_service),
):
    """List dictation attempts with filtering."""
    try:
        result = await run_in_threadpool(
            attempts_service.list_attempts,
            item_id,
            since,
            until,
            page,
            per_page,
        )

        # Convert to response format
        attempts = []
        for attempt_dict in result["attempts"]:
            attempts.append(AttemptResponse(**attempt_dict))

        return AttemptListResponse(
            attempts=attempts,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
            total_pages=result["total_pages"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list attempts: {str(e)}",
        )


@router.get(
    "/{attempt_id}",
    response_model=AttemptResponse,
    summary="Get dictation attempt",
    description="Get a specific dictation attempt by ID.",
    responses={
        200: {"description": "Attempt retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Attempt not found"},
    },
)
async def get_attempt(
    attempt_id: int,
    attempts_service: AttemptsService = Depends(get_attempts_service),
):
    """Get a specific dictation attempt."""
    try:
        attempt = await run_in_threadpool(attempts_service.get_attempt, attempt_id)
        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attempt not found",
            )

        return AttemptResponse(
            id=attempt.id,
            item_id=attempt.item_id,
            text=attempt.text,
            percentage=attempt.percentage,
            wer=attempt.wer,
            words_ref=attempt.words_ref,
            words_correct=attempt.words_correct,
            created_at=attempt.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve attempt: {str(e)}",
        )
