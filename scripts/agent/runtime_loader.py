"""Runtime file loader for QF_Wiz agent.

Loads and caches all runtime YAML/JSON files at startup.
"""

from __future__ import annotations

import functools
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from . import config
from ..core.result import Result, Success, Failure, is_success

# Use centralized exceptions
from ..core.exceptions import RuntimeLoadError

logger = logging.getLogger(__name__)


def _load_yaml_file(path: Path) -> Result[Dict[str, Any]]:
    """Load a YAML file with character sanitization and error handling.

    Returns:
        Success with parsed dict, or Failure with error details.
        This allows callers to distinguish between "file not found",
        "parse error", and "empty file".
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return Failure(f"File not found: {path}", error_type="not_found")
    except PermissionError:
        return Failure(f"Permission denied: {path}", error_type="permission_denied")

    # Sanitize non-printable characters
    safe_text = "".join(
        ch for ch in text
        if (32 <= ord(ch) <= 126) or ch in "\n\r\t" or ord(ch) >= 160
    )
    try:
        data = yaml.safe_load(safe_text)
        if not isinstance(data, dict):
            # Valid YAML but not a dict (could be list, string, None, etc.)
            return Success({})
        return Success(data)
    except yaml.YAMLError as e:
        logger.warning("YAML parse error in %s: %s", path.name, e)
        return Failure(f"YAML parse error in {path.name}: {e}", error_type="parse_error")


def _load_json_file(path: Path) -> Result[Dict[str, Any]]:
    """Load a JSON file, handling BOM and encoding issues.

    Returns:
        Success with parsed dict, or Failure with error details.
        This allows callers to distinguish between "file not found",
        "parse error", and "empty file".
    """
    try:
        # Use utf-8-sig to handle BOM
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
    except FileNotFoundError:
        return Failure(f"File not found: {path}", error_type="not_found")
    except PermissionError:
        return Failure(f"Permission denied: {path}", error_type="permission_denied")

    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return Success({})
        return Success(data)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse error in %s: %s", path.name, e)
        return Failure(f"JSON parse error in {path.name}: {e}", error_type="parse_error")


class RuntimeLoader:
    """Loads and provides access to all QF_Wiz runtime files."""

    def __init__(self, runtime_dir: Optional[Path] = None):
        self.runtime_dir = runtime_dir or config.RUNTIME_DIR
        self._loaded = False
        self._branch_packs: Dict[str, Any] = {}
        self._taxonomy: Dict[str, Any] = {}
        self._css_rules: Dict[str, Any] = {}
        self._workflow: Dict[str, Any] = {}
        self._state_machine: Dict[str, Any] = {}
        self._schema: Dict[str, Any] = {}
        self._template: Dict[str, Any] = {}
        self._ps_diagnostics: Dict[str, Any] = {}
        self._ps_operations: Dict[str, Any] = {}
        self._errors: list[str] = []

    def load_all(self) -> bool:
        """Load all runtime files. Returns True if all critical files loaded."""
        self._errors = []

        # Critical files (must load)
        self._branch_packs = self._load_yaml(config.BRANCH_PACKS_FILE, critical=True)
        self._taxonomy = self._load_yaml(config.TAXONOMY_FILE, critical=True)
        self._css_rules = self._load_yaml(config.CSS_RULES_FILE, critical=True)
        self._schema = self._load_json(config.SCHEMA_FILE, critical=True)
        self._template = self._load_json(config.TEMPLATE_FILE, critical=True)

        # Optional files (nice to have)
        self._workflow = self._load_yaml(config.WORKFLOW_FILE, critical=False)
        self._state_machine = self._load_yaml(config.STATE_MACHINE_FILE, critical=False)
        self._ps_diagnostics = self._load_yaml(config.PS_DIAGNOSTICS_FILE, critical=False)
        self._ps_operations = self._load_yaml(config.PS_OPERATIONS_FILE, critical=False)

        self._loaded = len(self._errors) == 0
        return self._loaded

    def _load_yaml(self, filename: str, critical: bool = True) -> Dict[str, Any]:
        """Load a YAML file from runtime directory."""
        path = self.runtime_dir / filename
        result = _load_yaml_file(path)

        if isinstance(result, Failure):
            if critical:
                self._errors.append(f"Failed to load critical file {filename}: {result.error}")
            else:
                logger.debug("Optional file %s not loaded: %s", filename, result.error)
            return {}

        return result.value

    def _load_json(self, filename: str, critical: bool = True) -> Dict[str, Any]:
        """Load a JSON file from runtime directory."""
        path = self.runtime_dir / filename
        result = _load_json_file(path)

        if isinstance(result, Failure):
            if critical:
                self._errors.append(f"Failed to load critical file {filename}: {result.error}")
            else:
                logger.debug("Optional file %s not loaded: %s", filename, result.error)
            return {}

        return result.value

    @property
    def is_loaded(self) -> bool:
        """Return True if all critical files loaded successfully."""
        return self._loaded

    @property
    def errors(self) -> list[str]:
        """Return list of loading errors."""
        return self._errors.copy()

    def get_branch_packs(self) -> Dict[str, Any]:
        """Return branch packs catalog."""
        return self._branch_packs

    def get_taxonomy_mapping(self) -> Dict[str, Any]:
        """Return taxonomy pack mapping."""
        return self._taxonomy

    def get_css_rules(self) -> Dict[str, Any]:
        """Return CSS scoring rules."""
        return self._css_rules

    def get_workflow(self) -> Dict[str, Any]:
        """Return workflow definition."""
        return self._workflow

    def get_state_machine(self) -> Dict[str, Any]:
        """Return state machine definition."""
        return self._state_machine

    def get_schema(self) -> Dict[str, Any]:
        """Return context payload schema."""
        return self._schema

    def get_template(self) -> Dict[str, Any]:
        """Return context payload template."""
        return self._template

    def get_ps_diagnostics(self) -> Dict[str, Any]:
        """Return PowerShell diagnostics catalog."""
        return self._ps_diagnostics

    def get_ps_operations(self) -> Dict[str, Any]:
        """Return PowerShell operations catalog."""
        return self._ps_operations

    def get_pack_by_id(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """Look up a branch pack by its ID."""
        packs = self._branch_packs.get("packs", [])
        if not isinstance(packs, list):
            return None
        for pack in packs:
            if isinstance(pack, dict) and pack.get("id") == pack_id:
                return pack
        return None

    def get_version(self) -> str:
        """Return the runtime version from loaded files."""
        return self._css_rules.get("version", "unknown")

    def validate_version(self) -> bool:
        """Validate that runtime version matches expected."""
        actual = self.get_version()
        expected = config.RUNTIME_VERSION
        return actual == expected
