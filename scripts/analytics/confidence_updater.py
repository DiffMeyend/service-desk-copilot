#!/usr/bin/env python3
"""
Confidence Updater for QF_Wiz Analytics.

Updates hypothesis confidence values based on resolution outcomes using
Bayesian inference. Generates an updated branch packs catalog with
learned confidence scores.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .resolution_logger import ResolutionLogger


@dataclass
class HypothesisOutcome:
    """Tracks outcomes for a single hypothesis."""
    hypothesis_id: str
    prior_confidence: float = 0.3  # Default prior
    confirmed: int = 0
    falsified: int = 0

    @property
    def total_observations(self) -> int:
        return self.confirmed + self.falsified

    @property
    def success_rate(self) -> float:
        """Observed success rate."""
        if self.total_observations == 0:
            return self.prior_confidence
        return self.confirmed / self.total_observations

    def compute_posterior(self, min_samples: int = 5, baseline_rate: float = 0.3) -> float:
        """
        Compute Bayesian posterior confidence.

        Uses a simplified Bayesian update where:
        - Prior is the original confidence_hint from the catalog
        - Likelihood ratio is success_rate / baseline_rate
        - Posterior is clamped to [0.1, 0.9]

        Args:
            min_samples: Minimum observations before updating
            baseline_rate: Expected base rate for comparison

        Returns:
            Updated confidence value
        """
        if self.total_observations < min_samples:
            return self.prior_confidence

        # Compute likelihood ratio
        if baseline_rate <= 0:
            baseline_rate = 0.3

        likelihood_ratio = self.success_rate / baseline_rate

        # Apply dampening to prevent extreme swings
        # Use log-odds transform for smoother updates
        prior_odds = self.prior_confidence / (1 - self.prior_confidence + 1e-6)
        posterior_odds = prior_odds * likelihood_ratio

        # Convert back to probability
        posterior = posterior_odds / (1 + posterior_odds)

        # Clamp to [0.1, 0.9] - never fully certain or impossible
        return max(0.1, min(0.9, posterior))


@dataclass
class ConfidenceReport:
    """Report of confidence updates for a pack."""
    pack_id: str
    hypotheses: dict[str, HypothesisOutcome] = field(default_factory=dict)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "generated_at": self.generated_at,
            "hypotheses": {
                h_id: {
                    "prior": round(h.prior_confidence, 3),
                    "posterior": round(h.compute_posterior(), 3),
                    "confirmed": h.confirmed,
                    "falsified": h.falsified,
                    "sample_size": h.total_observations,
                    "delta": round(h.compute_posterior() - h.prior_confidence, 3),
                }
                for h_id, h in self.hypotheses.items()
            },
        }


class ConfidenceUpdater:
    """Updates hypothesis confidence based on resolution outcomes."""

    def __init__(
        self,
        resolution_log_dir: Path | str | None = None,
        catalog_path: Path | str | None = None,
    ):
        """
        Initialize confidence updater.

        Args:
            resolution_log_dir: Directory containing resolution logs
            catalog_path: Path to branch packs catalog YAML
        """
        root = Path(__file__).resolve().parents[2]

        if resolution_log_dir is None:
            resolution_log_dir = root / "runtime" / "resolution_logs"
        self.resolution_log_dir = Path(resolution_log_dir)

        if catalog_path is None:
            catalog_path = root / "runtime" / "branch_packs_catalog_v1_0.yaml"
        self.catalog_path = Path(catalog_path)

        self._catalog: dict[str, Any] | None = None
        self._prior_confidences: dict[str, float] = {}

    def load_catalog(self) -> dict[str, Any]:
        """Load the branch packs catalog."""
        if self._catalog is None:
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                self._catalog = yaml.safe_load(f)

            # Extract prior confidences
            for pack in self._catalog.get("packs", []):
                pack_id = pack.get("id", "")
                for hyp in pack.get("hypotheses", []):
                    hyp_id = hyp.get("id", "")
                    conf = hyp.get("confidence_hint", 0.3)
                    self._prior_confidences[hyp_id] = conf

        return self._catalog

    def compute_updates(self, days: int = 365) -> dict[str, ConfidenceReport]:
        """
        Compute confidence updates from resolution history.

        Args:
            days: Number of days of history to analyze

        Returns:
            Dict mapping pack_id to ConfidenceReport
        """
        self.load_catalog()
        logger = ResolutionLogger(self.resolution_log_dir)
        resolutions = logger.get_recent_resolutions(days=days)

        # Build outcome tracking per pack
        pack_reports: dict[str, ConfidenceReport] = {}

        for r in resolutions:
            source_packs = r.get("source_pack", [])
            root_cause = r.get("actual_root_cause")
            collapsed = r.get("collapsed_hypotheses", [])

            for pack_id in source_packs:
                if pack_id not in pack_reports:
                    pack_reports[pack_id] = ConfidenceReport(
                        pack_id=pack_id,
                        generated_at=datetime.now().isoformat(),
                    )

                report = pack_reports[pack_id]

                # Track confirmed hypothesis
                if root_cause:
                    if root_cause not in report.hypotheses:
                        prior = self._prior_confidences.get(root_cause, 0.3)
                        report.hypotheses[root_cause] = HypothesisOutcome(
                            hypothesis_id=root_cause,
                            prior_confidence=prior,
                        )
                    report.hypotheses[root_cause].confirmed += 1

                # Track falsified hypotheses
                for c in collapsed:
                    h_id = c.get("hypothesis_id") if isinstance(c, dict) else c
                    if h_id and h_id != root_cause:
                        if h_id not in report.hypotheses:
                            prior = self._prior_confidences.get(h_id, 0.3)
                            report.hypotheses[h_id] = HypothesisOutcome(
                                hypothesis_id=h_id,
                                prior_confidence=prior,
                            )
                        report.hypotheses[h_id].falsified += 1

        return pack_reports

    def generate_learned_catalog(
        self,
        output_path: Path | str | None = None,
        days: int = 365,
        min_samples: int = 5,
    ) -> Path:
        """
        Generate an updated catalog with learned confidence values.

        Args:
            output_path: Where to write the learned catalog
            days: Days of history to analyze
            min_samples: Minimum samples before updating confidence

        Returns:
            Path to the generated catalog
        """
        catalog = self.load_catalog()
        updates = self.compute_updates(days=days)

        # Deep copy catalog structure
        learned_catalog = {
            "version": "2.0-learned",
            "generated_at": datetime.now().isoformat(),
            "source_catalog": str(self.catalog_path.name),
            "analysis_days": days,
            "min_samples": min_samples,
            "packs": [],
        }

        for pack in catalog.get("packs", []):
            pack_id = pack.get("id", "")
            pack_copy = dict(pack)  # Shallow copy

            report = updates.get(pack_id)

            # Update hypotheses with learned confidences
            updated_hypotheses = []
            for hyp in pack.get("hypotheses", []):
                hyp_copy = dict(hyp)
                hyp_id = hyp.get("id", "")
                prior = hyp.get("confidence_hint", 0.3)

                if report and hyp_id in report.hypotheses:
                    outcome = report.hypotheses[hyp_id]
                    if outcome.total_observations >= min_samples:
                        posterior = outcome.compute_posterior(min_samples=min_samples)
                        hyp_copy["confidence_hint"] = round(posterior, 3)
                        hyp_copy["confidence_source"] = "learned"
                        hyp_copy["confidence_prior"] = round(prior, 3)
                        hyp_copy["sample_size"] = outcome.total_observations
                        hyp_copy["confirmed"] = outcome.confirmed
                        hyp_copy["falsified"] = outcome.falsified
                    else:
                        hyp_copy["confidence_source"] = "prior"
                        hyp_copy["sample_size"] = outcome.total_observations
                else:
                    hyp_copy["confidence_source"] = "prior"
                    hyp_copy["sample_size"] = 0

                updated_hypotheses.append(hyp_copy)

            pack_copy["hypotheses"] = updated_hypotheses
            learned_catalog["packs"].append(pack_copy)

        # Write to output
        if output_path is None:
            output_path = self.catalog_path.parent / "branch_packs_catalog_v2_learned.yaml"
        output_path = Path(output_path)

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(learned_catalog, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return output_path

    def get_confidence_delta(self, hypothesis_id: str, days: int = 365) -> dict[str, Any] | None:
        """
        Get confidence delta for a specific hypothesis.

        Args:
            hypothesis_id: The hypothesis ID to check
            days: Days of history to analyze

        Returns:
            Dict with prior, posterior, delta, and sample info
        """
        updates = self.compute_updates(days=days)

        for report in updates.values():
            if hypothesis_id in report.hypotheses:
                outcome = report.hypotheses[hypothesis_id]
                posterior = outcome.compute_posterior()
                return {
                    "hypothesis_id": hypothesis_id,
                    "prior": round(outcome.prior_confidence, 3),
                    "posterior": round(posterior, 3),
                    "delta": round(posterior - outcome.prior_confidence, 3),
                    "confirmed": outcome.confirmed,
                    "falsified": outcome.falsified,
                    "sample_size": outcome.total_observations,
                }

        return None

    def format_confidence_summary(self, days: int = 365) -> str:
        """Format a summary of confidence updates."""
        updates = self.compute_updates(days=days)

        if not updates:
            return "No resolution data available for confidence updates."

        lines = [
            f"Confidence Updates (last {days} days)",
            "=" * 50,
            "",
        ]

        for pack_id, report in sorted(updates.items()):
            if not report.hypotheses:
                continue

            lines.append(f"Pack: {pack_id}")
            for h_id, outcome in sorted(report.hypotheses.items()):
                posterior = outcome.compute_posterior()
                delta = posterior - outcome.prior_confidence
                delta_str = f"+{delta:.2f}" if delta >= 0 else f"{delta:.2f}"
                arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"

                lines.append(
                    f"  {h_id}: {posterior:.2f} {arrow} ({delta_str}, n={outcome.total_observations})"
                )
            lines.append("")

        return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Confidence Updater CLI")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate learned catalog",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for learned catalog",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Days of history to analyze",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=5,
        help="Minimum samples before updating confidence",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print confidence update summary",
    )
    parser.add_argument(
        "--hypothesis",
        type=str,
        help="Get delta for specific hypothesis ID",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    updater = ConfidenceUpdater()

    if args.generate:
        output = updater.generate_learned_catalog(
            output_path=args.output,
            days=args.days,
            min_samples=args.min_samples,
        )
        print(f"Generated learned catalog: {output}")

    elif args.hypothesis:
        delta = updater.get_confidence_delta(args.hypothesis, days=args.days)
        if delta:
            if args.json:
                print(json.dumps(delta, indent=2))
            else:
                print(f"Hypothesis: {delta['hypothesis_id']}")
                print(f"  Prior: {delta['prior']}")
                print(f"  Posterior: {delta['posterior']}")
                print(f"  Delta: {delta['delta']}")
                print(f"  Samples: {delta['sample_size']} ({delta['confirmed']} confirmed, {delta['falsified']} falsified)")
        else:
            print(f"No data for hypothesis: {args.hypothesis}")

    elif args.summary or not any([args.generate, args.hypothesis]):
        print(updater.format_confidence_summary(days=args.days))
