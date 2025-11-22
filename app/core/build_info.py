"""Helpers for collecting build/commit metadata for the API."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import __version__ as fastapi_version

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class BuildInfo:
    """Normalized build metadata."""

    commit: str
    short_commit: str
    branch: str
    built_at: Optional[str]
    python_version: str
    fastapi_version: str


def _run_git_command(*args: str) -> Optional[str]:
    try:
        output = subprocess.check_output(
            ["git", *args], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
        )
        return output.decode().strip() or None
    except Exception:
        return None


def _resolve_commit_sha() -> Optional[str]:
    return (
        settings.metadata_commit_sha
        or os.getenv("BUILD_COMMIT_SHA")
        or _run_git_command("rev-parse", "HEAD")
    )


def _resolve_branch() -> Optional[str]:
    return (
        settings.metadata_build_branch
        or os.getenv("BUILD_BRANCH")
        or _run_git_command("rev-parse", "--abbrev-ref", "HEAD")
    )


def _resolve_timestamp() -> Optional[str]:
    return (
        settings.metadata_build_timestamp
        or os.getenv("BUILD_TIMESTAMP")
        or _run_git_command("show", "-s", "--format=%cI", "HEAD")
    )


def load_build_info() -> BuildInfo:
    """Collect build metadata with graceful fallbacks."""

    commit = _resolve_commit_sha() or "unknown"
    short_commit = commit[:7] if commit not in {None, "unknown"} else "unknown"

    if short_commit == "unknown":
        git_short = _run_git_command("rev-parse", "--short", "HEAD")
        short_commit = git_short or short_commit

    branch = _resolve_branch() or "unknown"
    built_at = _resolve_timestamp()

    if built_at is None:
        logger.debug("Build timestamp unavailable; falling back to python start time")

    return BuildInfo(
        commit=commit,
        short_commit=short_commit,
        branch=branch,
        built_at=built_at,
        python_version=platform.python_version(),
        fastapi_version=fastapi_version,
    )
