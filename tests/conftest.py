"""Pytest fixtures for unit and integration testing."""

from pathlib import Path

import pytest

from src.client.cache import SnapshotCache
from src.client.sectors_client import SectorsClient
from src.config import Settings


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Provide a clean temporary directory for caching tests."""
    cache_path = tmp_path / "test_cache"
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


@pytest.fixture
def snapshot_cache(temp_cache_dir: Path) -> SnapshotCache:
    """Create a SnapshotCache instance pointing to a temporary directory."""
    return SnapshotCache(cache_dir=temp_cache_dir, enabled=True, ttl_hours=24)


@pytest.fixture
def test_settings(temp_cache_dir: Path) -> Settings:
    """Provide isolated test settings with mock credentials."""
    return Settings(
        SECTORS_API_KEY="test_mock_api_key_12345",
        SECTORS_BASE_URL="https://api.sectors.app/v2/",
        SECTORS_CACHE_DIR=temp_cache_dir,
        SECTORS_CACHE_ENABLED=True,
        SECTORS_RATE_LIMIT_DELAY=0.0,
        SECTORS_MAX_RETRIES=2,
    )


@pytest.fixture
def client(test_settings: Settings, snapshot_cache: SnapshotCache) -> SectorsClient:
    """Create a SectorsClient instance with test settings and cache."""
    return SectorsClient(
        api_key=test_settings.sectors_api_key,
        base_url=test_settings.sectors_base_url,
        cache=snapshot_cache,
        cfg=test_settings,
    )
