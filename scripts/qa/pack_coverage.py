#!/usr/bin/env python3
"""Compute branch pack coverage against the taxonomy mapping."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List

import yaml


def scrub_yaml_text(text: str) -> str:
    return "".join(
        ch for ch in text if ch in "\n\r\t" or 32 <= ord(ch) <= 126 or ord(ch) >= 160
    )


def load_yaml(path: Path) -> Dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    safe_text = scrub_yaml_text(text)
    data = yaml.safe_load(safe_text)
    return data if isinstance(data, dict) else {}


def summarize(catalog_path: Path, taxonomy_path: Path) -> Dict[str, object]:
    catalog = load_yaml(catalog_path)
    packs = {pack.get("id"): pack for pack in catalog.get("packs", []) if isinstance(pack, dict)}

    taxonomy = load_yaml(taxonomy_path)
    mappings: List[Dict[str, object]] = taxonomy.get("mappings", []) or []

    total_mappings = len(mappings)
    covered = 0
    missing_primary: List[str] = []

    issue_counts = Counter()
    category_counts = Counter()
    for mapping in mappings:
        issue = mapping.get("issue_type") or "Unknown"
        issue_counts[issue] += 1
        primary = mapping.get("primary_pack")
        if primary in packs:
            covered += 1
            category_counts[packs[primary].get("category") or "unknown"] += 1
        else:
            missing_primary.append(primary or "undefined")

    total_packs = len(packs)
    coverage_pct = (covered / total_mappings * 100) if total_mappings else 100.0
    return {
        "total_catalog_packs": total_packs,
        "taxonomy_entries": total_mappings,
        "covered_entries": covered,
        "coverage_percent": round(coverage_pct, 2),
        "missing_primary_packs": sorted(set(missing_primary)),
        "issue_counts": dict(issue_counts),
        "category_usage": dict(category_counts),
    }


def print_summary(summary: Dict[str, object]) -> None:
    print("=" * 60)
    print("Branch Pack Coverage Summary")
    print("=" * 60)
    print(f"Total packs in catalog:         {summary['total_catalog_packs']}")
    print(f"Taxonomy entries:               {summary['taxonomy_entries']}")
    print(f"Covered taxonomy entries:       {summary['covered_entries']}")
    print(f"Coverage percent:               {summary['coverage_percent']:.2f}%")
    print()

    missing = summary["missing_primary_packs"]
    if missing:
        print("Missing primary packs referenced in taxonomy:")
        for pack_id in missing:
            print(f"  - {pack_id}")
        print()
    else:
        print("All taxonomy primary packs exist in the catalog.\n")

    print("Issue Type Counts:")
    for issue, count in sorted(summary["issue_counts"].items(), key=lambda item: item[0]):
        print(f"  - {issue}: {count}")
    print()

    print("Catalog Category Usage:")
    for category, count in sorted(summary["category_usage"].items(), key=lambda item: item[0]):
        print(f"  - {category}: {count}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare taxonomy mappings to branch pack catalog.")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("runtime/branch_packs_catalog_v1_0.yaml"),
        help="Path to branch packs catalog YAML.",
    )
    parser.add_argument(
        "--taxonomy",
        type=Path,
        default=Path("runtime/taxonomy_pack_mapping.yaml"),
        help="Path to taxonomy mapping YAML.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable summary.",
    )
    args = parser.parse_args()

    summary = summarize(args.catalog, args.taxonomy)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_summary(summary)


if __name__ == "__main__":
    main()
