"""Smoke test script to verify Gemini LLM API connectivity and text generation.

Usage:
    uv run python scripts/smoke_test_llm.py
"""

import sys
import time

from rich import box
from rich.console import Console
from rich.panel import Panel

from src.config import settings
from src.research.llm import GeminiClient

console = Console()


def main() -> int:
    console.print(
        Panel(
            "[bold cyan]LLM CONNECTIVITY & SYNTHESIS TEST[/bold cyan]\n"
            f"[dim]Provider: {settings.llm_provider} | Model: {settings.llm_model}[/dim]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    if not settings.llm_api_key or "your_" in settings.llm_api_key:
        console.print("[bold yellow]PERINGATAN: LLM_API_KEY belum diisi di .env![/bold yellow]")
        return 1

    client = GeminiClient()
    prompt = (
        "Analisis singkat emiten Astra International (ASII): "
        "Sebutkan 1 poin keunggulan dan 1 poin risiko dalam 2 kalimat ringkas."
    )
    system_instruction = (
        "Anda adalah Equity Analyst senior spesialis pasar modal Indonesia (IDX). "
        "Gunakan bahasa profesional yang tajam dan berbasis data."
    )

    console.print("[dim]Mengirim prompt ke Gemini API...[/dim]")
    start = time.perf_counter()

    try:
        response = client.generate_text(prompt=prompt, system_instruction=system_instruction)
        elapsed_ms = (time.perf_counter() - start) * 1000

        console.print("\n[bold green]✓ RESPON GEMINI DITERIMA DENGAN SUKSES![/bold green]")
        console.print(f"[dim]Latensi: {elapsed_ms:.1f} ms | Model: {settings.llm_model}[/dim]\n")
        console.print(
            Panel(
                response,
                title="[bold white]Output Analisis Gemini[/bold white]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
        return 0
    except Exception as e:
        console.print(f"\n[bold red]✕ GAGAL MENGHUBUNGI LLM:[/bold red] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
