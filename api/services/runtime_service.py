"""Runtime service - loads and provides access to runtime files."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for imports
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from scripts.agent import config as agent_config
from scripts.agent.runtime_loader import RuntimeLoader


class RuntimeService:
    """Singleton service for runtime file access."""

    _instance: Optional["RuntimeService"] = None
    _loader: Optional[RuntimeLoader] = None

    def __new__(cls) -> "RuntimeService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self) -> bool:
        """Initialize the runtime loader. Call once at startup."""
        if self._loader is not None and self._loader.is_loaded:
            return True

        self._loader = RuntimeLoader(agent_config.RUNTIME_DIR)
        return self._loader.load_all()

    @property
    def is_loaded(self) -> bool:
        """Check if runtime files are loaded."""
        return self._loader is not None and self._loader.is_loaded

    @property
    def errors(self) -> List[str]:
        """Get any loading errors."""
        if self._loader is None:
            return ["Runtime loader not initialized"]
        return self._loader.errors

    def get_loader(self) -> RuntimeLoader:
        """Get the runtime loader instance."""
        if self._loader is None:
            raise RuntimeError("Runtime loader not initialized. Call initialize() first.")
        return self._loader

    def get_schema(self) -> Dict[str, Any]:
        """Get the context payload schema."""
        return self.get_loader().get_schema()

    def get_template(self) -> Dict[str, Any]:
        """Get the context payload template."""
        return self.get_loader().get_template()

    def get_css_rules(self) -> Dict[str, Any]:
        """Get CSS scoring rules."""
        return self.get_loader().get_css_rules()

    def get_branch_packs(self) -> Dict[str, Any]:
        """Get all branch packs."""
        return self.get_loader().get_branch_packs()

    def get_pack_by_id(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific branch pack by ID."""
        return self.get_loader().get_pack_by_id(pack_id)

    def get_all_pack_ids(self) -> List[str]:
        """Get list of all pack IDs."""
        packs = self.get_branch_packs().get("packs", [])
        return [p.get("id", "") for p in packs if isinstance(p, dict) and p.get("id")]


# Global singleton instance
runtime_service = RuntimeService()
