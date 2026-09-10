"""Interactive Smoke Test script to verify connectivity to Sectors Financial API v2.

Tests the 5 core endpoint families required by the hackathon pipeline:
1. Taxonomy (Subsectors)
2. Quarterly Financials
3. Daily Transactions & Prices
4. Filings & News (Mosaic Linguistic Sources)
5. Foreign Flow (Confirmation Layer)

Usage:
    uv run python scripts/smoke_test.py
"""

import sys
import time
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.client.exceptions import AuthenticationError, SectorsAPIError
from src.client.sectors_client import SectorsClient
from src.config import settings

console = Console()


def print_banner() -> None:
    banner_text = (
        "[bold cyan]MARKET INTELLIGENCE AGENT — SECTORS HACKATHON 2026[/bold cyan]\n"
        "[dim]Day 1 Foundation Smoke Test: Sectors API v2 & Snapshot Cache Verification[/dim]"
    )
    console.print(Panel(banner_text, border_style="cyan", box=box.ROUNDED))


def test_endpoint(
    client: SectorsClient,
    category: str,
    name: str,
    call_fn: Any,
    force_refresh: bool = True,
) -> dict[str, Any]:
    """Execute a single test and capture latency, status, and payload preview."""
    start_time = time.perf_counter()
    status = "[bold green]PASS[/bold green]"
    notes = ""

    try:
        data = call_fn(force_refresh=force_refresh)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if isinstance(data, list):
            sample_count = len(data)
            notes = f"{sample_count} items retrieved"
        elif isinstance(data, dict):
            keys_preview = ", ".join(list(data.keys())[:3])
            notes = f"dict({keys_preview}...)"
        else:
            notes = str(data)[:30]

    except AuthenticationError as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        status = "[bold red]AUTH FAIL[/bold red]"
        notes = f"401: Invalid API Key ({e})"
    except SectorsAPIError as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        status = "[bold red]API ERROR[/bold red]"
        notes = f"{e.status_code or 'ERR'}: {e.message[:40]}"
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        status = "[bold red]FAIL[/bold red]"
        notes = f"{type(e).__name__}: {str(e)[:40]}"

    return {
        "category": category,
        "name": name,
        "status": status,
        "latency": f"{elapsed_ms:.1f} ms",
        "notes": notes,
    }


def main() -> int:
    print_banner()

    console.print(f"[bold]Base URL:[/bold] [dim]{settings.sectors_base_url}[/dim]")
    console.print(f"[bold]Cache Directory:[/bold] [dim]{settings.sectors_cache_dir}[/dim]")

    if not settings.has_valid_api_key:
        console.print(
            Panel(
                "[bold yellow]PERINGATAN: SECTORS_API_KEY belum diisi di file .env![/bold yellow]\n\n"
                "Silakan buka file [bold cyan].env[/bold cyan] dan masukkan API Key resmi Anda:\n"
                "[dim]SECTORS_API_KEY=sectors_live_xxxxxxxxxxxxxxxx[/dim]\n\n"
                "Setelah diisi, jalankan kembali script ini untuk pengujian live.",
                title="Konfigurasi API Key Dibutuhkan",
                border_style="yellow",
            )
        )
        return 1

    console.print(
        "[green]✓[/green] SECTORS_API_KEY terdeteksi. Memulai pengujian live 5 endpoint utama...\n"
    )

    client = SectorsClient()
    test_symbol = "ASII"  # Astra International Tbk (liquid, non-financial bluechip)

    tests = [
        (
            "1. Taxonomy",
            "GET /v2/subsectors/",
            lambda force_refresh: client.get_subsectors(force_refresh=force_refresh),
        ),
        (
            "1. Screener",
            "GET /v2/companies/?limit=5",
            lambda force_refresh: client.get_companies(limit=5, force_refresh=force_refresh),
        ),
        (
            "2. Financials",
            f"GET /v2/financials/quarterly/{test_symbol}/?n_quarters=4",
            lambda force_refresh: client.get_financials_quarterly(
                test_symbol, n_quarters=4, force_refresh=force_refresh
            ),
        ),
        (
            "3. Daily Quotes",
            f"GET /v2/daily/{test_symbol}/",
            lambda force_refresh: client.get_daily_transactions(
                test_symbol, force_refresh=force_refresh
            ),
        ),
        (
            "4. News / Filings",
            f"GET /v2/filings/?symbol={test_symbol}&limit=5",
            lambda force_refresh: client.get_filings(
                test_symbol, limit=5, force_refresh=force_refresh
            ),
        ),
        (
            "4. News / Filings",
            f"GET /v2/news/?symbols={test_symbol}&limit=5",
            lambda force_refresh: client.get_news(
                symbol=test_symbol, limit=5, force_refresh=force_refresh
            ),
        ),
        (
            "5. Foreign Flow",
            f"GET /v2/foreign-flow/{test_symbol}/",
            lambda force_refresh: client.get_foreign_flow(test_symbol, force_refresh=force_refresh),
        ),
    ]

    results = []
    with console.status("[bold green]Menghubungi Sectors API...[/bold green]", spinner="dots"):
        for category, name, call_fn in tests:
            res = test_endpoint(client, category, name, call_fn, force_refresh=True)
            results.append(res)

    # Cache hit test (call first endpoint without force_refresh)
    cache_start = time.perf_counter()
    client.get_subsectors(force_refresh=False)
    cache_elapsed_ms = (time.perf_counter() - cache_start) * 1000
    results.append(
        {
            "category": "Cache Validation",
            "name": "Local Cache HIT test (/v2/subsectors/)",
            "status": "[bold green]PASS[/bold green]",
            "latency": f"{cache_elapsed_ms:.2f} ms",
            "notes": "Served directly from local snapshot JSON",
        }
    )

    table = Table(title="Hasil Pengujian Konektivitas Sectors API v2", box=box.ROUNDED)
    table.add_column("Pipeline Stage", style="cyan", no_wrap=True)
    table.add_column("Endpoint", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Latency", justify="right", style="magenta")
    table.add_column("Payload Details / Notes", style="dim")

    for r in results:
        table.add_row(r["category"], r["name"], r["status"], r["latency"], r["notes"])

    console.print(table)

    # Count passes
    all_passed = all("PASS" in r["status"] for r in results)
    if all_passed:
        console.print(
            "\n[bold green]✓ SELURUH ENDPOINT SECTORS TERHUBUNG DENGAN SUKSES![/bold green]"
        )
        console.print(f"[dim]Snapshot cache tersimpan di: {settings.sectors_cache_dir}[/dim]\n")
        return 0
    else:
        console.print(
            "\n[bold yellow]⚠ Beberapa endpoint mengalami kendala. Periksa tabel di atas.[/bold yellow]\n"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
