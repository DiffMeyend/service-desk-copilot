"""Agent 2 -- Intake & Audit.

Public API for ticket parsing, pack routing, resolution logging, and analytics.
Re-exports from existing modules to provide a clean facade.
"""

import sys
from pathlib import Path

# parse_ticket.py uses `from parsing.branch_pack_selector import ...` which
# requires scripts/ on sys.path. Ensure it's available for all import contexts.
_scripts_dir = str(Path(__file__).resolve().parents[1])
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from scripts.analytics.confidence_updater import ConfidenceUpdater
from scripts.analytics.pack_metrics import PackMetrics
from scripts.analytics.pattern_detector import PatternDetector
from scripts.analytics.resolution_logger import ResolutionLogger
from scripts.parsing.branch_pack_selector import select_branch_pack_seed
from scripts.parsing.parse_ticket import build_payload, load_ticket_text

from .agent import IntakeAgent

__all__ = [
    "IntakeAgent",
    "build_payload",
    "load_ticket_text",
    "select_branch_pack_seed",
    "ResolutionLogger",
    "ConfidenceUpdater",
    "PatternDetector",
    "PackMetrics",
]
