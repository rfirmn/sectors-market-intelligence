"""FastAPI application entrypoint for Market Intelligence Agent.

Serves endpoints for the 3 frontend areas:
1. /api/overview       -> Area 1: Market Scan Overview
2. /api/opportunities  -> Area 2: Opportunity Feed (Ranked Candidates)
3. /api/memo/{symbol}  -> Area 3: Interactive Drilldown & Full Investment Memo
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings

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
