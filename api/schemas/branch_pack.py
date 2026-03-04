"""Pydantic schemas for branch pack data."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from .ticket import Hypothesis


class BranchPackSummary(BaseModel):
    """Summary of a branch pack for listing."""

    id: str
    name: str
    category: str
    goal: str
    hypothesis_count: int
    keywords: List[str] = Field(default_factory=list)


class BranchPackDetail(BaseModel):
    """Full branch pack details."""

    id: str
    name: str
    category: str
    goal: str
    notes: str = ""
    keywords: List[str] = Field(default_factory=list)
    signals: List[str] = Field(default_factory=list)
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    preconditions: dict = Field(default_factory=dict)
