"""Unit tests for robust statistics engine (src/engine/stats.py).

Tests cover:
- Percentile computation with interpolation
- Winsorizing (clipping + small-sample passthrough)
- Robust scale (median, MAD, scaled_MAD) with edge cases
- Peer z-score with guards (small sample, MAD=0)
- Full subsector z-score pipeline with synthetic data
"""

import pytest

from src.engine.models import MetricSet
from src.engine.stats import (
    MAD_CONSISTENCY_FACTOR,
    MAD_ZERO_FALLBACK_FRACTION,
    MIN_SAMPLE_NORMALIZE,
    compute_subsector_zscores,
    peer_z,
    percentile,
    robust_scale,
    winsorize,
)

# ──────────────────────────────────────────────────────────────────────
# percentile()
# ──────────────────────────────────────────────────────────────────────


class TestPercentile:
    def test_basic_median(self):
        """p=0.5 on [1,2,3,4,5] → 3.0."""
        assert percentile([1, 2, 3, 4, 5], 0.5) == 3.0

    def test_interpolation(self):
        """Fractional index → linear interpolation."""
        # p=0.25 on [0,10,20,30] → index=0.75, lerp(0,10,0.75) = 7.5
        result = percentile([0, 10, 20, 30], 0.25)
        assert result == pytest.approx(7.5)

    def test_boundaries(self):
        """p=0 returns min, p=1 returns max."""
        data = [10, 20, 30]
        assert percentile(data, 0.0) == 10
        assert percentile(data, 1.0) == 30

    def test_single_element(self):
        """Single element → always returns that element."""
        assert percentile([42.0], 0.0) == 42.0
        assert percentile([42.0], 0.5) == 42.0
        assert percentile([42.0], 1.0) == 42.0

    def test_empty_raises(self):
        """Empty list → ValueError."""
        with pytest.raises(ValueError, match="empty"):
            percentile([], 0.5)

    def test_out_of_range_raises(self):
        """p outside [0,1] → ValueError."""
        with pytest.raises(ValueError, match="must be in"):
            percentile([1, 2, 3], 1.5)


# ──────────────────────────────────────────────────────────────────────
# winsorize()
# ──────────────────────────────────────────────────────────────────────


class TestWinsorize:
    def test_clips_extremes(self):
        """Extreme value is clipped to p99 bound."""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]
        result = winsorize(data)
        # 100 should be clipped down to p99
        assert max(result) < 100
        # Middle values should be within clipping bounds and unchanged
        assert result[4] == 5
        assert result[5] == 6
        # Extremes are clipped to percentile bounds
        assert result[0] >= 1  # clipped up to p01
        assert result[9] < 100  # clipped down to p99

    def test_small_sample_noop(self):
        """n < MIN_SAMPLE_WINSORIZE → no clipping, returns copy."""
        data = [1, 2, 100]
        result = winsorize(data)
        assert result == [1, 2, 100]
        assert result is not data  # must be a copy

    def test_all_identical(self):
        """All identical values → output equals input."""
        data = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0]
        result = winsorize(data)
        assert result == data

    def test_preserves_length(self):
        """Output always has same length as input."""
        data = list(range(20))
        assert len(winsorize(data)) == len(data)


# ──────────────────────────────────────────────────────────────────────
# robust_scale()
# ──────────────────────────────────────────────────────────────────────


class TestRobustScale:
    def test_normal_distribution(self):
        """[1,2,3,4,5] → median=3, MAD=1, scaled=1.4826."""
        med, mad, scaled = robust_scale([1, 2, 3, 4, 5])
        assert med == 3.0
        assert mad == 1.0
        assert scaled == pytest.approx(MAD_CONSISTENCY_FACTOR * 1.0)

    def test_all_identical(self):
        """All values identical → MAD=0, scaled uses fallback."""
        med, mad, scaled = robust_scale([5.0, 5.0, 5.0])
        assert med == 5.0
        assert mad == 0.0
        # Fallback: |5.0| × 0.01 = 0.05
        assert scaled == pytest.approx(5.0 * MAD_ZERO_FALLBACK_FRACTION)

    def test_all_zero(self):
        """All zeros → median=0, MAD=0, scaled=0."""
        med, mad, scaled = robust_scale([0.0, 0.0, 0.0])
        assert med == 0.0
        assert mad == 0.0
        assert scaled == 0.0

    def test_single_value(self):
        """Single value → MAD=0, fallback applied."""
        med, mad, scaled = robust_scale([42.0])
        assert med == 42.0
        assert mad == 0.0
        assert scaled == pytest.approx(42.0 * MAD_ZERO_FALLBACK_FRACTION)

    def test_empty_raises(self):
        """Empty list → ValueError."""
        with pytest.raises(ValueError):
            robust_scale([])

    def test_even_length(self):
        """Even-length list → median is average of two middle values."""
        med, _, _ = robust_scale([1, 2, 3, 4])
        assert med == 2.5


# ──────────────────────────────────────────────────────────────────────
# peer_z()
# ──────────────────────────────────────────────────────────────────────


class TestPeerZ:
    def test_normal(self):
        """Standard z-score computation."""
        # value=10, median=8, scaled_mad=2, n=20
        z = peer_z(10.0, 8.0, 2.0, 20)
        assert z == pytest.approx(1.0)

    def test_at_median(self):
        """Value equals median → z = 0."""
        z = peer_z(8.0, 8.0, 2.0, 20)
        assert z == 0.0

    def test_below_median(self):
        """Value below median → negative z."""
        z = peer_z(6.0, 8.0, 2.0, 20)
        assert z == pytest.approx(-1.0)

    def test_small_sample(self):
        """n < MIN_SAMPLE_NORMALIZE → returns 0.0."""
        z = peer_z(100.0, 8.0, 2.0, MIN_SAMPLE_NORMALIZE - 1)
        assert z == 0.0

    def test_scaled_mad_zero(self):
        """scaled_mad = 0 → returns 0.0 (no information)."""
        z = peer_z(100.0, 8.0, 0.0, 20)
        assert z == 0.0


# ──────────────────────────────────────────────────────────────────────
# compute_subsector_zscores() — Integration
# ──────────────────────────────────────────────────────────────────────


class TestSubsectorZScores:
    def test_full_pipeline(self):
        """10 synthetic companies → verify z-score properties."""
        companies = {}
        for i in range(10):
            companies[f"SYM{i}"] = MetricSet(
                revenue_growth=0.05 * (i - 5),  # -0.25 to +0.20
                earnings_growth=0.10 * (i - 5),  # -0.50 to +0.40
                margin_change=0.01 * (i - 5),  # -0.05 to +0.04
                roe_ttm=0.08 + 0.02 * i,  # 0.08 to 0.26
                price_return=0.02 * (i - 5),  # -0.10 to +0.08
            )

        z_scores, profile = compute_subsector_zscores(companies, "test-sub", "test-sec")

        # All 10 companies should have z-scores
        assert len(z_scores) == 10

        # Profile should record correct sample count
        assert profile.n_companies == 10
        assert profile.n_with_metrics == 10

        # Median z-score across all companies should be near 0
        all_z_rev: list[float] = [
            z for s in z_scores if (z := z_scores[s].z_revenue_growth) is not None
        ]
        median_z = sorted(all_z_rev)[len(all_z_rev) // 2]
        assert abs(median_z) < 0.15

        # No z-score should be astronomically large (scaling check)
        for sym, zs in z_scores.items():
            for field_name in ("z_revenue_growth", "z_earnings_growth", "z_margin_change"):
                val = getattr(zs, field_name)
                if val is not None:
                    assert abs(val) < 10.0, f"{sym}.{field_name} = {val} is too extreme"

    def test_single_company(self):
        """Subsector with 1 company → all z = 0.0 (n < MIN_SAMPLE)."""
        companies = {
            "SOLO": MetricSet(
                revenue_growth=0.15,
                earnings_growth=0.20,
                margin_change=0.03,
            )
        }
        z_scores, profile = compute_subsector_zscores(companies)

        assert z_scores["SOLO"].z_revenue_growth == 0.0
        assert z_scores["SOLO"].z_earnings_growth == 0.0
        assert z_scores["SOLO"].z_margin_change == 0.0

    def test_all_none_metrics(self):
        """Company with all None metrics → all z remain None."""
        companies = {
            "EMPTY": MetricSet(),
            "OK": MetricSet(revenue_growth=0.10),
            "OK2": MetricSet(revenue_growth=0.20),
            "OK3": MetricSet(revenue_growth=0.05),
        }
        z_scores, _ = compute_subsector_zscores(companies)

        # EMPTY has no data → all z should be None
        assert z_scores["EMPTY"].z_revenue_growth is None
        assert z_scores["EMPTY"].z_earnings_growth is None

    def test_distributions_recorded(self):
        """Profile contains distribution stats for each metric."""
        companies = {}
        for i in range(8):
            companies[f"C{i}"] = MetricSet(
                revenue_growth=0.05 * i,
                price_return=0.01 * i,
            )

        _, profile = compute_subsector_zscores(companies, "test-sub")

        assert "revenue_growth" in profile.distributions
        assert "price_return" in profile.distributions
        assert profile.distributions["revenue_growth"].n_valid == 8
        assert profile.distributions["revenue_growth"].was_winsorized is True
        assert profile.distributions["revenue_growth"].scaled_mad > 0
