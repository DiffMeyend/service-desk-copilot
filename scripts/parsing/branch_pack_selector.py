#!/usr/bin/env python3
"""Branch pack selector utilities used during ticket ingestion."""

from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[2]
BRANCH_PACK_CATALOG = ROOT / "runtime" / "branch_packs_catalog_v1_0.yaml"
TAXONOMY_MAPPING = ROOT / "runtime" / "taxonomy_pack_mapping.yaml"
MAX_ACTIVE_HYPOTHESES = 5

logger = logging.getLogger(__name__)

# Track load failures for diagnostic purposes
_taxonomy_load_error: Optional[str] = None
_catalog_load_error: Optional[str] = None


def _safe_lower(value: str) -> str:
    return (value or "").lower()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@functools.lru_cache(maxsize=1)
def _load_taxonomy_data() -> Dict[str, object]:
    """Load the full taxonomy mapping YAML including aliases.

    Returns:
        Parsed taxonomy dict, or empty dict if loading fails.
        Check _taxonomy_load_error for failure details.
    """
    global _taxonomy_load_error
    _taxonomy_load_error = None

    try:
        text = TAXONOMY_MAPPING.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        _taxonomy_load_error = f"Taxonomy file not found: {TAXONOMY_MAPPING}"
        logger.warning(_taxonomy_load_error)
        return {}
    except PermissionError:
        _taxonomy_load_error = f"Permission denied reading taxonomy: {TAXONOMY_MAPPING}"
        logger.warning(_taxonomy_load_error)
        return {}

    safe_text = "".join(ch for ch in text if (32 <= ord(ch) <= 126) or ch in "\n\r\t" or ord(ch) >= 160)

    try:
        data = yaml.safe_load(safe_text)
    except yaml.YAMLError as e:
        _taxonomy_load_error = f"YAML parse error in taxonomy: {e}"
        logger.warning(_taxonomy_load_error)
        return {}

    if not isinstance(data, dict):
        _taxonomy_load_error = f"Taxonomy file does not contain a dict (got {type(data).__name__})"
        logger.warning(_taxonomy_load_error)
        return {}

    return data


def _load_taxonomy_mapping() -> List[Dict[str, object]]:
    """Load the taxonomy pack mappings list."""
    data = _load_taxonomy_data()
    mappings = data.get("mappings", [])
    return mappings if isinstance(mappings, list) else []


def _get_issue_type_aliases() -> Dict[str, str]:
    """Load Issue Type aliases mapping variant names to canonical names."""
    data = _load_taxonomy_data()
    aliases = data.get("issue_type_aliases", {})
    return aliases if isinstance(aliases, dict) else {}


def _resolve_issue_type_alias(issue_type: str) -> str:
    """Resolve an Issue Type to its canonical name using aliases."""
    if not issue_type:
        return issue_type
    aliases = _get_issue_type_aliases()
    # Try exact match first
    if issue_type in aliases:
        return aliases[issue_type]
    # Try case-insensitive match
    issue_lower = issue_type.lower()
    for alias, canonical in aliases.items():
        if alias.lower() == issue_lower:
            return canonical
    return issue_type


def _lookup_taxonomy(issue_type: str, sub_issue_type: str) -> Tuple[Optional[Dict[str, object]], Dict[str, object]]:
    """Look up pack mapping by Issue Type and Sub-Issue Type.

    Uses alias resolution and fuzzy matching to handle variants like:
    - "Workstation Issue" -> alias -> "Workstation"
    - "Microsoft Issue" -> alias -> "Microsoft 365"
    - "Software Issue" -> alias -> "Server"

    Returns mapping dict and metadata describing how the lookup matched.
    """
    detail: Dict[str, object] = {
        "matched": False,
        "match_stage": "none",
        "match_status": "not_found",
        "alias_applied": False,
        "issue_type_input": issue_type or "",
        "issue_type_resolved": issue_type or "",
        "mapping_issue_type": "",
        "mapping_sub_issue_type": "",
    }
    if not issue_type or not sub_issue_type:
        detail["match_stage"] = "skipped"
        detail["match_status"] = "skipped"
        return None, detail

    # Resolve Issue Type alias first
    resolved_issue = _resolve_issue_type_alias(issue_type)
    detail["issue_type_resolved"] = resolved_issue
    detail["alias_applied"] = _safe_lower(resolved_issue) != _safe_lower(issue_type)
    issue_lower = _safe_lower(resolved_issue)
    sub_lower = _safe_lower(sub_issue_type)
    mappings = _load_taxonomy_mapping()

    # Pass 1: Exact match on both Issue Type and Sub-Issue Type
    for mapping in mappings:
        map_issue = _safe_lower(mapping.get("issue_type", ""))
        map_sub = _safe_lower(mapping.get("sub_issue_type", ""))
        if map_issue == issue_lower and map_sub == sub_lower:
            detail.update(
                {
                    "matched": True,
                    "match_stage": "exact",
                    "mapping_issue_type": mapping.get("issue_type", ""),
                    "mapping_sub_issue_type": mapping.get("sub_issue_type", ""),
                }
            )
            return mapping, detail

    # Pass 2: Fuzzy match - ticket Issue Type CONTAINS mapping Issue Type
    # e.g., "Workstation Issue" contains "Workstation"
    # Sub-Issue Type must still match exactly
    for mapping in mappings:
        map_issue = _safe_lower(mapping.get("issue_type", ""))
        map_sub = _safe_lower(mapping.get("sub_issue_type", ""))
        if map_sub == sub_lower and map_issue and map_issue in issue_lower:
            detail.update(
                {
                    "matched": True,
                    "match_stage": "ticket_contains_mapping_issue",
                    "mapping_issue_type": mapping.get("issue_type", ""),
                    "mapping_sub_issue_type": mapping.get("sub_issue_type", ""),
                }
            )
            return mapping, detail

    # Pass 3: Fuzzy match - mapping Issue Type CONTAINS ticket Issue Type
    # e.g., "Microsoft 365" contains "Microsoft" (for "Microsoft Issue")
    for mapping in mappings:
        map_issue = _safe_lower(mapping.get("issue_type", ""))
        map_sub = _safe_lower(mapping.get("sub_issue_type", ""))
        # Extract base word from ticket issue type (e.g., "Microsoft" from "Microsoft Issue")
        issue_base = issue_lower.replace(" issue", "").replace(" problem", "").replace(" request", "").strip()
        if map_sub == sub_lower and issue_base and issue_base in map_issue:
            detail.update(
                {
                    "matched": True,
                    "match_stage": "mapping_contains_issue",
                    "mapping_issue_type": mapping.get("issue_type", ""),
                    "mapping_sub_issue_type": mapping.get("sub_issue_type", ""),
                }
            )
            return mapping, detail

    return None, detail


@functools.lru_cache(maxsize=1)
def _load_catalog() -> Dict[str, object]:
    """Load the branch packs catalog YAML.

    Returns:
        Parsed catalog dict, or empty dict if loading fails.
        Check _catalog_load_error for failure details.
    """
    global _catalog_load_error
    _catalog_load_error = None

    try:
        text = BRANCH_PACK_CATALOG.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        _catalog_load_error = f"Branch pack catalog not found: {BRANCH_PACK_CATALOG}"
        logger.warning(_catalog_load_error)
        return {}
    except PermissionError:
        _catalog_load_error = f"Permission denied reading catalog: {BRANCH_PACK_CATALOG}"
        logger.warning(_catalog_load_error)
        return {}

    safe_text = "".join(ch for ch in text if (32 <= ord(ch) <= 126) or ch in "\n\r\t" or ord(ch) >= 160)

    try:
        data = yaml.safe_load(safe_text)
    except yaml.YAMLError as e:
        _catalog_load_error = f"YAML parse error in catalog: {e}"
        logger.warning(_catalog_load_error)
        return {}

    if not isinstance(data, dict):
        _catalog_load_error = f"Catalog file does not contain a dict (got {type(data).__name__})"
        logger.warning(_catalog_load_error)
        return {}

    return data


def _iter_packs() -> Sequence[Dict[str, object]]:
    catalog = _load_catalog()
    packs = catalog.get("packs", [])
    return packs if isinstance(packs, list) else []


def _get_pack_by_id(pack_id: str) -> Optional[Dict[str, object]]:
    """Get a pack by its ID from the catalog."""
    if not pack_id:
        return None
    for pack in _iter_packs():
        if pack.get("id") == pack_id:
            return pack
    return None


def _match_stats(
    pack: Dict[str, object],
    haystack: str,
    summary_text: str,
) -> Tuple[int, int, int, List[str]]:
    tokens: List[str] = []
    for key in ("keywords", "signals"):
        values = pack.get(key) or []
        if isinstance(values, list):
            tokens.extend(str(item) for item in values if item)
    score = 0
    summary_hits = 0
    longest = 0
    matched_tokens: List[str] = []
    for token in tokens:
        normalized = token.strip().lower()
        if not normalized or normalized in {"-", "_"}:
            continue
        if normalized in haystack:
            score += 1
            longest = max(longest, len(normalized))
            if normalized in summary_text:
                summary_hits += 1
            matched_tokens.append(token.strip())
    return score, summary_hits, longest, matched_tokens


def _rank_key(item: Dict[str, object]) -> Tuple[int, int, int, str]:
    return (
        -item["score"],
        -item["summary_hits"],
        -item["longest_match"],
        item["pack"]["id"],
    )


def _format_hypothesis(
    pack: Dict[str, object],
    hypothesis: Dict[str, object],
    confidence: Optional[float] = None,
    match_type: str = "",
    explanation: str = "",
    matched_tokens: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    data = {
        "id": hypothesis.get("id", ""),
        "pack_id": pack.get("id", ""),
        "pack_name": pack.get("name", ""),
        "category": pack.get("category", ""),
        "hypothesis": hypothesis.get("hypothesis", ""),
        "confidence_hint": hypothesis.get("confidence_hint"),
        "discriminating_question": hypothesis.get("discriminating_question", ""),
        "discriminating_tests": hypothesis.get("discriminating_tests", []) or [],
        "command_refs": hypothesis.get("command_refs", []) or [],
        "notes": hypothesis.get("notes", ""),
        "goal": pack.get("goal", ""),
        "pack_notes": pack.get("notes", ""),
    }
    if confidence is not None:
        data["confidence_score"] = confidence
    if match_type:
        data["match_type"] = match_type
    if explanation:
        data["match_explanation"] = explanation
    if matched_tokens:
        data["matched_tokens"] = list(matched_tokens)
    return data


def _select_by_keywords(summary: str, raw_text: str) -> List[Dict[str, object]]:
    """Select packs using keyword matching (fallback method)."""
    summary_text = _safe_lower(summary)
    haystack = _safe_lower(f"{summary or ''}\n{raw_text or ''}")
    matches: List[Dict[str, object]] = []
    cross_matches: List[Dict[str, object]] = []

    for pack in _iter_packs():
        score, summary_hits, longest, hits = _match_stats(pack, haystack, summary_text)
        if score <= 0:
            continue
        entry = {
            "pack": pack,
            "score": score,
            "summary_hits": summary_hits,
            "longest_match": longest,
            "hits": hits[:5],
            "match_type": "keyword",
        }
        if pack.get("category") == "cross_cutting":
            cross_matches.append(entry)
        else:
            matches.append(entry)

    matches.sort(key=_rank_key)
    cross_matches.sort(key=_rank_key)

    selected: List[Dict[str, object]] = []
    if matches:
        selected.append(matches[0])
    elif cross_matches:
        selected.append(cross_matches[0])

    if selected and cross_matches:
        fallback = cross_matches[0]
        if fallback["pack"]["id"] not in {sel["pack"]["id"] for sel in selected}:
            selected.append(fallback)

    return selected


def _select_by_taxonomy(
    issue_type: str,
    sub_issue_type: str,
) -> Tuple[List[Dict[str, object]], bool, Dict[str, object]]:
    """Select packs using taxonomy mapping (primary method).

    Returns:
        Tuple of (selected pack entries, was_taxonomy_match, match_detail)
    """
    mapping, match_detail = _lookup_taxonomy(issue_type, sub_issue_type)
    if not mapping:
        return [], False, match_detail

    primary_pack_id = mapping.get("primary_pack")
    fallback_pack_ids = mapping.get("fallback_packs", []) or []
    match_detail["fallback_pack_ids"] = fallback_pack_ids

    # Skip if primary pack is marked as needing creation
    if not primary_pack_id or "NEW_PACK_NEEDED" in str(mapping.get("notes", "")):
        match_detail["match_status"] = "pack_missing"
        return [], False, match_detail

    selected: List[Dict[str, object]] = []

    # Get primary pack
    primary_pack = _get_pack_by_id(primary_pack_id)
    if primary_pack:
        selected.append(
            {
                "pack": primary_pack,
                "score": 100,  # High score for taxonomy match
                "summary_hits": 0,
                "longest_match": 0,
                "match_type": "taxonomy",
                "match_detail": match_detail,
            }
        )

    # Get first fallback pack (typically cross-cutting)
    for fb_id in fallback_pack_ids[:1]:
        fb_pack = _get_pack_by_id(fb_id)
        if fb_pack and fb_pack.get("id") != primary_pack_id:
            selected.append(
                {
                    "pack": fb_pack,
                    "score": 50,  # Lower score for fallback
                    "summary_hits": 0,
                    "longest_match": 0,
                    "match_type": "taxonomy_fallback",
                    "match_detail": match_detail,
                }
            )
            break

    match_detail["match_status"] = "pack_loaded" if selected else "pack_missing"
    match_detail["fallback_loaded"] = len(selected) > 1

    return selected, len(selected) > 0, match_detail


def _confidence_from_taxonomy(match_detail: Dict[str, object], is_fallback: bool = False) -> float:
    stage_scores = {
        "exact": 0.95,
        "ticket_contains_mapping_issue": 0.85,
        "mapping_contains_issue": 0.8,
        "none": 0.7,
        "skipped": 0.6,
    }
    base = stage_scores.get(match_detail.get("match_stage"), 0.7)
    if match_detail.get("alias_applied"):
        base -= 0.02
    if is_fallback:
        base -= 0.1
    return round(_clamp(base, 0.2, 0.98), 2)


def _confidence_from_keyword(entry: Dict[str, object]) -> float:
    score = entry.get("score", 0)
    summary_hits = entry.get("summary_hits", 0)
    longest = entry.get("longest_match", 0)
    base = 0.3 + min(score, 5) * 0.08 + min(summary_hits, 3) * 0.04 + min(longest, 40) / 250
    return round(_clamp(base, 0.25, 0.8), 2)


def _taxonomy_explanation(match_detail: Dict[str, object], match_type: str) -> str:
    stage_desc = {
        "exact": "Exact taxonomy match",
        "ticket_contains_mapping_issue": "Ticket issue contained canonical taxonomy issue",
        "mapping_contains_issue": "Canonical taxonomy issue contained ticket issue keyword",
        "none": "Taxonomy lookup",
        "skipped": "Taxonomy skipped",
    }
    issue_input = match_detail.get("issue_type_input") or "Unknown"
    resolved = match_detail.get("issue_type_resolved") or issue_input
    mapping_issue = match_detail.get("mapping_issue_type") or resolved
    mapping_sub = match_detail.get("mapping_sub_issue_type") or match_detail.get("sub_issue_type", "Unknown")
    parts = [stage_desc.get(match_detail.get("match_stage"), "Taxonomy lookup")]
    if match_detail.get("alias_applied"):
        parts.append(f"alias applied ({issue_input} → {resolved})")
    explanation = (
        f"{', '.join(parts)} for Issue '{issue_input}' mapped to '{mapping_issue}' / Sub-Issue '{mapping_sub}'."
    )
    if match_type == "taxonomy_fallback":
        explanation += " Using taxonomy-defined fallback pack."
    return explanation


def _keyword_explanation(entry: Dict[str, object]) -> str:
    hits = entry.get("hits") or []
    if hits:
        preview = ", ".join(hits[:3])
        explanation = f"Matched keywords: {preview}"
    else:
        explanation = "Selected via keyword score"
    summary_hits = entry.get("summary_hits", 0)
    if summary_hits:
        explanation += f" (summary hits: {summary_hits})"
    return explanation


def select_branch_pack_seed(
    summary: str,
    raw_text: str,
    issue_type: str = "",
    sub_issue_type: str = "",
    manual_override_packs: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    """Return selected pack IDs and formatted hypotheses based on ticket text.

    Uses taxonomy-first routing:
    1. If issue_type and sub_issue_type are provided, look up in taxonomy mapping
    2. If taxonomy lookup succeeds and pack exists, use that
    3. Otherwise, fall back to keyword matching

    Args:
        summary: Ticket summary/title
        raw_text: Full ticket text
        issue_type: PSA Issue Type (e.g., "Network", "User")
        sub_issue_type: PSA Sub-Issue Type (e.g., "VPN", "Login Issue")

    Returns:
        Dict with 'pack_ids', 'hypotheses', and 'routing_method' keys
    """
    routing_method = "keyword"
    taxonomy_detail: Dict[str, object] = {
        "matched": False,
        "match_stage": "skipped" if not (issue_type and sub_issue_type) else "none",
        "match_status": "skipped" if not (issue_type and sub_issue_type) else "not_found",
        "alias_applied": False,
        "issue_type_input": issue_type or "",
        "issue_type_resolved": issue_type or "",
        "mapping_issue_type": "",
        "mapping_sub_issue_type": "",
        "fallback_pack_ids": [],
        "fallback_loaded": False,
    }
    selected: List[Dict[str, object]] = []
    manual_override_info: Optional[Dict[str, List[str]]] = None

    if manual_override_packs:
        manual_override_info = {
            "requested": [],
            "applied": [],
            "invalid": [],
        }
        seen_override: set[str] = set()
        override_entries: List[Dict[str, object]] = []
        for raw_pack_id in manual_override_packs:
            pack_id = (raw_pack_id or "").strip()
            if not pack_id:
                continue
            normalized = pack_id.lower()
            manual_override_info["requested"].append(normalized)
            if normalized in seen_override:
                continue
            seen_override.add(normalized)
            pack = _get_pack_by_id(normalized)
            if not pack:
                manual_override_info["invalid"].append(normalized)
                continue
            override_entries.append(
                {
                    "pack": pack,
                    "score": 200,
                    "summary_hits": 0,
                    "longest_match": 0,
                    "match_type": "manual_override",
                    "hits": [],
                }
            )
            manual_override_info["applied"].append(normalized)
        if override_entries:
            selected = override_entries
            routing_method = "manual_override"
            taxonomy_detail.update(
                {
                    "match_stage": "manual_override",
                    "match_status": "manual_override",
                    "issue_type_input": issue_type or "",
                    "issue_type_resolved": issue_type or "",
                }
            )

    if routing_method != "manual_override":
        # Try taxonomy-first routing
        if issue_type and sub_issue_type:
            selected, taxonomy_matched, taxonomy_detail = _select_by_taxonomy(issue_type, sub_issue_type)
            if taxonomy_matched:
                routing_method = "taxonomy"

        # Fall back to keyword matching if taxonomy didn't yield results
        if not selected:
            selected = _select_by_keywords(summary, raw_text)
            routing_method = "keyword"

    for entry in selected:
        match_type = entry.get("match_type", "keyword")
        if match_type.startswith("taxonomy"):
            detail = taxonomy_detail if match_type.startswith("taxonomy") else entry.get("match_detail", {})
            entry["confidence"] = _confidence_from_taxonomy(detail or {}, match_type == "taxonomy_fallback")
            entry["explanation"] = _taxonomy_explanation(detail or {}, match_type)
        elif match_type == "manual_override":
            entry["confidence"] = 0.99
            pack_id = entry.get("pack", {}).get("id", "")
            entry["explanation"] = f"Manual override requested for pack '{pack_id}'."
        else:
            entry["confidence"] = _confidence_from_keyword(entry)
            entry["explanation"] = _keyword_explanation(entry)

    pack_ids = [item["pack"]["id"] for item in selected]
    hypotheses: List[Dict[str, object]] = []
    for item in selected:
        pack = item["pack"]
        pack_hypotheses = pack.get("hypotheses", [])
        if not isinstance(pack_hypotheses, list):
            continue
        for hypothesis in pack_hypotheses:
            hypotheses.append(
                _format_hypothesis(
                    pack,
                    hypothesis,
                    confidence=item.get("confidence"),
                    match_type=item.get("match_type", routing_method),
                    explanation=item.get("explanation", ""),
                    matched_tokens=item.get("hits"),
                )
            )
            if len(hypotheses) >= MAX_ACTIVE_HYPOTHESES:
                break
        if len(hypotheses) >= MAX_ACTIVE_HYPOTHESES:
            break

    routing_metadata = {
        "issue_type": issue_type or "",
        "sub_issue_type": sub_issue_type or "",
        "taxonomy_match": taxonomy_detail,
    }
    if manual_override_info:
        routing_metadata["manual_override"] = manual_override_info
    if routing_method == "keyword" and taxonomy_detail.get("match_status") != "pack_loaded":
        if taxonomy_detail["match_stage"] == "skipped":
            routing_metadata["keyword_reason"] = "taxonomy_missing_fields"
        elif taxonomy_detail.get("match_status") == "pack_missing":
            routing_metadata["keyword_reason"] = "taxonomy_pack_missing"
        else:
            routing_metadata["keyword_reason"] = "taxonomy_no_match"

    return {
        "pack_ids": pack_ids,
        "hypotheses": hypotheses,
        "routing_method": routing_method,
        "routing_metadata": routing_metadata,
    }
