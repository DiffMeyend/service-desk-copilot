"""Pytest configuration and shared fixtures for QF_Wiz tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# Ensure scripts directory is in path for imports
TESTS_DIR = Path(__file__).parent
SCRIPTS_DIR = TESTS_DIR.parent
ROOT_DIR = SCRIPTS_DIR.parent
RUNTIME_DIR = ROOT_DIR / "runtime"
FIXTURES_DIR = TESTS_DIR / "fixtures"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ============================================================================
# Path Fixtures
# ============================================================================


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def runtime_dir() -> Path:
    """Return path to runtime directory."""
    return RUNTIME_DIR


@pytest.fixture
def scripts_dir() -> Path:
    """Return path to scripts directory."""
    return SCRIPTS_DIR


@pytest.fixture
def root_dir() -> Path:
    """Return path to project root directory."""
    return ROOT_DIR


# ============================================================================
# Ticket Fixtures
# ============================================================================


@pytest.fixture
def sample_ticket_text(fixtures_dir: Path) -> str:
    """Load a sample ticket text for parsing tests."""
    ticket_file = fixtures_dir / "ticket_with_notes.md"
    if ticket_file.exists():
        return ticket_file.read_text(encoding="utf-8")
    return ""


@pytest.fixture
def quoted_reply_text(fixtures_dir: Path) -> str:
    """Load the quoted reply fixture."""
    reply_file = fixtures_dir / "quoted_reply.md"
    if reply_file.exists():
        return reply_file.read_text(encoding="utf-8")
    return ""


# ============================================================================
# Context Payload Fixtures
# ============================================================================


@pytest.fixture
def empty_cp() -> Dict[str, Any]:
    """Return an empty context payload structure."""
    return {
        "meta": {
            "schema_version": "1.3.1",
            "session_id": "test-session",
        },
        "ticket": {
            "id": "TEST001",
            "priority": "P3",
        },
        "environment": {
            "target_device": {
                "hostname": "",
            },
        },
        "problem": {
            "symptoms": [],
            "impact": {},
        },
        "evidence": {
            "tests_run": [],
            "results": [],
            "observations": [],
        },
        "branches": {
            "active_hypotheses": [],
            "source_pack": [],
        },
        "css": {
            "score": 0,
        },
        "decision": {
            "status": "triage",
        },
    }


@pytest.fixture
def minimal_cp() -> Dict[str, Any]:
    """Return a minimal but valid context payload."""
    return {
        "meta": {
            "schema_version": "1.3.1",
            "session_id": "test-minimal",
        },
        "ticket": {
            "id": "T20250101.001",
            "priority": "P2",
            "summary": "Test ticket for unit tests",
            "requester": {
                "name": "Test User",
                "email": "test@example.com",
            },
        },
        "environment": {
            "target_device": {
                "hostname": "TESTPC01",
                "os": "Windows 11",
            },
        },
        "problem": {
            "symptoms": ["Cannot connect to network"],
            "impact": {
                "work_stopped": True,
            },
        },
        "evidence": {
            "tests_run": ["ping_test"],
            "results": [
                {
                    "command_id": "ping_test",
                    "output": "Request timed out",
                    "captured_at": "2025-01-01T12:00:00Z",
                }
            ],
            "observations": ["Network cable appears connected"],
        },
        "branches": {
            "active_hypotheses": [
                {
                    "id": "dhcp_issue",
                    "hypothesis": "DHCP server not responding",
                    "confidence_hint": 0.7,
                }
            ],
            "source_pack": ["network_general"],
            "current_best_guess": "DHCP server not responding",
        },
        "css": {
            "score": 75,
        },
        "decision": {
            "status": "triage",
        },
    }


# ============================================================================
# Runtime Loader Fixtures
# ============================================================================


@pytest.fixture
def runtime_loader(runtime_dir: Path):
    """Create a RuntimeLoader with test runtime directory."""
    from scripts.agent.runtime_loader import RuntimeLoader

    loader = RuntimeLoader(runtime_dir)
    loader.load_all()
    return loader


# ============================================================================
# Temporary File Fixtures
# ============================================================================


@pytest.fixture
def temp_yaml_file(tmp_path: Path):
    """Factory fixture for creating temporary YAML files."""

    def _create_yaml(content: str, filename: str = "test.yaml") -> Path:
        file_path = tmp_path / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    return _create_yaml


@pytest.fixture
def temp_json_file(tmp_path: Path):
    """Factory fixture for creating temporary JSON files."""

    def _create_json(data: Dict[str, Any], filename: str = "test.json") -> Path:
        file_path = tmp_path / filename
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return file_path

    return _create_json


# ============================================================================
# CSS Calculator Fixtures
# ============================================================================


@pytest.fixture
def basic_css_rules() -> Dict[str, Any]:
    """Return minimal CSS rules for testing."""
    return {
        "version": "1.3.1",
        "target_css": 90,
        "domains": {
            "evidence_strength": {"weight": 35},
            "branch_quality": {"weight": 25},
            "symptom_specificity": {"weight": 20},
            "environment_specificity": {"weight": 20},
        },
        "hard_caps": [],
        "penalties": {},
        "bonuses": [],
    }
