"""Commands router - execute commands against tickets."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.commands import (
    DecideRequest,
    DecideResponse,
    LoadBranchPackRequest,
    LoadBranchPackResponse,
    LogResultRequest,
    LogResultResponse,
    NextActionResponse,
)
from api.services.command_service import CommandService
from api.services.llm_analyst import llm_analyst
from api.services.ticket_service import TicketService

router = APIRouter(prefix="/api/v1/tickets", tags=["commands"])


def get_ticket_service() -> TicketService:
    """Dependency for ticket service."""
    return TicketService()


def get_command_service(ticket_id: str, ticket_service: TicketService) -> CommandService:
    """Create command service for a ticket."""
    cp_manager = ticket_service.get_cp_manager(ticket_id)
    if cp_manager is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return CommandService(cp_manager, ticket_id)


@router.post("/{ticket_id}/log-result", response_model=LogResultResponse)
async def log_result(
    ticket_id: str,
    request: LogResultRequest,
    ticket_service: TicketService = Depends(get_ticket_service),
) -> LogResultResponse:
    """Log a test result for a ticket."""
    cmd_service = get_command_service(ticket_id, ticket_service)

    message, css_score = await cmd_service.log_result(
        command_id=request.command_id,
        output=request.output,
        notes=request.notes,
        captured_at=request.captured_at,
    )

    tests_run = cmd_service._cp.get_tests_run()
    ticket_service.save_ticket(ticket_id, cmd_service._cp)

    # Claude evidence interpretation — gracefully degrades
    hypotheses = cmd_service._cp.get_active_hypotheses()
    interp = llm_analyst.interpret_evidence(
        command_id=request.command_id,
        output=request.output,
        hypotheses=hypotheses,
    )
    claude_interp = interp.interpretation or None

    return LogResultResponse(
        status="ok",
        message=message,
        tests_run_count=len(tests_run),
        css_score=css_score,
        claude_interpretation=claude_interp,
    )


@router.post("/{ticket_id}/load-branch-pack", response_model=LoadBranchPackResponse)
async def load_branch_pack(
    ticket_id: str,
    request: LoadBranchPackRequest,
    ticket_service: TicketService = Depends(get_ticket_service),
) -> LoadBranchPackResponse:
    """Load a branch pack for a ticket."""
    cmd_service = get_command_service(ticket_id, ticket_service)

    message, hyp_count = await cmd_service.load_branch_pack(request.pack_id)

    if message.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=message)

    ticket_service.save_ticket(ticket_id, cmd_service._cp)

    return LoadBranchPackResponse(
        status="ok",
        message=message,
        pack_id=request.pack_id,
        hypothesis_count=hyp_count,
    )


@router.post("/{ticket_id}/decide", response_model=DecideResponse)
async def decide(
    ticket_id: str,
    request: DecideRequest = DecideRequest(),
    ticket_service: TicketService = Depends(get_ticket_service),
) -> DecideResponse:
    """Execute DECIDE command for a ticket."""
    cmd_service = get_command_service(ticket_id, ticket_service)

    message, decision_info = await cmd_service.decide(force=request.force)

    ticket_service.save_ticket(ticket_id, cmd_service._cp)

    return DecideResponse(
        status="ok",
        message=message,
        decision_status=decision_info["status"],
        best_guess=decision_info["best_guess"],
        css_score=decision_info["css_score"],
        warning=decision_info.get("warning"),
    )


@router.get("/{ticket_id}/next-action", response_model=NextActionResponse)
async def get_next_action(
    ticket_id: str,
    ticket_service: TicketService = Depends(get_ticket_service),
) -> NextActionResponse:
    """Get suggested next action for a ticket."""
    cmd_service = get_command_service(ticket_id, ticket_service)

    result = cmd_service.get_next_action()

    # Claude reasoning enrichment — gracefully degrades
    ai = llm_analyst.suggest_next_step(cmd_service._cp.cp)
    ai_reasoning = ai.reasoning or None
    ai_commands = ai.suggested_commands or None

    return NextActionResponse(
        action=result["action"],
        suggestion=result["suggestion"],
        hypothesis_id=result.get("hypothesis_id"),
        discriminating_test=result.get("discriminating_test"),
        ai_reasoning=ai_reasoning,
        ai_suggested_commands=ai_commands,
    )
