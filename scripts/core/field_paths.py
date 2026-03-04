"""Centralized field path constants for Context Payload access.

These constants map to the context_payload.schema.json structure.
Use these instead of hardcoded strings for:
- Type safety (IDE autocomplete)
- Refactoring support
- Single source of truth
- Preventing typos

Usage:
    from core.field_paths import TicketPaths, EvidencePaths

    # Instead of:
    hostname = cp.get_value("environment.target_device.hostname")

    # Use:
    hostname = cp.get_value(EnvironmentPaths.TargetDevice.HOSTNAME)
"""

from __future__ import annotations


class MetaPaths:
    """Paths under meta section."""

    SESSION_ID = "meta.session_id"
    LAST_UPDATED = "meta.last_updated"
    SCHEMA_VERSION = "meta.schema_version"
    TIMEZONE = "meta.timezone"


class TicketPaths:
    """Paths under ticket section."""

    ID = "ticket.id"
    PRIORITY = "ticket.priority"
    COMPANY = "ticket.company"
    SITE = "ticket.site"
    SUMMARY = "ticket.summary"
    CREATED_AT = "ticket.created_at"
    CATEGORY = "ticket.category"
    SERVICE = "ticket.service"
    RAW_DUMP = "ticket.raw_dump"

    class Requester:
        """Paths under ticket.requester."""

        NAME = "ticket.requester.name"
        EMAIL = "ticket.requester.email"
        PHONE = "ticket.requester.phone"
        CONTACT = "ticket.requester.contact"


class EnvironmentPaths:
    """Paths under environment section."""

    class TargetDevice:
        """Paths under environment.target_device."""

        HOSTNAME = "environment.target_device.hostname"
        OS = "environment.target_device.os"
        IP = "environment.target_device.ip"
        ASSET_TAG = "environment.target_device.asset_tag"
        SERIAL_NUMBER = "environment.target_device.serial_number"
        ON_DOMAIN = "environment.target_device.on_domain"

    class UserContext:
        """Paths under environment.user_context."""

        USERNAME = "environment.user_context.username"
        IS_ADMIN = "environment.user_context.is_admin"
        IS_REMOTE = "environment.user_context.is_remote"

    class Network:
        """Paths under environment.network."""

        CONNECTION_TYPE = "environment.network.connection_type"
        DNS_SERVERS = "environment.network.dns_servers"
        VPN = "environment.network.vpn"

    class ExecutionContext:
        """Paths under environment.execution_context."""

        TOOLING = "environment.execution_context.tooling"
        RUN_AS = "environment.execution_context.run_as"
        PRIVILEGE = "environment.execution_context.privilege"
        SANDBOX_PREPPED = "environment.execution_context.sandbox_prepped"


class ProblemPaths:
    """Paths under problem section."""

    SYMPTOMS = "problem.symptoms"
    START_TIME = "problem.start_time"
    LAST_KNOWN_GOOD = "problem.last_known_good"
    RECENT_CHANGES = "problem.recent_changes"

    class Impact:
        """Paths under problem.impact."""

        WORK_STOPPED = "problem.impact.work_stopped"
        WHO = "problem.impact.who"
        HOW_BAD = "problem.impact.how_bad"

    class Scope:
        """Paths under problem.scope."""

        SINGLE_USER = "problem.scope.single_user"
        MULTI_USER = "problem.scope.multi_user"
        SINGLE_DEVICE = "problem.scope.single_device"
        SERVICE_WIDE = "problem.scope.service_wide"


class EvidencePaths:
    """Paths under evidence section."""

    TESTS_RUN = "evidence.tests_run"
    RESULTS = "evidence.results"
    OBSERVATIONS = "evidence.observations"
    DISCRIMINATING_TEST = "evidence.discriminating_test"

    class Artifacts:
        """Paths under evidence.artifacts."""

        SCREENSHOTS = "evidence.artifacts.screenshots"
        LOGS = "evidence.artifacts.logs"
        ERROR_CODES = "evidence.artifacts.error_codes"


class BranchesPaths:
    """Paths under branches section."""

    ACTIVE_HYPOTHESES = "branches.active_hypotheses"
    COLLAPSED_HYPOTHESES = "branches.collapsed_hypotheses"
    CURRENT_BEST_GUESS = "branches.current_best_guess"
    SOURCE_PACK = "branches.source_pack"
    MANUAL_OVERRIDES = "branches.manual_overrides"
    ROUTING_METHOD = "branches.routing_method"


class CSSPaths:
    """Paths under css section."""

    SCORE = "css.score"
    TARGET = "css.target"
    DOMAIN_SCORES = "css.domain_scores"
    MISSING_FIELDS = "css.missing_fields"
    CONTRADICTIONS = "css.contradictions"
    CONFIDENCE_NOTES = "css.confidence_notes"


class DecisionPaths:
    """Paths under decision section."""

    STATUS = "decision.status"
    RECOMMENDED_OUTCOME = "decision.recommended_outcome"
    REASONING = "decision.reasoning"
    ACTUAL_ROOT_CAUSE = "decision.actual_root_cause"
    RESOLUTION_CHOICE = "decision.resolution_choice"
    RESOLUTION_CONFIDENCE = "decision.resolution_confidence"
    RESOLUTION_TIME_MINS = "decision.resolution_time_mins"
    STEPS_TAKEN = "decision.steps_taken"

    class IfEscalate:
        """Paths under decision.if_escalate."""

        TYPE = "decision.if_escalate.type"
        TO_TEAM = "decision.if_escalate.to_team"
        HANDOFF_PACK = "decision.if_escalate.handoff_pack"

    class EscalationGate:
        """Paths under decision.escalation_gate."""

        ELIGIBLE = "decision.escalation_gate.eligible"
        BLOCKED_REASON = "decision.escalation_gate.blocked_reason"


class ConstraintsPaths:
    """Paths under constraints section."""

    CANNOT_REBOOT = "constraints.cannot_reboot"
    CANNOT_DISCONNECT = "constraints.cannot_disconnect"
    CHANGE_FREEZE = "constraints.change_freeze"
    SECURITY_SENSITIVITY = "constraints.security_sensitivity"

    class SecurityControls:
        """Paths under constraints.security_controls."""

        THREATLOCKER_PRESENT = "constraints.security_controls.threatlocker_present"
        THREATLOCKER_NOTES = "constraints.security_controls.threatlocker_notes"


class GuardrailsPaths:
    """Paths under guardrails section."""

    class BasicTroubleshooting:
        """Paths under guardrails.basic_troubleshooting."""

        CONFIRMED = "guardrails.basic_troubleshooting.confirmed"
        MISSING_CHECKS = "guardrails.basic_troubleshooting.missing_checks"
        SCOPE_CONFIRMED = "guardrails.basic_troubleshooting.scope_confirmed"
        ERROR_MESSAGE_CONFIRMED = "guardrails.basic_troubleshooting.error_message_confirmed"
        REPRO_CONFIRMED = "guardrails.basic_troubleshooting.repro_confirmed"
        CONNECTIVITY_REQUIRED = "guardrails.basic_troubleshooting.connectivity_required"
        CONNECTIVITY_CONFIRMED = "guardrails.basic_troubleshooting.connectivity_confirmed"
        AUTHENTICATION_REQUIRED = "guardrails.basic_troubleshooting.authentication_required"
        AUTHENTICATION_CONFIRMED = "guardrails.basic_troubleshooting.authentication_confirmed"
        SERVICE_AVAILABILITY_REQUIRED = "guardrails.basic_troubleshooting.service_availability_required"
        SERVICE_AVAILABILITY_CONFIRMED = "guardrails.basic_troubleshooting.service_availability_confirmed"


class NotesPaths:
    """Paths under notes section."""

    ROLLING = "notes.rolling"
    FINAL = "notes.final"
    ESCALATION = "notes.escalation"


class QuickfixPaths:
    """Paths under quickfix section."""

    TIMEBOX_MINUTES = "quickfix.timebox_minutes"
    HARD_STOP_MINUTES = "quickfix.hard_stop_minutes"
    TIME_SPENT_MINUTES = "quickfix.time_spent_minutes"
    REMAINING_MINUTES = "quickfix.remaining_minutes"
    ALLOWED_SCOPE = "quickfix.allowed_scope"
    ESCALATION_PATHS = "quickfix.escalation_paths"
    TIMER = "quickfix.timer"

    class Timer:
        """Paths under quickfix.timer."""

        START_TIME = "quickfix.timer.start_time"
        ELAPSED_MINUTES = "quickfix.timer.elapsed_minutes"


class PlanPaths:
    """Paths under plan section."""

    NEXT_3_ACTIONS = "plan.next_3_actions"
    BEST_BRANCH_COLLAPSE_TEST = "plan.best_branch_collapse_test"


# Convenience aliases for commonly used paths
class CP:
    """Shorthand aliases for the most commonly used paths."""

    # Ticket
    TICKET_ID = TicketPaths.ID
    PRIORITY = TicketPaths.PRIORITY
    SUMMARY = TicketPaths.SUMMARY

    # Environment
    HOSTNAME = EnvironmentPaths.TargetDevice.HOSTNAME
    ASSET_TAG = EnvironmentPaths.TargetDevice.ASSET_TAG

    # Evidence
    TESTS_RUN = EvidencePaths.TESTS_RUN
    RESULTS = EvidencePaths.RESULTS

    # Branches
    HYPOTHESES = BranchesPaths.ACTIVE_HYPOTHESES
    BEST_GUESS = BranchesPaths.CURRENT_BEST_GUESS
    SOURCE_PACK = BranchesPaths.SOURCE_PACK

    # CSS
    CSS_SCORE = CSSPaths.SCORE

    # Decision
    STATUS = DecisionPaths.STATUS

    # Notes
    ROLLING_NOTES = NotesPaths.ROLLING
