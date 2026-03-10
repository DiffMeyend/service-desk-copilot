#!/usr/bin/env python3
"""QF_Wiz Phase 7: Local Runtime Agent - Main Loop.

A minimal CLI agent that orchestrates troubleshooting sessions using
QF_Wiz runtime files.

Usage:
    # Interactive mode
    python -m scripts.agent.agent_loop --ticket tickets/ready/T20260218.0100.json

    # Non-interactive mode (for Codex integration)
    python -m scripts.agent.agent_loop -t tickets/ready/T20260218.json -c "PRINT_CONTEXT"
    python -m scripts.agent.agent_loop -t tickets/ready/T20260218.json -c "LOAD_BRANCH_PACK email_security"
    python -m scripts.agent.agent_loop -t tickets/ready/T20260218.json -c "LOG ping Reply_from_server"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__, config
from .command_handler import CommandError, CommandHandler
from .cp_manager import CPError, CPManager
from .css_calculator import CSSCalculator
from .output_formatter import OutputFormatter
from .runtime_loader import RuntimeLoader


def list_available_tickets() -> List[Path]:
    """List available ticket files in tickets/ready/."""
    ready_dir = config.TICKETS_READY_DIR
    if not ready_dir.exists():
        return []
    return sorted(ready_dir.glob("*.json"))


def select_ticket_interactive() -> Optional[Path]:
    """Interactive ticket selection from available tickets."""
    tickets = list_available_tickets()

    if not tickets:
        print("No tickets found in tickets/ready/")
        print("Drop a ticket file or run the ingestion watcher first.")
        return None

    print("Available tickets:")
    for i, ticket in enumerate(tickets, 1):
        print(f"  {i}) {ticket.name}")

    print()
    try:
        choice = input("Select ticket number (or 'q' to quit): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None

    if choice.lower() in ("q", "quit", "exit"):
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(tickets):
            return tickets[idx]
        print(f"Invalid selection: {choice}")
        return None
    except ValueError:
        print(f"Invalid input: {choice}")
        return None


def run_single_command(ticket_path: Path, command: str) -> int:
    """Execute a single command and exit (non-interactive mode for Codex)."""
    # Initialize runtime loader (quiet mode)
    runtime = RuntimeLoader()
    if not runtime.load_all():
        print("ERROR: Failed to load runtime files")
        return 1

    # Initialize CP manager
    cp_manager = CPManager(runtime.get_schema())
    try:
        cp_manager.load_ticket(ticket_path)
    except CPError as e:
        print(f"ERROR: Failed to load ticket: {e}")
        return 1

    # Initialize components
    css_calc = CSSCalculator(runtime.get_css_rules())
    handler = CommandHandler(cp_manager, runtime)

    # Parse and execute command
    try:
        cmd, payload = handler.parse_input(command)
    except CommandError as e:
        print(f"ERROR: {e}")
        return 1

    if not cmd:
        print("ERROR: Empty command")
        return 1

    # Execute command
    result = handler.dispatch(cmd, payload)

    if result == "QUIT":
        cp_manager.save()
        print("Saved.")
        return 0

    # Print command result
    print(result)
    print()

    # Recalculate CSS and show compact block
    css_score, blockers = css_calc.calculate(cp_manager.cp)
    cp_manager.set_value("css.score", css_score)

    formatter = OutputFormatter(cp_manager.cp, css_score, blockers)
    print(formatter.render_compact_block())

    # Save changes
    if cp_manager.is_dirty():
        cp_manager.save()

    return 0


def run_agent_loop(ticket_path: Path) -> int:
    """Run the main agent loop for a ticket (interactive mode)."""
    print(f"QF_Wiz Agent v{__version__}")
    print(f"Loading ticket: {ticket_path}")
    print()

    # Initialize runtime loader
    runtime = RuntimeLoader()
    if not runtime.load_all():
        print("ERROR: Failed to load runtime files:")
        for err in runtime.errors:
            print(f"  - {err}")
        return 1

    # Validate version
    if not runtime.validate_version():
        print(f"WARNING: Runtime version mismatch. Expected {config.RUNTIME_VERSION}, got {runtime.get_version()}")

    # Initialize CP manager
    cp_manager = CPManager(runtime.get_schema())
    try:
        cp_manager.load_ticket(ticket_path)
    except CPError as e:
        print(f"ERROR: Failed to load ticket: {e}")
        return 1

    # Initialize CSS calculator
    css_calc = CSSCalculator(runtime.get_css_rules())

    # Initialize command handler
    handler = CommandHandler(cp_manager, runtime)

    # Calculate initial CSS
    css_score, blockers = css_calc.calculate(cp_manager.cp)
    cp_manager.set_value("css.score", css_score)

    # Display initial compact block
    formatter = OutputFormatter(cp_manager.cp, css_score, blockers)
    print(formatter.render_compact_block())
    print()

    # Auto-save initial state
    if cp_manager.is_dirty():
        cp_manager.save()

    # Main loop
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not user_input:
            continue

        # Parse and dispatch command
        try:
            cmd, payload = handler.parse_input(user_input)
        except CommandError as e:
            print(f"ERROR: {e}")
            continue

        if not cmd:
            continue

        # Execute command
        result = handler.dispatch(cmd, payload)

        # Handle quit
        if result == "QUIT":
            cp_manager.save()
            print("Saved and exiting.")
            break

        # Print result
        print(result)
        print()

        # Recalculate CSS
        css_score, blockers = css_calc.calculate(cp_manager.cp)
        cp_manager.set_value("css.score", css_score)

        # Output compact block after state-changing commands
        if cmd in ("LOG_RESULT", "LOAD_BRANCH_PACK", "DECIDE"):
            formatter = OutputFormatter(cp_manager.cp, css_score, blockers)
            print(formatter.render_compact_block())
            print()

        # Auto-save if dirty
        if cp_manager.is_dirty():
            cp_manager.save()

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="QF_Wiz Local Runtime Agent",
        epilog="Example: python -m scripts.agent.agent_loop --ticket tickets/ready/T20260218.json",
    )
    parser.add_argument(
        "--ticket",
        "-t",
        type=Path,
        help="Path to ticket JSON file",
    )
    parser.add_argument(
        "--cmd",
        "-c",
        type=str,
        help="Execute single command and exit (non-interactive mode)",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"QF_Wiz Agent v{__version__}",
    )
    args = parser.parse_args()

    # Determine ticket path
    ticket_path: Optional[Path] = None

    if args.ticket:
        ticket_path = args.ticket
        if not ticket_path.exists():
            print(f"ERROR: Ticket file not found: {ticket_path}")
            return 1
    else:
        # Non-interactive mode requires ticket path
        if args.cmd:
            print("ERROR: --cmd requires --ticket")
            return 1
        # Interactive selection
        ticket_path = select_ticket_interactive()
        if ticket_path is None:
            return 0

    # Dispatch to appropriate mode
    if args.cmd:
        return run_single_command(ticket_path, args.cmd)
    else:
        return run_agent_loop(ticket_path)


if __name__ == "__main__":
    sys.exit(main())
