"""Data contracts for Market State Engine (Hari 2).

Defines the structured representations for:
- Raw financial metrics before normalization (MetricSet)
- Peer-normalized z-scores after robust statistics (PeerZScores)
- Complete company state with provenance (CompanyState)
- Subsector statistical profiles (SubsectorProfile)
- Pipeline result container (MarketStateResult)

All metric fields are Optional[float]: None means data unavailable or
formula produced undefined result (division by zero, negative equity, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CompanyInfo:
    """Identity of a listed company from Sectors screener.

    Attributes:
        symbol: Ticker without .JK suffix (e.g., "ASII", not "ASII.JK").
        company_name: Full legal name from Sectors API.
        sector: Top-level sector slug (e.g., "consumer-cyclicals").
        subsector: Subsector slug (e.g., "automobiles-components").
    """

    symbol: str
    company_name: str | None
    sector: str
    subsector: str


@dataclass
class MetricSet:
    """Raw financial metrics before peer normalization.

    Mapping to Sectors API fields and formulas:
    - revenue_growth:    (Q_latest.revenue − Q_comp.revenue) / |Q_comp.revenue|
    - earnings_growth:   (Q_latest.earnings − Q_comp.earnings) / |Q_comp.earnings|
    - operating_margin:  Q_latest.operating_pnl / Q_latest.revenue
    - margin_change:     operating_margin(Q_latest) − operating_margin(Q_comp)  (pp)
    - roe_ttm:           sum(4Q earnings) / Q_latest.total_equity
    - price_return:      (daily_close_last − daily_close_first) / daily_close_first
    - pe_ttm:            market_cap / sum(4Q earnings)  [informational, not in discrepancy]
    - pb:                market_cap / Q_latest.total_equity  [informational]

    Where Q_comp = YoY comparison quarter (same quarter prior year) with QoQ fallback.
    """

    revenue_growth: float | None = None
    earnings_growth: float | None = None
    operating_margin: float | None = None
    margin_change: float | None = None
    roe_ttm: float | None = None
    price_return: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None


@dataclass
class PeerZScores:
    """Peer-normalized z-scores after winsorizing + MAD scaling.

    Formula (Iglewicz & Hoaglin, 1993):
        z = (x − median) / (1.4826 × MAD)

    The consistency factor k=1.4826 makes z ≈ standard z-score under normality,
    so thresholds 1.0/1.5 are interpretable as σ-units.

    None means the raw metric was None or sample too small for normalization.
    """

    z_revenue_growth: float | None = None
    z_earnings_growth: float | None = None
    z_margin_change: float | None = None
    z_roe: float | None = None
    z_price_return: float | None = None


@dataclass
class CompanyState:
    """Complete company representation — output of Hari 2 engine.

    Corresponds to §6.1 CompanyState in project.md, enriched with
    peer_z scores and inline provenance metadata.
    """

    symbol: str
    company_name: str | None
    sector: str
    subsector: str

    # Layer 1: raw metrics
    raw_metrics: MetricSet

    # Layer 2: peer-normalized z-scores (within subsector context)
    peer_z: PeerZScores

    # Provenance metadata (inline, not a separate lineage system — per §6.1)
    growth_period: str | None = None  # e.g., "Q2 2026 vs Q2 2025 (YoY)"
    growth_method: str | None = None  # "YoY" or "QoQ"
    price_period: str | None = None  # e.g., "2026-08-11 to 2026-09-09"
    data_timestamp: str | None = None


@dataclass
class MetricDistribution:
    """Distribution statistics for one metric within one subsector.

    Computed after winsorizing (1%/99%) on the raw metric values.
    """

    median: float
    mad: float
    scaled_mad: float  # 1.4826 × MAD (robust σ estimator)
    p1: float  # 1st percentile bound (winsorizing lower clip)
    p99: float  # 99th percentile bound (winsorizing upper clip)
    n_valid: int  # number of companies with valid data for this metric
    was_winsorized: bool  # True if n >= 5 and winsorizing was applied


@dataclass
class SubsectorProfile:
    """Complete statistical profile for one subsector."""

    subsector: str
    sector: str
    n_companies: int  # total companies in subsector
    n_with_metrics: int  # companies with at least one valid metric
    distributions: dict[str, MetricDistribution] = field(default_factory=dict)


@dataclass
class UniverseStats:
    """Summary statistics for the full scan universe."""

    total_subsectors_scanned: int
    total_companies_universe: int  # all non-financial companies
    total_with_data: int  # companies with ≥ 1 valid metric
    total_excluded_financial: int  # companies in financial sector


@dataclass
class MarketStateResult:
    """Complete output of the Hari 2 Market State Engine pipeline."""

    companies: list[CompanyState]
    subsector_profiles: dict[str, SubsectorProfile]
    universe_stats: UniverseStats
    methodology_notes: list[str] = field(default_factory=list)
