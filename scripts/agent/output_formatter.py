"""Output formatter for QF_Wiz agent.

Generates compact block output per router.txt format.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from . import config

logger = logging.getLogger(__name__)

# Optional analytics import for confidence deltas
try:
    from ..analytics.confidence_updater import ConfidenceUpdater

    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False


def _get_nested(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get nested value by dot-separated path."""
    parts = path.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict):
            return default
        current = current.get(part)
        if current is None:
            return default
    return current


class OutputFormatter:
    """Generates compact block output per router.txt format."""

    def __init__(
        self,
        cp: Dict[str, Any],
        css_score: int,
        blockers: List[str],
        target: int = config.CSS_TARGET,
        show_confidence_deltas: bool = True,
    ):
        self._cp = cp
        self._css_score = css_score
        self._blockers = blockers
        self._target = target
        self._show_confidence_deltas = show_confidence_deltas
        self._confidence_cache: Dict[str, Dict[str, Any]] = {}

        # Pre-load confidence deltas if analytics available
        if self._show_confidence_deltas and ANALYTICS_AVAILABLE:
            try:
                updater = ConfidenceUpdater()
                updates = updater.compute_updates(days=365)
                for report in updates.values():
                    for h_id, outcome in report.hypotheses.items():
                        posterior = outcome.compute_posterior()
                        self._confidence_cache[h_id] = {
                            "prior": outcome.prior_confidence,
                            "posterior": posterior,
                            "delta": posterior - outcome.prior_confidence,
                            "sample_size": outcome.total_observations,
                        }
            except (AttributeError, TypeError, KeyError) as e:
                # Expected errors when analytics data is malformed or missing
                logger.debug("Could not load confidence data: %s", e)
            except (OSError, IOError) as e:
                # File system errors reading analytics logs
                logger.debug("Could not read analytics files: %s", e)
            except ValueError as e:
                # Data conversion errors
                logger.debug("Invalid analytics data: %s", e)

    def format_snapshot_header(self) -> str:
        """Format the CP snapshot header line."""
        ticket_id = _get_nested(self._cp, "ticket.id", "UNKNOWN")
        priority = _get_nested(self._cp, "ticket.priority", "UNKNOWN")
        hostname = _get_nested(self._cp, "environment.target_device.hostname", "UNKNOWN")
        return f"CP Snapshot: {ticket_id} | {priority} | {hostname}"

    def format_cp_bullets(self) -> str:
        """Format 1-8 bullet points summarizing what we know."""
        bullets = []

        # Company/site
        company = _get_nested(self._cp, "ticket.company", "")
        site = _get_nested(self._cp, "ticket.site", "")
        if company:
            loc = company
            if site:
                loc += f" / {site}"
            bullets.append(f"Location: {loc}")

        # Requester
        requester = _get_nested(self._cp, "ticket.requester.name", "")
        if requester:
            bullets.append(f"Requester: {requester}")

        # Summary/symptoms
        summary = _get_nested(self._cp, "ticket.summary", "")
        if summary:
            # Truncate long summaries
            if len(summary) > 60:
                summary = summary[:57] + "..."
            bullets.append(f"Issue: {summary}")

        # Symptoms
        symptoms = _get_nested(self._cp, "problem.symptoms", [])
        if symptoms and isinstance(symptoms, list) and len(symptoms) > 0:
            bullets.append(f"Symptoms: {', '.join(symptoms[:3])}")

        # Impact
        impact = _get_nested(self._cp, "problem.impact.work_stopped")
        if impact is not None:
            bullets.append(f"Work stopped: {'Yes' if impact else 'No'}")

        # Scope
        scope_parts = []
        if _get_nested(self._cp, "problem.scope.single_user"):
            scope_parts.append("single user")
        if _get_nested(self._cp, "problem.scope.single_device"):
            scope_parts.append("single device")
        if _get_nested(self._cp, "problem.scope.service_wide"):
            scope_parts.append("service-wide")
        if scope_parts:
            bullets.append(f"Scope: {', '.join(scope_parts)}")

        # Tests run
        tests = _get_nested(self._cp, "evidence.tests_run", [])
        if tests and isinstance(tests, list):
            bullets.append(f"Tests run: {len(tests)}")

        # Current best guess
        best_guess = _get_nested(self._cp, "branches.current_best_guess", "")
        if best_guess:
            bullets.append(f"Best guess: {best_guess}")

        # Limit to 8 bullets
        bullets = bullets[:8]

        if not bullets:
            bullets = ["No context captured yet"]

        return "\n".join(f"  - {b}" for b in bullets)

    def format_css_section(self) -> str:
        """Format the CSS score line."""
        return f"CSS: {self._css_score}/{self._target}"

    def format_blockers(self) -> str:
        """Format the blockers list."""
        if not self._blockers:
            return "Blockers: None"

        lines = ["Blockers:"]
        for i, blocker in enumerate(self._blockers[:5], 1):
            lines.append(f"  {i}) {blocker}")
        return "\n".join(lines)

    def format_hypotheses(self) -> str:
        """Format the hypotheses list (max 5) with optional confidence deltas."""
        hyps = _get_nested(self._cp, "branches.active_hypotheses", [])

        if not hyps or not isinstance(hyps, list):
            source_pack = _get_nested(self._cp, "branches.source_pack", [])
            if source_pack:
                return f"HYPOTHESES: Pack loaded ({', '.join(source_pack)}) but no hypotheses defined"
            return "HYPOTHESES: None (run LOAD_BRANCH_PACK to add)"

        lines = ["HYPOTHESES:"]
        for i, hyp in enumerate(hyps[: config.MAX_ACTIVE_HYPOTHESES], 1):
            if isinstance(hyp, dict):
                # Try 'hypothesis' field first (branch pack format), then 'name'
                name = hyp.get("hypothesis") or hyp.get("name", "Unknown")
                hyp_id = hyp.get("id", "")
                confidence = hyp.get("confidence_hint", "")

                # Check for learned confidence delta
                conf_str = ""
                if confidence:
                    if hyp_id and hyp_id in self._confidence_cache:
                        cached = self._confidence_cache[hyp_id]
                        posterior = cached["posterior"]
                        delta = cached["delta"]
                        n = cached["sample_size"]

                        # Format: [0.52 ↑ (was 0.45, n=37)]
                        if delta > 0.01:
                            arrow = "↑"
                        elif delta < -0.01:
                            arrow = "↓"
                        else:
                            arrow = "→"

                        conf_str = f"[{posterior:.2f} {arrow} (was {confidence}, n={n})]"
                    else:
                        conf_str = f"[{confidence}]"

                if conf_str:
                    lines.append(f"  {i}) {name} {conf_str}")
                else:
                    lines.append(f"  {i}) {name}")
            elif isinstance(hyp, str):
                lines.append(f"  {i}) {hyp}")

        return "\n".join(lines)

    def format_next_action(self) -> str:
        """Format the suggested next action."""
        hyps = _get_nested(self._cp, "branches.active_hypotheses", [])
        tests = _get_nested(self._cp, "evidence.tests_run", [])

        # If CSS is high enough, suggest decision
        if self._css_score >= self._target:
            return "NEXT:\n  CSS target reached. Run DECIDE to evaluate resolution."

        # If no hypotheses, suggest loading a pack
        if not hyps:
            return "NEXT:\n  Q: What pack should we load? (LOAD_BRANCH_PACK <pack_id>)"

        # Check if first hypothesis has a discriminating test
        first_hyp = hyps[0] if hyps else {}
        if isinstance(first_hyp, dict):
            disc_tests = first_hyp.get("discriminating_tests", [])
            if disc_tests:
                test = disc_tests[0]
                hyp_name = first_hyp.get("hypothesis") or first_hyp.get("name", "hypothesis")
                return f"NEXT:\n  Run the command below to test '{hyp_name}':\n  {test}"

            # Check for command_refs
            cmd_refs = first_hyp.get("command_refs", [])
            if cmd_refs:
                return f"NEXT:\n  Run: {cmd_refs[0]}"

        # Default to asking for more evidence
        return "NEXT:\n  Q: What evidence can we gather to narrow down the issue?"

    def format_input_hint(self) -> str:
        """Format the input hint."""
        return 'INPUT:\n  Paste with: LOG_RESULT {"command_id": "...", "output": "..."}'

    def render_compact_block(self) -> str:
        """Render the full compact block output."""
        sections = [
            self.format_snapshot_header(),
            "",
            self.format_cp_bullets(),
            "",
            self.format_css_section(),
            self.format_blockers(),
            "",
            self.format_hypotheses(),
            "",
            self.format_next_action(),
            "",
            self.format_input_hint(),
        ]
        return "\n".join(sections)
