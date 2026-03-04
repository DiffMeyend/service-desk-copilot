#!/usr/bin/env python3
"""
Resolution Logger for QF_Wiz Analytics.

Persists resolution outcomes to JSONL files for learning and pattern detection.
Each resolution creates an entry that can be used to:
- Update hypothesis confidence scores
- Detect device/user patterns
- Build the knowledge graph
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ResolutionLogger:
    """Log ticket resolutions for analytics and learning."""

    def __init__(self, log_dir: Path | str | None = None):
        """
        Initialize the resolution logger.

        Args:
            log_dir: Directory for resolution logs. Defaults to runtime/resolution_logs/
        """
        if log_dir is None:
            # Default to runtime/resolution_logs/ relative to this file
            log_dir = Path(__file__).resolve().parents[2] / "runtime" / "resolution_logs"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_resolution(self, cp: dict[str, Any]) -> Path:
        """
        Extract and persist resolution metadata from a context payload.

        Args:
            cp: The context payload dict after DECIDE

        Returns:
            Path to the log file that was written to
        """
        # Extract resolution metadata
        entry = self._extract_resolution_entry(cp)

        # Append to monthly JSONL file
        log_file = self.log_dir / f"{datetime.now():%Y-%m}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return log_file

    def _extract_resolution_entry(self, cp: dict[str, Any]) -> dict[str, Any]:
        """Extract relevant fields from CP for logging."""
        ticket = cp.get("ticket", {})
        environment = cp.get("environment", {})
        target_device = environment.get("target_device", {})
        problem = cp.get("problem", {})
        evidence = cp.get("evidence", {})
        branches = cp.get("branches", {})
        decision = cp.get("decision", {})
        css = cp.get("css", {})

        return {
            # Identifiers
            "ticket_id": ticket.get("id"),
            "timestamp": datetime.now().isoformat(),

            # Resolution outcome
            "resolution_status": decision.get("status"),
            "resolution_choice": decision.get("resolution_choice"),
            "actual_root_cause": decision.get("actual_root_cause"),
            "resolution_confidence": decision.get("resolution_confidence"),
            "resolution_time_mins": decision.get("resolution_time_mins"),
            "steps_taken": decision.get("steps_taken", []),

            # Context
            "device": target_device.get("hostname"),
            "asset_tag": target_device.get("asset_tag"),
            "user": ticket.get("requester", {}).get("name"),
            "user_email": ticket.get("requester", {}).get("email"),
            "company": ticket.get("company"),
            "site": ticket.get("site"),

            # Problem characterization
            "symptoms": problem.get("symptoms", []),
            "impact_work_stopped": problem.get("impact", {}).get("work_stopped"),
            "scope": problem.get("scope", {}),

            # Hypothesis journey
            "source_pack": branches.get("source_pack", []),
            "active_hypotheses": [
                h.get("id") if isinstance(h, dict) else h
                for h in branches.get("active_hypotheses", [])
            ],
            "current_best_guess": branches.get("current_best_guess"),
            "collapsed_hypotheses": branches.get("collapsed_hypotheses", []),

            # Evidence gathered
            "tests_run": evidence.get("tests_run", []),
            "discriminating_test": evidence.get("discriminating_test"),

            # Final score
            "css_score": css.get("score"),
        }

    def get_recent_resolutions(self, days: int = 30) -> list[dict[str, Any]]:
        """
        Load recent resolution entries.

        Args:
            days: Number of days to look back

        Returns:
            List of resolution entries
        """
        resolutions = []
        cutoff = datetime.now().timestamp() - (days * 86400)

        for log_file in sorted(self.log_dir.glob("*.jsonl"), reverse=True):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry["timestamp"]).timestamp()
                    if entry_time >= cutoff:
                        resolutions.append(entry)

        return resolutions

    def get_resolutions_for_device(self, hostname: str) -> list[dict[str, Any]]:
        """Get all resolutions for a specific device."""
        return [
            r for r in self.get_recent_resolutions(days=365)
            if r.get("device") == hostname
        ]

    def get_resolutions_for_user(self, user_name: str) -> list[dict[str, Any]]:
        """Get all resolutions for a specific user."""
        return [
            r for r in self.get_recent_resolutions(days=365)
            if r.get("user") == user_name
        ]

    def get_resolutions_for_pack(self, pack_id: str) -> list[dict[str, Any]]:
        """Get all resolutions that used a specific pack."""
        return [
            r for r in self.get_recent_resolutions(days=365)
            if pack_id in r.get("source_pack", [])
        ]


if __name__ == "__main__":
    # CLI usage example
    import argparse

    parser = argparse.ArgumentParser(description="Resolution Logger CLI")
    parser.add_argument("--list", action="store_true", help="List recent resolutions")
    parser.add_argument("--days", type=int, default=30, help="Days to look back")
    parser.add_argument("--device", type=str, help="Filter by device hostname")
    parser.add_argument("--user", type=str, help="Filter by user name")
    parser.add_argument("--pack", type=str, help="Filter by pack ID")

    args = parser.parse_args()

    logger = ResolutionLogger()

    if args.device:
        resolutions = logger.get_resolutions_for_device(args.device)
    elif args.user:
        resolutions = logger.get_resolutions_for_user(args.user)
    elif args.pack:
        resolutions = logger.get_resolutions_for_pack(args.pack)
    else:
        resolutions = logger.get_recent_resolutions(days=args.days)

    print(f"Found {len(resolutions)} resolutions")
    for r in resolutions[:10]:  # Show first 10
        print(f"  {r['timestamp'][:10]} | {r['ticket_id']} | {r.get('device', 'N/A')} | {r.get('actual_root_cause', 'N/A')}")
