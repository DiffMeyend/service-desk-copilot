#!/usr/bin/env python3
"""
Pattern Detector for QF_Wiz Analytics.

Analyzes ticket history to detect:
- Recurring device issues
- Recurring user issues
- Temporal patterns (time-of-day, day-of-week)
- Symptom clusters
- Blast radius events (multi-device/user issues)
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .resolution_logger import ResolutionLogger


@dataclass
class DevicePattern:
    """Pattern for a recurring device issue."""

    hostname: str
    ticket_count: int
    categories: dict[str, int] = field(default_factory=dict)  # category -> count
    last_seen: str = ""
    avg_resolution_time: float = 0.0


@dataclass
class UserPattern:
    """Pattern for a recurring user issue."""

    user_name: str
    ticket_count: int
    categories: dict[str, int] = field(default_factory=dict)
    last_seen: str = ""
    common_symptoms: list[str] = field(default_factory=list)


@dataclass
class TemporalPattern:
    """Time-based pattern."""

    pattern_type: str  # "hour_of_day" or "day_of_week"
    peak_value: int  # Hour (0-23) or day (0-6)
    peak_label: str  # "8-9am" or "Monday"
    ticket_count: int
    category: str = ""  # Optional: specific issue type


@dataclass
class SymptomCluster:
    """Cluster of co-occurring symptoms."""

    symptoms: tuple[str, ...]
    occurrences: int
    common_hypothesis: str = ""
    confidence: float = 0.0


@dataclass
class PatternReport:
    """Complete pattern analysis report."""

    generated_at: str
    analysis_days: int
    total_resolutions: int

    recurring_devices: list[DevicePattern] = field(default_factory=list)
    recurring_users: list[UserPattern] = field(default_factory=list)
    temporal_patterns: list[TemporalPattern] = field(default_factory=list)
    symptom_clusters: list[SymptomCluster] = field(default_factory=list)
    blast_radius_events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "analysis_days": self.analysis_days,
            "total_resolutions": self.total_resolutions,
            "recurring_devices": [
                {
                    "hostname": d.hostname,
                    "ticket_count": d.ticket_count,
                    "categories": d.categories,
                    "last_seen": d.last_seen,
                    "avg_resolution_time": round(d.avg_resolution_time, 1),
                }
                for d in self.recurring_devices
            ],
            "recurring_users": [
                {
                    "user_name": u.user_name,
                    "ticket_count": u.ticket_count,
                    "categories": u.categories,
                    "last_seen": u.last_seen,
                    "common_symptoms": u.common_symptoms[:3],
                }
                for u in self.recurring_users
            ],
            "temporal_patterns": [
                {
                    "type": t.pattern_type,
                    "peak": t.peak_label,
                    "count": t.ticket_count,
                    "category": t.category,
                }
                for t in self.temporal_patterns
            ],
            "symptom_clusters": [
                {
                    "symptoms": list(s.symptoms),
                    "occurrences": s.occurrences,
                    "common_hypothesis": s.common_hypothesis,
                }
                for s in self.symptom_clusters
            ],
        }


class PatternDetector:
    """Detects patterns in ticket resolution history."""

    def __init__(self, resolution_log_dir: Path | str | None = None):
        """
        Initialize pattern detector.

        Args:
            resolution_log_dir: Directory containing resolution logs
        """
        if resolution_log_dir is None:
            resolution_log_dir = Path(__file__).resolve().parents[2] / "runtime" / "resolution_logs"
        self.resolution_log_dir = Path(resolution_log_dir)

    def detect_patterns(
        self,
        days: int = 30,
        min_device_tickets: int = 3,
        min_user_tickets: int = 3,
    ) -> PatternReport:
        """
        Run full pattern detection analysis.

        Args:
            days: Number of days to analyze
            min_device_tickets: Minimum tickets for device recurrence
            min_user_tickets: Minimum tickets for user recurrence

        Returns:
            PatternReport with all detected patterns
        """
        logger = ResolutionLogger(self.resolution_log_dir)
        resolutions = logger.get_recent_resolutions(days=days)

        report = PatternReport(
            generated_at=datetime.now().isoformat(),
            analysis_days=days,
            total_resolutions=len(resolutions),
        )

        if not resolutions:
            return report

        # Run all detectors
        report.recurring_devices = self._detect_device_recurrence(resolutions, min_tickets=min_device_tickets)
        report.recurring_users = self._detect_user_recurrence(resolutions, min_tickets=min_user_tickets)
        report.temporal_patterns = self._detect_temporal_patterns(resolutions)
        report.symptom_clusters = self._detect_symptom_clusters(resolutions)
        report.blast_radius_events = self._detect_blast_radius(resolutions)

        return report

    def _detect_device_recurrence(
        self,
        resolutions: list[dict],
        min_tickets: int = 3,
    ) -> list[DevicePattern]:
        """Find devices with recurring issues."""
        device_data: dict[str, dict] = defaultdict(
            lambda: {
                "count": 0,
                "categories": defaultdict(int),
                "resolution_times": [],
                "last_seen": "",
            }
        )

        for r in resolutions:
            device = r.get("device")
            if not device:
                continue

            data = device_data[device]
            data["count"] += 1
            data["last_seen"] = r.get("timestamp", "")

            # Track category
            packs = r.get("source_pack", [])
            for pack in packs:
                # Extract category from pack_id (e.g., "email_security" -> "email")
                category = pack.split("_")[0] if "_" in pack else pack
                data["categories"][category] += 1

            # Track resolution time
            res_time = r.get("resolution_time_mins", 0)
            if res_time:
                data["resolution_times"].append(res_time)

        # Filter and create patterns
        patterns = []
        for hostname, data in device_data.items():
            if data["count"] >= min_tickets:
                avg_time = (
                    sum(data["resolution_times"]) / len(data["resolution_times"]) if data["resolution_times"] else 0
                )
                patterns.append(
                    DevicePattern(
                        hostname=hostname,
                        ticket_count=data["count"],
                        categories=dict(data["categories"]),
                        last_seen=data["last_seen"],
                        avg_resolution_time=avg_time,
                    )
                )

        # Sort by ticket count descending
        patterns.sort(key=lambda p: p.ticket_count, reverse=True)
        return patterns[:20]  # Top 20

    def _detect_user_recurrence(
        self,
        resolutions: list[dict],
        min_tickets: int = 3,
    ) -> list[UserPattern]:
        """Find users with recurring issues."""
        user_data: dict[str, dict] = defaultdict(
            lambda: {
                "count": 0,
                "categories": defaultdict(int),
                "symptoms": defaultdict(int),
                "last_seen": "",
            }
        )

        for r in resolutions:
            user = r.get("user")
            if not user:
                continue

            data = user_data[user]
            data["count"] += 1
            data["last_seen"] = r.get("timestamp", "")

            # Track categories
            packs = r.get("source_pack", [])
            for pack in packs:
                category = pack.split("_")[0] if "_" in pack else pack
                data["categories"][category] += 1

            # Track symptoms
            for symptom in r.get("symptoms", []):
                data["symptoms"][symptom] += 1

        # Filter and create patterns
        patterns = []
        for user_name, data in user_data.items():
            if data["count"] >= min_tickets:
                # Get top 3 symptoms
                top_symptoms = sorted(
                    data["symptoms"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:3]

                patterns.append(
                    UserPattern(
                        user_name=user_name,
                        ticket_count=data["count"],
                        categories=dict(data["categories"]),
                        last_seen=data["last_seen"],
                        common_symptoms=[s[0] for s in top_symptoms],
                    )
                )

        patterns.sort(key=lambda p: p.ticket_count, reverse=True)
        return patterns[:20]

    def _detect_temporal_patterns(
        self,
        resolutions: list[dict],
    ) -> list[TemporalPattern]:
        """Find time-based patterns."""
        hour_counts: dict[int, int] = defaultdict(int)
        day_counts: dict[int, int] = defaultdict(int)

        # Also track by category
        category_hour_counts: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

        for r in resolutions:
            timestamp = r.get("timestamp", "")
            if not timestamp:
                continue

            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                hour_counts[dt.hour] += 1
                day_counts[dt.weekday()] += 1

                # Track by category
                packs = r.get("source_pack", [])
                for pack in packs:
                    category = pack.split("_")[0] if "_" in pack else pack
                    category_hour_counts[category][dt.hour] += 1
            except (ValueError, TypeError):
                continue

        patterns = []

        # Find peak hour
        if hour_counts:
            peak_hour = max(hour_counts, key=hour_counts.get)
            patterns.append(
                TemporalPattern(
                    pattern_type="hour_of_day",
                    peak_value=peak_hour,
                    peak_label=f"{peak_hour}:00-{peak_hour + 1}:00",
                    ticket_count=hour_counts[peak_hour],
                )
            )

        # Find peak day
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if day_counts:
            peak_day = max(day_counts, key=day_counts.get)
            patterns.append(
                TemporalPattern(
                    pattern_type="day_of_week",
                    peak_value=peak_day,
                    peak_label=day_names[peak_day],
                    ticket_count=day_counts[peak_day],
                )
            )

        # Find category-specific patterns (e.g., "VPN issues peak at 8am")
        for category, hours in category_hour_counts.items():
            if sum(hours.values()) >= 5:  # Minimum sample
                peak_hour = max(hours, key=hours.get)
                if hours[peak_hour] >= 3:  # Significant peak
                    patterns.append(
                        TemporalPattern(
                            pattern_type="category_hour",
                            peak_value=peak_hour,
                            peak_label=f"{peak_hour}:00-{peak_hour + 1}:00",
                            ticket_count=hours[peak_hour],
                            category=category,
                        )
                    )

        return patterns

    def _detect_symptom_clusters(
        self,
        resolutions: list[dict],
        min_occurrences: int = 3,
    ) -> list[SymptomCluster]:
        """Find symptoms that frequently co-occur."""
        # Track symptom pair co-occurrences
        pair_counts: dict[tuple, dict] = defaultdict(lambda: {"count": 0, "hypotheses": defaultdict(int)})

        for r in resolutions:
            symptoms = r.get("symptoms", [])
            if len(symptoms) < 2:
                continue

            # Normalize and sort symptoms
            symptoms = sorted(set(s.lower().strip() for s in symptoms if s))

            # Count all pairs
            for i, s1 in enumerate(symptoms):
                for s2 in symptoms[i + 1 :]:
                    pair = (s1, s2)
                    pair_counts[pair]["count"] += 1

                    # Track which hypothesis resolved this
                    root_cause = r.get("actual_root_cause", "")
                    if root_cause:
                        pair_counts[pair]["hypotheses"][root_cause] += 1

        # Filter and create clusters
        clusters = []
        for pair, data in pair_counts.items():
            if data["count"] >= min_occurrences:
                # Find most common hypothesis for this pair
                common_hyp = ""
                confidence = 0.0
                if data["hypotheses"]:
                    common_hyp = max(data["hypotheses"], key=data["hypotheses"].get)
                    confidence = data["hypotheses"][common_hyp] / data["count"]

                clusters.append(
                    SymptomCluster(
                        symptoms=pair,
                        occurrences=data["count"],
                        common_hypothesis=common_hyp,
                        confidence=confidence,
                    )
                )

        clusters.sort(key=lambda c: c.occurrences, reverse=True)
        return clusters[:10]

    def _detect_blast_radius(
        self,
        resolutions: list[dict],
        time_window_hours: int = 4,
    ) -> list[dict[str, Any]]:
        """Find events affecting multiple users/devices in a short time."""
        # Group by time windows
        events_by_window: dict[str, list] = defaultdict(list)

        for r in resolutions:
            timestamp = r.get("timestamp", "")
            if not timestamp:
                continue

            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                # Create 4-hour window key
                window_start = dt.replace(
                    hour=(dt.hour // time_window_hours) * time_window_hours,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                window_key = window_start.isoformat()
                events_by_window[window_key].append(r)
            except (ValueError, TypeError):
                continue

        # Find windows with multiple unique devices/users
        blast_events = []
        for window_key, events in events_by_window.items():
            devices = set(e.get("device") for e in events if e.get("device"))
            users = set(e.get("user") for e in events if e.get("user"))

            if len(devices) >= 3 or len(users) >= 3:
                # Potential blast radius event
                common_symptoms = defaultdict(int)
                common_packs = defaultdict(int)

                for e in events:
                    for s in e.get("symptoms", []):
                        common_symptoms[s] += 1
                    for p in e.get("source_pack", []):
                        common_packs[p] += 1

                blast_events.append(
                    {
                        "time_window": window_key,
                        "affected_devices": len(devices),
                        "affected_users": len(users),
                        "ticket_count": len(events),
                        "common_symptoms": sorted(
                            common_symptoms.items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:3],
                        "common_packs": sorted(
                            common_packs.items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:3],
                    }
                )

        blast_events.sort(key=lambda e: e["ticket_count"], reverse=True)
        return blast_events[:5]

    def get_alerts_for_ticket(
        self,
        device: str | None,
        user: str | None,
        symptoms: list[str] | None = None,
        days: int = 30,
    ) -> list[str]:
        """
        Get pattern-based alerts relevant to a new ticket.

        Args:
            device: Device hostname
            user: User name
            symptoms: List of symptoms

        Returns:
            List of alert strings
        """
        report = self.detect_patterns(days=days)
        alerts = []

        # Check device recurrence
        if device:
            for d in report.recurring_devices:
                if d.hostname == device:
                    cats = ", ".join(f"{k}({v})" for k, v in list(d.categories.items())[:3])
                    alerts.append(f"⚠️ {device} has had {d.ticket_count} tickets in last {days} days [{cats}]")
                    break

        # Check user recurrence
        if user:
            for u in report.recurring_users:
                if u.user_name == user:
                    cats = ", ".join(f"{k}({v})" for k, v in list(u.categories.items())[:3])
                    alerts.append(f"⚠️ {user} has reported {u.ticket_count} issues in last {days} days [{cats}]")
                    break

        # Check symptom clusters
        if symptoms and len(symptoms) >= 2:
            symptom_set = set(s.lower().strip() for s in symptoms)
            for cluster in report.symptom_clusters:
                if set(cluster.symptoms).issubset(symptom_set):
                    if cluster.common_hypothesis:
                        alerts.append(
                            f"💡 Symptoms '{' + '.join(cluster.symptoms)}' often resolved by: {cluster.common_hypothesis}"
                        )
                    break

        return alerts

    def format_report(self, report: PatternReport) -> str:
        """Format pattern report for display."""
        lines = [
            f"Pattern Analysis ({report.analysis_days} days, {report.total_resolutions} resolutions)",
            "=" * 60,
            "",
        ]

        # Device recurrence
        if report.recurring_devices:
            lines.append("Device Recurrence (≥3 tickets):")
            for d in report.recurring_devices[:5]:
                cats = ", ".join(f"{k}({v})" for k, v in list(d.categories.items())[:3])
                lines.append(f"  - {d.hostname}: {d.ticket_count} tickets [{cats}]")
            lines.append("")

        # User recurrence
        if report.recurring_users:
            lines.append("User Recurrence (≥3 tickets):")
            for u in report.recurring_users[:5]:
                cats = ", ".join(f"{k}({v})" for k, v in list(u.categories.items())[:3])
                lines.append(f"  - {u.user_name}: {u.ticket_count} tickets [{cats}]")
            lines.append("")

        # Temporal patterns
        if report.temporal_patterns:
            lines.append("Temporal Patterns:")
            for t in report.temporal_patterns:
                if t.category:
                    lines.append(f"  - {t.category} issues peak at {t.peak_label} ({t.ticket_count} tickets)")
                else:
                    lines.append(f"  - Peak {t.pattern_type}: {t.peak_label} ({t.ticket_count} tickets)")
            lines.append("")

        # Symptom clusters
        if report.symptom_clusters:
            lines.append("Symptom Clusters:")
            for s in report.symptom_clusters[:5]:
                hyp_note = f" → {s.common_hypothesis}" if s.common_hypothesis else ""
                lines.append(f"  - '{' + '.join(s.symptoms)}' ({s.occurrences}x){hyp_note}")
            lines.append("")

        # Blast radius
        if report.blast_radius_events:
            lines.append("Blast Radius Events:")
            for b in report.blast_radius_events[:3]:
                lines.append(
                    f"  - {b['time_window'][:16]}: {b['affected_devices']} devices, {b['affected_users']} users"
                )
            lines.append("")

        if len(lines) <= 3:
            lines.append("No significant patterns detected.")

        return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pattern Detector CLI")
    parser.add_argument("--days", type=int, default=30, help="Days to analyze")
    parser.add_argument("--device", type=str, help="Get alerts for specific device")
    parser.add_argument("--user", type=str, help="Get alerts for specific user")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    detector = PatternDetector()

    if args.device or args.user:
        alerts = detector.get_alerts_for_ticket(
            device=args.device,
            user=args.user,
            days=args.days,
        )
        if alerts:
            for alert in alerts:
                print(alert)
        else:
            print("No pattern alerts for this device/user.")
    else:
        report = detector.detect_patterns(days=args.days)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(detector.format_report(report))
