"""Versioned, inspectable storage for immutable discovery inputs.

The discovery endpoint only reads these files.  Capturing a market state is a
separate CLI operation so a request can never change its own peer cohort.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import BASE_DIR
from src.engine.models import (
    CompanyState,
    MarketStateResult,
    MetricDistribution,
    MetricSet,
    PeerZScores,
    SubsectorProfile,
    UniverseStats,
)

SNAPSHOT_DIR = BASE_DIR / "data" / "snapshots"
METHODOLOGY_VERSION = "day3-personalized-discovery-v1"


def _state_from_dict(data: dict[str, Any]) -> MarketStateResult:
    companies = [
        CompanyState(
            **{
                **item,
                "raw_metrics": MetricSet(**item["raw_metrics"]),
                "peer_z": PeerZScores(**item["peer_z"]),
            }
        )
        for item in data["companies"]
    ]
    profiles = {
        name: SubsectorProfile(
            **{
                **profile,
                "distributions": {
                    metric: MetricDistribution(**distribution)
                    for metric, distribution in profile.get("distributions", {}).items()
                },
            }
        )
        for name, profile in data["subsector_profiles"].items()
    }
    return MarketStateResult(
        companies=companies,
        subsector_profiles=profiles,
        universe_stats=UniverseStats(**data["universe_stats"]),
        methodology_notes=data.get("methodology_notes", []),
    )


class SnapshotStore:
    """File store deliberately small enough for local demo and replay use."""

    def __init__(self, directory: Path = SNAPSHOT_DIR):
        self.directory = directory

    def list_ids(self) -> list[str]:
        if not self.directory.exists():
            return []
        return sorted(path.stem for path in self.directory.glob("*.json"))

    def save(
        self,
        state: MarketStateResult,
        *,
        source_mode: str,
        manifest: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> str:
        state_data = asdict(state)
        canonical = json.dumps(state_data, sort_keys=True, separators=(",", ":"), allow_nan=False)
        snapshot_id = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        payload = {
            "snapshot_id": snapshot_id,
            "methodology_version": METHODOLOGY_VERSION,
            "captured_at": datetime.now(UTC).isoformat(),
            "source_mode": source_mode,
            "manifest": manifest or {},
            "warnings": warnings or [],
            "state": state_data,
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{snapshot_id}.json"
        if not path.exists():
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return snapshot_id

    def load(self, snapshot_id: str) -> tuple[MarketStateResult, dict[str, Any]] | None:
        path = self.directory / f"{snapshot_id}.json"
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _state_from_dict(payload["state"]), payload
