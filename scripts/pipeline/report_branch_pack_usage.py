#!/usr/bin/env python3
"""
Aggregate audit telemetry logs and highlight branch-pack maintenance signals.
Usage:
  python report_branch_pack_usage.py <AuditLogs dir>

Outputs a summary to stdout listing:
- total logs processed
- pack override counts / missing keywords
- missing catalog keywords aggregated
"""

import json
import sys
from collections import Counter
from pathlib import Path


def load_logs(log_dir: Path):
    for path in sorted(log_dir.glob("*_audit.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        yield path.name, data


def main():
    if len(sys.argv) != 2:
        print("Usage: report_branch_pack_usage.py <AuditLogs dir>", file=sys.stderr)
        sys.exit(1)
    log_dir = Path(sys.argv[1])
    if not log_dir.exists():
        print(f"Audit log directory not found: {log_dir}", file=sys.stderr)
        sys.exit(1)

    total = 0
    pack_counts = Counter()
    override_counts = Counter()
    keyword_hits = Counter()
    missing_keywords = Counter()

    for name, data in load_logs(log_dir):
        total += 1
        branch = data.get("branch", {})
        pack = branch.get("source_pack") or "UNKNOWN"
        pack_counts[pack] += 1
        if branch.get("manual_override"):
            override_counts[pack] += 1
        for kw in branch.get("new_keywords", []) or []:
            missing_keywords[kw.lower()] += 1
        hypothesis_count = branch.get("hypotheses_evaluated")
        if hypothesis_count:
            keyword_hits[pack] += hypothesis_count

    print(f"Audit logs processed: {total}")
    if not total:
        return
    print("\nPacks by frequency:")
    for pack, count in pack_counts.most_common():
        overrides = override_counts.get(pack, 0)
        print(f"- {pack}: {count} runs ({overrides} overrides)")

    if missing_keywords:
        print("\nMissing keyword candidates (>=1 hit):")
        for kw, count in missing_keywords.most_common():
            print(f"- {kw} ({count})")
    else:
        print("\nNo missing keyword candidates recorded.")

    print("\nSuggested follow-ups:")
    if override_counts:
        top_pack, top_count = override_counts.most_common(1)[0]
        print(f"- Review pack '{top_pack}' (overrides: {top_count}).")
    else:
        print("- No packs exceeded manual override counts.")


if __name__ == "__main__":
    main()
