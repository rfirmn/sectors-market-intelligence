"""Local Snapshot Cache for Sectors API responses.

Fulfills Demo Reliability Mechanism (§6.10):
- Stores successful API responses locally as inspectable JSON files.
- Provides sub-millisecond retrieval during repeated development runs.
- Offers automatic fail-safe fallback if network or rate limit issues occur.
"""

import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.client.exceptions import CacheError
from src.config import settings

logger = logging.getLogger(__name__)


class SnapshotCache:
    """Deterministic, human-readable file-based JSON cache."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        enabled: bool | None = None,
        ttl_hours: int | None = None,
        offline_fallback: bool | None = None,
    ):
        self.cache_dir = Path(cache_dir or settings.sectors_cache_dir)
        self.enabled = settings.sectors_cache_enabled if enabled is None else enabled
        self.ttl_hours = settings.sectors_cache_ttl_hours if ttl_hours is None else ttl_hours
        self.offline_fallback = (
            settings.sectors_offline_fallback if offline_fallback is None else offline_fallback
        )

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_cache_filename(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        """Create a clean, human-readable yet unique filename for each request."""
        clean_ep = endpoint.strip("/").replace("/", "_")
        clean_ep = re.sub(r"[^\w\-]", "_", clean_ep)

        params_str = ""
        if params:
            # Sort keys for deterministic hash
            sorted_items = sorted((str(k), str(v)) for k, v in params.items() if v is not None)
            flat_items = "_".join(f"{k}-{v}" for k, v in sorted_items)
            clean_params = re.sub(r"[^\w\-]", "_", flat_items)
            # If short enough, keep in filename; otherwise hash it
            if len(clean_params) <= 40:
                params_str = f"__{clean_params}"
            else:
                params_hash = hashlib.sha256(flat_items.encode("utf-8")).hexdigest()[:10]
                params_str = f"__{params_hash}"

        return f"{clean_ep}{params_str}.json"

    def get_cache_path(self, endpoint: str, params: dict[str, Any] | None = None) -> Path:
        """Get absolute path to cache file for a given endpoint and params."""
        filename = self._generate_cache_filename(endpoint, params)
        return self.cache_dir / filename

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        ignore_ttl: bool = False,
    ) -> Any | None:
        """Retrieve cached data if present and valid.

        Args:
            endpoint: API path (e.g. 'subsectors/', 'financials/quarterly/ASII/')
            params: Query parameter dict
            ignore_ttl: If True, return cached content even if expired (offline fallback)

        Returns:
            Parsed JSON data if cache hit, else None.
        """
        if not self.enabled:
            return None

        cache_path = self.get_cache_path(endpoint, params)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                payload = json.load(f)

            # Validate cache structure
            if not isinstance(payload, dict) or "_metadata" not in payload:
                return payload  # Raw json support

            metadata = payload["_metadata"]
            saved_time_str = metadata.get("timestamp")

            if not ignore_ttl and self.ttl_hours > 0 and saved_time_str:
                saved_time = datetime.fromisoformat(saved_time_str)
                age_seconds = (datetime.now(UTC) - saved_time).total_seconds()
                if age_seconds > self.ttl_hours * 3600:
                    logger.debug(
                        "Cache expired for %s (age: %.1f hours)", endpoint, age_seconds / 3600
                    )
                    return None

            logger.info("Cache HIT: %s -> %s", endpoint, cache_path.name)
            return payload.get("data")

        except Exception as e:
            logger.warning("Error reading cache file %s: %s", cache_path, e)
            return None

    def set(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        data: Any,
    ) -> Path:
        """Store API response to local disk snapshot.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            data: The JSON serializable data payload

        Returns:
            Path of the saved cache file.
        """
        if not self.enabled:
            return self.get_cache_path(endpoint, params)

        cache_path = self.get_cache_path(endpoint, params)
        payload = {
            "_metadata": {
                "endpoint": endpoint,
                "params": params or {},
                "timestamp": datetime.now(UTC).isoformat(),
                "ttl_hours": self.ttl_hours,
            },
            "data": data,
        }

        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            logger.info("Saved snapshot cache: %s", cache_path.name)
            return cache_path
        except Exception as e:
            raise CacheError(f"Failed to write cache to {cache_path}: {e}") from e

    def exists(self, endpoint: str, params: dict[str, Any] | None = None) -> bool:
        """Check if cache file exists on disk."""
        return self.get_cache_path(endpoint, params).exists()
