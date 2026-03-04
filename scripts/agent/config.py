"""Configuration constants for the QF_Wiz agent."""

from pathlib import Path

# Root paths
ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "runtime"
TICKETS_READY_DIR = ROOT / "tickets" / "ready"
TICKETS_RESULTS_DIR = ROOT / "tickets" / "results"

# Runtime file names
BRANCH_PACKS_FILE = "branch_packs_catalog_v1_0.yaml"
TAXONOMY_FILE = "taxonomy_pack_mapping.yaml"
CSS_RULES_FILE = "css_scoring.yaml"
WORKFLOW_FILE = "Workflow.yaml"
STATE_MACHINE_FILE = "State_Machine.yaml"
SCHEMA_FILE = "context_payload.schema.json"
TEMPLATE_FILE = "context_payload.template.json"
PS_DIAGNOSTICS_FILE = "powershell_diagnostics_catalog.yaml"
PS_OPERATIONS_FILE = "powershell_operations_catalog.yaml"
ROUTER_FILE = "router.txt"

# Agent constraints (from router.txt)
MAX_ACTIVE_HYPOTHESES = 5
MAX_CLARIFYING_QUESTIONS = 3
CSS_TARGET = 90

# Runtime version
RUNTIME_VERSION = "1.3.1"

# Valid decision statuses (from State_Machine.yaml)
VALID_STATES = [
    "START",
    "INGESTED",
    "TRIAGE",
    "TESTING",
    "CONVERGING",
    "DECIDE",
    "RESOLVED",
    "ESCALATED_TIME",
    "ESCALATED_SKILL",
]
