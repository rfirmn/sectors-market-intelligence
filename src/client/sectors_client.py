"""Robust HTTP Client for Sectors Financial API v2.

Features:
- Authentication via Sectors Global API Key
- Tenacity exponential backoff retry on 429 & 5xx errors
- Rate limiting / politeness delay
- Deterministic Snapshot Cache integration (Demo Reliability Mechanism §6.10)
- Graceful offline fallback
- Rich logging
"""

import asyncio
import logging
import time
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.client.cache import SnapshotCache
from src.client.exceptions import (
    AuthenticationError,
    RateLimitExceededError,
    ResourceNotFoundError,
    SectorsAPIError,
    ServerError,
)
from src.config import Settings, settings

logger = logging.getLogger(__name__)


class SectorsClient:
    """Production-grade Sectors API v2 Client with caching and resilience."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        cache: SnapshotCache | None = None,
        cfg: Settings | None = None,
    ):
        self.cfg = cfg or settings
        self.api_key = api_key or self.cfg.sectors_api_key
        self.base_url = (base_url or self.cfg.sectors_base_url).rstrip("/") + "/"
        self.cache = cache or SnapshotCache()
        self.rate_limit_delay = self.cfg.sectors_rate_limit_delay
        self._last_request_time: float = 0.0

        # Base headers
        self._headers = {
            "Authorization": self.api_key.strip(),
            "Content-Type": "application/json",
            "User-Agent": "MarketIntelligenceAgent/0.1.0 (Hackathon-2026)",
        }

    def _apply_rate_limit(self) -> None:
        """Enforce inter-request politeness delay."""
        if self.rate_limit_delay > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
            self._last_request_time = time.time()

    async def _apply_rate_limit_async(self) -> None:
        """Enforce inter-request politeness delay asynchronously."""
        if self.rate_limit_delay > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
            self._last_request_time = time.time()

    def _normalize_symbol(self, symbol: str) -> str:
        """Ensure symbol is uppercase without whitespace."""
        return symbol.strip().upper()

    def _handle_error_response(self, response: httpx.Response, endpoint: str) -> None:
        """Map HTTP error status codes to domain exceptions."""
        status = response.status_code
        try:
            body = response.json()
        except Exception:
            body = response.text

        msg = f"Sectors API request failed: {status} on {endpoint}"

        if status in (401, 403):
            raise AuthenticationError(
                f"Authentication failed ({status}). Please verify your SECTORS_API_KEY in .env.",
                status_code=status,
                response_body=body,
                endpoint=endpoint,
            )
        elif status == 404:
            raise ResourceNotFoundError(
                f"Resource or symbol not found ({status}) on {endpoint}.",
                status_code=status,
                response_body=body,
                endpoint=endpoint,
            )
        elif status == 429:
            raise RateLimitExceededError(
                "Rate limit exceeded (429). Too many requests sent to Sectors API.",
                status_code=status,
                response_body=body,
                endpoint=endpoint,
            )
        elif 500 <= status < 600:
            raise ServerError(
                f"Sectors server error ({status}) encountered.",
                status_code=status,
                response_body=body,
                endpoint=endpoint,
            )
        else:
            raise SectorsAPIError(
                f"{msg}: {body}",
                status_code=status,
                response_body=body,
                endpoint=endpoint,
            )

    def request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        force_refresh: bool = False,
    ) -> Any:
        """Synchronously execute a GET request with caching, retry, and fallback."""
        clean_endpoint = endpoint.lstrip("/")

        # 1. Check Snapshot Cache (if not forced to refresh)
        if not force_refresh:
            cached_data = self.cache.get(clean_endpoint, params)
            if cached_data is not None:
                return cached_data

        # 2. Check API Key validity before network call
        if not self.api_key or self.api_key == "your_sectors_api_key_here":
            if self.cfg.sectors_offline_fallback:
                fallback = self.cache.get(clean_endpoint, params, ignore_ttl=True)
                if fallback is not None:
                    logger.warning(
                        "API key is missing, but found offline snapshot cache for %s. Using fallback.",
                        clean_endpoint,
                    )
                    return fallback
            raise AuthenticationError(
                "SECTORS_API_KEY is not configured in .env. Please provide a valid key.",
                status_code=401,
                endpoint=clean_endpoint,
            )

        # 3. Network Call with retry on transient errors
        @retry(
            reraise=True,
            stop=stop_after_attempt(self.cfg.sectors_max_retries),
            wait=wait_exponential_jitter(initial=1, max=10),
            retry=retry_if_exception_type(
                (RateLimitExceededError, ServerError, httpx.NetworkError, httpx.TimeoutException)
            ),
        )
        def _do_request() -> Any:
            self._apply_rate_limit()
            url = f"{self.base_url}{clean_endpoint}"
            logger.info("Executing Sectors API call: GET %s params=%s", clean_endpoint, params)

            try:
                with httpx.Client(timeout=self.cfg.sectors_timeout_seconds) as client:
                    resp = client.get(url, headers=self._headers, params=params)
                    if resp.is_error:
                        self._handle_error_response(resp, clean_endpoint)
                    return resp.json()
            except (httpx.NetworkError, httpx.TimeoutException) as exc:
                logger.warning("Network issue connecting to Sectors (%s): %s", url, exc)
                raise

        try:
            data = _do_request()
            # Save to Snapshot Cache
            self.cache.set(clean_endpoint, params, data)
            return data
        except Exception as err:
            # 4. Fail-Safe Offline Fallback (Demo Reliability §6.10)
            if self.cfg.sectors_offline_fallback:
                fallback = self.cache.get(clean_endpoint, params, ignore_ttl=True)
                if fallback is not None:
                    logger.warning(
                        "Request to %s failed (%s), but recovered via offline snapshot cache!",
                        clean_endpoint,
                        err,
                    )
                    return fallback
            raise

    async def request_async(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        force_refresh: bool = False,
    ) -> Any:
        """Asynchronously execute a GET request with caching, retry, and fallback."""
        clean_endpoint = endpoint.lstrip("/")

        # Check Cache
        if not force_refresh:
            cached_data = self.cache.get(clean_endpoint, params)
            if cached_data is not None:
                return cached_data

        if not self.api_key or self.api_key == "your_sectors_api_key_here":
            if self.cfg.sectors_offline_fallback:
                fallback = self.cache.get(clean_endpoint, params, ignore_ttl=True)
                if fallback is not None:
                    return fallback
            raise AuthenticationError(
                "SECTORS_API_KEY is not configured in .env.",
                status_code=401,
                endpoint=clean_endpoint,
            )

        await self._apply_rate_limit_async()
        url = f"{self.base_url}{clean_endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.cfg.sectors_timeout_seconds) as client:
                resp = await client.get(url, headers=self._headers, params=params)
                if resp.is_error:
                    self._handle_error_response(resp, clean_endpoint)
                data = resp.json()
                self.cache.set(clean_endpoint, params, data)
                return data
        except Exception as err:
            if self.cfg.sectors_offline_fallback:
                fallback = self.cache.get(clean_endpoint, params, ignore_ttl=True)
                if fallback is not None:
                    logger.warning(
                        "Async request to %s failed (%s), fallback used.", clean_endpoint, err
                    )
                    return fallback
            raise

    # =========================================================================
    # High-level Convenience Methods for Core Pipeline Endpoints
    # =========================================================================

    def get_subsectors(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """1. Taxonomy: Fetch all sectors and subsectors.

        Endpoint: GET /v2/subsectors/
        """
        return self.request("subsectors/", force_refresh=force_refresh)

    def get_companies(
        self,
        sector: str | None = None,
        sub_sector: str | None = None,
        limit: int = 50,
        offset: int = 0,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """1. Screener: List companies with optional sector/subsector filter.

        Endpoint: GET /v2/companies/
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        clauses: list[str] = []
        if sector:
            clauses.append(f"sector = '{sector.replace(chr(39), chr(39) * 2)}'")
        if sub_sector:
            clauses.append(f"sub_sector = '{sub_sector.replace(chr(39), chr(39) * 2)}'")
        if clauses:
            params["where"] = " and ".join(clauses)
        return self.request("companies/", params=params, force_refresh=force_refresh)

    def get_financials_quarterly(
        self,
        symbol: str,
        n_quarters: int = 4,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """2. Financials: Fetch quarterly report data for metric calculations.

        Endpoint: GET /v2/financials/quarterly/{symbol}/?n_quarters=N
        """
        sym = self._normalize_symbol(symbol)
        endpoint = f"financials/quarterly/{sym}/"
        params = {"n_quarters": n_quarters}
        return self.request(endpoint, params=params, force_refresh=force_refresh)

    def get_company_report(
        self,
        symbol: str,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """2. Company Report: Fetch comprehensive overview report.

        Endpoint: GET /v2/company-report/{symbol}/
        """
        sym = self._normalize_symbol(symbol)
        return self.request(f"company-report/{sym}/", force_refresh=force_refresh)

    def get_daily_transactions(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """3. Daily Transactions: OHLCV and daily price return.

        Endpoint: GET /v2/daily/{symbol}/?start=...&end=...
        """
        sym = self._normalize_symbol(symbol)
        params: dict[str, Any] = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self.request(f"daily/{sym}/", params=params, force_refresh=force_refresh)

    def get_filings(
        self,
        symbol: str,
        limit: int = 10,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """4. Mosaic Evidence 1: Company Filings (insider trading, ownership).

        Endpoint: GET /v2/filings/?symbol={symbol}&limit=N
        """
        sym = self._normalize_symbol(symbol)
        params = {"symbol": sym, "limit": limit}
        return self.request("filings/", params=params, force_refresh=force_refresh)

    def get_corporate_actions(
        self,
        symbol: str,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """4. Mosaic Evidence 2: Corporate Actions (dividends, splits, etc).

        Endpoint: GET /v2/company/corporate-actions/{symbol}/
        """
        sym = self._normalize_symbol(symbol)
        return self.request(f"company/corporate-actions/{sym}/", force_refresh=force_refresh)

    def get_news(
        self,
        symbol: str | None = None,
        limit: int = 10,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """4. Mosaic Evidence 3: Curated IDX News.

        Endpoint: GET /v2/news/?symbols={symbol}&limit=N
        """
        params: dict[str, Any] = {"limit": limit}
        if symbol:
            params["symbols"] = self._normalize_symbol(symbol)
        return self.request("news/", params=params, force_refresh=force_refresh)

    def get_foreign_flow(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """5. Confirmation Layer: Net foreign inflow/outflow.

        Endpoint: GET /v2/foreign-flow/{symbol}/
        """
        sym = self._normalize_symbol(symbol)
        params: dict[str, Any] = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self.request(f"foreign-flow/{sym}/", params=params, force_refresh=force_refresh)
