"""Pure domain services for personalized opportunity discovery."""

from src.discovery.discovery_engine import DiscoveryEngine, discover_opportunities
from src.discovery.models import (
    DiscoveryResult,
    EvidenceStandard,
    LensName,
    PresetName,
    ResearchMandate,
)

__all__ = [
    "DiscoveryEngine",
    "DiscoveryResult",
    "EvidenceStandard",
    "LensName",
    "PresetName",
    "ResearchMandate",
    "discover_opportunities",
]
