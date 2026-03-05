#!/usr/bin/env python3
"""
Ticket ingestion watcher for BASIS runtime.

Monitors tickets/inbox for new files, parses each into the Context Payload
schema via scripts/parsing/parse_ticket.py, writes the JSON artifact into
tickets/ready, and moves the original file to tickets/processed. Failures are
moved to tickets/error.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from parsing import parse_ticket, parse_ticket_sanitize  # noqa: E402

PARSER_MODULES = {
    "all": parse_ticket,
    "pii": parse_ticket_sanitize,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch the ticket inbox directory and emit Context Payload JSON."
    )
    parser.add_argument(
        "--inbox",
        type=Path,
        default=ROOT / "tickets" / "inbox",
        help="Directory to watch for new ticket dump files (default: %(default)s).",
    )
    parser.add_argument(
        "--ready-dir",
        type=Path,
        default=ROOT / "tickets" / "ready",
        help="Directory to write parsed Context Payload JSON (default: %(default)s).",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=ROOT / "tickets" / "processed",
        help="Directory to move successfully processed files (default: %(default)s).",
    )
    parser.add_argument(
        "--error-dir",
        type=Path,
        default=ROOT / "tickets" / "error",
        help="Directory to move files that failed processing (default: %(default)s).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=0.5,
        help="Delay to allow files to finish writing before ingestion (default: %(default)s).",
    )
    parser.add_argument(
        "--parser",
        choices=tuple(PARSER_MODULES.keys()),
        default="all",
        help="Select which parser implementation to use (default: %(default)s).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process the current inbox contents once and exit instead of looping.",
    )
    return parser.parse_args()


def ensure_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def safe_ticket_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", value or "UNSPECIFIED")


def build_output_path(ready_dir: Path, ticket_id: str) -> Path:
    base = safe_ticket_id(ticket_id)
    return ready_dir / f"{base}.json"


def now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def move_with_suffix(src: Path, dest_dir: Path, base_name: str | None = None, suffix: str | None = None) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = base_name or src.stem
    ext = suffix if suffix is not None else (src.suffix or ".txt")
    dest = dest_dir / f"{name}{ext}"
    if dest.exists():
        suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = dest_dir / f"{name}_{suffix}{ext}"
    shutil.move(str(src), dest)
    return dest


def _safe_move_to_error(file_path: Path, error_dir: Path) -> Optional[Path]:
    """Safely move a file to the error directory, returning the new path or None on failure."""
    try:
        return move_with_suffix(file_path, error_dir)
    except (OSError, IOError, shutil.Error) as e:
        logger.warning("Could not move %s to error directory: %s", file_path.name, e)
        return None





def iter_evidence_sidecars(base_path: Path) -> List[Path]:
    """Return possible sidecar evidence files for a ticket text file."""
    return [
        base_path.with_suffix(".evidence.jsonl"),
        base_path.with_suffix(".evidence.txt"),
    ]


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def parse_evidence_lines(lines: List[str]) -> List[dict]:
    """Parse evidence lines in JSONL or LOG/LOG_RESULT format."""
    results: List[dict] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("LOG_RESULT "):
            json_part = line[len("LOG_RESULT "):].strip()
            try:
                payload = json.loads(json_part)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("command_id"):
                results.append(payload)
            continue

        if line.startswith("LOG "):
            parts = line[4:].strip().split(maxsplit=1)
            if not parts:
                continue
            command_id = parts[0]
            output = _strip_quotes(parts[1]) if len(parts) > 1 else ""
            results.append({"command_id": command_id, "output": output})
            continue

        if line.startswith("{") and line.endswith("}"):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("command_id"):
                results.append(payload)
    return results


def load_sidecar_evidence(base_path: Path) -> List[dict]:
    """Load evidence entries from sidecar files next to the ticket text file."""
    entries: List[dict] = []
    for sidecar in iter_evidence_sidecars(base_path):
        if not sidecar.exists():
            continue
        try:
            lines = sidecar.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
        except OSError:
            continue
        entries.extend(parse_evidence_lines(lines))
    return entries


def merge_evidence(payload: dict, entries: List[dict]) -> int:
    """Merge evidence entries into the payload. Returns number of merged results."""
    if not entries:
        return 0

    evidence = payload.setdefault("evidence", {})
    tests_run = evidence.setdefault("tests_run", [])
    results = evidence.setdefault("results", [])

    existing = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        key = (item.get("command_id"), item.get("output"), item.get("captured_at"))
        existing.add(key)

    merged = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        command_id = entry.get("command_id")
        output = entry.get("output", "")
        captured_at = entry.get("captured_at") or datetime.now(timezone.utc).isoformat(timespec="seconds")
        notes = entry.get("notes", "")
        key = (command_id, output, captured_at)
        if not command_id or key in existing:
            continue
        results.append(
            {
                "command_id": command_id,
                "output": output[:500] if isinstance(output, str) and len(output) > 500 else output,
                "captured_at": captured_at,
                "notes": notes,
            }
        )
        if command_id not in tests_run:
            tests_run.append(command_id)
        existing.add(key)
        merged += 1

    return merged


def process_file(
    file_path: Path,
    ready_dir: Path,
    processed_dir: Path,
    settle_seconds: float,
    parser_module,
    parser_mode: str,
) -> None:
    time.sleep(settle_seconds)
    raw_text = parser_module.load_ticket_text(file_path)
    split_fn = getattr(parser_module, "split_ticket_and_evidence", None)
    if split_fn:
        clean_text, extracted = split_fn(raw_text)
    else:
        clean_text, extracted = raw_text, []

    payload = parser_module.build_payload(clean_text)
    ticket_id = (payload.get("ticket", {}).get("id") or payload.get("case", {}).get("id") or "UNSPECIFIED")

    merged = merge_evidence(payload, extracted + load_sidecar_evidence(file_path))

    ready_path = build_output_path(ready_dir, ticket_id)
    ready_existed = ready_path.exists()
    ready_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    processed_base = safe_ticket_id(ticket_id)
    archived_path = move_with_suffix(file_path, processed_dir, base_name=processed_base, suffix=".txt")
    verb = "Updated" if ready_existed else "Created"
    print(
        f"[{now_ts()}][ticket-ingest][{parser_mode}] {verb} {ready_path.name} from {file_path.name} "
        f"(archived: {archived_path.name})",
        flush=True,
    )
    if merged:
        print(f"[{now_ts()}][ticket-ingest][{parser_mode}]   merged_evidence: {merged}", flush=True)
    # Log selected branch pack(s) for observability
    source_pack = payload.get("branches", {}).get("source_pack", [])
    if source_pack:
        print(f"[{now_ts()}][ticket-ingest][{parser_mode}]   source_pack: {source_pack}", flush=True)

def summarize_top_level_changes(previous: dict | None, current: dict) -> str:
    if previous is None:
        return "new"
    prev_keys = set(previous.keys())
    curr_keys = set(current.keys())

    added = sorted(curr_keys - prev_keys)
    removed = sorted(prev_keys - curr_keys)
    common = prev_keys & curr_keys
    changed = sorted(k for k in common if previous.get(k) != current.get(k))

    parts: list[str] = []
    if added:
        parts.append("+" + ", +".join(added))
    if removed:
        parts.append("-" + ", -".join(removed))
    if changed:
        parts.append("~" + ", ~".join(changed))
    return "; ".join(parts) if parts else "no top-level changes"


def process_processed_file(
    file_path: Path,
    ready_dir: Path,
    settle_seconds: float,
    parser_module,
    parser_mode: str,
) -> None:
    time.sleep(settle_seconds)
    raw_text = parser_module.load_ticket_text(file_path)
    split_fn = getattr(parser_module, "split_ticket_and_evidence", None)
    if split_fn:
        clean_text, extracted = split_fn(raw_text)
    else:
        clean_text, extracted = raw_text, []

    payload = parser_module.build_payload(clean_text)
    ticket_id = (payload.get("ticket", {}).get("id") or payload.get("case", {}).get("id") or "UNSPECIFIED")

    merged = merge_evidence(payload, extracted + load_sidecar_evidence(file_path))

    ready_path = build_output_path(ready_dir, ticket_id)
    previous_payload = None
    if ready_path.exists():
        try:
            previous_payload = json.loads(ready_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous_payload = None

    ready_existed = ready_path.exists()
    ready_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    verb = "Updated" if ready_existed else "Created"
    summary = summarize_top_level_changes(previous_payload, payload)
    print(
        f"[{now_ts()}][ticket-reingest][{parser_mode}] {verb} {ready_path.name} from {file_path.name} ({summary})",
        flush=True,
    )
    # Log selected branch pack(s) for observability
    source_pack = payload.get("branches", {}).get("source_pack", [])
    if source_pack:
        print(f"[{now_ts()}][ticket-reingest][{parser_mode}]   source_pack: {source_pack}", flush=True)



def main() -> int:
    args = parse_args()
    ensure_dirs([args.inbox, args.ready_dir, args.processed_dir, args.error_dir])
    parser_module = PARSER_MODULES[args.parser]
    print(
        f"[ticket-ingest][{args.parser}] Watching {args.inbox} (interval {args.interval}s)...",
        flush=True,
    )

    processed_seen: dict[Path, float] = {}

    while True:
        try:
            files = sorted(
                [path for path in args.inbox.iterdir() if path.is_file()],
                key=lambda p: p.stat().st_mtime,
            )
        except FileNotFoundError:
            ensure_dirs([args.inbox])
            files = []

        pending_files = False
        for file_path in files:
            try:
                if time.time() - file_path.stat().st_mtime < args.settle_seconds:
                    pending_files = True
                    continue
                process_file(
                    file_path,
                    args.ready_dir,
                    args.processed_dir,
                    args.settle_seconds,
                    parser_module,
                    args.parser,
                )
            except (OSError, IOError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                # Expected errors during file processing
                error_target = _safe_move_to_error(file_path, args.error_dir)
                suffix = f" (moved to {error_target.name})" if error_target else ""
                logger.error(
                    "[ticket-ingest][%s] ERROR processing %s: %s%s",
                    args.parser, file_path.name, exc, suffix
                )
                print(f"[ticket-ingest][{args.parser}] ERROR processing {file_path.name}: {exc}{suffix}", file=sys.stderr)
            except Exception as exc:
                # Unexpected error - log full traceback for debugging
                error_target = _safe_move_to_error(file_path, args.error_dir)
                suffix = f" (moved to {error_target.name})" if error_target else ""
                logger.exception(
                    "[ticket-ingest][%s] UNEXPECTED ERROR processing %s%s",
                    args.parser, file_path.name, suffix
                )
                print(f"[ticket-ingest][{args.parser}] ERROR processing {file_path.name}: {exc}{suffix}", file=sys.stderr)

        try:
            processed_files = [path for path in args.processed_dir.iterdir() if path.is_file()]
        except FileNotFoundError:
            ensure_dirs([args.processed_dir])
            processed_files = []

        for file_path in processed_files:
            try:
                mtime = file_path.stat().st_mtime
            except FileNotFoundError:
                continue

            last_seen = processed_seen.get(file_path)
            if last_seen is None:
                processed_seen[file_path] = mtime
                continue

            if mtime <= last_seen:
                continue

            if time.time() - mtime < args.settle_seconds:
                pending_files = True
                continue

            try:
                process_processed_file(
                    file_path,
                    args.ready_dir,
                    args.settle_seconds,
                    parser_module,
                    args.parser,
                )
                processed_seen[file_path] = mtime
            except (OSError, IOError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                # Expected errors during file re-processing
                logger.error(
                    "[ticket-reingest][%s] ERROR processing %s: %s",
                    args.parser, file_path.name, exc
                )
                print(
                    f"[ticket-reingest][{args.parser}] ERROR processing {file_path.name}: {exc}",
                    file=sys.stderr,
                )
                processed_seen[file_path] = mtime
            except Exception as exc:
                # Unexpected error - log full traceback for debugging
                logger.exception(
                    "[ticket-reingest][%s] UNEXPECTED ERROR processing %s",
                    args.parser, file_path.name
                )
                print(
                    f"[ticket-reingest][{args.parser}] ERROR processing {file_path.name}: {exc}",
                    file=sys.stderr,
                )
                processed_seen[file_path] = mtime

        if args.once and not pending_files:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())


