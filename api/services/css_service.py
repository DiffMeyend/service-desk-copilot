"""CSS service - calculates Context Stability Score."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add project root to path for imports
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from scripts.agent.css_calculator import CSSCalculator
from scripts.agent import config as agent_config

from api.services.runtime_service import runtime_service
from api.schemas.css import CSSResponse


class CSSService:
    """Service for CSS calculations."""

    def __init__(self):
        self._calculator: CSSCalculator | None = None

    def _get_calculator(self) -> CSSCalculator:
        """Get or create the CSS calculator."""
        if self._calculator is None:
            rules = runtime_service.get_css_rules()
            self._calculator = CSSCalculator(rules)
        return self._calculator

    def calculate(self, cp: Dict[str, Any]) -> Tuple[int, List[str]]:
        """Calculate CSS score and blockers."""
        calculator = self._get_calculator()
        return calculator.calculate(cp)

    def get_css_response(self, cp: Dict[str, Any]) -> CSSResponse:
        """Get full CSS response with all details."""
        calculator = self._get_calculator()
        score, blockers = calculator.calculate(cp)
        missing_for_90 = calculator.get_missing_for_90(cp)

        # Get domain scores from CP (they should be set after calculation)
        domain_scores = cp.get("css", {}).get("domain_scores", {})

        return CSSResponse(
            score=score,
            target=calculator.target,
            blockers=blockers,
            domain_scores=domain_scores,
            missing_for_90=missing_for_90,
            can_decide=score >= calculator.target,
        )

    @property
    def target(self) -> int:
        """Get the target CSS score."""
        return self._get_calculator().target
