"""Unit tests for FastAPI health and status endpoints."""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify /api/health responds with 200 OK."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "has_api_key" in data
    assert "cache_enabled" in data


def test_status_endpoint():
    """Verify /api/status exposes configuration details."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "base_url" in data
    assert "cached_files_count" in data
