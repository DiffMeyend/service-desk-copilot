"""Tickets router - CRUD operations for Context Payloads."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.css import CSSResponse
from api.schemas.ticket import TicketSummary
from api.services.css_service import CSSService
from api.services.ticket_service import TicketService

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


def get_ticket_service() -> TicketService:
    """Dependency for ticket service."""
    return TicketService()


def get_css_service() -> CSSService:
    """Dependency for CSS service."""
    return CSSService()


@router.get("", response_model=List[TicketSummary])
async def list_tickets(
    service: TicketService = Depends(get_ticket_service),
) -> List[TicketSummary]:
    """List all available tickets."""
    return service.list_tickets()


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    service: TicketService = Depends(get_ticket_service),
    css_service: CSSService = Depends(get_css_service),
) -> Dict[str, Any]:
    """Get full Context Payload for a ticket, with CSS recalculated."""
    cp = service.get_ticket(ticket_id)
    if cp is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    # Recalculate CSS on every load so the score (and domain_scores) are always fresh
    score, blockers = css_service.calculate(cp)
    if "css" not in cp:
        cp["css"] = {}
    cp["css"]["score"] = score
    cp["css"]["missing_fields"] = blockers

    return cp


@router.get("/{ticket_id}/css", response_model=CSSResponse)
async def get_ticket_css(
    ticket_id: str,
    ticket_service: TicketService = Depends(get_ticket_service),
    css_service: CSSService = Depends(get_css_service),
) -> CSSResponse:
    """Get CSS score details for a ticket."""
    cp = ticket_service.get_ticket(ticket_id)
    if cp is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    return css_service.get_css_response(cp)
