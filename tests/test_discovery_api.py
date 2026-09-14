"""API and snapshot replay contracts for Day 3 discovery."""

from __future__ import annotations

import httpx
import pytest

import src.api.main as api_main
from src.api.snapshot_store import SnapshotStore
from src.engine.models import CompanyState, MarketStateResult, MetricSet, PeerZScores, UniverseStats


def _state(symbol: str, value: float) -> CompanyState:
    return CompanyState(
        symbol=symbol,
        company_name=symbol,
        sector="technology",
        subsector="software",
        raw_metrics=MetricSet(
            revenue_growth=0.1 + value / 100,
            earnings_growth=0.1 + value / 100,
            operating_margin=0.1 + value / 100,
            margin_change=0.01 + value / 1000,
            price_return=0.01,
            pb=5 - value / 10,
        ),
        peer_z=PeerZScores(
            z_revenue_growth=value,
            z_earnings_growth=value,
            z_margin_change=value,
            z_price_return=-value / 2,
        ),
        growth_period="2026-06-30 vs 2025-06-30 (YoY)",
        price_period="2026-08-01 to 2026-08-30",
        financial_period="2026-06-30",
        price_end_date="2026-08-30",
        market_cap=1_000_000_000,
        market_cap_date="2026-08-30",
        latest_equity=500_000_000,
    )


@pytest.fixture
def discovery_snapshot(tmp_path, monkeypatch) -> str:
    store = SnapshotStore(tmp_path / "snapshots")
    monkeypatch.setattr(api_main, "_snapshot_store", store)
    state = MarketStateResult(
        companies=[_state(f"S{i}", float(i)) for i in range(8)],
        subsector_profiles={},
        universe_stats=UniverseStats(1, 8, 8, 0),
    )
    return store.save(state, source_mode="cached", manifest={"requested_companies": 8})


@pytest.fixture
async def discovery_client():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api_main.app), base_url="http://test"
    ) as client:
        yield client


async def test_discovery_options_search_and_overview(
    discovery_client: httpx.AsyncClient, discovery_snapshot: str
) -> None:
    options = await discovery_client.get("/api/discovery/options")
    assert options.status_code == 200
    assert discovery_snapshot in options.json()["snapshot_ids"]

    search = await discovery_client.post(
        "/api/opportunities/search",
        json={"snapshot_id": discovery_snapshot, "mandate": {"preset": "dislocation"}},
    )
    assert search.status_code == 200
    assert search.json()["result"]["mandate"]["preset"] == "dislocation"

    overview = await discovery_client.get("/api/overview", params={"snapshot_id": discovery_snapshot})
    assert overview.status_code == 200
    assert sum(overview.json()["discrepancy_distribution"].values()) == 8


async def test_discovery_api_rejects_unknown_snapshot_and_invalid_mandate(
    discovery_client: httpx.AsyncClient,
) -> None:
    missing = await discovery_client.get("/api/overview", params={"snapshot_id": "missing"})
    assert missing.status_code == 404

    invalid = await discovery_client.post(
        "/api/opportunities/search",
        json={"snapshot_id": "missing", "mandate": {"unknown": True}},
    )
    assert invalid.status_code == 422
