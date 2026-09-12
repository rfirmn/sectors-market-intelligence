"""Market State Engine package (Hari 2).

Public API:
- MarketStateEngine: Pipeline orchestrator
- CompanyState: Output per company
- MarketStateResult: Full pipeline output
- MetricSet: Raw financial metrics
- PeerZScores: Peer-normalized z-scores
- CompanyInfo: Company identity from screener
- SubsectorProfile: Subsector statistical profile
"""

from src.engine.market_state_engine import MarketStateEngine
from src.engine.models import (
    CompanyInfo,
    CompanyState,
    MarketStateResult,
    MetricDistribution,
    MetricSet,
    PeerZScores,
    SubsectorProfile,
    UniverseStats,
)
from src.engine.stats import (
    MAD_CONSISTENCY_FACTOR,
    MIN_SAMPLE_NORMALIZE,
    MIN_SAMPLE_WINSORIZE,
)

__all__ = [
    # Engine
    "MarketStateEngine",
    # Data models
    "CompanyInfo",
    "CompanyState",
    "MarketStateResult",
    "MetricDistribution",
    "MetricSet",
    "PeerZScores",
    "SubsectorProfile",
    "UniverseStats",
    # Constants
    "MAD_CONSISTENCY_FACTOR",
    "MIN_SAMPLE_NORMALIZE",
    "MIN_SAMPLE_WINSORIZE",
]
