"""Taxonomy and universe builder for IDX non-financial companies.

Responsibilities (Task T2.1):
- Fetch subsector taxonomy from Sectors API
- Exclude financial-sector subsectors (banks, insurance, multifinance, etc.)
- Build mapping subsector → list of CompanyInfo (with .JK suffix stripped)
- Handle paginated company lists

Exclusion rationale (§6.1 project.md):
Financial companies use different financial structures (NII, gross loan,
total deposit instead of revenue/margin), making cross-sectional comparison
with non-financial metrics mathematically invalid.
"""

from __future__ import annotations

import logging
from typing import Any

from src.engine.models import CompanyInfo

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

EXCLUDED_SECTOR = "financials"
"""Top-level sector slug to exclude. Subsectors: banks, insurance,
financing-service, investment-service, holding-investment-companies."""

_SCREENER_PAGE_LIMIT = 200
"""Maximum items per page supported by the companies screener endpoint."""

_MAX_COMPANIES_PER_SUBSECTOR = 2000
"""Safety cap to prevent infinite pagination loops."""


# ──────────────────────────────────────────────────────────────────────
# Utility Functions
# ──────────────────────────────────────────────────────────────────────


def strip_jk_suffix(symbol: str) -> str:
    """Remove '.JK' suffix from IDX ticker symbols.

    Screener returns 'ASII.JK' but financial/daily endpoints expect 'ASII'.
    """
    return symbol.removesuffix(".JK")


def is_financial_sector(sector: str) -> bool:
    """Check if a sector slug belongs to the excluded financial sector."""
    return sector.lower().strip() == EXCLUDED_SECTOR


def filter_non_financial_subsectors(
    subsectors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filter out subsectors belonging to the financial sector.

    Args:
        subsectors: Raw API response from GET /v2/subsectors/
                    Each item: {"sector": "...", "subsector": "..."}

    Returns:
        List of non-financial subsector dicts.
    """
    result = []
    excluded_count = 0
    for item in subsectors:
        sector = item.get("sector", "")
        if is_financial_sector(sector):
            excluded_count += 1
            continue
        result.append(item)

    if excluded_count > 0:
        logger.info("Taxonomy: excluded %d financial subsector(s) from universe", excluded_count)

    return result


# ──────────────────────────────────────────────────────────────────────
# Universe Builder (requires SectorsClient instance)
# ──────────────────────────────────────────────────────────────────────


def build_universe(client: Any) -> dict[str, list[CompanyInfo]]:
    """Build mapping of non-financial subsectors → listed companies.

    Pipeline:
    1. Fetch all subsectors from Sectors API
    2. Filter out financial sector
    3. For each non-financial subsector, fetch all companies (paginated)
    4. Strip .JK suffix from symbols
    5. Return dict[subsector_slug, list[CompanyInfo]]

    Args:
        client: SectorsClient instance with get_subsectors() and get_companies().

    Returns:
        Dict mapping subsector slug to list of CompanyInfo objects.
    """
    # 1. Fetch taxonomy
    all_subsectors = client.get_subsectors()
    logger.info("Taxonomy: fetched %d total subsectors", len(all_subsectors))

    # 2. Filter
    non_fin = filter_non_financial_subsectors(all_subsectors)
    logger.info(
        "Taxonomy: %d non-financial subsectors, %d excluded",
        len(non_fin),
        len(all_subsectors) - len(non_fin),
    )

    # 3. Build universe per subsector
    universe: dict[str, list[CompanyInfo]] = {}
    total_companies = 0

    for sub_info in non_fin:
        sector = sub_info["sector"]
        subsector = sub_info["subsector"]
        try:
            companies = _fetch_all_companies_in_subsector(client, sector, subsector)
        except Exception as error:
            # A universe snapshot may be partial under API throttling. Keep
            # successful subsectors rather than discarding the entire scan.
            logger.warning("Taxonomy: failed subsector '%s': %s", subsector, error)
            continue

        if not companies:
            logger.warning("Taxonomy: subsector '%s' has 0 companies, skipping", subsector)
            continue

        universe[subsector] = companies
        total_companies += len(companies)
        logger.debug("Taxonomy: %s → %d companies", subsector, len(companies))

    logger.info(
        "Universe built: %d subsectors, %d total companies",
        len(universe),
        total_companies,
    )
    return universe


def _fetch_all_companies_in_subsector(
    client: Any,
    sector: str,
    subsector: str,
) -> list[CompanyInfo]:
    """Fetch all companies in a subsector with pagination handling.

    Uses the companies screener endpoint with sub_sector filter.
    Paginates until has_next is False or safety cap is reached.
    """
    companies: list[CompanyInfo] = []
    seen_symbols: set[str] = set()
    offset = 0

    while len(companies) < _MAX_COMPANIES_PER_SUBSECTOR:
        # The screener uses `where` param with sub_sector filter
        # But the convenience method uses sub_sector param directly
        response = client.get_companies(
            sub_sector=subsector,
            limit=_SCREENER_PAGE_LIMIT,
            offset=offset,
        )

        # Handle both paginated dict response and direct list response
        if isinstance(response, dict):
            results = response.get("results", [])
            pagination = response.get("pagination", {})
            has_next = pagination.get("has_next", False)
            next_offset = pagination.get("next_offset", offset + _SCREENER_PAGE_LIMIT)
        elif isinstance(response, list):
            results = response
            has_next = False
            next_offset = 0
        else:
            logger.warning("Unexpected response type for companies: %s", type(response))
            break

        for item in results:
            raw_symbol = item.get("symbol", "")
            if not raw_symbol:
                continue

            symbol = strip_jk_suffix(raw_symbol)
            if symbol in seen_symbols:
                logger.warning(
                    "Taxonomy: duplicate symbol %s in subsector %s ignored", symbol, subsector
                )
                continue
            seen_symbols.add(symbol)
            companies.append(
                CompanyInfo(
                    symbol=symbol,
                    company_name=item.get("company_name"),
                    sector=sector,
                    subsector=subsector,
                )
            )

        if not has_next or not results:
            break

        if not isinstance(next_offset, int) or next_offset <= offset:
            logger.warning(
                "Taxonomy: non-advancing pagination for subsector %s, stopping", subsector
            )
            break
        offset = next_offset

    return companies
