#!/usr/bin/env python3
"""Capture and replay deterministic personalized discovery snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.snapshot_store import SnapshotStore
from src.client.cache import SnapshotCache
from src.client.sectors_client import SectorsClient
from src.config import Settings
from src.discovery import DiscoveryEngine, PresetName, ResearchMandate
from src.engine.market_state_engine import MarketStateEngine


def _write(value: object, path: str | None) -> None:
    rendered = json.dumps(value, indent=2, ensure_ascii=False, default=str)
    if path:
        Path(path).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


def _mandate(path: str | None) -> ResearchMandate:
    if not path:
        return ResearchMandate()
    return ResearchMandate.model_validate_json(Path(path).read_text(encoding="utf-8"))


def capture(args: argparse.Namespace) -> dict[str, object]:
    if args.request_budget < 1:
        raise SystemExit("--request-budget must be positive")
    if args.rate_limit_delay < 0:
        raise SystemExit("--rate-limit-delay must be non-negative")
    base = Settings()
    if args.mode == "cached":
        cfg = Settings(
            SECTORS_API_KEY="your_sectors_api_key_here",
            SECTORS_OFFLINE_FALLBACK=True,
            SECTORS_CACHE_ENABLED=True,
            SECTORS_CACHE_DIR=base.sectors_cache_dir,
            SECTORS_RATE_LIMIT_DELAY=0.0,
        )
        cache = SnapshotCache(cache_dir=cfg.sectors_cache_dir, enabled=True, ttl_hours=0)
    elif args.mode == "live":
        cfg = Settings(
            SECTORS_API_KEY=base.sectors_api_key,
            SECTORS_OFFLINE_FALLBACK=False,
            SECTORS_CACHE_ENABLED=False,
            SECTORS_RATE_LIMIT_DELAY=args.rate_limit_delay,
        )
        cache = SnapshotCache(cache_dir=base.sectors_cache_dir, enabled=False)
    else:
        cfg = base
        cache = SnapshotCache(cache_dir=cfg.sectors_cache_dir)
    client = SectorsClient(cfg=cfg, cache=cache)
    engine = MarketStateEngine(client)
    universe = engine.build_universe_map()
    requested_before_budget = sum(len(items) for items in universe.values())
    max_by_budget = max((args.request_budget - len(universe)) // 2, 0)
    limit = args.max_companies
    if max_by_budget < requested_before_budget:
        limit = min(limit, max_by_budget) if limit is not None else max_by_budget
    if limit is not None:
        remaining = limit
        limited = {}
        for subsector, companies in universe.items():
            if remaining <= 0:
                break
            take = companies[:remaining]
            if take:
                limited[subsector] = take
                remaining -= len(take)
        universe = limited
    state = engine.compute_market_state(
        universe=universe,
        n_quarters=args.n_quarters,
        price_start=args.price_start,
        price_end=args.price_end,
    )
    manifest = {
        "requested_companies": sum(len(items) for items in universe.values()),
        "universe_companies_before_budget": requested_before_budget,
        "processed_companies": len(state.companies),
        "price_start": args.price_start,
        "price_end": args.price_end,
        "n_quarters": args.n_quarters,
        "request_budget": args.request_budget,
        "request_budget_note": "Budget reserves one taxonomy request per subsector and two endpoint calls per company; retries remain recorded by the client but cannot be pre-counted.",
        "budget_truncated": limit is not None and limit < requested_before_budget,
    }
    warnings = [
        "Snapshot is a replay input, not a point-in-time historical dataset.",
        "Source publication time and later restatements are not established by this capture.",
    ]
    snapshot_id = SnapshotStore().save(state, source_mode=args.mode, manifest=manifest, warnings=warnings)
    return {"snapshot_id": snapshot_id, "manifest": manifest, "universe_stats": state.universe_stats.__dict__, "warnings": warnings}


def search(args: argparse.Namespace) -> dict[str, object]:
    loaded = SnapshotStore().load(args.snapshot_id)
    if loaded is None:
        raise SystemExit(f"snapshot not found: {args.snapshot_id}")
    state, payload = loaded
    result = DiscoveryEngine().discover(state.companies, _mandate(args.mandate), snapshot_date=payload["captured_at"])
    return {"snapshot_id": args.snapshot_id, "result": result.model_dump(mode="json")}


def validate(args: argparse.Namespace) -> dict[str, object]:
    loaded = SnapshotStore().load(args.snapshot_id)
    if loaded is None:
        raise SystemExit(f"snapshot not found: {args.snapshot_id}")
    state, payload = loaded
    engine = DiscoveryEngine()
    outputs = {}
    for preset in (PresetName.DISLOCATION, PresetName.GROWTH, PresetName.PROFITABILITY, PresetName.VALUE):
        result = engine.discover(state.companies, ResearchMandate(preset=preset), snapshot_date=payload["captured_at"])
        outputs[preset.value] = {
            "symbols": [candidate.symbol for candidate in result.candidates],
            "coverage": {name.value: value.model_dump(mode="json") for name, value in result.coverage.items()},
            "funnel": result.funnel.model_dump(mode="json"),
        }
    return {"snapshot_id": args.snapshot_id, "presets": outputs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--mode", choices=("live", "cached", "fallback"), default="fallback")
    capture_parser.add_argument("--price-start")
    capture_parser.add_argument("--price-end")
    capture_parser.add_argument("--n-quarters", type=int, default=8)
    capture_parser.add_argument("--max-companies", type=int)
    capture_parser.add_argument("--request-budget", type=int, default=3000)
    capture_parser.add_argument(
        "--rate-limit-delay",
        type=float,
        default=0.75,
        help="Seconds between live requests; conservative default stays below the 60 minute scan budget.",
    )
    capture_parser.add_argument("--out")
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("snapshot_id")
    search_parser.add_argument("--mandate", help="JSON ResearchMandate")
    search_parser.add_argument("--out")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("snapshot_id")
    validate_parser.add_argument("--out")
    args = parser.parse_args()
    if args.command == "capture":
        result = capture(args)
    elif args.command == "search":
        result = search(args)
    else:
        result = validate(args)
    _write(result, getattr(args, "out", None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
