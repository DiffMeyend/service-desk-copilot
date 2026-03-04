#!/usr/bin/env python3
"""Deterministic harness to re-ingest a ticket fixture through the watcher."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Tuple

ROOT = Path(__file__).resolve().parents[2]
WATCHER = ROOT / "scripts" / "Queue Scripts" / "ticket_ingestion_watcher.py"
DEFAULT_TICKET = ROOT / "tickets" / "processed" / "Untitled-1.md"
TICKETS_ROOT = ROOT / "tickets"
INBOX_DIR = TICKETS_ROOT / "inbox"
READY_DIR = TICKETS_ROOT / "ready"
PROCESSED_DIR = TICKETS_ROOT / "processed"
ERROR_DIR = TICKETS_ROOT / "error"
EPSILON = 1e-6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-ingest a ticket fixture via the ingestion watcher.")
    parser.add_argument(
        "--ticket",
        type=Path,
        default=DEFAULT_TICKET,
        help=f"Fixture to ingest (default: {DEFAULT_TICKET})",
    )
    parser.add_argument(
        "--parser",
        choices=("all", "pii", "both"),
        default="both",
        help="Select which parser(s) to run (default: %(default)s).",
    )
    parser.add_argument(
        "--once",
        dest="once",
        action="store_true",
        default=True,
        help="Run the watcher with --once (default: enabled).",
    )
    parser.add_argument(
        "--loop",
        dest="once",
        action="store_false",
        help="Keep the watcher running instead of using --once.",
    )
    return parser.parse_args()


def ensure_ticket_path(ticket_path: Path) -> Path:
    ticket_path = ticket_path if ticket_path.is_absolute() else (ROOT / ticket_path)
    if not ticket_path.exists():
        raise SystemExit(f"Ticket fixture {ticket_path} not found.")
    if not ticket_path.is_file():
        raise SystemExit(f"Ticket fixture {ticket_path} is not a file.")
    return ticket_path


def ensure_dirs() -> None:
    for path in (INBOX_DIR, READY_DIR, PROCESSED_DIR, ERROR_DIR):
        path.mkdir(parents=True, exist_ok=True)


def stage_fixture(ticket_path: Path) -> Path:
    ensure_dirs()
    dest = INBOX_DIR / ticket_path.name
    if dest.exists():
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        suffix = ticket_path.suffix or ".txt"
        dest = INBOX_DIR / f"{ticket_path.stem}_{timestamp}{suffix}"
    shutil.copy2(ticket_path, dest)
    return dest


def snapshot_dir(directory: Path) -> Dict[Path, float]:
    if not directory.exists():
        return {}
    return {
        path: path.stat().st_mtime
        for path in directory.iterdir()
        if path.is_file()
    }


def run_watcher(parser_mode: str, once: bool) -> None:
    if not WATCHER.exists():
        raise SystemExit(f"Watcher script {WATCHER} not found.")
    cmd = [sys.executable, str(WATCHER), "--parser", parser_mode]
    if once:
        cmd.append("--once")
    subprocess.run(cmd, check=True, cwd=ROOT)


def detect_ready_artifact(
    before: Dict[Path, float],
    after: Dict[Path, float],
    started_at: float,
) -> Tuple[Path, str]:
    candidate = None
    candidate_mtime = 0.0
    status = ""
    for path, mtime in after.items():
        previous = before.get(path)
        if previous is None or mtime - previous > EPSILON:
            if previous is not None and mtime + EPSILON < started_at:
                continue
            if candidate is None or mtime > candidate_mtime:
                candidate = path
                candidate_mtime = mtime
                status = "updated" if previous is not None else "created"
    if candidate is None:
        raise SystemExit("Watcher completed but no JSON artifact was written to tickets/ready.")
    return candidate, status


def match_stage_name(stage_path: Path, target_path: Path) -> bool:
    suffix = stage_path.suffix or ".txt"
    if target_path.suffix != suffix:
        return False
    if target_path.name == stage_path.name:
        return True
    return target_path.name.startswith(f"{stage_path.stem}_")


def detect_archive(
    stage_path: Path,
    before: Dict[Path, float],
    after: Dict[Path, float],
    started_at: float,
) -> Path:
    candidate = None
    candidate_mtime = 0.0
    for path, mtime in after.items():
        if not match_stage_name(stage_path, path):
            continue
        previous = before.get(path)
        if previous is None or mtime - previous > EPSILON:
            if previous is not None and mtime + EPSILON < started_at:
                continue
            if candidate is None or mtime > candidate_mtime:
                candidate = path
                candidate_mtime = mtime
    if candidate is None:
        raise RuntimeError("Watcher did not archive the staged ticket into processed/ or error/.")
    return candidate


def summarize_ready(ready_path: Path) -> Dict[str, str]:
    payload = json.loads(ready_path.read_text(encoding="utf-8"))
    ticket = payload.get("ticket", {}) if isinstance(payload, dict) else {}
    target = ticket.get("target_device", {}) if isinstance(ticket, dict) else {}
    requester = ticket.get("requester", {}) if isinstance(ticket, dict) else {}
    return {
        "ticket_id": ticket.get("id") or payload.get("case", {}).get("id") or "UNKNOWN",
        "title": ticket.get("title") or "UNKNOWN",
        "hostname": target.get("hostname") or "UNKNOWN",
        "username": target.get("username") or requester.get("name") or "UNKNOWN",
    }


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def reingest(ticket_path: Path, parser_mode: str, once: bool) -> None:
    staged_path = stage_fixture(ticket_path)
    print(f"[reingest] Staged {ticket_path.name} -> {relpath(staged_path)}", flush=True)
    start = time.time()
    ready_before = snapshot_dir(READY_DIR)
    processed_before = snapshot_dir(PROCESSED_DIR)
    error_before = snapshot_dir(ERROR_DIR)
    run_watcher(parser_mode, once)
    ready_after = snapshot_dir(READY_DIR)
    processed_after = snapshot_dir(PROCESSED_DIR)
    error_after = snapshot_dir(ERROR_DIR)
    ready_path, ready_status = detect_ready_artifact(ready_before, ready_after, start)
    archived_bucket = "processed"
    try:
        archived_path = detect_archive(staged_path, processed_before, processed_after, start)
    except RuntimeError:
        archived_path = detect_archive(staged_path, error_before, error_after, start)
        archived_bucket = "error"
    summary = summarize_ready(ready_path)
    ready_rel = relpath(ready_path)
    archived_rel = relpath(archived_path)
    warning = " (WARNING: overwrote existing artifact)" if ready_status == "updated" else ""
    print(
        f"[reingest] parser={parser_mode} ticket_id={summary['ticket_id']} "
        f"ready={ready_rel}{warning} archived={archived_bucket}:{archived_rel}",
        flush=True,
    )


def main() -> None:
    args = parse_args()
    ticket_path = ensure_ticket_path(args.ticket)
    parser_modes: Iterable[str] = ("all", "pii") if args.parser == "both" else (args.parser,)
    for mode in parser_modes:
        reingest(ticket_path, mode, args.once)


if __name__ == "__main__":
    main()
