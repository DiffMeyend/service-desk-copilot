"""Command handler for QF_Wiz agent.

Parses and dispatches operator commands.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Import from centralized exceptions module
from ..core.exceptions import CommandError
from . import config
from .cp_manager import CPManager
from .runtime_loader import RuntimeLoader

# Re-export for backward compatibility
__all__ = ["CommandError", "CommandHandler"]

# Import IntakeAgent for resolution logging, pack stats, and patterns
try:
    from ..intake.agent import IntakeAgent

    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False


class CommandHandler:
    """Parses and dispatches operator commands."""

    # Supported commands
    COMMANDS = {
        "LOG": "Record test result (simple syntax)",
        "LOG_RESULT": "Record test result (JSON syntax)",
        "LOAD_BRANCH_PACK": "Override/load specific pack",
        "PRINT_CONTEXT": "Output CP summary",
        "PRINT_CONTEXT_FULL": "Output full CP JSON",
        "PRINT_NEXT": "Show suggested next action",
        "DECIDE": "Force decision evaluation",
        "PACK_STATS": "Show pack effectiveness metrics",
        "PATTERNS": "Show detected patterns (device/user recurrence, temporal)",
        "QUIT": "Save and exit",
        "EXIT": "Save and exit",
        "HELP": "Show available commands",
    }

    def __init__(self, cp_manager: CPManager, runtime: RuntimeLoader):
        self._cp = cp_manager
        self._runtime = runtime
        self._session_start = datetime.now(timezone.utc)

    def parse_input(self, raw_input: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Parse raw input into command and optional payload.

        Returns (command_name, payload_dict_or_None).
        """
        raw_input = raw_input.strip()
        if not raw_input:
            return ("", None)

        # Check for simple LOG syntax: LOG <command_id> <output>
        # Supports: LOG ping "Reply from server" or LOG ping Reply_from_server
        if raw_input.upper().startswith("LOG ") and not raw_input.upper().startswith("LOG_RESULT"):
            parts = raw_input[4:].strip().split(maxsplit=1)
            if parts:
                command_id = parts[0]
                output = ""
                if len(parts) > 1:
                    # Strip surrounding quotes if present
                    output = parts[1].strip()
                    if (output.startswith('"') and output.endswith('"')) or (
                        output.startswith("'") and output.endswith("'")
                    ):
                        output = output[1:-1]
                return ("LOG_RESULT", {"command_id": command_id, "output": output})

        # Check for JSON payload (LOG_RESULT with JSON)
        if raw_input.startswith("LOG_RESULT "):
            json_part = raw_input[len("LOG_RESULT ") :].strip()
            if json_part.startswith("{"):
                try:
                    payload = json.loads(json_part)
                    return ("LOG_RESULT", payload)
                except json.JSONDecodeError as e:
                    raise CommandError(f"Invalid JSON in LOG_RESULT: {e}")

        # Check for pack ID (LOAD_BRANCH_PACK pack_id)
        if raw_input.startswith("LOAD_BRANCH_PACK "):
            pack_id = raw_input[len("LOAD_BRANCH_PACK ") :].strip()
            return ("LOAD_BRANCH_PACK", {"pack_id": pack_id})

        # Check for PACK_STATS with optional pack_id
        if raw_input.upper().startswith("PACK_STATS"):
            parts = raw_input.split(maxsplit=1)
            pack_id = parts[1].strip() if len(parts) > 1 else None
            return ("PACK_STATS", {"pack_id": pack_id} if pack_id else None)

        # Check for PATTERNS with optional scope (device/user/all)
        if raw_input.upper().startswith("PATTERNS"):
            parts = raw_input.split(maxsplit=1)
            scope = parts[1].strip().lower() if len(parts) > 1 else None
            return ("PATTERNS", {"scope": scope} if scope else None)

        # Simple commands without payload
        parts = raw_input.split(maxsplit=1)
        cmd = parts[0].upper()
        if cmd in self.COMMANDS:
            return (cmd, None)

        # Unknown command
        return (raw_input, None)

    def dispatch(self, cmd: str, payload: Optional[Dict[str, Any]]) -> str:
        """Dispatch command to appropriate handler. Returns response string."""
        if cmd == "LOG_RESULT":
            if not payload:
                return "ERROR: LOG_RESULT requires JSON payload"
            return self.handle_log_result(payload)

        if cmd == "LOAD_BRANCH_PACK":
            if not payload or "pack_id" not in payload:
                return "ERROR: LOAD_BRANCH_PACK requires pack ID"
            return self.handle_load_branch_pack(payload["pack_id"])

        if cmd == "PRINT_CONTEXT":
            return self.handle_print_context(full=False)

        if cmd == "PRINT_CONTEXT_FULL":
            return self.handle_print_context(full=True)

        if cmd == "PRINT_NEXT":
            return self.handle_print_next()

        if cmd == "DECIDE":
            return self.handle_decide()

        if cmd == "PACK_STATS":
            pack_id = payload.get("pack_id") if payload else None
            return self.handle_pack_stats(pack_id)

        if cmd == "PATTERNS":
            scope = payload.get("scope") if payload else None
            return self.handle_patterns(scope)

        if cmd in ("QUIT", "EXIT"):
            return "QUIT"

        if cmd == "HELP":
            return self.handle_help()

        return f"ERROR: Unknown command '{cmd}'. Type HELP for available commands."

    def handle_log_result(self, payload: Dict[str, Any]) -> str:
        """Handle LOG_RESULT command - record test result in CP."""
        command_id = payload.get("command_id", "unknown")
        output = payload.get("output", "")
        notes = payload.get("notes", "")
        captured_at = payload.get(
            "captured_at",
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        # Build test entry
        test_entry = {
            "command_id": command_id,
            "captured_at": captured_at,
            "notes": notes,
        }

        # Build result entry
        result_entry = {
            "command_id": command_id,
            "output": output[:500] if len(output) > 500 else output,  # Truncate for summary
            "captured_at": captured_at,
        }

        # Add to evidence
        self._cp.append_value("evidence.tests_run", command_id)
        self._cp.append_value("evidence.results", result_entry)

        # Add to rolling notes
        note_line = f"[{captured_at}] Logged result for {command_id}"
        if notes:
            note_line += f": {notes}"
        rolling = self._cp.get_value("notes.rolling") or ""
        if rolling:
            rolling += "\n"
        rolling += note_line
        self._cp.set_value("notes.rolling", rolling)

        return f"Logged result for: {command_id}"

    def handle_load_branch_pack(self, pack_id: str) -> str:
        """Handle LOAD_BRANCH_PACK command - override pack selection."""
        pack = self._runtime.get_pack_by_id(pack_id)
        if not pack:
            # List available packs
            available = self._get_available_pack_ids()[:10]
            return f"ERROR: Pack '{pack_id}' not found. Try: {', '.join(available)}"

        # Get hypotheses from pack (limit to MAX_ACTIVE_HYPOTHESES)
        hypotheses = pack.get("hypotheses", [])
        if len(hypotheses) > config.MAX_ACTIVE_HYPOTHESES:
            hypotheses = hypotheses[: config.MAX_ACTIVE_HYPOTHESES]

        # Update CP
        self._cp.set_value("branches.source_pack", [pack_id])
        self._cp.set_value("branches.active_hypotheses", hypotheses)

        # Add to manual overrides tracking
        overrides = self._cp.get_value("branches.manual_overrides") or []
        if not isinstance(overrides, list):
            overrides = []
        overrides.append(
            {
                "pack_id": pack_id,
                "loaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
        self._cp.set_value("branches.manual_overrides", overrides)

        # Add to rolling notes
        note = f"Manual override: loaded pack '{pack_id}' ({len(hypotheses)} hypotheses)"
        rolling = self._cp.get_value("notes.rolling") or ""
        if rolling:
            rolling += "\n"
        rolling += note
        self._cp.set_value("notes.rolling", rolling)

        return f"Loaded pack: {pack_id} ({len(hypotheses)} hypotheses)"

    def handle_print_context(self, full: bool = False) -> str:
        """Handle PRINT_CONTEXT or PRINT_CONTEXT_FULL."""
        if full:
            return json.dumps(self._cp.cp, indent=2, ensure_ascii=False)

        # Summary format
        lines = [
            f"Ticket: {self._cp.get_ticket_id()}",
            f"Priority: {self._cp.get_priority()}",
            f"Hostname: {self._cp.get_hostname() or 'UNKNOWN'}",
            f"Status: {self._cp.get_current_state()}",
            f"CSS: {self._cp.get_css_score()}/{config.CSS_TARGET}",
            f"Source Pack: {', '.join(self._cp.get_source_pack()) or 'None'}",
            f"Tests Run: {len(self._cp.get_tests_run())}",
            f"Hypotheses: {len(self._cp.get_active_hypotheses())}",
        ]
        return "\n".join(lines)

    def handle_print_next(self) -> str:
        """Handle PRINT_NEXT - suggest next action."""
        hyps = self._cp.get_active_hypotheses()
        tests = self._cp.get_tests_run()
        css = self._cp.get_css_score()

        # If no hypotheses, suggest loading a pack
        if not hyps:
            return "NEXT: No active hypotheses. Run LOAD_BRANCH_PACK <pack_id> to load one."

        # If CSS is high enough, suggest decision
        if css >= config.CSS_TARGET:
            return "NEXT: CSS >= 90. Run DECIDE to evaluate resolution options."

        # Otherwise, suggest running the first hypothesis's discriminating test
        first_hyp = hyps[0] if hyps else {}
        disc_tests = first_hyp.get("discriminating_tests", [])
        if disc_tests:
            test = disc_tests[0]
            hyp_name = first_hyp.get("hypothesis") or first_hyp.get("name", "unknown")
            return f"NEXT: Run discriminating test for '{hyp_name}': {test}"

        return "NEXT: Gather more evidence to increase CSS score."

    def handle_decide(self) -> str:
        """Handle DECIDE - force decision evaluation and log resolution."""
        css = self._cp.get_css_score()
        warning = ""

        if css < config.CSS_TARGET:
            warning = f"WARNING: CSS is {css}/{config.CSS_TARGET}. Decision may be premature.\n"

        # Update status
        self._cp.set_value("decision.status", "DECIDE")

        # Set resolution metadata
        best_guess = self._cp.get_value("branches.current_best_guess") or "Unknown"
        self._cp.set_value("decision.actual_root_cause", best_guess)
        self._cp.set_value("decision.resolution_choice", "RESOLVE")
        self._cp.set_value("decision.resolution_confidence", css / 100.0)

        # Calculate resolution time from session start
        elapsed = round((datetime.now(timezone.utc) - self._session_start).total_seconds() / 60, 1)
        self._cp.set_value("decision.resolution_time_mins", elapsed)

        # Log resolution to analytics via IntakeAgent
        if ANALYTICS_AVAILABLE:
            try:
                intake = IntakeAgent()
                log_file = intake.log_resolution(self._cp.cp)
                resolution_note = f"\nResolution logged to {log_file.name}"
            except Exception as e:
                resolution_note = f"\nFailed to log resolution: {e}"
        else:
            resolution_note = ""

        return f"{warning}Decision mode entered. Best guess: {best_guess}{resolution_note}"

    def handle_help(self) -> str:
        """Handle HELP - show available commands."""
        lines = ["Available commands:"]
        for cmd, desc in self.COMMANDS.items():
            lines.append(f"  {cmd}: {desc}")
        lines.append("")
        lines.append("Examples:")
        lines.append('  LOG_RESULT {"command_id": "ping_test", "output": "Reply from..."}')
        lines.append("  LOAD_BRANCH_PACK vpn_client")
        lines.append("  PRINT_CONTEXT")
        return "\n".join(lines)

    def _get_available_pack_ids(self) -> List[str]:
        """Get list of available pack IDs."""
        packs = self._runtime.get_branch_packs().get("packs", [])
        return [p.get("id", "") for p in packs if isinstance(p, dict) and p.get("id")]

    def handle_pack_stats(self, pack_id: Optional[str] = None) -> str:
        """Handle PACK_STATS - show pack effectiveness metrics."""
        if not ANALYTICS_AVAILABLE:
            return "ERROR: Analytics module not available. Check scripts/analytics/ setup."

        try:
            intake = IntakeAgent()
            stats_dict = intake.get_pack_stats(pack_id=pack_id)

            if not stats_dict:
                if pack_id:
                    return f"No data for pack: {pack_id}"
                return "No resolution data available yet. Resolve some tickets first!"

            if pack_id:
                # Format single pack stats
                from ..analytics.pack_metrics import PackMetrics

                metrics = PackMetrics()
                stats_obj = metrics.get_pack_stats(pack_id)
                if stats_obj:
                    return metrics.format_stats(stats_obj)
                return f"No data for pack: {pack_id}"
            else:
                # Top 10 packs by resolution count
                sorted_packs = sorted(
                    stats_dict.items(),
                    key=lambda x: x[1].get("total_resolutions", 0),
                    reverse=True,
                )[:10]

                lines = ["Top 10 Packs by Resolution Count:", ""]
                for pid, s in sorted_packs:
                    lines.append(
                        f"  {pid}: {s['total_resolutions']} resolutions, {s['avg_resolution_time_mins']:.1f} min avg"
                    )
                lines.append("")
                lines.append("Use PACK_STATS <pack_id> for detailed hypothesis accuracy.")
                return "\n".join(lines)

        except Exception as e:
            return f"ERROR computing pack stats: {e}"

    def handle_patterns(self, scope: Optional[str] = None) -> str:
        """Handle PATTERNS - show detected patterns in ticket history."""
        if not ANALYTICS_AVAILABLE:
            return "ERROR: Analytics module not available. Check scripts/analytics/ setup."

        try:
            from ..analytics.pattern_detector import PatternDetector

            detector = PatternDetector()
            report = detector.detect_patterns(days=30)

            if scope == "device":
                # Device recurrence only
                if not report.recurring_devices:
                    return "No recurring device issues detected (threshold: 3+ tickets in 30 days)"
                lines = ["Device Recurrence (≥3 tickets in 30 days):", ""]
                for d in report.recurring_devices[:10]:
                    cats = ", ".join(f"{k}({v})" for k, v in list(d.categories.items())[:3])
                    lines.append(f"  - {d.hostname}: {d.ticket_count} tickets [{cats}]")
                return "\n".join(lines)

            elif scope == "user":
                # User recurrence only
                if not report.recurring_users:
                    return "No recurring user issues detected (threshold: 3+ tickets in 30 days)"
                lines = ["User Recurrence (≥3 tickets in 30 days):", ""]
                for u in report.recurring_users[:10]:
                    cats = ", ".join(f"{k}({v})" for k, v in list(u.categories.items())[:3])
                    lines.append(f"  - {u.user_name}: {u.ticket_count} tickets [{cats}]")
                return "\n".join(lines)

            else:
                # Full report
                return detector.format_report(report)

        except Exception as e:
            return f"ERROR detecting patterns: {e}"
