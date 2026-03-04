"""Tests for CSS (Context Sufficiency Score) calculator."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pytest

ROOT = Path(__file__).resolve().parents[2]
# Add project root to path for package imports
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.agent.css_calculator import (
    CSSCalculator,
    _is_empty,
    _is_not_empty,
    _len_eq,
    _len_gt,
    _get_nested,
    _evaluate_condition,
)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_is_empty_none(self):
        """None should be empty."""
        assert _is_empty(None) is True

    def test_is_empty_empty_string(self):
        """Empty string should be empty."""
        assert _is_empty("") is True
        assert _is_empty("   ") is True

    def test_is_empty_empty_list(self):
        """Empty list should be empty."""
        assert _is_empty([]) is True

    def test_is_empty_non_empty(self):
        """Non-empty values should not be empty."""
        assert _is_empty("value") is False
        assert _is_empty(["item"]) is False
        assert _is_empty(0) is False  # 0 is not empty
        assert _is_empty(False) is False  # False is not empty

    def test_is_not_empty(self):
        """is_not_empty should be inverse of is_empty."""
        assert _is_not_empty("value") is True
        assert _is_not_empty(None) is False

    def test_len_eq(self):
        """len_eq should compare lengths."""
        assert _len_eq([1, 2, 3], 3) is True
        assert _len_eq([1, 2], 3) is False
        assert _len_eq("abc", 3) is True
        assert _len_eq(123, 3) is False  # Non-sequence

    def test_len_gt(self):
        """len_gt should compare lengths."""
        assert _len_gt([1, 2, 3], 2) is True
        assert _len_gt([1, 2], 2) is False
        assert _len_gt("abc", 2) is True


class TestGetNested:
    """Tests for _get_nested function."""

    def test_simple_path(self):
        """Should get value from simple path."""
        data = {"key": "value"}
        assert _get_nested(data, "key") == "value"

    def test_nested_path(self):
        """Should get value from nested path."""
        data = {"level1": {"level2": {"level3": "value"}}}
        assert _get_nested(data, "level1.level2.level3") == "value"

    def test_missing_path_returns_none(self):
        """Should return None for missing path."""
        data = {"key": "value"}
        assert _get_nested(data, "missing") is None
        assert _get_nested(data, "missing.nested") is None

    def test_partial_path_returns_dict(self):
        """Should return dict for partial path."""
        data = {"level1": {"level2": "value"}}
        result = _get_nested(data, "level1")
        assert isinstance(result, dict)
        assert result["level2"] == "value"


class TestEvaluateCondition:
    """Tests for _evaluate_condition function."""

    def test_empty_condition(self):
        """Empty condition with path/op."""
        cp = {"field": ""}
        assert _evaluate_condition({"path": "field", "op": "empty"}, cp) is True
        assert _evaluate_condition({"path": "field", "op": "not_empty"}, cp) is False

    def test_any_condition(self):
        """OR logic with 'any'."""
        cp = {"a": "", "b": "value"}
        condition = {
            "any": [
                {"path": "a", "op": "not_empty"},
                {"path": "b", "op": "not_empty"},
            ]
        }
        assert _evaluate_condition(condition, cp) is True

    def test_all_condition(self):
        """AND logic with 'all'."""
        cp = {"a": "value", "b": "value"}
        condition = {
            "all": [
                {"path": "a", "op": "not_empty"},
                {"path": "b", "op": "not_empty"},
            ]
        }
        assert _evaluate_condition(condition, cp) is True

        cp_partial = {"a": "value", "b": ""}
        assert _evaluate_condition(condition, cp_partial) is False


class TestCSSCalculator:
    """Tests for CSSCalculator class."""

    def test_init_with_rules(self, basic_css_rules):
        """Should initialize with rules."""
        calc = CSSCalculator(basic_css_rules)
        assert calc.target == 90

    def test_calculate_returns_tuple(self, basic_css_rules, empty_cp):
        """calculate should return (score, blockers) tuple."""
        calc = CSSCalculator(basic_css_rules)
        result = calc.calculate(empty_cp)

        assert isinstance(result, tuple)
        assert len(result) == 2
        score, blockers = result
        assert isinstance(score, int)
        assert isinstance(blockers, list)

    def test_empty_cp_scores_zero(self, basic_css_rules, empty_cp):
        """Empty CP should score 0."""
        calc = CSSCalculator(basic_css_rules)
        score, _ = calc.calculate(empty_cp)
        assert score == 0

    def test_score_clamped_to_100(self, basic_css_rules):
        """Score should never exceed 100."""
        # Create rules that would give > 100 points
        rules = basic_css_rules.copy()
        rules["bonuses"] = [{"condition": {"path": "always", "op": "empty"}, "points": 200}]

        calc = CSSCalculator(rules)
        cp = {"always": None}  # Will trigger bonus
        score, _ = calc.calculate(cp)
        assert score <= 100

    def test_score_clamped_to_zero(self, basic_css_rules):
        """Score should never go below 0."""
        rules = basic_css_rules.copy()
        rules["penalties"] = {
            "test_penalty": {
                "default": 1000,  # Huge penalty
            }
        }

        calc = CSSCalculator(rules)
        score, _ = calc.calculate({})
        assert score >= 0

    def test_evidence_increases_score(self, basic_css_rules):
        """Adding evidence should increase score."""
        calc = CSSCalculator(basic_css_rules)

        cp_empty = {"evidence": {"tests_run": [], "results": []}}
        score_empty, _ = calc.calculate(cp_empty)

        cp_with_evidence = {
            "evidence": {
                "tests_run": ["test1", "test2"],
                "results": [{"id": "r1"}, {"id": "r2"}],
            }
        }
        score_with_evidence, _ = calc.calculate(cp_with_evidence)

        assert score_with_evidence > score_empty

    def test_hard_cap_limits_score(self):
        """Hard cap should limit score."""
        rules = {
            "target_css": 90,
            "domains": {"evidence_strength": {"weight": 100}},
            "hard_caps": [
                {
                    "condition": {"path": "hostname", "op": "empty"},
                    "cap": 50,
                    "reason": "No hostname",
                }
            ],
            "penalties": {},
            "bonuses": [],
        }
        calc = CSSCalculator(rules)

        # CP that would score high but has empty hostname
        cp = {
            "hostname": "",
            "evidence": {
                "tests_run": ["t1", "t2"],
                "results": [{"id": "r1"}, {"id": "r2"}],
            },
        }
        score, blockers = calc.calculate(cp)

        assert score <= 50
        assert "No hostname" in blockers

    def test_target_property(self, basic_css_rules):
        """target property should return target CSS."""
        calc = CSSCalculator(basic_css_rules)
        assert calc.target == 90

    def test_get_missing_for_90(self, basic_css_rules):
        """get_missing_for_90 should return missing requirements."""
        rules = basic_css_rules.copy()
        rules["required_evidence_for_css_ge_90"] = {
            "must_have": [
                "ticket.priority (not UNKNOWN)",
                "evidence.tests_run (>=1)",
            ]
        }
        calc = CSSCalculator(rules)

        cp = {"ticket": {"priority": "UNKNOWN"}, "evidence": {"tests_run": []}}
        missing = calc.get_missing_for_90(cp)

        assert len(missing) == 2


class TestCSSCalculatorWithRealRules:
    """Tests using actual runtime CSS rules (integration tests)."""

    @pytest.mark.integration
    def test_with_runtime_rules(self, runtime_loader, minimal_cp):
        """Test calculator with actual runtime CSS rules."""
        if not runtime_loader.is_loaded:
            pytest.skip("Runtime files not available")

        rules = runtime_loader.get_css_rules()
        if not rules:
            pytest.skip("CSS rules not loaded")

        calc = CSSCalculator(rules)
        score, blockers = calc.calculate(minimal_cp)

        # Basic sanity checks
        assert 0 <= score <= 100
        assert isinstance(blockers, list)
