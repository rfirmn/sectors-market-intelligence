"""Unit tests for SnapshotCache module."""

from pathlib import Path

from src.client.cache import SnapshotCache


def test_cache_miss_initially(snapshot_cache: SnapshotCache):
    """Test that a non-existent cache key returns None."""
    data = snapshot_cache.get("subsectors/")
    assert data is None
    assert not snapshot_cache.exists("subsectors/")


def test_cache_set_and_get(snapshot_cache: SnapshotCache):
    """Test storing and retrieving valid data from cache."""
    test_data = [{"sector": "basic-materials", "sub_sectors": ["metals-mining"]}]
    path = snapshot_cache.set("subsectors/", None, test_data)

    assert path.exists()
    assert snapshot_cache.exists("subsectors/")

    retrieved = snapshot_cache.get("subsectors/")
    assert retrieved == test_data


def test_cache_with_params(snapshot_cache: SnapshotCache):
    """Test that different parameters generate distinct cache entries."""
    data_1 = [{"symbol": "ASII"}]
    data_2 = [{"symbol": "BBCA"}]

    snapshot_cache.set("companies/", {"sub_sector": "automobiles"}, data_1)
    snapshot_cache.set("companies/", {"sub_sector": "banks"}, data_2)

    res_1 = snapshot_cache.get("companies/", {"sub_sector": "automobiles"})
    res_2 = snapshot_cache.get("companies/", {"sub_sector": "banks"})

    assert res_1 == data_1
    assert res_2 == data_2


def test_cache_expiration_and_fallback(temp_cache_dir: Path):
    """Test TTL expiration and ignore_ttl fallback."""
    # Cache with 0 hours TTL isn't expiring, so let's test with tiny TTL logic
    cache = SnapshotCache(cache_dir=temp_cache_dir, enabled=True, ttl_hours=1)
    test_data = {"price": 1000}
    cache.set("daily/ASII/", None, test_data)

    # Immediately should hit
    assert cache.get("daily/ASII/") == test_data

    # Simulate expired cache file by modifying timestamp
    cache_path = cache.get_cache_path("daily/ASII/")
    import json

    with open(cache_path, encoding="utf-8") as f:
        content = json.load(f)
    content["_metadata"]["timestamp"] = "2020-01-01T00:00:00+00:00"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(content, f)

    # With normal get, expired returns None
    assert cache.get("daily/ASII/") is None

    # With ignore_ttl=True (offline fallback), it returns the data
    assert cache.get("daily/ASII/", ignore_ttl=True) == test_data
