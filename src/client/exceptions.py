"""Custom exceptions for Sectors Financial API client."""

from typing import Any


class SectorsAPIError(Exception):
    """Base exception for all Sectors API related errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: Any | None = None,
        endpoint: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.endpoint = endpoint

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"(Status: {self.status_code})")
        if self.endpoint:
            parts.append(f"[Endpoint: {self.endpoint}]")
        return " ".join(parts)


class AuthenticationError(SectorsAPIError):
    """Raised when API Key is missing, invalid, or expired (HTTP 401/403)."""

    pass


class ResourceNotFoundError(SectorsAPIError):
    """Raised when the requested symbol or endpoint is not found (HTTP 404)."""

    pass


class RateLimitExceededError(SectorsAPIError):
    """Raised when Sectors API rate limit has been exceeded (HTTP 429)."""

    pass


class ServerError(SectorsAPIError):
    """Raised when Sectors API encounters a 5xx server error."""

    pass


class CacheError(SectorsAPIError):
    """Raised when local snapshot cache fails to read or write."""

    pass
