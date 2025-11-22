"""Service assembling payloads for the metadata API."""

from __future__ import annotations

import os
import socket
import threading
import time
from typing import Any, Dict, Optional, Set

from app.core.build_info import load_build_info
from app.core.config import settings
from app.core.runtime_state import get_app_started_at, get_uptime_seconds
from app.models.database_manager import DatabaseManager
from app.models.enums import MetadataDetailLevel
from app.models.schemas import (
    ApplicationMetadataResponse,
    MetadataBuildInfo,
    MetadataProvidersSection,
    MetadataRuntimeInfo,
    MetadataServiceInfo,
)
from app.tts_engine.tts_engine_manager import TTSEngineManager


_FIELD_MATRIX: dict[MetadataDetailLevel, Set[str]] = {
    MetadataDetailLevel.CORE: {"build", "links"},
    MetadataDetailLevel.RUNTIME: {"runtime"},
    MetadataDetailLevel.FULL: {
        "build",
        "runtime",
        "providers",
        "features",
        "limits",
        "links",
    },
}


class MetadataService:
    """Aggregates build, configuration, and runtime state."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        tts_manager: TTSEngineManager,
        cache_ttl: Optional[int] = None,
    ) -> None:
        self.db_manager = db_manager
        self.tts_manager = tts_manager
        self.cache_ttl = cache_ttl or settings.metadata_cache_ttl_seconds
        self._cache_lock = threading.Lock()
        self._static_sections: Optional[dict[str, Any]] = None
        self._cache_expires_at = 0.0

    def get_metadata(
        self,
        detail: MetadataDetailLevel = MetadataDetailLevel.FULL,
        include_fields: Optional[Set[str]] = None,
    ) -> ApplicationMetadataResponse:
        """Return a metadata response honoring the requested detail level."""

        normalized_fields = self._normalize_fields(include_fields)
        default_fields = _FIELD_MATRIX.get(detail, set())
        requested_fields = normalized_fields or default_fields

        static_sections = self._get_static_sections()
        payload: dict[str, Any] = {"service": static_sections["service"]}

        for field in requested_fields:
            if field == "runtime":
                payload["runtime"] = self._build_runtime_section()
                continue

            section_value = static_sections.get(field)
            if section_value is not None:
                payload[field] = section_value

        return ApplicationMetadataResponse(**payload)

    # Internal helpers -------------------------------------------------

    def _normalize_fields(self, fields: Optional[Set[str]]) -> Optional[Set[str]]:
        if not fields:
            return None

        allowed = {
            "service",
            "build",
            "runtime",
            "providers",
            "features",
            "limits",
            "links",
        }
        normalized = {
            field for field in (f.strip().lower() for f in fields) if field in allowed
        }
        return normalized or None

    def _get_static_sections(self) -> dict[str, Any]:
        now = time.time()
        if self._static_sections and now < self._cache_expires_at:
            return self._static_sections

        with self._cache_lock:
            if self._static_sections and now < self._cache_expires_at:
                return self._static_sections

            self._static_sections = self._build_static_sections()
            self._cache_expires_at = now + self.cache_ttl
            return self._static_sections

    def _build_static_sections(self) -> dict[str, Any]:
        build_info = load_build_info()

        service_section = MetadataServiceInfo(
            name=settings.app_name,
            description=settings.app_description,
            environment=settings.environment,
            version=settings.app_version,
            schema_version=settings.metadata_schema_version,
        )

        build_section = MetadataBuildInfo(
            commit=build_info.commit,
            short_commit=build_info.short_commit,
            branch=build_info.branch,
            built_at=build_info.built_at,
            python_version=build_info.python_version,
            fastapi_version=build_info.fastapi_version,
        )

        providers_section = MetadataProvidersSection(
            database=self._database_provider_info(),
            tts={
                "provider": settings.tts_provider,
                "supported_languages": settings.tts_supported_languages,
            },
            translation={
                "provider": settings.translation_provider,
                "supported_languages": settings.translation_supported_languages,
            },
        )

        features = {
            "tts_submission_workers": settings.tts_submission_workers,
            "tts_languages": settings.tts_supported_languages,
            "translation_languages": settings.translation_supported_languages,
        }

        limits = {
            "max_items_per_bulk_request": 100,
            "max_tags_per_item": 20,
            "max_tag_length": 50,
            "max_text_length": 10000,
        }

        links = self._collect_links()

        return {
            "service": service_section,
            "build": build_section,
            "providers": providers_section,
            "features": features,
            "limits": limits,
            "links": links,
        }

    def _database_provider_info(self) -> Dict[str, Any]:
        engine = getattr(getattr(self.db_manager, "engine", None), "name", "unknown")
        info: Dict[str, Any] = {"engine": engine}
        url = settings.database_url
        if engine == "sqlite" and url.startswith("sqlite:///"):
            info["file"] = url.replace("sqlite:///", "", 1)
        else:
            info["connection"] = url.split("@")[-1] if "@" in url else "managed"
            info["masked"] = True
        return info

    def _collect_links(self) -> Dict[str, str]:
        links: Dict[str, str] = {"status": "/health", "metadata": "/metadata"}
        if settings.docs_url:
            links["docs"] = settings.docs_url
        if settings.redoc_url:
            links["redoc"] = settings.redoc_url
        if settings.openapi_url:
            links["openapi"] = settings.openapi_url
        if settings.metadata_additional_links:
            links.update(settings.metadata_additional_links)
        return links

    def _build_runtime_section(self) -> MetadataRuntimeInfo:
        started_at = get_app_started_at()
        worker_stats: Dict[str, Any] = {}
        try:
            if hasattr(self.tts_manager, "get_tts_worker_health"):
                worker_stats = self.tts_manager.get_tts_worker_health() or {}
        except Exception:
            worker_stats = {}

        return MetadataRuntimeInfo(
            started_at=started_at,
            uptime_seconds=round(get_uptime_seconds(), 2),
            process_id=os.getpid(),
            host=socket.gethostname(),
            worker=worker_stats,
        )
