"""Tests for IntakeAgent orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

# ============================================================================
# IntakeAgent.ingest() tests
# ============================================================================


class TestIntakeAgentIngest:
    """Test ticket parsing via IntakeAgent."""

    def test_ingest_returns_dict(self, sample_ticket_text: str):
        """ingest() returns a dict with expected top-level keys."""
        if not sample_ticket_text:
            pytest.skip("No sample_ticket_text fixture available")

        from scripts.intake import IntakeAgent

        agent = IntakeAgent()
        cp = agent.ingest(sample_ticket_text)

        assert isinstance(cp, dict)
        assert "ticket" in cp
        assert "environment" in cp
        assert "problem" in cp
        assert "evidence" in cp
        assert "branches" in cp

    def test_ingest_extracts_ticket_id(self, sample_ticket_text: str):
        """ingest() should extract a ticket ID."""
        if not sample_ticket_text:
            pytest.skip("No sample_ticket_text fixture available")

        from scripts.intake import IntakeAgent

        agent = IntakeAgent()
        cp = agent.ingest(sample_ticket_text)

        ticket_id = cp.get("ticket", {}).get("id")
        assert ticket_id is not None
        assert ticket_id != ""

    def test_ingest_includes_branches(self, sample_ticket_text: str):
        """ingest() should populate branches with source_pack routing."""
        if not sample_ticket_text:
            pytest.skip("No sample_ticket_text fixture available")

        from scripts.intake import IntakeAgent

        agent = IntakeAgent()
        cp = agent.ingest(sample_ticket_text)

        branches = cp.get("branches", {})
        assert isinstance(branches, dict)
        # source_pack should be a list (may be empty if no routing match)
        source_pack = branches.get("source_pack", [])
        assert isinstance(source_pack, list)


# ============================================================================
# IntakeAgent.log_resolution() tests
# ============================================================================


class TestIntakeAgentLogResolution:
    """Test resolution logging via IntakeAgent."""

    def test_log_resolution_creates_jsonl(self, tmp_path: Path, minimal_cp: Dict[str, Any]):
        """log_resolution() appends to a JSONL file."""
        from scripts.intake import IntakeAgent

        # Set decision status so the logger has something to extract
        minimal_cp.setdefault("decision", {})["status"] = "DECIDE"
        minimal_cp["decision"]["actual_root_cause"] = "DHCP server not responding"

        agent = IntakeAgent(resolution_log_dir=tmp_path)
        log_file = agent.log_resolution(minimal_cp)

        assert log_file.exists()
        assert log_file.suffix == ".jsonl"

        # Verify the entry is valid JSON
        content = log_file.read_text(encoding="utf-8").strip()
        entry = json.loads(content)
        assert entry["ticket_id"] == "T20250101.001"
        assert entry["actual_root_cause"] == "DHCP server not responding"

    def test_log_resolution_appends(self, tmp_path: Path, minimal_cp: Dict[str, Any]):
        """Multiple log_resolution() calls append to the same monthly file."""
        from scripts.intake import IntakeAgent

        minimal_cp.setdefault("decision", {})["status"] = "DECIDE"
        agent = IntakeAgent(resolution_log_dir=tmp_path)

        agent.log_resolution(minimal_cp)
        agent.log_resolution(minimal_cp)

        # Find the log file
        log_files = list(tmp_path.glob("*.jsonl"))
        assert len(log_files) == 1

        lines = log_files[0].read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2


# ============================================================================
# IntakeAgent.get_alerts() tests
# ============================================================================


class TestIntakeAgentGetAlerts:
    """Test pattern alerts via IntakeAgent."""

    def test_get_alerts_returns_list(self, tmp_path: Path):
        """get_alerts() returns a list of strings (may be empty with no data)."""
        from scripts.intake import IntakeAgent

        agent = IntakeAgent(resolution_log_dir=tmp_path)
        alerts = agent.get_alerts(device="TESTPC01")

        assert isinstance(alerts, list)
        # With no resolution history, should be empty
        assert len(alerts) == 0

    def test_get_alerts_with_no_args(self, tmp_path: Path):
        """get_alerts() works with no device/user."""
        from scripts.intake import IntakeAgent

        agent = IntakeAgent(resolution_log_dir=tmp_path)
        alerts = agent.get_alerts()

        assert isinstance(alerts, list)


# ============================================================================
# IntakeAgent.get_pack_stats() tests
# ============================================================================


class TestIntakeAgentPackStats:
    """Test pack stats via IntakeAgent."""

    def test_get_pack_stats_empty(self, tmp_path: Path):
        """get_pack_stats() returns empty dict when no data."""
        from scripts.intake import IntakeAgent

        agent = IntakeAgent(resolution_log_dir=tmp_path)
        stats = agent.get_pack_stats()

        assert isinstance(stats, dict)
        assert len(stats) == 0


# ============================================================================
# IntakeAgent repr and construction
# ============================================================================


class TestIntakeAgentConstruction:
    """Test IntakeAgent construction and repr."""

    def test_default_construction(self):
        """IntakeAgent() with defaults doesn't raise."""
        from scripts.intake import IntakeAgent

        agent = IntakeAgent()
        assert agent is not None

    def test_repr(self):
        """repr() includes class name and params."""
        from scripts.intake import IntakeAgent

        agent = IntakeAgent()
        r = repr(agent)
        assert "IntakeAgent" in r

    def test_custom_paths(self, tmp_path: Path):
        """IntakeAgent accepts custom resolution_log_dir."""
        from scripts.intake import IntakeAgent

        agent = IntakeAgent(resolution_log_dir=tmp_path)
        assert agent._resolution_log_dir == tmp_path


# ============================================================================
# LLM abstraction tests
# ============================================================================


class TestLLMAbstraction:
    """Test the vendor-agnostic LLM client."""

    def test_protocol_is_runtime_checkable(self):
        """LLMClient Protocol can be checked at runtime."""
        from scripts.core.llm import LLMClient

        # A class implementing complete() should satisfy the protocol
        class MockClient:
            def complete(self, system, messages, **kwargs):
                return "mock response"

        assert isinstance(MockClient(), LLMClient)

    def test_get_client_invalid_provider(self):
        """get_client() raises ValueError for unknown provider."""
        from scripts.core.llm import get_client

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_client(provider="nonexistent")

    def test_provider_registry(self):
        """Both openai and anthropic are registered providers."""
        from scripts.core.llm import _PROVIDERS

        assert "openai" in _PROVIDERS
        assert "anthropic" in _PROVIDERS
