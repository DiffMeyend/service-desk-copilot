"""Tests for CPManager context payload operations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# Add project root to path for package imports
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.agent.cp_manager import CPManager
from scripts.core.exceptions import CPError


class TestCPManagerBasics:
    """Basic CPManager functionality tests."""

    def test_init_creates_empty_cp(self):
        """CPManager should initialize with empty CP."""
        manager = CPManager()
        assert manager.cp == {}

    def test_load_from_dict(self, minimal_cp):
        """load_from_dict should populate CP."""
        manager = CPManager()
        result = manager.load_from_dict(minimal_cp)

        assert result == minimal_cp
        assert manager.cp["ticket"]["id"] == "T20250101.001"

    def test_load_from_dict_makes_copy(self, minimal_cp):
        """load_from_dict should make a deep copy."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        # Modifying original shouldn't affect manager
        minimal_cp["ticket"]["id"] = "CHANGED"
        assert manager.cp["ticket"]["id"] == "T20250101.001"


class TestCPManagerGetValue:
    """Tests for get_value method."""

    def test_get_simple_path(self, minimal_cp):
        """get_value should return value for simple path."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        assert manager.get_value("ticket.id") == "T20250101.001"

    def test_get_nested_path(self, minimal_cp):
        """get_value should return value for nested path."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        assert manager.get_value("environment.target_device.hostname") == "TESTPC01"

    def test_get_missing_path_returns_none(self, minimal_cp):
        """get_value should return None for missing path."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        assert manager.get_value("nonexistent.path") is None

    def test_get_partial_path_returns_dict(self, minimal_cp):
        """get_value should return dict for partial path."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        result = manager.get_value("ticket.requester")
        assert isinstance(result, dict)
        assert result["name"] == "Test User"


class TestCPManagerSetValue:
    """Tests for set_value method."""

    def test_set_simple_value(self, empty_cp):
        """set_value should set simple value."""
        manager = CPManager()
        manager.load_from_dict(empty_cp)
        manager.set_value("ticket.priority", "P1")

        assert manager.cp["ticket"]["priority"] == "P1"

    def test_set_creates_intermediate_dicts(self, empty_cp):
        """set_value should create intermediate dicts as needed."""
        manager = CPManager()
        manager.load_from_dict(empty_cp)
        manager.set_value("new.nested.deep.value", "test")

        assert manager.cp["new"]["nested"]["deep"]["value"] == "test"

    def test_set_marks_dirty(self, empty_cp):
        """set_value should mark CP as dirty."""
        manager = CPManager()
        manager.load_from_dict(empty_cp)

        assert not manager.is_dirty()
        manager.set_value("ticket.priority", "P1")
        assert manager.is_dirty()


class TestCPManagerAppendValue:
    """Tests for append_value method."""

    def test_append_to_existing_list(self, minimal_cp):
        """append_value should add to existing list."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)
        manager.append_value("evidence.tests_run", "new_test")

        assert "new_test" in manager.cp["evidence"]["tests_run"]

    def test_append_creates_list_if_missing(self, empty_cp):
        """append_value should create list if path doesn't exist."""
        manager = CPManager()
        manager.load_from_dict(empty_cp)
        manager.append_value("new.list", "first_item")

        assert manager.cp["new"]["list"] == ["first_item"]

    def test_append_to_non_list_raises_error(self, minimal_cp):
        """append_value should raise CPError if target is not a list."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        with pytest.raises(CPError):
            manager.append_value("ticket.id", "value")


class TestCPManagerHelperMethods:
    """Tests for helper methods."""

    def test_get_session_id(self, minimal_cp):
        """get_session_id should return session ID."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        assert manager.get_session_id() == "test-minimal"

    def test_get_ticket_id(self, minimal_cp):
        """get_ticket_id should return ticket ID."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        assert manager.get_ticket_id() == "T20250101.001"

    def test_get_hostname(self, minimal_cp):
        """get_hostname should return hostname."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        assert manager.get_hostname() == "TESTPC01"

    def test_get_priority(self, minimal_cp):
        """get_priority should return priority."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        assert manager.get_priority() == "P2"

    def test_get_css_score(self, minimal_cp):
        """get_css_score should return CSS score as int."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        assert manager.get_css_score() == 75
        assert isinstance(manager.get_css_score(), int)

    def test_get_active_hypotheses(self, minimal_cp):
        """get_active_hypotheses should return list."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        hyps = manager.get_active_hypotheses()
        assert isinstance(hyps, list)
        assert len(hyps) == 1
        assert hyps[0]["id"] == "dhcp_issue"

    def test_get_tests_run(self, minimal_cp):
        """get_tests_run should return list."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        tests = manager.get_tests_run()
        assert isinstance(tests, list)
        assert "ping_test" in tests


class TestCPManagerFileOperations:
    """Tests for file load/save operations."""

    def test_load_ticket_from_file(self, temp_json_file, minimal_cp):
        """load_ticket should load CP from file."""
        path = temp_json_file(minimal_cp, "ticket.json")
        manager = CPManager()
        result = manager.load_ticket(path)

        assert result["ticket"]["id"] == "T20250101.001"
        assert not manager.is_dirty()

    def test_load_ticket_missing_file_raises_error(self, tmp_path):
        """load_ticket should raise CPError for missing file."""
        manager = CPManager()

        with pytest.raises(CPError) as exc_info:
            manager.load_ticket(tmp_path / "nonexistent.json")

        assert "not found" in str(exc_info.value).lower()

    def test_load_ticket_invalid_json_raises_error(self, tmp_path):
        """load_ticket should raise CPError for invalid JSON."""
        path = tmp_path / "invalid.json"
        path.write_text("{invalid json", encoding="utf-8")
        manager = CPManager()

        with pytest.raises(CPError) as exc_info:
            manager.load_ticket(path)

        assert "invalid json" in str(exc_info.value).lower()

    def test_save_creates_file(self, tmp_path, minimal_cp):
        """save should create JSON file."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        save_path = tmp_path / "saved.json"
        result_path = manager.save(save_path)

        assert result_path.exists()
        saved_data = json.loads(result_path.read_text())
        assert saved_data["ticket"]["id"] == "T20250101.001"

    def test_save_updates_timestamp(self, tmp_path, minimal_cp):
        """save should update meta.last_updated."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)

        save_path = tmp_path / "saved.json"
        manager.save(save_path)

        assert manager.get_value("meta.last_updated") is not None

    def test_save_clears_dirty_flag(self, tmp_path, minimal_cp):
        """save should clear dirty flag."""
        manager = CPManager()
        manager.load_from_dict(minimal_cp)
        manager.set_value("ticket.priority", "P1")

        assert manager.is_dirty()
        manager.save(tmp_path / "saved.json")
        assert not manager.is_dirty()

    def test_save_without_path_raises_error(self, empty_cp):
        """save without path should raise CPError if no source path."""
        manager = CPManager()
        manager.load_from_dict(empty_cp)

        with pytest.raises(CPError):
            manager.save()
