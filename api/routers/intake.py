"""Intake & Audit API endpoints (Agent 2)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.services.intake_service import IntakeService
from api.services.llm_analyst import llm_analyst

router = APIRouter(prefix="/api/v1/intake", tags=["intake"])

_service = IntakeService()


# --- Request/Response schemas ---


class ParseRequest(BaseModel):
    raw_text: str = Field(..., description="Raw ticket dump text to parse")


class ParseResponse(BaseModel):
    context_payload: Dict[str, Any] = Field(..., description="Parsed Context Payload")
    ticket_id: str = Field("", description="Extracted ticket ID")
    source_pack: List[str] = Field(default_factory=list, description="Routed branch pack(s)")
    # Claude triage fields — present when ANTHROPIC_API_KEY is set
    routing_suggestion: Optional[str] = Field(None, description="Claude-suggested routing category")
    triage_reasoning: Optional[str] = Field(None, description="Claude's triage explanation")


class AlertsResponse(BaseModel):
    alerts: List[str] = Field(default_factory=list, description="Pattern-based alert strings")


class MetricsResponse(BaseModel):
    packs: Dict[str, Any] = Field(default_factory=dict, description="Pack effectiveness metrics")


class ConfidenceResponse(BaseModel):
    updates: Dict[str, Any] = Field(default_factory=dict, description="Confidence delta reports")


# --- Routes ---


@router.post("/parse", response_model=ParseResponse)
async def parse_ticket(request: ParseRequest) -> ParseResponse:
    """Parse raw ticket text into a Context Payload."""
    try:
        cp = _service.parse_ticket(request.raw_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Parse error: {exc}")

    ticket_id = cp.get("ticket", {}).get("id", "")
    source_pack = cp.get("branches", {}).get("source_pack", [])

    # Claude triage — gracefully degrades if no API key
    triage = llm_analyst.analyze_ticket(request.raw_text, cp)

    return ParseResponse(
        context_payload=cp,
        ticket_id=ticket_id,
        source_pack=source_pack,
        routing_suggestion=triage.routing_suggestion or None,
        triage_reasoning=triage.triage_reasoning or None,
    )


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    device: Optional[str] = None,
    user: Optional[str] = None,
    days: int = 30,
) -> AlertsResponse:
    """Get pattern-based alerts for a device/user."""
    try:
        alerts = _service.get_alerts(device=device, user=user, days=days)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Alert detection error: {exc}")

    return AlertsResponse(alerts=alerts)


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(days: int = 365) -> MetricsResponse:
    """Get pack effectiveness metrics."""
    try:
        metrics = _service.get_metrics(days=days)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Metrics error: {exc}")

    return MetricsResponse(packs=metrics)


@router.get("/confidence", response_model=ConfidenceResponse)
async def get_confidence(days: int = 365) -> ConfidenceResponse:
    """Get learned confidence updates from resolution history."""
    try:
        updates = _service.get_confidence_updates(days=days)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Confidence update error: {exc}")

    return ConfidenceResponse(updates=updates)
