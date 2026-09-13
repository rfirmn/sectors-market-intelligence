"""Robust statistics for peer-normalized z-score computation.

Implements the mathematical core of the Market State Engine (§6.1 project.md):
- Percentile computation with linear interpolation
- Winsorizing at 1%/99% to contain outlier influence
- Median and MAD (Median Absolute Deviation) as robust location/scale estimators
- Peer z-score with consistency factor k=1.4826 (Iglewicz & Hoaglin, 1993)

All functions are pure Python (no numpy/scipy dependency).

Interpretation:
- peer_z(median_company) = 0.0
- peer_z > 0 → above subsector median; < 0 → below
- Normal consistency of MAD is asymptotic, not a probability calibration.
- Robust center/scale do not bound an individual score using a raw numerator.
- Insufficient samples or degenerate scale produce None, not a neutral score.
"""

from __future__ import annotations

import logging
import math
import statistics as pystats
from collections.abc import Sequence

from src.engine.models import (
    MetricDistribution,
    MetricSet,
    PeerZScores,
    SubsectorProfile,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Constants (locked a priori — not tuned to fit results)
# ──────────────────────────────────────────────────────────────────────

MAD_CONSISTENCY_FACTOR = 1.4826
"""Scaling factor that makes 1.4826 × MAD a consistent estimator of σ
under the assumption of normality. This is the reciprocal of
Φ⁻¹(3/4) ≈ 0.6745. Reference: Iglewicz & Hoaglin (1993)."""

MIN_SAMPLE_WINSORIZE = 5
"""Minimum sample size for winsorizing to be meaningful. Below this,
percentile-based clipping has no statistical power."""

MIN_SAMPLE_NORMALIZE = 3
"""Minimum sample size for z-score normalization. Below this, median
and MAD are unreliable and peer_z returns None. This is a computational
minimum, not a guarantee of reliable inference at n=3."""

# Names of metrics that participate in z-score normalization
NORMALIZED_METRIC_NAMES = (
    "revenue_growth",
    "earnings_growth",
    "margin_change",
    "roe_ttm",
    "price_return",
)

# Mapping from MetricSet field name → PeerZScores field name
_METRIC_TO_Z_FIELD = {
    "revenue_growth": "z_revenue_growth",
    "earnings_growth": "z_earnings_growth",
    "margin_change": "z_margin_change",
    "roe_ttm": "z_roe",
    "price_return": "z_price_return",
}


# ──────────────────────────────────────────────────────────────────────
# Core Statistical Functions
# ──────────────────────────────────────────────────────────────────────


def percentile(sorted_values: Sequence[float | int], p: float) -> float:
    """Compute the p-th percentile using linear interpolation.

    Args:
        sorted_values: Pre-sorted sequence of numbers (ascending). Must be non-empty.
        p: Percentile in [0, 1]. E.g., 0.01 for 1st percentile.

    Returns:
        Interpolated value at the p-th percentile.

    Raises:
        ValueError: If sorted_values is empty or p is out of range.
    """
    if not sorted_values:
        raise ValueError("Cannot compute percentile of empty list")
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"Percentile p must be in [0, 1], got {p}")

    n = len(sorted_values)
    if n == 1:
        return float(sorted_values[0])

    idx = p * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return float(sorted_values[lo]) * (1.0 - frac) + float(sorted_values[hi]) * frac


def winsorize(
    values: Sequence[float | int],
    p_low: float = 0.01,
    p_high: float = 0.99,
) -> list[float]:
    """Clamp values to percentile bounds to limit outlier influence.

    If sample size < MIN_SAMPLE_WINSORIZE, returns a copy without clipping
    (winsorizing is not meaningful for very small samples).

    Args:
        values: Raw metric values.
        p_low: Lower percentile bound (default 0.01 = 1%).
        p_high: Upper percentile bound (default 0.99 = 99%).

    Returns:
        New list with values clamped to [percentile(p_low), percentile(p_high)].
    """
    if len(values) < MIN_SAMPLE_WINSORIZE:
        return [float(v) for v in values]

    sorted_v = sorted(values)
    lower_bound = percentile(sorted_v, p_low)
    upper_bound = percentile(sorted_v, p_high)
    return [max(lower_bound, min(upper_bound, float(v))) for v in values]


def robust_scale(values: Sequence[float | int]) -> tuple[float, float, float]:
    """Compute robust location and scale estimators.

    Returns:
        Tuple of (median, MAD, scaled_MAD) where:
        - median: Median of values
        - MAD: Median Absolute Deviation = median(|xi - median(x)|)
        - scaled_MAD: 1.4826 × MAD (consistent σ estimator)

    Guards:
        - Empty list → raises ValueError
        - Non-finite or non-numeric data → raises ValueError
        - MAD = 0 → scaled_MAD = 0.0 (can also occur with a majority of ties)
    """
    if not values:
        raise ValueError("Cannot compute robust_scale of empty list")
    if not all(is_finite_number(v) for v in values):
        raise ValueError("robust_scale requires finite numeric values")

    med = pystats.median(values)
    deviations = [abs(v - med) for v in values]
    mad = pystats.median(deviations)

    scaled_mad = MAD_CONSISTENCY_FACTOR * mad

    return med, mad, scaled_mad


def peer_z(
    value: float,
    median: float,
    scaled_mad: float,
    n_sample: int,
) -> float | None:
    """Compute peer-normalized z-score.

    Formula: z = (value - median) / scaled_mad

    Args:
        value: Individual company metric value.
        median: Subsector median for this metric.
        scaled_mad: 1.4826 × MAD for this metric.
        n_sample: Number of companies in the subsector with valid data.

    Returns:
        Z-score, or None if inputs, sample size, or scale are unusable.
    """
    if n_sample < MIN_SAMPLE_NORMALIZE:
        return None
    if not all(is_finite_number(v) for v in (value, median, scaled_mad)):
        return None
    if scaled_mad <= 0.0:
        return None
    result = (value - median) / scaled_mad
    return result if math.isfinite(result) else None


def is_finite_number(value: object) -> bool:
    """Accept JSON numeric values, excluding bool, strings, NaN and infinity."""
    try:
        return (
            isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        )
    except OverflowError:
        return False


# ──────────────────────────────────────────────────────────────────────
# Subsector-Level Normalization Pipeline
# ──────────────────────────────────────────────────────────────────────


def compute_subsector_zscores(
    companies: dict[str, MetricSet],
    subsector: str = "",
    sector: str = "",
) -> tuple[dict[str, PeerZScores], SubsectorProfile]:
    """Compute peer-normalized z-scores for all companies in one subsector.

    Pipeline per metric:
    1. Collect all valid (non-None) values
    2. If n >= MIN_SAMPLE_WINSORIZE: winsorize at 1%/99%
    3. Compute median, MAD, scaled_MAD via robust_scale()
    4. Compute peer_z for each company

    Args:
        companies: Dict mapping symbol → MetricSet for one subsector.
        subsector: Subsector slug for profile metadata.
        sector: Sector slug for profile metadata.

    Returns:
        Tuple of:
        - Dict mapping symbol → PeerZScores
        - SubsectorProfile with distribution statistics
    """
    n_total = len(companies)
    z_scores: dict[str, PeerZScores] = {sym: PeerZScores() for sym in companies}
    distributions: dict[str, MetricDistribution] = {}

    n_with_any_metric = 0
    companies_have_metric = set()

    for metric_name in NORMALIZED_METRIC_NAMES:
        # 1. Collect valid values
        valid: dict[str, float] = {}
        for sym, ms in companies.items():
            val = getattr(ms, metric_name)
            if is_finite_number(val):
                valid[sym] = val
                companies_have_metric.add(sym)

        n_valid = len(valid)
        z_field = _METRIC_TO_Z_FIELD[metric_name]

        if n_valid < 1:
            # No data at all for this metric
            distributions[metric_name] = MetricDistribution(
                median=0.0,
                mad=0.0,
                scaled_mad=0.0,
                p1=0.0,
                p99=0.0,
                n_valid=0,
                was_winsorized=False,
                normalization_status="no_data",
            )
            continue

        raw_values = list(valid.values())

        # 2. Winsorize
        should_winsorize = n_valid >= MIN_SAMPLE_WINSORIZE
        if should_winsorize:
            winsorized_values = winsorize(raw_values)
        else:
            winsorized_values = list(raw_values)

        # 3. Compute robust scale on winsorized values
        med, mad_val, scaled_mad_val = robust_scale(winsorized_values)
        invalid_range = not all(is_finite_number(v) for v in (med, mad_val, scaled_mad_val))
        if invalid_range:
            # Even finite inputs can overflow intermediate float arithmetic.
            # Explicit status distinguishes these placeholders from a valid zero.
            med = mad_val = scaled_mad_val = 0.0

        # Percentile bounds (for profile / debugging)
        sorted_raw = sorted(raw_values)
        p1 = percentile(sorted_raw, 0.01) if n_valid >= 2 else sorted_raw[0]
        p99 = percentile(sorted_raw, 0.99) if n_valid >= 2 else sorted_raw[0]

        distributions[metric_name] = MetricDistribution(
            median=med,
            mad=mad_val,
            scaled_mad=scaled_mad_val,
            p1=p1,
            p99=p99,
            n_valid=n_valid,
            was_winsorized=should_winsorize,
            normalization_status=(
                "invalid_numeric_range"
                if invalid_range
                else "insufficient_sample"
                if n_valid < MIN_SAMPLE_NORMALIZE
                else "degenerate_scale"
                if scaled_mad_val <= 0 or not math.isfinite(scaled_mad_val)
                else "low_sample"
                if n_valid < 8
                else "ok"
            ),
        )

        # 4. Compute peer_z for each company
        for sym, val in valid.items():
            # Retained baseline: winsorizing estimates scale, not score bounds.
            # Alternative bounded scores stay in the offline simulation.
            z_val = peer_z(val, med, scaled_mad_val, n_valid)
            setattr(z_scores[sym], z_field, z_val)

    n_with_any_metric = len(companies_have_metric)

    profile = SubsectorProfile(
        subsector=subsector,
        sector=sector,
        n_companies=n_total,
        n_with_metrics=n_with_any_metric,
        distributions=distributions,
    )

    return z_scores, profile
