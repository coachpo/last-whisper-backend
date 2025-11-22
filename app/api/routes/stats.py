"""Stats API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.concurrency import run_in_threadpool

from app.core.security import rate_limit_dependency
from app.models.schemas import (
    ErrorResponse,
    StatsSummaryResponse,
    PracticeLogResponse,
    PracticeLogEntry,
)
from app.services.stats_service import StatsService

router = APIRouter(
    prefix="/v1/stats",
    tags=["Stats"],
    dependencies=[Depends(rate_limit_dependency("stats"))],
)


# We'll need dependency injection for services
def get_stats_service() -> StatsService:
    """Get stats service instance."""
    # This will be implemented in dependencies.py
    from app.api.dependencies import get_stats_service as _get_stats_service

    return _get_stats_service()


@router.get(
    "/summary",
    response_model=StatsSummaryResponse,
    summary="Get summary statistics",
    description="Get aggregated statistics for attempts within a time window.",
    responses={
        200: {"description": "Summary statistics retrieved"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
    },
)
async def get_summary_stats(
    since: Optional[datetime] = Query(None, description="Start of time window"),
    until: Optional[datetime] = Query(None, description="End of time window"),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get summary statistics."""
    try:
        # Validate time window
        if since and until and since >= until:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="'since' must be before 'until'",
            )

        stats = await run_in_threadpool(
            stats_service.get_summary_stats,
            since,
            until,
        )

        return StatsSummaryResponse(
            total_attempts=stats["total_attempts"],
            unique_items_practiced=stats["unique_items_practiced"],
            average_score=stats["average_score"],
            best_score=stats["best_score"],
            worst_score=stats["worst_score"],
            total_practice_time_minutes=stats["total_practice_time_minutes"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get summary stats: {str(e)}",
        )


@router.get(
    "/practice-log",
    response_model=PracticeLogResponse,
    summary="Get practice log",
    description="Get per-audio practice log with aggregated statistics.",
    responses={
        200: {"description": "Practice log retrieved"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
    },
)
async def get_practice_log(
    since: Optional[datetime] = Query(None, description="Start of time window"),
    until: Optional[datetime] = Query(None, description="End of time window"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get practice log with per-audio statistics."""
    try:
        # Validate time window
        if since and until and since >= until:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="'since' must be before 'until'",
            )

        result = await run_in_threadpool(
            stats_service.get_practice_log,
            since,
            until,
            page,
            per_page,
        )

        # Convert to response format
        practice_log = []
        for entry_dict in result["practice_log"]:
            practice_log.append(PracticeLogEntry(**entry_dict))

        return PracticeLogResponse(
            practice_log=practice_log,
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
            detail=f"Failed to get practice log: {str(e)}",
        )


@router.get(
    "/items/{item_id}",
    summary="Get item statistics",
    description="Get detailed statistics for a specific item.",
    responses={
        200: {"description": "Item statistics retrieved"},
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
)
async def get_item_stats(
    item_id: int,
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get detailed statistics for a specific item."""
    try:
        stats = await run_in_threadpool(stats_service.get_item_stats, item_id)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get item stats: {str(e)}",
        )


@router.get(
    "/progress",
    summary="Get progress over time",
    description="Get progress over time for a specific item or all items.",
    responses={
        200: {"description": "Progress data retrieved"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
    },
)
async def get_progress_over_time(
    item_id: Optional[int] = Query(
        None, description="Item ID (leave empty for all items)"
    ),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get progress over time."""
    try:
        progress = await run_in_threadpool(
            stats_service.get_progress_over_time,
            item_id,
            days,
        )
        return {"progress": progress}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get progress data: {str(e)}",
        )
