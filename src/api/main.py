"""FastAPI application entrypoint for Market Intelligence Agent.

Serves endpoints for the 3 frontend areas:
1. /api/overview       -> Area 1: Market Scan Overview
2. /api/opportunities  -> Area 2: Opportunity Feed (Ranked Candidates)
3. /api/memo/{symbol}  -> Area 3: Interactive Drilldown & Full Investment Memo
"""

import math

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from src.api.snapshot_store import SnapshotStore
from src.config import settings
from src.discovery import DiscoveryEngine, ResearchMandate
from src.discovery.models import PRESET_WEIGHTS

app = FastAPI(
    title="Market Intelligence Agent API",
    version="0.1.0",
    description="Backend API supporting Sectors Hackathon 2026 quantitative-qualitative pipeline",
)

# Enable CORS for frontend UI development (Vite/Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_snapshot_store = SnapshotStore()


class DiscoverySearchRequest(BaseModel):
    """Read-only search request over an already captured snapshot."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    mandate: ResearchMandate = ResearchMandate()


def _snapshot_or_404(snapshot_id: str):
    loaded = _snapshot_store.load(snapshot_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Discovery snapshot not found")
    return loaded


def _discrepancy(value) -> float | None:
    scores = value.peer_z
    inputs = (
        scores.z_revenue_growth,
        scores.z_earnings_growth,
        scores.z_margin_change,
        scores.z_price_return,
    )
    if any(item is None or not math.isfinite(item) for item in inputs):
        return None
    return (inputs[0] + inputs[1] + inputs[2]) / 3 - inputs[3]


@app.get("/api/discovery/options")
def discovery_options() -> dict[str, object]:
    """Describe fixed presets and locally available replay snapshots."""
    return {
        "presets": {name.value: weights.model_dump() for name, weights in PRESET_WEIGHTS.items()},
        "units": {
            "growth_return_margin": "decimal ratio (0.15 = 15%)",
            "margin_change": "decimal ratio (0.02 = 2 percentage points)",
            "pb": "multiple",
            "market_cap": "IDR",
        },
        "capabilities": {
            "transaction_activity_filter": False,
            "pe_or_roe_ranking": False,
            "network_on_search": False,
        },
        "snapshot_ids": _snapshot_store.list_ids(),
    }


@app.post("/api/opportunities/search")
def search_opportunities(request: DiscoverySearchRequest) -> dict[str, object]:
    """Rank one immutable snapshot without fetching market or LLM data."""
    state, payload = _snapshot_or_404(request.snapshot_id)
    result = DiscoveryEngine().discover(
        state.companies,
        request.mandate,
        snapshot_date=payload.get("captured_at"),
    )
    return {
        "snapshot_id": request.snapshot_id,
        "snapshot": {
            "captured_at": payload.get("captured_at"),
            "source_mode": payload.get("source_mode"),
            "warnings": payload.get("warnings", []),
        },
        "result": result.model_dump(mode="json"),
    }


@app.get("/api/overview")
def discovery_overview(snapshot_id: str) -> dict[str, object]:
    """Return raw snapshot coverage and fixed discrepancy histogram."""
    state, payload = _snapshot_or_404(snapshot_id)
    bins = {
        "price_outperforms_fundamentals": 0,
        "neutral_alignment": 0,
        "mild_divergence": 0,
        "medium_opportunity": 0,
        "high_opportunity": 0,
        "not_evaluable": 0,
    }
    for company in state.companies:
        value = _discrepancy(company)
        if value is None:
            bins["not_evaluable"] += 1
        elif value < 0:
            bins["price_outperforms_fundamentals"] += 1
        elif value < 0.5:
            bins["neutral_alignment"] += 1
        elif value < 1.0:
            bins["mild_divergence"] += 1
        elif value <= 1.5:
            bins["medium_opportunity"] += 1
        else:
            bins["high_opportunity"] += 1
    return {
        "snapshot_id": snapshot_id,
        "captured_at": payload.get("captured_at"),
        "source_mode": payload.get("source_mode"),
        "universe": state.universe_stats.__dict__,
        "discrepancy_distribution": bins,
        "warnings": payload.get("warnings", []),
    }


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Health check endpoint verifying configuration status."""
    return {
        "status": "healthy",
        "has_api_key": str(settings.has_valid_api_key),
        "cache_enabled": str(settings.sectors_cache_enabled),
    }


@app.get("/api/status")
def system_status() -> dict[str, object]:
    """Inspect system readiness and cache directory statistics."""
    cache_count = (
        len(list(settings.sectors_cache_dir.glob("*.json")))
        if settings.sectors_cache_dir.exists()
        else 0
    )
    return {
        "base_url": settings.sectors_base_url,
        "cache_directory": str(settings.sectors_cache_dir),
        "cached_files_count": cache_count,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }
