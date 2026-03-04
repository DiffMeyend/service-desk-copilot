"""Pydantic schemas for CSS (Context Stability Score) data."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class DomainScore(BaseModel):
    """Score for a single CSS domain."""

    domain: str
    weight: int
    score: int
    max_score: int
    completeness: float = Field(
        ..., ge=0.0, le=1.0, description="Domain completeness (0.0 to 1.0)"
    )


class CSSResponse(BaseModel):
    """Full CSS score response."""

    score: int = Field(..., ge=0, le=100, description="Current CSS score")
    target: int = Field(90, description="Target CSS score for decision")
    blockers: List[str] = Field(default_factory=list, description="Active blockers")
    domain_scores: Dict[str, int] = Field(
        default_factory=dict, description="Score per domain"
    )
    missing_for_90: List[str] = Field(
        default_factory=list, description="Missing items to reach CSS >= 90"
    )
    can_decide: bool = Field(
        False, description="Whether CSS is high enough to decide"
    )
