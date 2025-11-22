"""Domain-level service exceptions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(eq=False)
class ServiceError(Exception):
    """Base error raised by service-layer code."""

    message: str
    status_code: int = 500
    detail: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover - repr helper
        return self.message


class NotFoundError(ServiceError):
    """Raised when an entity cannot be located."""

    status_code: int = 404


class ValidationError(ServiceError):
    """Raised for domain validation issues."""

    status_code: int = 422


class ConflictError(ServiceError):
    """Raised when the requested operation conflicts with existing state."""

    status_code: int = 409


class RateLimitExceeded(ServiceError):
    """Raised when a caller exceeds a rate limit."""

    status_code: int = 429
