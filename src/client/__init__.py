"""Sectors Client package."""

from src.client.cache import SnapshotCache
from src.client.exceptions import (
    AuthenticationError,
    CacheError,
    RateLimitExceededError,
    ResourceNotFoundError,
    SectorsAPIError,
    ServerError,
)
from src.client.sectors_client import SectorsClient

__all__ = [
    "SectorsClient",
    "SnapshotCache",
    "SectorsAPIError",
    "AuthenticationError",
    "ResourceNotFoundError",
    "RateLimitExceededError",
    "ServerError",
    "CacheError",
]
