"""Unit tests for FastAPI health and status endpoints."""

import httpx
import pytest

from src.api.main import app


@pytest.fixture
async def async_client():
    """Async HTTP client bound directly to FastAPI app via ASGITransport."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


async def test_health_endpoint(async_client: httpx.AsyncClient):
    """Verify /api/health responds with 200 OK."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "has_api_key" in data
    assert "cache_enabled" in data


async def test_status_endpoint(async_client: httpx.AsyncClient):
    """Verify /api/status exposes configuration details."""
    response = await async_client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "base_url" in data
    assert "cached_files_count" in data
