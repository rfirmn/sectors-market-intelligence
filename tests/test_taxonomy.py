"""Unit tests for taxonomy and universe builder (src/engine/taxonomy.py).

Tests cover:
- Financial sector exclusion logic
- Non-financial sector preservation
- .JK symbol suffix stripping
- Empty subsector handling
- CompanyInfo construction from screener response
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.engine.taxonomy import (
    build_universe,
    filter_non_financial_subsectors,
    is_financial_sector,
    strip_jk_suffix,
)

# ──────────────────────────────────────────────────────────────────────
# strip_jk_suffix()
# ──────────────────────────────────────────────────────────────────────


class TestStripJkSuffix:
    def test_removes_jk(self):
        """Standard .JK suffix is removed."""
        assert strip_jk_suffix("ASII.JK") == "ASII"

    def test_no_suffix_unchanged(self):
        """Symbol without .JK is returned unchanged."""
        assert strip_jk_suffix("ASII") == "ASII"

    def test_lowercase_jk_not_stripped(self):
        """Only exact '.JK' (uppercase) is stripped."""
        assert strip_jk_suffix("ASII.jk") == "ASII.jk"

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert strip_jk_suffix("") == ""


# ──────────────────────────────────────────────────────────────────────
# is_financial_sector()
# ──────────────────────────────────────────────────────────────────────


class TestIsFinancialSector:
    def test_financial_detected(self):
        assert is_financial_sector("financials") is True

    def test_financial_case_insensitive(self):
        assert is_financial_sector("Financials") is True
        assert is_financial_sector("FINANCIALS") is True

    def test_non_financial(self):
        assert is_financial_sector("consumer-cyclicals") is False
        assert is_financial_sector("energy") is False


# ──────────────────────────────────────────────────────────────────────
# filter_non_financial_subsectors()
# ──────────────────────────────────────────────────────────────────────


class TestFilterNonFinancialSubsectors:
    def test_financial_sectors_excluded(self):
        """Banks, insurance, financing-service are excluded."""
        subsectors = [
            {"sector": "financials", "subsector": "banks"},
            {"sector": "financials", "subsector": "insurance"},
            {"sector": "financials", "subsector": "financing-service"},
            {"sector": "consumer-cyclicals", "subsector": "automobiles-components"},
            {"sector": "energy", "subsector": "oil-gas-coal"},
        ]
        result = filter_non_financial_subsectors(subsectors)
        names = [r["subsector"] for r in result]

        assert "banks" not in names
        assert "insurance" not in names
        assert "financing-service" not in names
        assert "automobiles-components" in names
        assert "oil-gas-coal" in names
        assert len(result) == 2

    def test_non_financial_preserved(self):
        """All non-financial subsectors pass through."""
        subsectors = [
            {"sector": "basic-materials", "subsector": "metals-mining"},
            {"sector": "technology", "subsector": "software-it-services"},
            {"sector": "healthcare", "subsector": "pharmaceuticals"},
        ]
        result = filter_non_financial_subsectors(subsectors)
        assert len(result) == 3

    def test_empty_input(self):
        """Empty list returns empty list."""
        assert filter_non_financial_subsectors([]) == []


# ──────────────────────────────────────────────────────────────────────
# build_universe() — with mocked SectorsClient
# ──────────────────────────────────────────────────────────────────────


class TestBuildUniverse:
    def _make_mock_client(self):
        """Create a mock SectorsClient with realistic responses."""
        client = MagicMock()

        # Mock subsectors response
        client.get_subsectors.return_value = [
            {"sector": "consumer-cyclicals", "subsector": "automobiles-components"},
            {"sector": "energy", "subsector": "oil-gas-coal"},
            {"sector": "financials", "subsector": "banks"},
            {"sector": "financials", "subsector": "insurance"},
        ]

        # Mock companies response (paginated format)
        def mock_get_companies(sub_sector=None, limit=200, offset=0, **kw):
            if sub_sector == "automobiles-components":
                return {
                    "results": [
                        {"symbol": "ASII.JK", "company_name": "Astra International Tbk"},
                        {"symbol": "AUTO.JK", "company_name": "Astra Otoparts Tbk"},
                    ],
                    "pagination": {"has_next": False, "next_offset": None},
                }
            elif sub_sector == "oil-gas-coal":
                return {
                    "results": [
                        {"symbol": "ADRO.JK", "company_name": "Adaro Energy Indonesia Tbk"},
                    ],
                    "pagination": {"has_next": False, "next_offset": None},
                }
            else:
                return {"results": [], "pagination": {"has_next": False}}

        client.get_companies.side_effect = mock_get_companies
        return client

    def test_full_universe_build(self):
        """Build universe excludes financials and builds correct mapping."""
        client = self._make_mock_client()
        universe = build_universe(client)

        # Should have 2 non-financial subsectors
        assert "automobiles-components" in universe
        assert "oil-gas-coal" in universe
        assert "banks" not in universe
        assert "insurance" not in universe

        # Check company count
        assert len(universe["automobiles-components"]) == 2
        assert len(universe["oil-gas-coal"]) == 1

    def test_symbol_jk_stripped(self):
        """Symbols in universe should not have .JK suffix."""
        client = self._make_mock_client()
        universe = build_universe(client)

        for companies in universe.values():
            for c in companies:
                assert not c.symbol.endswith(".JK"), f"Symbol {c.symbol} still has .JK"

    def test_company_info_fields(self):
        """CompanyInfo objects have correct sector/subsector from parent."""
        client = self._make_mock_client()
        universe = build_universe(client)

        asii = universe["automobiles-components"][0]
        assert asii.symbol == "ASII"
        assert asii.company_name == "Astra International Tbk"
        assert asii.sector == "consumer-cyclicals"
        assert asii.subsector == "automobiles-components"

    def test_empty_subsector_skipped(self):
        """Subsector with 0 companies is not included in universe."""
        client = MagicMock()
        client.get_subsectors.return_value = [
            {"sector": "testing", "subsector": "empty-sector"},
        ]
        client.get_companies.return_value = {
            "results": [],
            "pagination": {"has_next": False},
        }

        universe = build_universe(client)
        assert "empty-sector" not in universe
