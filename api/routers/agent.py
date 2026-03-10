"""Agent chat router — freeform Claude Q&A about a ticket."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.services.llm_analyst import llm_analyst
from api.services.ticket_service import TicketService

router = APIRouter(prefix="/api/v1/tickets", tags=["agent"])

_ticket_service = TicketService()


class ChatRequest(BaseModel):
    message: str = Field(..., description="Technician's question about the ticket")


class ChatResponse(BaseModel):
    response: str
    hypothesis_updates: Dict[str, str] = {}
    suggested_commands: List[str] = []


@router.post("/{ticket_id}/chat", response_model=ChatResponse)
async def chat(ticket_id: str, request: ChatRequest) -> ChatResponse:
    """Freeform Claude Q&A grounded in the current ticket state."""
    cp_manager = _ticket_service.get_cp_manager(ticket_id)
    if cp_manager is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    result = llm_analyst.chat(cp_manager.cp, request.message)

    return ChatResponse(
        response=result.response,
        hypothesis_updates=result.hypothesis_updates,
        suggested_commands=result.suggested_commands,
    )
