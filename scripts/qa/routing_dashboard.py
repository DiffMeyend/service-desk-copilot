#!/usr/bin/env python3
"""Summarize routing telemetry for QA/observability."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import yaml

def gather_payload_files(inputs: Sequence[Path]) -> List[Path]:
    files: List[Path] = []
    for item in inputs:
        if item.is_dir():
            files.extend(sorted(item.glob("*.json")))
        elif item.suffix.lower() == ".json" and item.exists():
            files.append(item)
    return files


def load_payload(path: Path) -> Dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def scrub_yaml_text(text: str) -> str:
    return "".join(ch for ch in text if ch in "\n\r\t" or 32 <= ord(ch) <= 126 or ord(ch) >= 160)


def load_pack_categories(path: Path) -> Dict[str, str]:
    try:
        text = scrub_yaml_text(path.read_text(encoding="utf-8", errors="ignore"))
        data = yaml.safe_load(text)
    except OSError:
        return {}
    categories: Dict[str, str] = {}
    for pack in data.get("packs", []) or []:
        if not isinstance(pack, dict):
            continue
        pack_id = pack.get("id")
        if pack_id:
            categories[pack_id] = pack.get("category", "unknown")
    return categories


def analyze_payloads(files: Iterable[Path], pack_categories: Dict[str, str]) -> Dict[str, object]:
    method_counts: Counter[str] = Counter()
    match_stage_counts: Counter[str] = Counter()
    keyword_reason_counts: Counter[str] = Counter()
    match_type_counts: Counter[str] = Counter()
    alias_count = 0
    fallback_count = 0
    confidence_values: List[float] = []
    pack_counts: Counter[str] = Counter()
    manual_requested = 0
    manual_applied = 0
    manual_invalid = 0
    collision_count = 0

    total = 0
    for path in files:
        data = load_payload(path)
        branches = data.get("branches") or {}
        method = branches.get("routing_method") or "unknown"
        method_counts[method] += 1

        metadata = branches.get("routing_metadata") or {}
        taxonomy = metadata.get("taxonomy_match") or {}
        stage = taxonomy.get("match_stage") or ("skipped" if method != "taxonomy" else "unknown")
        match_stage_counts[stage] += 1
        if taxonomy.get("alias_applied"):
            alias_count += 1
        if taxonomy.get("fallback_loaded"):
            fallback_count += 1

        keyword_reason = metadata.get("keyword_reason")
        if keyword_reason:
            keyword_reason_counts[keyword_reason] += 1

        manual_info = metadata.get("manual_override") or {}
        manual_requested += len(manual_info.get("requested", []))
        manual_applied += len(manual_info.get("applied", []))
        manual_invalid += len(manual_info.get("invalid", []))

        for hyp in branches.get("active_hypotheses") or []:
            match_type = hyp.get("match_type") or method
            match_type_counts[match_type] += 1
            conf = hyp.get("confidence_score")
            if isinstance(conf, (int, float)):
                confidence_values.append(float(conf))

        pack_ids = branches.get("source_pack") or []
        for pack_id in pack_ids:
            pack_counts[pack_id] += 1

        non_cross = sum(
            1
            for pid in set(pack_ids or [])
            if pack_categories.get(pid, "unknown") != "cross_cutting"
        )
        if non_cross > 1:
            collision_count += 1

        total += 1

    summary: Dict[str, object] = {
        "total_payloads": total,
        "routing_method_counts": method_counts,
        "taxonomy_match_stage_counts": match_stage_counts,
        "keyword_fallback_reasons": keyword_reason_counts,
        "match_type_counts": match_type_counts,
        "alias_matches": alias_count,
        "taxonomy_fallbacks": fallback_count,
        "pack_counts": pack_counts,
        "confidence_values": confidence_values,
        "manual_override": {
            "requested": manual_requested,
            "applied": manual_applied,
            "invalid": manual_invalid,
        },
        "collision_count": collision_count,
        "collision_rate": round((collision_count / total * 100) if total else 0.0, 2),
        "manual_override_rate": round((manual_applied / total * 100) if total else 0.0, 2),
    }
    return summary


def print_summary(summary: Dict[str, object]) -> None:
    total = summary["total_payloads"]
    print("=" * 60)
    print("Routing QA Dashboard")
    print("=" * 60)
    print(f"Payloads analyzed: {total}")
    print()

    def print_counter(title: str, counter: Counter[str]) -> None:
        if not counter:
            return
        print(title)
        for key, count in counter.most_common():
            perc = (count / total * 100) if total else 0
            print(f"  - {key}: {count} ({perc:.1f}%)")
        print()

    print_counter("Routing methods:", summary["routing_method_counts"])
    print_counter("Taxonomy match stages:", summary["taxonomy_match_stage_counts"])
    print_counter("Keyword fallback reasons:", summary["keyword_fallback_reasons"])
    print_counter("Hypothesis match types:", summary["match_type_counts"])

    alias = summary["alias_matches"]
    fallback = summary["taxonomy_fallbacks"]
    if total:
        print(f"Alias-applied taxonomy routes: {alias} ({alias/total*100:.1f}%)")
        print(f"Taxonomy fallback usage: {fallback} ({fallback/total*100:.1f}%)")
        print()
        print(
            f"Collision rate (multiple non-cross-cutting packs): "
            f"{summary['collision_rate']:.2f}% ({summary['collision_count']} payloads)"
        )
        print(
            f"Manual override rate: {summary['manual_override_rate']:.2f}% "
            f"({summary.get('manual_override', {}).get('applied', 0)} payloads)"
        )
        print()

    confidences = summary["confidence_values"]
    if confidences:
        print("Confidence scores:")
        print(f"  - mean:   {statistics.mean(confidences):.3f}")
        print(f"  - median: {statistics.median(confidences):.3f}")
        print(f"  - stdev:  {statistics.pstdev(confidences):.3f}")
        print()

    pack_counts: Counter[str] = summary["pack_counts"]
    if pack_counts:
        print("Top source packs:")
        for pack_id, count in pack_counts.most_common(10):
            perc = (count / total * 100) if total else 0
            print(f"  - {pack_id}: {count} ({perc:.1f}%)")
        print()

    manual_info = summary.get("manual_override", {})
    if manual_info and any(manual_info.values()):
        print("Manual override stats:")
        print(f"  - Requested: {manual_info.get('requested', 0)}")
        print(f"  - Applied:   {manual_info.get('applied', 0)}")
        print(f"  - Invalid:   {manual_info.get('invalid', 0)}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize routing metadata for QA. Defaults to tickets/ready/*.json."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Payload JSON files or directories (default: tickets/ready)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output summary as JSON instead of human-readable text.",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("runtime/branch_packs_catalog_v1_0.yaml"),
        help="Path to branch packs catalog for category lookups.",
    )
    args = parser.parse_args()

    paths = args.paths or [Path("tickets/ready")]
    files = gather_payload_files(paths)
    pack_categories = load_pack_categories(args.catalog)
    summary = analyze_payloads(files, pack_categories)
    if args.json:
        safe_summary = {
            key: (dict(value) if isinstance(value, Counter) else value)
            for key, value in summary.items()
            if key not in {"confidence_values"}
        }
        safe_summary["confidence_mean"] = (
            statistics.mean(summary["confidence_values"]) if summary["confidence_values"] else None
        )
        safe_summary["confidence_median"] = (
            statistics.median(summary["confidence_values"]) if summary["confidence_values"] else None
        )
        print(json.dumps(safe_summary, indent=2, default=list))
    else:
        print_summary(summary)


if __name__ == "__main__":
    main()
