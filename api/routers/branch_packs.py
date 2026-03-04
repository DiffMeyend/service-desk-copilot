"""Branch packs router - list and get branch pack details."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from api.schemas.branch_pack import BranchPackSummary, BranchPackDetail
from api.schemas.ticket import Hypothesis
from api.services.runtime_service import runtime_service


router = APIRouter(prefix="/api/v1/branch-packs", tags=["branch-packs"])


@router.get("", response_model=List[BranchPackSummary])
async def list_branch_packs() -> List[BranchPackSummary]:
    """List all available branch packs."""
    packs_data = runtime_service.get_branch_packs()
    packs = packs_data.get("packs", [])

    result = []
    for pack in packs:
        if not isinstance(pack, dict):
            continue

        result.append(
            BranchPackSummary(
                id=pack.get("id", ""),
                name=pack.get("name", ""),
                category=pack.get("category", ""),
                goal=pack.get("goal", ""),
                hypothesis_count=len(pack.get("hypotheses", [])),
                keywords=pack.get("keywords", []),
            )
        )

    return result


@router.get("/{pack_id}", response_model=BranchPackDetail)
async def get_branch_pack(pack_id: str) -> BranchPackDetail:
    """Get detailed information about a branch pack."""
    pack = runtime_service.get_pack_by_id(pack_id)

    if pack is None:
        available = runtime_service.get_all_pack_ids()[:10]
        raise HTTPException(
            status_code=404,
            detail=f"Pack '{pack_id}' not found. Available: {', '.join(available)}",
        )

    # Convert hypotheses to schema objects
    hypotheses = []
    for hyp in pack.get("hypotheses", []):
        if isinstance(hyp, dict):
            hypotheses.append(
                Hypothesis(
                    id=hyp.get("id", ""),
                    hypothesis=hyp.get("hypothesis", ""),
                    confidence_hint=hyp.get("confidence_hint", 0.0),
                    discriminating_question=hyp.get("discriminating_question", ""),
                    discriminating_tests=hyp.get("discriminating_tests", []),
                    command_refs=hyp.get("command_refs", []),
                    notes=hyp.get("notes", ""),
                )
            )

    return BranchPackDetail(
        id=pack.get("id", ""),
        name=pack.get("name", ""),
        category=pack.get("category", ""),
        goal=pack.get("goal", ""),
        notes=pack.get("notes", ""),
        keywords=pack.get("keywords", []),
        signals=pack.get("signals", []),
        hypotheses=hypotheses,
        preconditions=pack.get("preconditions", {}),
    )
