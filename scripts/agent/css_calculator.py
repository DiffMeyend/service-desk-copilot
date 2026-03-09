"""CSS (Context Stability Score) calculator for QF_Wiz agent.

Implements the scoring rules from css_scoring.yaml.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..core.field_paths import (
    BranchesPaths,
    ConstraintsPaths,
    EnvironmentPaths,
    EvidencePaths,
    GuardrailsPaths,
    ProblemPaths,
)
from . import config


def _is_empty(value: Any) -> bool:
    """Check if a value is empty (None, empty string, empty list)."""
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


def _is_not_empty(value: Any) -> bool:
    """Check if a value is not empty."""
    return not _is_empty(value)


def _len_eq(value: Any, target: int) -> bool:
    """Check if length equals target."""
    if isinstance(value, (list, str)):
        return len(value) == target
    return False


def _len_gt(value: Any, target: int) -> bool:
    """Check if length is greater than target."""
    if isinstance(value, (list, str)):
        return len(value) > target
    return False


def _is_true(value: Any) -> bool:
    """Check if value is True."""
    return value is True


def _is_false(value: Any) -> bool:
    """Check if value is False."""
    return value is False


def _is_null(value: Any) -> bool:
    """Check if value is None."""
    return value is None


def _get_nested(data: Dict[str, Any], path: str) -> Any:
    """Get nested value by dot-separated path."""
    parts = path.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current


def _evaluate_condition(condition: Dict[str, Any], cp: Dict[str, Any]) -> bool:
    """Evaluate a single condition against the context payload."""
    # Handle 'any' - OR logic
    if "any" in condition:
        return any(_evaluate_condition(c, cp) for c in condition["any"])

    # Handle 'all' - AND logic
    if "all" in condition:
        return all(_evaluate_condition(c, cp) for c in condition["all"])

    # Simple condition with path and op
    path = condition.get("path", "")
    op = condition.get("op", "")
    target = condition.get("value")

    value = _get_nested(cp, path)

    if op == "empty":
        return _is_empty(value)
    elif op == "not_empty":
        return _is_not_empty(value)
    elif op == "len_eq":
        return _len_eq(value, target)
    elif op == "len_gt":
        return _len_gt(value, target)
    elif op == "is_true":
        return _is_true(value)
    elif op == "is_false":
        return _is_false(value)
    elif op == "is_null":
        return _is_null(value)

    return False


class CSSCalculator:
    """Calculates Context Stability Score based on rules."""

    def __init__(self, rules: Dict[str, Any]):
        self._rules = rules
        self._target = rules.get("target_css", config.CSS_TARGET)

    def calculate(self, cp: Dict[str, Any]) -> Tuple[int, List[str]]:
        """Calculate CSS score and return (score, blockers).

        Returns a tuple of (score, list_of_blocker_messages).
        """
        blockers: List[str] = []

        # Start with domain-based score
        score = self._calculate_domain_scores(cp)

        # Apply hard caps
        score, cap_blockers = self._apply_hard_caps(cp, score)
        blockers.extend(cap_blockers)

        # Apply penalties
        score, penalty_blockers = self._apply_penalties(cp, score)
        blockers.extend(penalty_blockers)

        # Apply bonuses
        score = self._apply_bonuses(cp, score)

        # Clamp to valid range
        score = max(0, min(100, score))

        return score, blockers

    def _calculate_domain_scores(self, cp: Dict[str, Any]) -> int:
        """Calculate weighted domain scores."""
        domains = self._rules.get("domains", {})
        total_score = 0

        for domain_id, domain_info in domains.items():
            weight = domain_info.get("weight", 0)
            # Calculate domain completeness (simplified heuristic)
            completeness = self._evaluate_domain_completeness(domain_id, cp)
            total_score += round(weight * completeness)

        return total_score

    def _evaluate_domain_completeness(self, domain_id: str, cp: Dict[str, Any]) -> float:
        """Evaluate completeness of a domain (0.0 to 1.0)."""
        # Evidence strength: tests_run and results
        if domain_id == "evidence_strength":
            tests = _get_nested(cp, EvidencePaths.TESTS_RUN) or []
            results = _get_nested(cp, EvidencePaths.RESULTS) or []
            if len(tests) >= 2 and len(results) >= 2:
                return 1.0
            elif len(tests) >= 1 or len(results) >= 1:
                return 0.5
            return 0.0

        # Branch quality: hypotheses and collapse notes
        if domain_id == "branch_quality":
            hyps = _get_nested(cp, BranchesPaths.ACTIVE_HYPOTHESES) or []
            best = _get_nested(cp, BranchesPaths.CURRENT_BEST_GUESS) or ""
            collapsed = _get_nested(cp, BranchesPaths.COLLAPSED_HYPOTHESES) or []
            if best and len(hyps) >= 1:
                return 1.0
            elif len(hyps) >= 1 or len(collapsed) >= 1:
                return 0.5
            return 0.0

        # Symptom specificity: symptoms and impact
        if domain_id == "symptom_specificity":
            symptoms = _get_nested(cp, ProblemPaths.SYMPTOMS) or []
            impact = _get_nested(cp, ProblemPaths.Impact.WORK_STOPPED)
            if len(symptoms) >= 1 and impact is not None:
                return 1.0
            elif len(symptoms) >= 1 or impact is not None:
                return 0.5
            return 0.0

        # Environment specificity: hostname and asset
        if domain_id == "environment_specificity":
            hostname = _get_nested(cp, EnvironmentPaths.TargetDevice.HOSTNAME) or ""
            asset = _get_nested(cp, EnvironmentPaths.TargetDevice.ASSET_TAG) or ""
            serial = _get_nested(cp, EnvironmentPaths.TargetDevice.SERIAL_NUMBER) or ""
            if hostname and (asset or serial):
                return 1.0
            elif hostname:
                return 0.5
            return 0.0

        # Timeline/changes: start time and recent changes
        if domain_id == "timeline_changes":
            start = _get_nested(cp, ProblemPaths.START_TIME) or ""
            changes = _get_nested(cp, ProblemPaths.RECENT_CHANGES) or []
            last_good = _get_nested(cp, ProblemPaths.LAST_KNOWN_GOOD) or ""
            if start and (changes or last_good):
                return 1.0
            elif start or changes or last_good:
                return 0.5
            return 0.0

        # Constraints/risk: ThreatLocker and scope
        if domain_id == "constraints_risk":
            tl = _get_nested(cp, ConstraintsPaths.SecurityControls.THREATLOCKER_PRESENT)
            scope = _get_nested(cp, ProblemPaths.Scope.SINGLE_USER)
            if tl is not None and scope is not None:
                return 1.0
            elif tl is not None or scope is not None:
                return 0.5
            return 0.0

        # Unknown domain
        return 0.0

    def _apply_hard_caps(self, cp: Dict[str, Any], score: int) -> Tuple[int, List[str]]:
        """Apply hard caps based on conditions."""
        blockers = []
        hard_caps = self._rules.get("hard_caps", [])

        for cap_rule in hard_caps:
            condition = cap_rule.get("condition", {})
            cap_value = cap_rule.get("cap", 100)
            reason = cap_rule.get("reason", "Unknown blocker")

            if _evaluate_condition(condition, cp):
                if score > cap_value:
                    score = cap_value
                    blockers.append(reason)

        return score, blockers

    def _apply_penalties(self, cp: Dict[str, Any], score: int) -> Tuple[int, List[str]]:
        """Apply penalties based on conditions."""
        blockers = []
        penalties = self._rules.get("penalties", {})

        # Check for advanced hypothesis before basics
        adv_before = penalties.get("advanced_hypothesis_before_basics", {})
        if adv_before:
            basics_confirmed = _get_nested(cp, GuardrailsPaths.BasicTroubleshooting.CONFIRMED)
            hyps = _get_nested(cp, BranchesPaths.ACTIVE_HYPOTHESES) or []
            if basics_confirmed is False and len(hyps) > 0:
                penalty = adv_before.get("default", 15)
                score -= penalty
                blockers.append(adv_before.get("description", "Advanced hypothesis before basics"))

        # Check for guardrail skipped
        guardrail_penalty = penalties.get("basic_guardrail_skipped", {})
        if guardrail_penalty:
            missing = _get_nested(cp, GuardrailsPaths.BasicTroubleshooting.MISSING_CHECKS) or []
            if len(missing) > 0:
                per_missing = guardrail_penalty.get("per_missing_check", 2)
                max_pen = guardrail_penalty.get("max_penalty", 10)
                penalty = min(len(missing) * per_missing, max_pen)
                score -= penalty

        return score, blockers

    def _apply_bonuses(self, cp: Dict[str, Any], score: int) -> int:
        """Apply bonuses based on conditions."""
        bonuses = self._rules.get("bonuses", [])

        for bonus in bonuses:
            condition = bonus.get("condition", {})
            points = bonus.get("points", 0)

            if _evaluate_condition(condition, cp):
                score += points

        return score

    def get_missing_for_90(self, cp: Dict[str, Any]) -> List[str]:
        """Return list of what's needed to reach CSS >= 90."""
        missing = []
        required = self._rules.get("required_evidence_for_css_ge_90", {})
        must_have = required.get("must_have", [])

        for item in must_have:
            # Parse requirement string (e.g., "ticket.priority (not UNKNOWN)")
            # This is simplified - just check if the base path has a value
            parts = item.split(" (")
            path = parts[0].strip()
            value = _get_nested(cp, path)

            if _is_empty(value):
                missing.append(item)
            elif "(not UNKNOWN)" in item and value == "UNKNOWN":
                missing.append(item)
            elif "(>=1)" in item and (not isinstance(value, list) or len(value) < 1):
                missing.append(item)

        return missing

    @property
    def target(self) -> int:
        """Return the target CSS score."""
        return self._target
