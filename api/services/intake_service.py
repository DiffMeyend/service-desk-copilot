"""Service wrapper for IntakeAgent, bridging agent code to the API layer."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from scripts.intake.agent import IntakeAgent


class IntakeService:
    """Wraps IntakeAgent for use in FastAPI route handlers."""

    def __init__(self) -> None:
        self._agent = IntakeAgent()

    def parse_ticket(self, raw_text: str) -> Dict[str, Any]:
        """Parse raw ticket text and return a Context Payload."""
        return self._agent.ingest(raw_text)

    def get_alerts(
        self,
        device: Optional[str] = None,
        user: Optional[str] = None,
        symptoms: Optional[List[str]] = None,
        days: int = 30,
    ) -> List[str]:
        """Get pattern-based alerts for a ticket."""
        return self._agent.get_alerts(
            device=device,
            user=user,
            symptoms=symptoms,
            days=days,
        )

    def get_metrics(self, days: int = 365) -> Dict[str, Any]:
        """Get pack effectiveness metrics."""
        return self._agent.get_pack_stats(days=days)

    def get_confidence_updates(self, days: int = 365) -> Dict[str, Any]:
        """Get learned confidence updates."""
        return self._agent.compute_confidence_updates(days=days)
