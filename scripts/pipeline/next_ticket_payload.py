#!/usr/bin/env python3
"""
Emit the next ticket payload produced by ticket_ingestion_watcher.

Reads the oldest JSON file under tickets/ready (or custom path), prints the JSON
payload to stdout, and optionally moves the file to a consumed directory once
Codex has ingested it.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Emit next ticket payload for RouterBrain ingestion.")
    parser.add_argument(
        "--ready-dir",
        type=Path,
        default=root / "tickets" / "ready",
        help="Directory containing ready JSON payloads (default: %(default)s).",
    )
    parser.add_argument(
        "--consume",
        action="store_true",
        help="Move the file into ready/consumed after emitting (default: disabled).",
    )
    parser.add_argument(
        "--consumed-dir",
        type=Path,
        default=root / "tickets" / "ready" / "consumed",
        help="Destination for consumed files when --consume is set (default: %(default)s).",
    )
    return parser.parse_args()


def select_oldest_file(directory: Path) -> Optional[Path]:
    files = [path for path in directory.iterdir() if path.is_file()]
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime)
    return files[0]


def main() -> int:
    args = parse_args()
    if not args.ready_dir.exists():
        print(f"[next-ticket] Ready directory not found: {args.ready_dir}", file=sys.stderr)
        return 1

    payload_path = select_oldest_file(args.ready_dir)
    if not payload_path:
        print("[next-ticket] No ready payloads found.", file=sys.stderr)
        return 2

    content = payload_path.read_text(encoding="utf-8")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        print(f"[next-ticket] Invalid JSON in {payload_path.name}: {exc}", file=sys.stderr)
        return 3

    # Print normalized JSON (pretty) so Codex can pass it directly to RouterBrain.
    normalized = json.dumps(data, ensure_ascii=False, indent=2)
    print(normalized)

    if args.consume:
        args.consumed_dir.mkdir(parents=True, exist_ok=True)
        ticket_id = (data.get("ticket_id") or data.get("ticket", {}).get("id") or payload_path.stem)
        safe_ticket_id = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in ticket_id)
        destination = args.consumed_dir / f"{safe_ticket_id}.json"
        if destination.exists():
            suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            destination = args.consumed_dir / f"{safe_ticket_id}_{suffix}.json"
        shutil.move(str(payload_path), destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

