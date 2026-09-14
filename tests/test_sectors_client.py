"""Unit tests for SectorsClient with offline respx mocks."""

import httpx
import pytest
import respx

from src.client.exceptions import (
    AuthenticationError,
    ResourceNotFoundError,
    ServerError,
)
from src.client.sectors_client import SectorsClient


@respx.mock
def test_client_headers(client: SectorsClient):
    """Verify that Sectors Global API Key is sent in Authorization header."""
    route = respx.get("https://api.sectors.app/v2/subsectors/").respond(
        200, json=[{"sector": "technology", "sub_sectors": ["software"]}]
    )

    data = client.get_subsectors()
    assert len(data) == 1
    assert data[0]["sector"] == "technology"
    assert route.called
    # Sectors API expects bare API key in Authorization header
    assert route.calls.last.request.headers["Authorization"] == "test_mock_api_key_12345"


@respx.mock
def test_client_cache_hit_avoids_network(client: SectorsClient):
    """Verify that an existing cache hit executes in 0 network calls."""
    # Pre-populate cache
    client.cache.set("subsectors/", None, [{"sector": "cached-energy"}])

    route = respx.get("https://api.sectors.app/v2/subsectors/").respond(200, json=[])

    data = client.get_subsectors()
    assert data == [{"sector": "cached-energy"}]
    assert not route.called


@respx.mock
def test_client_force_refresh_bypasses_cache(client: SectorsClient):
    """Verify that force_refresh=True ignores cache and calls API."""
    client.cache.set("subsectors/", None, [{"sector": "old-cache"}])

    route = respx.get("https://api.sectors.app/v2/subsectors/").respond(
        200, json=[{"sector": "fresh-live"}]
    )

    data = client.get_subsectors(force_refresh=True)
    assert data == [{"sector": "fresh-live"}]
    assert route.called


@respx.mock
def test_client_error_401(client: SectorsClient):
    """Verify 401 raises AuthenticationError."""
    respx.get("https://api.sectors.app/v2/subsectors/").respond(401, json={"detail": "Invalid Key"})

    with pytest.raises(AuthenticationError):
        client.get_subsectors()


@respx.mock
def test_client_error_404(client: SectorsClient):
    """Verify 404 raises ResourceNotFoundError."""
    respx.get("https://api.sectors.app/v2/daily/UNKNOWN/").respond(
        404, json={"detail": "Not found"}
    )

    with pytest.raises(ResourceNotFoundError):
        client.get_daily_transactions("UNKNOWN")


@respx.mock
def test_client_error_500_server_error(client: SectorsClient):
    """Verify 500 raises ServerError."""
    respx.get("https://api.sectors.app/v2/subsectors/").respond(500, text="Internal Error")

    with pytest.raises(ServerError):
        client.get_subsectors()


@respx.mock
def test_client_offline_fallback_on_network_failure(client: SectorsClient):
    """Verify Demo Reliability Mechanism (§6.10): fall back to cached snapshot when offline."""
    # Seed cache
    client.cache.set("daily/ASII/", None, [{"close": 5000}])

    # Simulate network failure on live request
    respx.get("https://api.sectors.app/v2/daily/ASII/").mock(
        side_effect=httpx.NetworkError("DNS failure")
    )

    # force_refresh tries live request, fails, and falls back to snapshot cache
    data = client.get_daily_transactions("ASII", force_refresh=True)
    assert data == [{"close": 5000}]


@respx.mock
def test_convenience_methods(client: SectorsClient):
    """Test standard convenience methods across the 5 endpoint families."""
    respx.get("https://api.sectors.app/v2/financials/quarterly/BBCA/?n_quarters=4").respond(
        200, json=[{"year": 2024, "quarter": 4, "revenue": 100}]
    )
    respx.get("https://api.sectors.app/v2/filings/?symbol=BBCA&limit=5").respond(
        200, json=[{"id": 1, "title": "Laporan Insider"}]
    )
    respx.get("https://api.sectors.app/v2/foreign-flow/BBCA/").respond(
        200, json=[{"date": "2026-03-01", "net_foreign": 5000000}]
    )

    fin = client.get_financials_quarterly("bbca", n_quarters=4)
    assert fin[0]["revenue"] == 100

    filings = client.get_filings("bbca", limit=5)
    assert filings[0]["title"] == "Laporan Insider"

    flow = client.get_foreign_flow("BBCA")
    assert flow[0]["net_foreign"] == 5000000


@respx.mock
def test_companies_subsector_uses_supported_where_parameter(client: SectorsClient):
    """The companies screener accepts ``where``, not a raw sub_sector query key."""
    route = respx.get(
        "https://api.sectors.app/v2/companies/",
        params={"limit": "200", "offset": "0", "where": "sub_sector = 'software-it-services'"},
    ).respond(200, json={"results": [], "pagination": {"has_next": False}})

    assert client.get_companies(sub_sector="software-it-services", limit=200) == {
        "results": [],
        "pagination": {"has_next": False},
    }
    assert route.called
