"""Tests for RuntimeLoader and file loading utilities."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# Add project root to path for package imports
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.agent.runtime_loader import RuntimeLoader, _load_yaml_file, _load_json_file
from scripts.core.result import Success, Failure, is_success


class TestLoadYamlFile:
    """Tests for _load_yaml_file function."""

    def test_load_valid_yaml(self, temp_yaml_file):
        """Valid YAML file should return Success with dict."""
        yaml_content = """
        key1: value1
        key2:
          nested: value2
        """
        path = temp_yaml_file(yaml_content)
        result = _load_yaml_file(path)

        assert is_success(result)
        assert result.value["key1"] == "value1"
        assert result.value["key2"]["nested"] == "value2"

    def test_load_missing_file(self, tmp_path):
        """Missing file should return Failure with not_found error type."""
        path = tmp_path / "nonexistent.yaml"
        result = _load_yaml_file(path)

        assert isinstance(result, Failure)
        assert result.error_type == "not_found"
        assert "not found" in result.error.lower()

    def test_load_invalid_yaml(self, temp_yaml_file):
        """Invalid YAML should return Failure with parse_error type."""
        yaml_content = "invalid: yaml: content: ["
        path = temp_yaml_file(yaml_content)
        result = _load_yaml_file(path)

        assert isinstance(result, Failure)
        assert result.error_type == "parse_error"

    def test_load_non_dict_yaml(self, temp_yaml_file):
        """YAML that parses to list should return Success with empty dict."""
        yaml_content = "- item1\n- item2\n- item3"
        path = temp_yaml_file(yaml_content)
        result = _load_yaml_file(path)

        assert is_success(result)
        assert result.value == {}

    def test_load_empty_yaml(self, temp_yaml_file):
        """Empty YAML file should return Success with empty dict."""
        path = temp_yaml_file("")
        result = _load_yaml_file(path)

        assert is_success(result)
        assert result.value == {}

    def test_sanitizes_non_printable_characters(self, temp_yaml_file):
        """Non-printable characters should be sanitized before parsing."""
        # Include some control characters that should be stripped
        yaml_content = "key: value\x00\x01\x02"
        path = temp_yaml_file(yaml_content)
        result = _load_yaml_file(path)

        assert is_success(result)
        assert result.value["key"] == "value"


class TestLoadJsonFile:
    """Tests for _load_json_file function."""

    def test_load_valid_json(self, temp_json_file):
        """Valid JSON file should return Success with dict."""
        data = {"key1": "value1", "key2": {"nested": "value2"}}
        path = temp_json_file(data)
        result = _load_json_file(path)

        assert is_success(result)
        assert result.value["key1"] == "value1"
        assert result.value["key2"]["nested"] == "value2"

    def test_load_missing_file(self, tmp_path):
        """Missing file should return Failure with not_found error type."""
        path = tmp_path / "nonexistent.json"
        result = _load_json_file(path)

        assert isinstance(result, Failure)
        assert result.error_type == "not_found"

    def test_load_invalid_json(self, tmp_path):
        """Invalid JSON should return Failure with parse_error type."""
        path = tmp_path / "invalid.json"
        path.write_text("{invalid json", encoding="utf-8")
        result = _load_json_file(path)

        assert isinstance(result, Failure)
        assert result.error_type == "parse_error"

    def test_load_non_dict_json(self, tmp_path):
        """JSON that parses to list should return Success with empty dict."""
        path = tmp_path / "list.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        result = _load_json_file(path)

        assert is_success(result)
        assert result.value == {}


class TestRuntimeLoader:
    """Tests for RuntimeLoader class."""

    def test_init_with_default_dir(self):
        """RuntimeLoader should use default runtime dir if not specified."""
        loader = RuntimeLoader()
        assert loader.runtime_dir is not None

    def test_init_with_custom_dir(self, tmp_path):
        """RuntimeLoader should use custom runtime dir if specified."""
        loader = RuntimeLoader(tmp_path)
        assert loader.runtime_dir == tmp_path

    def test_load_all_returns_bool(self, runtime_dir):
        """load_all should return True if critical files loaded."""
        loader = RuntimeLoader(runtime_dir)
        result = loader.load_all()
        assert isinstance(result, bool)

    def test_is_loaded_property(self, runtime_dir):
        """is_loaded should reflect load_all result."""
        loader = RuntimeLoader(runtime_dir)
        loader.load_all()
        # is_loaded should be True if no critical errors
        assert loader.is_loaded == (len(loader.errors) == 0)

    def test_errors_property_returns_copy(self, runtime_dir):
        """errors property should return a copy of error list."""
        loader = RuntimeLoader(runtime_dir)
        loader.load_all()
        errors1 = loader.errors
        errors2 = loader.errors
        assert errors1 is not errors2  # Should be different objects

    def test_get_pack_by_id_returns_none_for_missing(self, runtime_dir):
        """get_pack_by_id should return None for non-existent pack."""
        loader = RuntimeLoader(runtime_dir)
        loader.load_all()
        result = loader.get_pack_by_id("nonexistent_pack_id")
        assert result is None

    def test_get_pack_by_id_returns_pack_dict(self, runtime_dir):
        """get_pack_by_id should return pack dict for existing pack."""
        loader = RuntimeLoader(runtime_dir)
        loader.load_all()
        # If packs are loaded, try to get one
        packs = loader.get_branch_packs().get("packs", [])
        if packs:
            first_pack_id = packs[0].get("id")
            if first_pack_id:
                result = loader.get_pack_by_id(first_pack_id)
                assert result is not None
                assert result["id"] == first_pack_id

    def test_get_version_returns_string(self, runtime_dir):
        """get_version should return a version string."""
        loader = RuntimeLoader(runtime_dir)
        loader.load_all()
        version = loader.get_version()
        assert isinstance(version, str)

    def test_missing_critical_files_adds_errors(self, tmp_path):
        """Missing critical files should add errors to error list."""
        loader = RuntimeLoader(tmp_path)  # Empty directory
        loader.load_all()
        assert len(loader.errors) > 0
        assert loader.is_loaded is False
