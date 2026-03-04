"""Commands router - execute commands against tickets."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends

from api.schemas.commands import (
    LogResultRequest,
    LogResultResponse,
    LoadBranchPackRequest,
    LoadBranchPackResponse,
    DecideRequest,
    DecideResponse,
    NextActionResponse,
)
from api.services.ticket_service import TicketService
from api.services.command_service import CommandService


router = APIRouter(prefix="/api/v1/tickets", tags=["commands"])


def get_ticket_service() -> TicketService:
    """Dependency for ticket service."""
    return TicketService()


def get_command_service(ticket_id: str, ticket_service: TicketService) -> CommandService:
    """Create command service for a ticket."""
    cp_manager = ticket_service.get_cp_manager(ticket_id)
    if cp_manager is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return CommandService(cp_manager)


@router.post("/{ticket_id}/log-result", response_model=LogResultResponse)
async def log_result(
    ticket_id: str,
    request: LogResultRequest,
    ticket_service: TicketService = Depends(get_ticket_service),
) -> LogResultResponse:
    """Log a test result for a ticket."""
    cmd_service = get_command_service(ticket_id, ticket_service)

    message, css_score = cmd_service.log_result(
        command_id=request.command_id,
        output=request.output,
        notes=request.notes,
        captured_at=request.captured_at,
    )

    # Save the updated CP
    cp_manager = ticket_service.get_cp_manager(ticket_id)
    if cp_manager:
        # Reload to get fresh state (command service has its own copy)
        # Actually, command_service modifies cp_manager in place, so we save it
        pass  # The cp_manager used in cmd_service is what we need

    # Get tests run count from the command service's CP
    tests_run = cmd_service._cp.get_tests_run()

    # Save changes
    ticket_service.save_ticket(ticket_id, cmd_service._cp)

    return LogResultResponse(
        status="ok",
        message=message,
        tests_run_count=len(tests_run),
        css_score=css_score,
    )


@router.post("/{ticket_id}/load-branch-pack", response_model=LoadBranchPackResponse)
async def load_branch_pack(
    ticket_id: str,
    request: LoadBranchPackRequest,
    ticket_service: TicketService = Depends(get_ticket_service),
) -> LoadBranchPackResponse:
    """Load a branch pack for a ticket."""
    cmd_service = get_command_service(ticket_id, ticket_service)

    message, hyp_count = cmd_service.load_branch_pack(request.pack_id)

    if message.startswith("ERROR"):
        raise HTTPException(status_code=400, detail=message)

    # Save changes
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

    message, decision_info = cmd_service.decide(force=request.force)

    # Save changes
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

    return NextActionResponse(
        action=result["action"],
        suggestion=result["suggestion"],
        hypothesis_id=result.get("hypothesis_id"),
        discriminating_test=result.get("discriminating_test"),
    )
