#!/usr/bin/env python3
"""Quick parser smoke harness for local validation."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
DEFAULT_TICKET = ROOT / "tickets" / "processed" / "Untitled-1.md"
PARSER_MAP = {
    "all": "parsing.parse_ticket",
    "pii": "parsing.parse_ticket_pii",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ticket parsers against a local sample ticket.")
    parser.add_argument(
        "--ticket",
        type=Path,
        default=DEFAULT_TICKET,
        help=f"Ticket file to ingest (default: {DEFAULT_TICKET})",
    )
    parser.add_argument(
        "--parser",
        choices=("all", "pii", "both"),
        default="both",
        help="Select which parser(s) to run (default: %(default)s).",
    )
    parser.add_argument(
        "--dump-json",
        action="store_true",
        help="Print the full payload JSON after the summary.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON when --dump-json is used.",
    )
    parser.add_argument(
        "--validate-schema",
        type=Path,
        help="Optional JSON schema path to validate payload output.",
    )
    parser.add_argument(
        "--skip-cli-smoke",
        action="store_true",
        help="Skip running `python scripts/parsing/*.py --help` before executing parsers.",
    )
    return parser.parse_args()


def load_parser(name: str):
    module_name = PARSER_MAP[name]
    return importlib.import_module(module_name)


def build_validator(schema_path: Path) -> Tuple[object, str]:
    schema_path = schema_path.resolve()
    if not schema_path.exists():
        raise SystemExit(f"Schema file {schema_path} not found.")
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise SystemExit(
            "jsonschema is required for --validate-schema. "
            "Install with `pip install jsonschema` or omit the flag."
        ) from exc
    with schema_path.open("r", encoding="utf-8") as handle:
        schema_data = json.load(handle)
    validator_cls = jsonschema.validators.validator_for(schema_data)
    validator_cls.check_schema(schema_data)
    label = schema_path
    try:
        label = schema_path.relative_to(ROOT)
    except ValueError:
        pass
    return validator_cls(schema_data), str(label)


def describe_error_path(error: object) -> str:
    json_path = getattr(error, "json_path", None)
    if json_path:
        return str(json_path)
    path_parts = ["$"]
    for part in getattr(error, "path", []):
        if isinstance(part, int):
            path_parts.append(f"[{part}]")
        else:
            path_parts.append(f".{part}")
    return "".join(path_parts)


def validate_payload(validator: Optional[object], payload: Dict[str, object]) -> Tuple[bool, int, Tuple[str, ...]]:
    if validator is None:
        return True, 0, ()
    errors = sorted(
        validator.iter_errors(payload),  # type: ignore[attr-defined]
        key=lambda err: getattr(err, "json_path", ""),
    )
    formatted = tuple(f"{describe_error_path(err)}: {err.message}" for err in errors[:5])
    return not errors, len(errors), formatted


def summarize_payload(payload: Dict[str, object]) -> Dict[str, object]:
    ticket = payload.get("ticket", {}) if isinstance(payload, dict) else {}
    target = ticket.get("target_device", {}) if isinstance(ticket, dict) else {}
    requester = ticket.get("requester", {}) if isinstance(ticket, dict) else {}
    environment = payload.get("environment", {}) if isinstance(payload, dict) else {}
    target_device = environment.get("target_device", {}) if isinstance(environment, dict) else {}
    user_context = environment.get("user_context", {}) if isinstance(environment, dict) else {}
    notes = payload.get("notes", {}) if isinstance(payload, dict) else {}
    evidence = payload.get("evidence", {}) if isinstance(payload, dict) else {}
    observations = evidence.get("observations", []) if isinstance(evidence, dict) else []

    # Count notes in rolling field (separated by double newlines)
    rolling_notes = notes.get("rolling", "") if isinstance(notes, dict) else ""
    note_count = len([n for n in rolling_notes.split("\n\n") if n.strip()]) if rolling_notes else 0

    return {
        "ticket_id": ticket.get("id"),
        "summary": ticket.get("summary"),
        "hostname": target_device.get("hostname") or target.get("hostname"),
        "username": user_context.get("username") or target.get("username") or requester.get("name"),
        "os": target_device.get("os") or target.get("os"),
        "asset_tag": target_device.get("asset_tag") or target.get("asset_tag"),
        "ip": target_device.get("ip") or target.get("ip"),
        "notes_count": note_count,
        "observations": len(observations),
    }


def run_parser(
    mode: str,
    ticket_path: Path,
    dump_json: bool,
    pretty: bool,
    validator: Optional[object],
    schema_label: str,
) -> bool:
    parser_module = load_parser(mode)
    raw_text = parser_module.load_ticket_text(ticket_path)
    payload = parser_module.build_payload(raw_text)
    summary = summarize_payload(payload)
    print(f"=== parser: {mode} | ticket: {ticket_path.name} ===")
    for key, value in summary.items():
        print(f"{key:>12}: {value or '—'}")
    schema_ok = True
    if validator is not None:
        schema_ok, total_errors, formatted_errors = validate_payload(validator, payload)
        label = f" [{schema_label}]" if schema_label else ""
        if schema_ok:
            print(f"{'schema':>12}: OK{label}")
        else:
            print(f"{'schema':>12}: FAIL ({total_errors} errors){label}")
            for line in formatted_errors:
                print(f"{'':>12}  - {line}")
    if dump_json:
        indent = 2 if pretty else None
        print(json.dumps(payload, indent=indent))
    print()
    return schema_ok


def run_cli_smoke() -> None:
    """Verify direct script invocation does not raise import errors."""
    scripts = (
        ROOT / "scripts" / "parsing" / "parse_ticket.py",
        ROOT / "scripts" / "parsing" / "parse_ticket_pii.py",
    )
    for script in scripts:
        cmd = (sys.executable, str(script), "--help")
        completed = subprocess.run(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        script_name = script.relative_to(ROOT)
        print(f"[cli-smoke] {script_name} --help ({len(completed.stdout)} bytes stdout)")


def main() -> None:
    args = parse_args()
    if not args.skip_cli_smoke:
        run_cli_smoke()
    ticket_path = args.ticket if args.ticket.is_absolute() else (ROOT / args.ticket)
    if not ticket_path.exists():
        raise SystemExit(f"Ticket {ticket_path} not found.")
    validator: Optional[object] = None
    schema_label = ""
    if args.validate_schema:
        schema_path = args.validate_schema if args.validate_schema.is_absolute() else (ROOT / args.validate_schema)
        validator, schema_label = build_validator(schema_path)
    modes: Iterable[str]
    if args.parser == "both":
        modes = ("all", "pii")
    else:
        modes = (args.parser,)
    schema_failed = False
    for mode in modes:
        schema_failed |= not run_parser(
            mode,
            ticket_path,
            args.dump_json,
            args.pretty,
            validator,
            schema_label,
        )
    if schema_failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
