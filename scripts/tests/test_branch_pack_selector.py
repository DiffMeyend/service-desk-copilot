#!/usr/bin/env python3
"""Regression tests for branch pack selection.

Verifies that specific ticket content triggers the expected branch packs,
preventing silent regressions when the catalog or matching logic changes.

Can be run:
- As pytest: pytest scripts/tests/test_branch_pack_selector.py -v
- Standalone: python scripts/tests/test_branch_pack_selector.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from parsing.branch_pack_selector import select_branch_pack_seed


# ============================================================================
# Test Data
# ============================================================================

# Test cases as pytest params: (test_id, summary, body, expected_pack_ids)
BRANCH_PACK_TEST_CASES = [
    # Network packs
    pytest.param(
        "dhcp_ip_conflict",
        "Workstation showing APIPA address 169.254.x.x",
        "User reports no network connectivity. ipconfig shows 169.254.100.50. "
        "DHCP server may be unreachable or lease expired.",
        ["dhcp_ip_conflict"],
        id="dhcp_ip_conflict",
    ),
    pytest.param(
        "vpn_client",
        "VPN disconnects every 30 minutes",
        "User on AnyConnect VPN. Connection drops after exactly 30 minutes. "
        "Split tunnel is enabled. Need to check idle timeout settings.",
        ["vpn_client"],
        id="vpn_client",
    ),
    pytest.param(
        "dns_proxy_tls",
        "Cannot resolve external DNS names",
        "DNS queries for external domains fail. nslookup times out. "
        "Internal DNS works. Possible proxy or Schannel issue.",
        ["dns_proxy_tls"],
        id="dns_proxy_tls",
    ),
    # Identity packs
    pytest.param(
        "m365_mfa_method",
        "User not receiving MFA prompt on new device",
        "Authenticator app not prompting. User registered methods show phone only. "
        "Need to verify MFA registration and Conditional Access.",
        ["m365_mfa_method"],
        id="m365_mfa_method",
    ),
    pytest.param(
        "m365_conditional_access",
        "Sign-in blocked by Conditional Access policy",
        "Error AADSTS50158 when signing in from home network. "
        "Device shows compliant in Intune. Need to check CA policies.",
        ["m365_conditional_access"],
        id="m365_conditional_access",
    ),
    pytest.param(
        "ad_auth_dc",
        "Trust relationship with domain controller failed",
        "User cannot log in with domain credentials. LSASS errors in event log. "
        "Netlogon service shows domain controller unreachable.",
        ["ad_auth_dc"],
        id="ad_auth_dc",
    ),
    # M365/Messaging packs
    pytest.param(
        "exchange_autodiscover",
        "Outlook cannot connect to Exchange",
        "Outlook keeps prompting for password. Autodiscover test fails. "
        "OWA works fine. Need to check profile and autodiscover DNS.",
        ["exchange_autodiscover"],
        id="exchange_autodiscover",
    ),
    pytest.param(
        "shared_mailbox_permissions",
        "Cannot send as shared mailbox",
        "User has Full Access but SendAs permissions missing on shared mailbox. "
        "Need to verify Exchange permissions.",
        ["shared_mailbox_permissions"],
        id="shared_mailbox_permissions",
    ),
    # Endpoint packs
    pytest.param(
        "disk_io_pressure",
        "System running extremely slow with disk at 100%",
        "Task Manager shows disk at 100%. Low disk space warning. "
        "NTFS errors in event log. storahci warnings present.",
        ["disk_io_pressure"],
        id="disk_io_pressure",
    ),
    pytest.param(
        "print_subsystem",
        "Printer queue stuck and spooler crashing",
        "Print spooler service keeps stopping. Queue shows pending jobs. "
        "Point and Print driver installation failed.",
        ["print_subsystem"],
        id="print_subsystem",
    ),
    # Cross-cutting packs
    pytest.param(
        "recent_change",
        "Application broken after Windows update",
        "Issue started after Patch Tuesday. Recent change in Office build. "
        "Regression from previous working state.",
        ["recent_change"],
        id="recent_change",
    ),
    pytest.param(
        "only_this_user",
        "Only this user experiencing the issue",
        "Tested with another user on same machine - works fine. "
        "License assignment looks correct. User-specific profile issue.",
        ["only_this_user"],
        id="only_this_user",
    ),
    # Combined: primary + cross-cutting
    pytest.param(
        "vpn_plus_recent_change",
        "VPN stopped working after Windows update",
        "AnyConnect VPN was working until Patch Tuesday. Recent change broke it. "
        "Split tunnel configuration unchanged.",
        ["vpn_client", "recent_change"],
        id="vpn_plus_recent_change",
    ),
]


# ============================================================================
# Pytest Test Class
# ============================================================================


class TestBranchPackSelector:
    """Tests for branch pack selection logic."""

    @pytest.mark.parametrize("test_id,summary,body,expected_packs", BRANCH_PACK_TEST_CASES)
    def test_pack_selection(
        self, test_id: str, summary: str, body: str, expected_packs: List[str]
    ):
        """Verify correct pack selection for given ticket content."""
        result = select_branch_pack_seed(summary, body)
        actual_packs = result.get("pack_ids", [])

        # Check that all expected packs are present
        missing = [p for p in expected_packs if p not in actual_packs]
        assert not missing, (
            f"Test '{test_id}' failed.\n"
            f"Expected packs: {expected_packs}\n"
            f"Actual packs: {actual_packs}\n"
            f"Missing: {missing}"
        )

    def test_empty_input_returns_empty_packs(self):
        """Verify empty input doesn't crash and returns empty or minimal packs."""
        result = select_branch_pack_seed("", "")
        assert "pack_ids" in result
        assert isinstance(result["pack_ids"], list)

    def test_routing_method_returned(self):
        """Verify routing_method is always present in result."""
        result = select_branch_pack_seed("test summary", "test body content")
        assert "routing_method" in result
        assert result["routing_method"] in ("keyword", "taxonomy", "manual_override")

    def test_hypotheses_returned(self):
        """Verify hypotheses list is always present."""
        result = select_branch_pack_seed(
            "VPN disconnects", "AnyConnect VPN connection drops"
        )
        assert "hypotheses" in result
        assert isinstance(result["hypotheses"], list)

    def test_hypotheses_limited_to_max(self):
        """Verify hypotheses are limited to MAX_ACTIVE_HYPOTHESES (5)."""
        result = select_branch_pack_seed(
            "Multiple issues with VPN, DNS, DHCP, and printing",
            "VPN drops, DNS fails, DHCP issues, printer problems, disk slow",
        )
        assert len(result.get("hypotheses", [])) <= 5

    def test_routing_metadata_present(self):
        """Verify routing_metadata is present for debugging."""
        result = select_branch_pack_seed(
            "Network issue",
            "Cannot connect to network",
        )
        assert "routing_metadata" in result


# ============================================================================
# Standalone Execution (backward compatibility)
# ============================================================================

# Original test cases format for standalone execution
TEST_CASES: List[Tuple[str, str, str, List[str]]] = [
    (
        "dhcp_ip_conflict",
        "Workstation showing APIPA address 169.254.x.x",
        "User reports no network connectivity. ipconfig shows 169.254.100.50. "
        "DHCP server may be unreachable or lease expired.",
        ["dhcp_ip_conflict"],
    ),
    (
        "vpn_client",
        "VPN disconnects every 30 minutes",
        "User on AnyConnect VPN. Connection drops after exactly 30 minutes. "
        "Split tunnel is enabled. Need to check idle timeout settings.",
        ["vpn_client"],
    ),
    (
        "dns_proxy_tls",
        "Cannot resolve external DNS names",
        "DNS queries for external domains fail. nslookup times out. "
        "Internal DNS works. Possible proxy or Schannel issue.",
        ["dns_proxy_tls"],
    ),
    (
        "m365_mfa_method",
        "User not receiving MFA prompt on new device",
        "Authenticator app not prompting. User registered methods show phone only. "
        "Need to verify MFA registration and Conditional Access.",
        ["m365_mfa_method"],
    ),
    (
        "m365_conditional_access",
        "Sign-in blocked by Conditional Access policy",
        "Error AADSTS50158 when signing in from home network. "
        "Device shows compliant in Intune. Need to check CA policies.",
        ["m365_conditional_access"],
    ),
    (
        "ad_auth_dc",
        "Trust relationship with domain controller failed",
        "User cannot log in with domain credentials. LSASS errors in event log. "
        "Netlogon service shows domain controller unreachable.",
        ["ad_auth_dc"],
    ),
    (
        "exchange_autodiscover",
        "Outlook cannot connect to Exchange",
        "Outlook keeps prompting for password. Autodiscover test fails. "
        "OWA works fine. Need to check profile and autodiscover DNS.",
        ["exchange_autodiscover"],
    ),
    (
        "shared_mailbox_permissions",
        "Cannot send as shared mailbox",
        "User has Full Access but SendAs permissions missing on shared mailbox. "
        "Need to verify Exchange permissions.",
        ["shared_mailbox_permissions"],
    ),
    (
        "disk_io_pressure",
        "System running extremely slow with disk at 100%",
        "Task Manager shows disk at 100%. Low disk space warning. "
        "NTFS errors in event log. storahci warnings present.",
        ["disk_io_pressure"],
    ),
    (
        "print_subsystem",
        "Printer queue stuck and spooler crashing",
        "Print spooler service keeps stopping. Queue shows pending jobs. "
        "Point and Print driver installation failed.",
        ["print_subsystem"],
    ),
    (
        "recent_change",
        "Application broken after Windows update",
        "Issue started after Patch Tuesday. Recent change in Office build. "
        "Regression from previous working state.",
        ["recent_change"],
    ),
    (
        "only_this_user",
        "Only this user experiencing the issue",
        "Tested with another user on same machine - works fine. "
        "License assignment looks correct. User-specific profile issue.",
        ["only_this_user"],
    ),
    (
        "vpn_plus_recent_change",
        "VPN stopped working after Windows update",
        "AnyConnect VPN was working until Patch Tuesday. Recent change broke it. "
        "Split tunnel configuration unchanged.",
        ["vpn_client", "recent_change"],
    ),
]


def run_tests() -> Tuple[int, int, List[str]]:
    """Run all test cases and return (passed, failed, failure_messages)."""
    passed = 0
    failed = 0
    failures: List[str] = []

    for name, summary, body, expected_packs in TEST_CASES:
        result = select_branch_pack_seed(summary, body)
        actual_packs = result.get("pack_ids", [])

        # Check that all expected packs are present
        missing = [p for p in expected_packs if p not in actual_packs]

        if missing:
            failed += 1
            failures.append(
                f"FAIL: {name}\n"
                f"  Expected: {expected_packs}\n"
                f"  Actual:   {actual_packs}\n"
                f"  Missing:  {missing}"
            )
        else:
            passed += 1
            print(f"PASS: {name} -> {actual_packs}")

    return passed, failed, failures


def main() -> int:
    print("=" * 60)
    print("Branch Pack Selector Regression Tests")
    print("=" * 60)
    print()

    passed, failed, failures = run_tests()

    print()
    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    if failures:
        print()
        print("Failures:")
        for msg in failures:
            print(msg)
            print()
        return 1

    print("All tests passed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
