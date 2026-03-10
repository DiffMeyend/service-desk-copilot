"""Pydantic schemas for ticket/Context Payload data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Requester(BaseModel):
    """Requester information from ticket."""

    name: str = ""
    email: str = ""
    phone: str = ""


class TargetDevice(BaseModel):
    """Target device information."""

    hostname: str = ""
    os: str = ""
    ip: str = ""
    asset_tag: str = ""
    serial_number: str = ""
    on_domain: Optional[bool] = None


class UserContext(BaseModel):
    """User context for troubleshooting."""

    username: str = ""
    is_admin: Optional[bool] = None
    is_remote: Optional[bool] = None


class Network(BaseModel):
    """Network context."""

    connection_type: str = ""
    dns_servers: List[str] = Field(default_factory=list)
    vpn: Optional[bool] = None


class ExecutionContext(BaseModel):
    """Execution context for remote operations."""

    tooling: str = ""
    run_as: str = ""
    privilege: str = ""
    sandbox_prepped: Optional[bool] = None


class Environment(BaseModel):
    """Environment section of CP."""

    target_device: TargetDevice = Field(default_factory=TargetDevice)
    user_context: UserContext = Field(default_factory=UserContext)
    network: Network = Field(default_factory=Network)
    execution_context: ExecutionContext = Field(default_factory=ExecutionContext)


class Impact(BaseModel):
    """Impact assessment."""

    who: str = ""
    how_bad: str = ""
    work_stopped: Optional[bool] = None


class Scope(BaseModel):
    """Problem scope."""

    single_user: Optional[bool] = None
    multi_user: Optional[bool] = None
    single_device: Optional[bool] = None
    service_wide: Optional[bool] = None


class Problem(BaseModel):
    """Problem section of CP."""

    symptoms: List[str] = Field(default_factory=list)
    impact: Impact = Field(default_factory=Impact)
    scope: Scope = Field(default_factory=Scope)
    start_time: str = ""
    last_known_good: str = ""
    recent_changes: List[str] = Field(default_factory=list)


class TestResult(BaseModel):
    """A single test result."""

    command_id: str
    output: str
    captured_at: str = ""


class Hypothesis(BaseModel):
    """A troubleshooting hypothesis."""

    id: str
    hypothesis: str
    confidence_hint: float = 0.0
    discriminating_question: str = ""
    discriminating_tests: List[str] = Field(default_factory=list)
    command_refs: List[str] = Field(default_factory=list)
    notes: str = ""


class Branches(BaseModel):
    """Branches section of CP."""

    active_hypotheses: List[Hypothesis] = Field(default_factory=list)
    collapsed_hypotheses: List[str] = Field(default_factory=list)
    current_best_guess: str = ""
    source_pack: List[str] = Field(default_factory=list)
    manual_overrides: List[Dict[str, Any]] = Field(default_factory=list)
    routing_method: str = ""


class Evidence(BaseModel):
    """Evidence section of CP."""

    tests_run: List[str] = Field(default_factory=list)
    results: List[TestResult] = Field(default_factory=list)
    observations: List[str] = Field(default_factory=list)
    discriminating_test: str = ""
    artifacts: Dict[str, List[str]] = Field(default_factory=dict)


class DomainScores(BaseModel):
    """CSS domain score breakdown."""

    evidence_strength: int = 0
    branch_quality: int = 0
    symptom_specificity: int = 0
    environment_specificity: int = 0
    timeline_changes: int = 0
    constraints_risk: int = 0


class CSSInfo(BaseModel):
    """CSS section of CP."""

    score: int = 0
    target: int = 90
    domain_scores: Dict[str, int] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    confidence_notes: str = ""


class Decision(BaseModel):
    """Decision section of CP."""

    status: str = "triage"
    recommended_outcome: str = ""
    reasoning: List[str] = Field(default_factory=list)
    if_escalate: Dict[str, Any] = Field(default_factory=dict)
    resolution_choice: str = ""
    actual_root_cause: str = ""
    resolution_confidence: Optional[float] = None
    resolution_time_mins: int = 0


class GuardrailChecks(BaseModel):
    """Basic troubleshooting guardrail checks."""

    confirmed: bool = False
    scope_confirmed: bool = False
    error_message_confirmed: bool = False
    repro_confirmed: bool = False
    connectivity_confirmed: bool = False
    authentication_confirmed: bool = False
    service_availability_confirmed: bool = False
    missing_checks: List[str] = Field(default_factory=list)


class Guardrails(BaseModel):
    """Guardrails section of CP."""

    basic_troubleshooting: GuardrailChecks = Field(default_factory=GuardrailChecks)


class Notes(BaseModel):
    """Notes section of CP."""

    rolling: str = ""
    final: str = ""
    escalation: str = ""


class Meta(BaseModel):
    """Meta section of CP."""

    schema_version: str = ""
    session_id: str = ""
    last_updated: str = ""
    timezone: str = "America/Chicago"


class Ticket(BaseModel):
    """Ticket section of CP."""

    id: str = ""
    created_at: str = ""
    company: str = ""
    site: str = ""
    priority: str = "UNKNOWN"
    category: str = ""
    service: str = ""
    summary: str = ""
    raw_dump: str = ""
    requester: Requester = Field(default_factory=Requester)


class ContextPayload(BaseModel):
    """Full Context Payload schema."""

    meta: Meta = Field(default_factory=Meta)
    ticket: Ticket = Field(default_factory=Ticket)
    environment: Environment = Field(default_factory=Environment)
    problem: Problem = Field(default_factory=Problem)
    evidence: Evidence = Field(default_factory=Evidence)
    branches: Branches = Field(default_factory=Branches)
    css: CSSInfo = Field(default_factory=CSSInfo)
    decision: Decision = Field(default_factory=Decision)
    guardrails: Guardrails = Field(default_factory=Guardrails)
    notes: Notes = Field(default_factory=Notes)

    class Config:
        extra = "allow"


class TicketSummary(BaseModel):
    """Summary of a ticket for listing."""

    id: str
    priority: str
    company: str
    summary: str
    hostname: str
    status: str
    css_score: int
    last_updated: str
