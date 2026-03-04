#!/usr/bin/env python3
"""Package manual command output into LOG_RESULT payload."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parents[2] / "tickets" / "results"


def main() -> int:
    parser = argparse.ArgumentParser(description="Wrap a command output file into LOG_RESULT JSON.")
    parser.add_argument("ticket_id", help="Ticket ID")
    parser.add_argument("command_id", help="Catalog command id or description")
    parser.add_argument("output_file", type=Path, help="Path to text file containing command output")
    parser.add_argument(
        "--notes",
        default="",
        help="Optional notes or context",
    )
    args = parser.parse_args()

    if not args.output_file.exists():
        raise SystemExit(f"Output file not found: {args.output_file}")

    payload = {
        "ticket_id": args.ticket_id,
        "command_id": args.command_id,
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": args.notes,
        "output": args.output_file.read_text(encoding="utf-8", errors="replace"),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_ticket = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in args.ticket_id)
    safe_cmd = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in args.command_id)
    out_path = RESULTS_DIR / f"{safe_ticket}_{safe_cmd}.logresult.json"
    formatted = json.dumps(payload, ensure_ascii=False, indent=2)
    out_path.write_text(formatted, encoding="utf-8")
    print(out_path)
    inline = json.dumps(payload, ensure_ascii=False)
    print("\nPaste the line below into RouterBrain:\n")
    print(f"LOG_RESULT {inline}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
