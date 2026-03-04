"""Pydantic schemas for command requests/responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LogResultRequest(BaseModel):
    """Request body for LOG_RESULT command."""

    command_id: str = Field(..., description="ID of the command/test being logged")
    output: str = Field(..., description="Output from the command execution")
    notes: Optional[str] = Field(None, description="Optional notes about the result")
    captured_at: Optional[str] = Field(
        None, description="ISO timestamp when result was captured"
    )


class LogResultResponse(BaseModel):
    """Response from LOG_RESULT command."""

    status: str = "ok"
    message: str
    tests_run_count: int
    css_score: int


class LoadBranchPackRequest(BaseModel):
    """Request body for LOAD_BRANCH_PACK command."""

    pack_id: str = Field(..., description="ID of the branch pack to load")


class LoadBranchPackResponse(BaseModel):
    """Response from LOAD_BRANCH_PACK command."""

    status: str = "ok"
    message: str
    pack_id: str
    hypothesis_count: int


class DecideRequest(BaseModel):
    """Request body for DECIDE command."""

    force: bool = Field(
        False, description="Force decision even if CSS < target"
    )


class DecideResponse(BaseModel):
    """Response from DECIDE command."""

    status: str = "ok"
    message: str
    decision_status: str
    best_guess: str
    css_score: int
    warning: Optional[str] = None


class NextActionResponse(BaseModel):
    """Response from PRINT_NEXT command."""

    action: str
    suggestion: str
    hypothesis_id: Optional[str] = None
    discriminating_test: Optional[str] = None
