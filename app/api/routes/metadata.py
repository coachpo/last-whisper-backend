"""Endpoints exposing application metadata for clients."""

from __future__ import annotations

from typing import Annotated, Optional, Set

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.api.dependencies import get_metadata_service
from app.core.security import rate_limit_dependency
from app.models.enums import MetadataDetailLevel
from app.models.schemas import ApplicationMetadataResponse
from app.services.metadata_service import MetadataService

router = APIRouter(
    prefix="/metadata",
    tags=["metadata"],
    dependencies=[Depends(rate_limit_dependency("metadata", limit=20))],
)


def _parse_fields(raw: Optional[str]) -> Optional[Set[str]]:
    if not raw:
        return None
    return {chunk.strip().lower() for chunk in raw.split(",") if chunk.strip()}


@router.get(
    "",
    response_model=ApplicationMetadataResponse,
    response_model_exclude_none=True,
    summary="Application metadata",
    description="Build identifiers, provider wiring, and runtime diagnostics.",
)
async def read_metadata(
    detail: MetadataDetailLevel = MetadataDetailLevel.FULL,
    fields: Annotated[
        Optional[str],
        Query(
            description="Comma-separated list of sections (service, build, runtime, providers, features, limits, links)",
        ),
    ] = None,
    metadata_service: MetadataService = Depends(get_metadata_service),
):
    include = _parse_fields(fields)
    return await run_in_threadpool(
        metadata_service.get_metadata,
        detail,
        include,
    )
