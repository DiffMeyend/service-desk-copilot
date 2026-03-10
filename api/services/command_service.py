"""Command service - executes commands against Context Payloads."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Add project root to path for imports
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from api.services.css_service import CSSService
from api.services.runtime_service import runtime_service
from api.websocket import ws_manager
from scripts.agent.command_handler import CommandHandler
from scripts.agent.cp_manager import CPManager


class CommandService:
    """Service for executing commands against CPs."""

    def __init__(self, cp_manager: CPManager, ticket_id: str = "") -> None:
        self._cp = cp_manager
        self._ticket_id = ticket_id
        self._handler = CommandHandler(cp_manager, runtime_service.get_loader())
        self._css_service = CSSService()

    async def log_result(
        self,
        command_id: str,
        output: str,
        notes: Optional[str] = None,
        captured_at: Optional[str] = None,
    ) -> Tuple[str, int]:
        """Log a test result and return (message, new_css_score)."""
        payload: Dict[str, Any] = {
            "command_id": command_id,
            "output": output,
        }
        if notes:
            payload["notes"] = notes
        if captured_at:
            payload["captured_at"] = captured_at

        message = self._handler.handle_log_result(payload)

        # Recalculate CSS after logging
        score, blockers = self._css_service.calculate(self._cp.cp)
        self._cp.set_value("css.score", score)

        # Broadcast real-time updates
        if self._ticket_id:
            await ws_manager.send_cp_update(self._ticket_id, self._cp.cp)
            await ws_manager.send_css_update(self._ticket_id, score, blockers)

        return message, score

    async def load_branch_pack(self, pack_id: str) -> Tuple[str, int]:
        """Load a branch pack and return (message, hypothesis_count)."""
        message = self._handler.handle_load_branch_pack(pack_id)

        if message.startswith("ERROR"):
            return message, 0

        hyps = self._cp.get_active_hypotheses()

        # Broadcast updated CP after pack load
        if self._ticket_id:
            await ws_manager.send_cp_update(self._ticket_id, self._cp.cp)

        return message, len(hyps)

    async def decide(self, force: bool = False) -> Tuple[str, Dict[str, Any]]:
        """Execute DECIDE command and return (message, decision_info)."""
        message = self._handler.handle_decide()

        decision_info = {
            "status": self._cp.get_current_state(),
            "best_guess": self._cp.get_value("branches.current_best_guess") or "",
            "css_score": self._cp.get_css_score(),
            "warning": None,
        }

        if message.startswith("WARNING"):
            lines = message.split("\n")
            decision_info["warning"] = lines[0]

        # Broadcast decision state
        if self._ticket_id:
            await ws_manager.send_decision_ready(self._ticket_id, decision_info["status"])
            await ws_manager.send_cp_update(self._ticket_id, self._cp.cp)

        return message, decision_info

    def get_next_action(self) -> Dict[str, Any]:
        """Get suggested next action."""
        message = self._handler.handle_print_next()

        result = {
            "action": "unknown",
            "suggestion": message,
            "hypothesis_id": None,
            "discriminating_test": None,
        }

        if "LOAD_BRANCH_PACK" in message:
            result["action"] = "load_pack"
        elif "DECIDE" in message:
            result["action"] = "decide"
        elif "discriminating test" in message.lower():
            result["action"] = "run_test"
            hyps = self._cp.get_active_hypotheses()
            if hyps:
                result["hypothesis_id"] = hyps[0].get("id", "")
                disc_tests = hyps[0].get("discriminating_tests", [])
                if disc_tests:
                    result["discriminating_test"] = disc_tests[0]
        else:
            result["action"] = "gather_evidence"

        return result

    def get_context_summary(self) -> str:
        """Get context summary (PRINT_CONTEXT)."""
        return self._handler.handle_print_context(full=False)

    def get_context_full(self) -> Dict[str, Any]:
        """Get full context payload."""
        return self._cp.cp
