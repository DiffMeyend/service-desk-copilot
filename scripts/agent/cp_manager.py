"""Context Payload state management for QF_Wiz agent.

Handles loading, modifying, and persisting Context Payload JSON.
"""

from __future__ import annotations

import copy
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import from centralized exceptions module
from ..core.exceptions import CPError

# Re-export for backward compatibility
__all__ = ["CPError", "CPManager"]


class CPManager:
    """Manages in-memory Context Payload state and persistence."""

    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        self._schema = schema or {}
        self._cp: Dict[str, Any] = {}
        self._source_path: Optional[Path] = None
        self._dirty = False
        self._original_hash: Optional[int] = None

    def load_ticket(self, path: Path) -> Dict[str, Any]:
        """Load a Context Payload from a JSON file."""
        if not path.exists():
            raise CPError(f"Ticket file not found: {path}")

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            self._cp = json.loads(text)
        except json.JSONDecodeError as e:
            raise CPError(f"Invalid JSON in {path}: {e}")

        if not isinstance(self._cp, dict):
            raise CPError(f"Expected dict, got {type(self._cp).__name__}")

        self._source_path = path
        self._dirty = False
        self._original_hash = hash(json.dumps(self._cp, sort_keys=True))
        return self._cp

    def load_from_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Load a Context Payload from a dictionary."""
        self._cp = copy.deepcopy(data)
        self._source_path = None
        self._dirty = False
        self._original_hash = hash(json.dumps(self._cp, sort_keys=True))
        return self._cp

    @property
    def cp(self) -> Dict[str, Any]:
        """Return the current Context Payload."""
        return self._cp

    def is_dirty(self) -> bool:
        """Return True if CP has been modified since load/save."""
        return self._dirty

    def get_value(self, json_path: str) -> Any:
        """Get a value by JSON path (e.g., 'environment.target_device.hostname').

        Returns None if path doesn't exist.
        """
        parts = json_path.split(".")
        current = self._cp
        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None
        return current

    def set_value(self, json_path: str, value: Any) -> None:
        """Set a value by JSON path (e.g., 'css.score')."""
        parts = json_path.split(".")
        current = self._cp

        # Navigate to parent, creating dicts as needed
        for part in parts[:-1]:
            if part not in current or not isinstance(current.get(part), dict):
                current[part] = {}
            current = current[part]

        # Set the final value
        current[parts[-1]] = value
        self._dirty = True

    def append_value(self, json_path: str, item: Any) -> None:
        """Append an item to a list at JSON path."""
        current = self.get_value(json_path)
        if current is None:
            # Create the list if it doesn't exist
            self.set_value(json_path, [item])
        elif isinstance(current, list):
            current.append(item)
            self._dirty = True
        else:
            raise CPError(f"Cannot append to non-list at {json_path}")

    def extend_value(self, json_path: str, items: List[Any]) -> None:
        """Extend a list at JSON path with multiple items."""
        for item in items:
            self.append_value(json_path, item)

    def update_timestamp(self) -> None:
        """Update meta.last_updated with current UTC timestamp."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.set_value("meta.last_updated", now)

    def save(self, path: Optional[Path] = None) -> Path:
        """Save the Context Payload to disk.

        Uses atomic write (temp file + rename) to prevent corruption.
        Updates meta.last_updated before saving.
        """
        save_path = path or self._source_path
        if save_path is None:
            raise CPError("No save path specified and no source path available")

        # Update timestamp
        self.update_timestamp()

        # Write to temp file then rename (atomic)
        save_path = Path(save_path)
        temp_fd = None
        try:
            temp_fd = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                dir=save_path.parent,
                delete=False,
                encoding="utf-8",
            )
            json.dump(self._cp, temp_fd, indent=2, ensure_ascii=False)
            temp_fd.close()
            Path(temp_fd.name).replace(save_path)
        except Exception as e:
            if temp_fd:
                Path(temp_fd.name).unlink(missing_ok=True)
            raise CPError(f"Failed to save: {e}")

        self._source_path = save_path
        self._dirty = False
        self._original_hash = hash(json.dumps(self._cp, sort_keys=True))
        return save_path

    def get_session_id(self) -> str:
        """Return the session ID from meta."""
        return self.get_value("meta.session_id") or ""

    def get_ticket_id(self) -> str:
        """Return the ticket ID."""
        return self.get_value("ticket.id") or ""

    def get_current_state(self) -> str:
        """Return the current decision status."""
        return self.get_value("decision.status") or "triage"

    def get_hostname(self) -> str:
        """Return the target device hostname."""
        return self.get_value("environment.target_device.hostname") or ""

    def get_priority(self) -> str:
        """Return the ticket priority."""
        return self.get_value("ticket.priority") or "UNKNOWN"

    def get_css_score(self) -> int:
        """Return the current CSS score."""
        score = self.get_value("css.score")
        return int(score) if score is not None else 0

    def get_active_hypotheses(self) -> List[Dict[str, Any]]:
        """Return the list of active hypotheses."""
        hyps = self.get_value("branches.active_hypotheses")
        return hyps if isinstance(hyps, list) else []

    def get_tests_run(self) -> List[str]:
        """Return the list of tests run."""
        tests = self.get_value("evidence.tests_run")
        return tests if isinstance(tests, list) else []

    def get_source_pack(self) -> List[str]:
        """Return the source pack IDs."""
        packs = self.get_value("branches.source_pack")
        return packs if isinstance(packs, list) else []
