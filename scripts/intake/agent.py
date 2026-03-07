"""IntakeAgent -- orchestrator for ticket ingestion, routing, audit, and analytics.

Ties together the parsing and analytics modules behind a single class.
This is the primary entry point for Agent 2 (Intake & Audit) in the 3-agent
architecture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.analytics.confidence_updater import ConfidenceUpdater
from scripts.analytics.pack_metrics import PackMetrics
from scripts.analytics.pattern_detector import PatternDetector
from scripts.analytics.resolution_logger import ResolutionLogger
from scripts.parsing.parse_ticket import build_payload, load_ticket_text


class IntakeAgent:
    """Orchestrates ticket ingestion, routing, audit, and analytics."""

    def __init__(
        self,
        resolution_log_dir: Path | str | None = None,
        catalog_path: Path | str | None = None,
    ):
        """Initialize IntakeAgent with optional path overrides.

        Args:
            resolution_log_dir: Directory for resolution JSONL logs.
            catalog_path: Path to branch packs catalog YAML.
        """
        self._resolution_log_dir = resolution_log_dir
        self._catalog_path = catalog_path

    def ingest(self, raw_text: str) -> Dict[str, Any]:
        """Parse raw ticket text into a Context Payload with initial pack routing.

        Args:
            raw_text: Raw ticket dump text.

        Returns:
            Context Payload dict ready for Agent 1 (Reasoning).
        """
        return build_payload(raw_text)

    def ingest_file(self, file_path: Path | str) -> Dict[str, Any]:
        """Load and parse a ticket file into a Context Payload.

        Args:
            file_path: Path to a raw ticket text file.

        Returns:
            Context Payload dict.
        """
        raw_text = load_ticket_text(Path(file_path))
        return self.ingest(raw_text)

    def log_resolution(self, cp: Dict[str, Any]) -> Path:
        """Log a completed ticket resolution to the audit trail.

        Args:
            cp: Context Payload dict after DECIDE.

        Returns:
            Path to the JSONL log file that was written to.
        """
        logger = ResolutionLogger(log_dir=self._resolution_log_dir)
        return logger.log_resolution(cp)

    def get_alerts(
        self,
        device: Optional[str] = None,
        user: Optional[str] = None,
        symptoms: Optional[List[str]] = None,
        days: int = 30,
    ) -> List[str]:
        """Get pattern-based alerts relevant to a ticket.

        Args:
            device: Device hostname.
            user: User name.
            symptoms: List of symptoms.
            days: Days of history to analyze.

        Returns:
            List of alert strings.
        """
        detector = PatternDetector(resolution_log_dir=self._resolution_log_dir)
        return detector.get_alerts_for_ticket(
            device=device,
            user=user,
            symptoms=symptoms,
            days=days,
        )

    def compute_confidence_updates(self, days: int = 365) -> Dict[str, Any]:
        """Compute Bayesian posterior updates from resolution history.

        Args:
            days: Days of history to analyze.

        Returns:
            Dict mapping pack_id to ConfidenceReport.to_dict().
        """
        updater = ConfidenceUpdater(
            resolution_log_dir=self._resolution_log_dir,
            catalog_path=self._catalog_path,
        )
        reports = updater.compute_updates(days=days)
        return {pack_id: report.to_dict() for pack_id, report in reports.items()}

    def get_pack_stats(
        self,
        pack_id: Optional[str] = None,
        days: int = 365,
    ) -> Dict[str, Any]:
        """Get pack effectiveness metrics.

        Args:
            pack_id: Specific pack ID, or None for all packs.
            days: Days of history to analyze.

        Returns:
            Pack stats dict. If pack_id is given, returns stats for that pack.
            Otherwise returns a dict mapping pack_id to stats.
        """
        metrics = PackMetrics(log_dir=self._resolution_log_dir)
        if pack_id:
            stats = metrics.get_pack_stats(pack_id, days=days)
            return stats.to_dict() if stats else {}
        all_stats = metrics.compute_metrics(days=days)
        return {pid: s.to_dict() for pid, s in all_stats.items()}

    def __repr__(self) -> str:
        return f"IntakeAgent(resolution_log_dir={self._resolution_log_dir!r}, catalog_path={self._catalog_path!r})"
