#!/usr/bin/env python3
"""
Pack Effectiveness Metrics for QF_Wiz Analytics.

Computes statistics from resolution logs to measure pack and hypothesis effectiveness.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class HypothesisStats:
    """Statistics for a single hypothesis."""
    hypothesis_id: str
    confirmed: int = 0
    falsified: int = 0
    total_uses: int = 0
    avg_resolution_time_mins: float = 0.0
    resolution_times: list[float] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        """Confirmation rate (0-1)."""
        total = self.confirmed + self.falsified
        return self.confirmed / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "confirmed": self.confirmed,
            "falsified": self.falsified,
            "total_uses": self.total_uses,
            "accuracy": round(self.accuracy, 3),
            "avg_resolution_time_mins": round(self.avg_resolution_time_mins, 1),
        }


@dataclass
class PackStats:
    """Statistics for a branch pack."""
    pack_id: str
    total_resolutions: int = 0
    avg_resolution_time_mins: float = 0.0
    resolution_times: list[float] = field(default_factory=list)
    hypotheses: dict[str, HypothesisStats] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "total_resolutions": self.total_resolutions,
            "avg_resolution_time_mins": round(self.avg_resolution_time_mins, 1),
            "hypothesis_accuracy": {
                h_id: h.to_dict() for h_id, h in self.hypotheses.items()
            },
        }


class PackMetrics:
    """Compute pack effectiveness metrics from resolution logs."""

    def __init__(self, log_dir: Path | str | None = None):
        """
        Initialize pack metrics calculator.

        Args:
            log_dir: Directory containing resolution logs
        """
        if log_dir is None:
            log_dir = Path(__file__).resolve().parents[2] / "runtime" / "resolution_logs"
        self.log_dir = Path(log_dir)

    def compute_metrics(self, days: int = 365) -> dict[str, PackStats]:
        """
        Compute metrics for all packs from resolution logs.

        Args:
            days: Number of days to analyze

        Returns:
            Dict mapping pack_id to PackStats
        """
        resolutions = self._load_resolutions(days)
        pack_stats: dict[str, PackStats] = {}

        for r in resolutions:
            source_packs = r.get("source_pack", [])
            root_cause = r.get("actual_root_cause")
            resolution_time = r.get("resolution_time_mins", 0) or 0

            for pack_id in source_packs:
                if pack_id not in pack_stats:
                    pack_stats[pack_id] = PackStats(pack_id=pack_id)

                stats = pack_stats[pack_id]
                stats.total_resolutions += 1
                if resolution_time > 0:
                    stats.resolution_times.append(resolution_time)

                # Track hypothesis outcomes
                if root_cause:
                    # Root cause was confirmed
                    if root_cause not in stats.hypotheses:
                        stats.hypotheses[root_cause] = HypothesisStats(hypothesis_id=root_cause)
                    stats.hypotheses[root_cause].confirmed += 1
                    stats.hypotheses[root_cause].total_uses += 1
                    if resolution_time > 0:
                        stats.hypotheses[root_cause].resolution_times.append(resolution_time)

                # Track falsified hypotheses
                for collapsed in r.get("collapsed_hypotheses", []):
                    h_id = collapsed.get("hypothesis_id") if isinstance(collapsed, dict) else collapsed
                    if h_id and h_id != root_cause:
                        if h_id not in stats.hypotheses:
                            stats.hypotheses[h_id] = HypothesisStats(hypothesis_id=h_id)
                        stats.hypotheses[h_id].falsified += 1
                        stats.hypotheses[h_id].total_uses += 1

        # Compute averages
        for stats in pack_stats.values():
            if stats.resolution_times:
                stats.avg_resolution_time_mins = sum(stats.resolution_times) / len(stats.resolution_times)
            for h_stats in stats.hypotheses.values():
                if h_stats.resolution_times:
                    h_stats.avg_resolution_time_mins = sum(h_stats.resolution_times) / len(h_stats.resolution_times)

        return pack_stats

    def get_pack_stats(self, pack_id: str, days: int = 365) -> PackStats | None:
        """Get stats for a specific pack."""
        all_stats = self.compute_metrics(days)
        return all_stats.get(pack_id)

    def get_top_packs(self, n: int = 10, sort_by: str = "resolutions") -> list[PackStats]:
        """
        Get top N packs by various criteria.

        Args:
            n: Number of packs to return
            sort_by: 'resolutions' or 'avg_time'
        """
        all_stats = self.compute_metrics()

        if sort_by == "avg_time":
            # Sort by fastest resolution (ascending)
            sorted_stats = sorted(
                all_stats.values(),
                key=lambda s: s.avg_resolution_time_mins if s.avg_resolution_time_mins > 0 else float('inf')
            )
        else:
            # Sort by most resolutions (descending)
            sorted_stats = sorted(
                all_stats.values(),
                key=lambda s: s.total_resolutions,
                reverse=True
            )

        return sorted_stats[:n]

    def format_stats(self, stats: PackStats) -> str:
        """Format pack stats for display."""
        lines = [
            f"Pack: {stats.pack_id}",
            f"  Total Resolutions: {stats.total_resolutions}",
            f"  Avg Resolution Time: {stats.avg_resolution_time_mins:.1f} mins",
            "",
            "  Hypothesis Accuracy:",
        ]

        for h_id, h_stats in sorted(
            stats.hypotheses.items(),
            key=lambda x: x[1].total_uses,
            reverse=True
        ):
            accuracy_pct = h_stats.accuracy * 100
            lines.append(
                f"    {h_id}: {accuracy_pct:.0f}% "
                f"({h_stats.confirmed} confirmed, {h_stats.falsified} falsified)"
            )

        return "\n".join(lines)

    def _load_resolutions(self, days: int) -> list[dict[str, Any]]:
        """Load resolution entries from log files."""
        resolutions = []
        cutoff = datetime.now().timestamp() - (days * 86400)

        if not self.log_dir.exists():
            return resolutions

        for log_file in sorted(self.log_dir.glob("*.jsonl"), reverse=True):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry["timestamp"]).timestamp()
                        if entry_time >= cutoff:
                            resolutions.append(entry)
                    except (json.JSONDecodeError, KeyError):
                        continue

        return resolutions


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pack Metrics CLI")
    parser.add_argument("--pack", type=str, help="Show stats for specific pack")
    parser.add_argument("--top", type=int, default=10, help="Show top N packs")
    parser.add_argument("--days", type=int, default=365, help="Days to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    metrics = PackMetrics()

    if args.pack:
        stats = metrics.get_pack_stats(args.pack, days=args.days)
        if stats:
            if args.json:
                print(json.dumps(stats.to_dict(), indent=2))
            else:
                print(metrics.format_stats(stats))
        else:
            print(f"No data for pack: {args.pack}")
    else:
        top_packs = metrics.get_top_packs(n=args.top)
        if args.json:
            print(json.dumps([p.to_dict() for p in top_packs], indent=2))
        else:
            print(f"Top {args.top} Packs by Resolution Count:\n")
            for stats in top_packs:
                print(f"  {stats.pack_id}: {stats.total_resolutions} resolutions, "
                      f"{stats.avg_resolution_time_mins:.1f} min avg")
