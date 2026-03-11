"""Ticket service - manages Context Payload operations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for imports
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from api.config import settings
from api.schemas.ticket import TicketSummary
from scripts.agent.cp_manager import CPManager


class TicketService:
    """Service for ticket/Context Payload operations."""

    def __init__(self):
        self._ready_dir = settings.tickets_ready_dir
        self._results_dir = settings.tickets_results_dir

    def list_tickets(self) -> List[TicketSummary]:
        """List all tickets in the ready directory."""
        tickets = []

        if not self._ready_dir.exists():
            return tickets

        for path in sorted(self._ready_dir.glob("*.json"), reverse=True):
            try:
                cp = self._load_cp_file(path)
                if cp:
                    tickets.append(self._cp_to_summary(path.stem, cp))
            except Exception:
                # Skip invalid files
                continue

        return tickets

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get full Context Payload for a ticket. Checks results/ (working copy) first."""
        path = self._results_dir / f"{ticket_id}.json"
        if not path.exists():
            path = self._ready_dir / f"{ticket_id}.json"
        if not path.exists():
            return None

        return self._load_cp_file(path)

    def get_cp_manager(self, ticket_id: str) -> Optional[CPManager]:
        """Get a CPManager instance for a ticket. Checks results/ (working copy) first."""
        path = self._results_dir / f"{ticket_id}.json"
        if not path.exists():
            path = self._ready_dir / f"{ticket_id}.json"
        if not path.exists():
            return None

        from api.services.runtime_service import runtime_service

        cp_manager = CPManager(runtime_service.get_schema())
        cp_manager.load_ticket(path)
        return cp_manager

    def save_ticket(self, ticket_id: str, cp_manager: CPManager) -> Path:
        """Save a Context Payload to results/ (never mutates the ready/ fixture)."""
        self._results_dir.mkdir(parents=True, exist_ok=True)
        path = self._results_dir / f"{ticket_id}.json"
        return cp_manager.save(path)

    def _load_cp_file(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load a CP file from disk."""
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            return json.loads(text)
        except (json.JSONDecodeError, IOError):
            return None

    def _cp_to_summary(self, ticket_id: str, cp: Dict[str, Any]) -> TicketSummary:
        """Convert a CP dict to a TicketSummary."""
        ticket = cp.get("ticket", {})
        env = cp.get("environment", {})
        decision = cp.get("decision", {})
        css = cp.get("css", {})
        meta = cp.get("meta", {})

        return TicketSummary(
            id=ticket_id,
            priority=ticket.get("priority", "UNKNOWN"),
            company=ticket.get("company", ""),
            summary=ticket.get("summary", "")[:100],
            hostname=env.get("target_device", {}).get("hostname", ""),
            status=decision.get("status", "triage"),
            css_score=css.get("score", 0),
            last_updated=meta.get("last_updated", ""),
        )
