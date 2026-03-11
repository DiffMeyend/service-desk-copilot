#!/usr/bin/env python3
"""Parse raw PSA ticket text into the QF_Wiz context payload schema."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if __package__ in (None, ""):
    # Allow running the parser directly via `python scripts/parsing/parse_ticket_sanitize.py`
    SCRIPT_DIR = Path(__file__).resolve().parent
    SCRIPTS_ROOT = SCRIPT_DIR.parent
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))

from parsing.branch_pack_selector import select_branch_pack_seed
from parsing.text_sanitize import sanitize_description

RE_TICKET_ID = re.compile(r"(T\d{8}\.\d+)")
RE_EMAIL = re.compile(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", re.I)
RE_PHONE = re.compile(r"(\+?\d[\d\s().\-]{6,}\d)")
RE_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
RE_IPV6 = re.compile(r"\b([0-9a-f]{1,4}:){2,7}[0-9a-f]{1,4}\b", re.I)
RE_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
RE_CREDIT_CARD = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
RE_INLINE_FIELD = re.compile(r"^[^:]+:\s*.+$")
RE_ERROR_CODE = re.compile(r"error(?:\s+code)?\s*([A-Z0-9\-]*\d[A-Z0-9\-]*)", re.I)
RE_INLINE_KEYVALUE = re.compile(r"([A-Za-z0-9][A-Za-z0-9 _/().-]{1,40})\s*[:=]")
RE_MANUAL_OVERRIDE = re.compile(r"LOAD[_\s-]*BRANCH[_\s-]*PACK\s*:?\s*([A-Za-z0-9_.-]+)", re.I)

INLINE_STOP_PHRASES = (
    "attachment |",
    "ticket note |",
    "file name / url",
    "requestor",
    "requester",
    "description",
    "smart ticket summary",
    "timeline",
    "hash",
    "process path",
)

KNOWN_KV_KEYS = {
    "requester",
    "requester name",
    "requestor",
    "requestor name",
    "contact",
    "contact name",
    "name",
    "email",
    "email address",
    "contact email",
    "requester email",
    "requestor email",
    "phone",
    "phone number",
    "contact phone",
    "mobile",
    "mobile phone",
    "company",
    "account",
    "account name",
    "client",
    "customer",
    "organization",
    "company info",
    "site",
    "location",
    "site/location",
    "location details",
    "location information",
    "site details",
    "address",
    "site info",
    "office",
    "office location",
    "physical location",
    "created",
    "created date",
    "date created",
    "opened",
    "opened date",
    "report date",
    "time stamp",
    "ticket category",
    "category",
    "issue type",
    "issue category",
    "ticket type",
    "service",
    "service type",
    "service level",
    "service category",
    "work type",
    "priority",
    "urgency",
    "severity",
    "impact",
    "impact level",
    "host name",
    "hostname",
    "computer name",
    "device name",
    "machine name",
    "operating system",
    "os name",
    "os version",
    "internal ip",
    "private network address",
    "ipv4 address",
    "ip address",
    "external ip",
    "public ip",
    "network address",
    "internet ip",
    "wan ip",
    "serial",
    "serial number",
    "system serial number",
    "asset tag",
    "asset",
    "asset id",
    "asset reference name",
    "user name",
    "username",
    "logged on user",
    "last user",
    "domain",
    "logon domain",
}

SYSTEMINFO_PATTERNS = {
    "hostname": [
        r"\bHost\s*Name\s*(?:\.|\s)*:\s*([A-Za-z0-9._-]+)",
        r"\bComputer\s*Name\s*(?:\.|\s)*:\s*([A-Za-z0-9._-]+)",
        r"\bDevice\s*Name\s*(?:\.|\s)*:\s*([A-Za-z0-9._-]+)",
    ],
    "username": [
        r"\bUser(?:\s*Name)?\s*(?:\.|\s)*:\s*([A-Za-z0-9._\\-]+)",
        r"\bLogged\s*On\s*User\s*(?:\.|\s)*:\s*([A-Za-z0-9._\\-]+)",
    ],
    "os": [
        r"\bOS\s*Name\s*(?:\.|\s)*:\s*([^\r\n|]+)",
        r"\bOperating\s*System\s*(?:\.|\s)*:\s*([^\r\n|]+)",
        r"\bOS\s*Version\s*(?:\.|\s)*:\s*([^\r\n|]+)",
    ],
    "serial": [
        r"\bSystem\s*Serial\s*Number\s*(?:\.|\s)*:\s*([A-Za-z0-9._-]+)",
        r"\bSerial\s*Number\s*(?:\.|\s)*:\s*([A-Za-z0-9._-]+)",
    ],
    "asset_tag": [
        r"\bAsset\s*(?:Tag|ID|Number)\s*(?:\.|\s)*:\s*([A-Za-z0-9._-]+)",
    ],
    "internal_ip": [
        r"IPv4\s*Address[^\w]*:\s*([0-9.]+)",
        r"\bIP\s*Address[^\w]*:\s*([0-9.]+)",
        r"Wireless\s*LAN\s*adapter[^\n]+IPv4\s*Address[^\w]*:\s*([0-9.]+)",
    ],
    "external_ip": [
        r"\bPublic\s*IP[^\w]*:\s*([0-9.]+)",
        r"\bWAN\s*IP[^\w]*:\s*([0-9.]+)",
    ],
}

USER_PATTERNS = {
    "username": [
        r"\bLogged\s+(?:in|on)\s+User[^\w]*:\s*([A-Za-z0-9._\\-]+)",
        r"\bCurrent\s+User[^\w]*:\s*([A-Za-z0-9._\\-]+)",
        r"\bLast\s+Logged\s+On[^\w]*:\s*([A-Za-z0-9._\\-]+)",
    ],
    "domain": [
        r"\bLogon\s*Domain[^\w]*:\s*([A-Za-z0-9._-]+)",
        r"\bDomain[^\w]*:\s*([A-Za-z0-9._-]+)",
    ],
}

SENSITIVE_PATTERNS = [
    re.compile(r"BitLocker\s*Key[^\s]*\s*[0-9\-]{10,}", re.I),
    re.compile(r"BitLocker\s*Key[^\n]*", re.I),
    re.compile(r"LocalAdmin\s*PW:[^\s]+", re.I),
    re.compile(r"localadmin", re.I),
]

PII_PATTERNS = [
    RE_EMAIL,
    RE_PHONE,
    RE_IPV4,
    RE_IPV6,
    RE_SSN,
    RE_CREDIT_CARD,
]

INLINE_LABELS = [
    "your name",
    "your email",
    "your phone number",
    "how urgent is your request?",
    "who is impacted?",
    "how is the business impacted?",
]

SECTION_BREAKS = {
    "time stamp",
    "paste_ticket",
    "general information",
    "company",
    "location",
    "contact",
    "created",
    "last activity",
    "report date",
    "ticket type",
    "ticket category",
    "associated problem",
    "total billable hours",
    "total hours worked",
    "description",
    "smart ticket summary",
    "timeline",
    "first response target",
    "resolution plan target",
    "resolution target",
    "first response actual",
    "resolution plan actual",
    "resolution actual",
    "resolution",
    "tags",
    "potentially impacted assets",
    "details",
    "general",
    "status",
    "priority",
    "ticket information",
    "issue type",
    "sub-issue type",
    "work type",
    "source",
    "due date",
    "estimated hours",
    "assignment",
    "queue",
    "primary resource (role)",
    "secondary resources (role)",
    "contract & billing",
    "line of business",
    "contract",
    "service level agreement",
    "other contacts",
    "additional contacts",
    "related",
    "asset",
    "asset reference name",
    "asset serial number",
    "project",
    "opportunity",
    "purchase order number",
    "additional assets",
    "user-defined fields",
    "my change request approval status",
    "change request approval status",
    "sla paused - next sla event (hours)",
    "request type",
    "co-managed visibility",
    "activity",
    "charges & expenses",
    "service calls & to-dos",
    "changes",
    "configuration item",
    "problems",
    "incidents",
    "change information",
    "impact analysis",
    "implementation plan",
    "roll out plan",
    "back out plan",
    "review notes",
    "change approvals",
    "approval status",
}


SECTION_ALIASES = {
    "contact": [
        "contact info",
        "contact information",
        "contact details",
        "requester",
        "requestor",
        "requester info",
        "requestor info",
        "caller",
        "user",
        "end user",
    ],
    "location": [
        "site",
        "site/location",
        "location details",
        "location information",
        "site details",
        "address",
        "office",
        "site info",
        "office location",
        "physical location",
    ],
    "company": [
        "account",
        "account name",
        "client",
        "customer",
        "organization",
        "company info",
    ],
    "description": [
        "issue description",
        "problem description",
        "details",
        "ticket summary",
        "summary",
        "issue details",
        "problem details",
        "smart ticket summary",
    ],
    "created": [
        "created date",
        "date created",
        "opened",
        "opened date",
        "report date",
    ],
    "last activity": [
        "last updated",
        "last update",
        "updated",
        "updated date",
        "activity",
    ],
    "ticket category": [
        "category",
        "issue category",
        "ticket class",
    ],
    "work type": [
        "service",
        "service type",
        "service level",
        "service category",
    ],
    "priority": [
        "urgency",
        "severity",
        "impact",
        "impact level",
    ],
    "asset": [
        "asset information",
        "configuration item",
        "ci",
        "device",
        "device info",
        "device information",
    ],
    "status": [
        "state",
        "ticket status",
    ],
    "ticket information": [
        "ticket info",
        "ticket details",
        "ticket metadata",
    ],
    "issue type": [
        "issue classification",
        "issue",
    ],
    "sub-issue type": [
        "sub issue type",
        "sub issue",
    ],
    "timeline": [
        "history",
        "activity log",
    ],
}

SECTION_ALIAS_LOOKUP = {alias: canonical for canonical, aliases in SECTION_ALIASES.items() for alias in aliases}
DESCRIPTION_STOPS = SECTION_BREAKS.union(
    {
        "**created via incoming email processor**",
        "**created via email with message-id",
        "attachment |",
        "ticket note |",
    }
)


REPLY_CUTOFF_PATTERNS = [
    re.compile(r"^>+\s*On .+wrote:?", re.I),
    re.compile(r"^On .+wrote:?", re.I),
    re.compile(r"^-{2,}\s*original message\s*-{2,}", re.I),
    re.compile(r"^Begin forwarded message", re.I),
    re.compile(r"^From:\s", re.I),
    re.compile(r"^Sent:\s", re.I),
    re.compile(r"^To:\s", re.I),
    re.compile(r"^Subject:\s", re.I),
]


def is_reply_marker(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith(">"):
        return True
    for pattern in REPLY_CUTOFF_PATTERNS:
        if pattern.match(stripped):
            return True
    return False


def scrub_text(text: str) -> str:
    if not text:
        return text

    # Protect ticket IDs from being redacted by broad PII patterns (e.g., phone regex).
    placeholders = {}

    def _hold_ticket_id(match: re.Match[str]) -> str:
        key = f"__TICKETID_{len(placeholders)}__"
        placeholders[key] = match.group(1)
        return key

    scrubbed = RE_TICKET_ID.sub(_hold_ticket_id, text)
    for pattern in SENSITIVE_PATTERNS:
        scrubbed = pattern.sub("[REDACTED]", scrubbed)
    for pattern in PII_PATTERNS:
        scrubbed = pattern.sub("[REDACTED]", scrubbed)
    for key, value in placeholders.items():
        scrubbed = scrubbed.replace(key, value)
    return scrubbed


def scrub_value(value: object) -> object:
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, list):
        return [scrub_value(item) for item in value]
    if isinstance(value, dict):
        return {key: scrub_value(val) for key, val in value.items()}
    return value


def load_ticket_text(path: Path) -> str:
    """Return the raw ticket body, handling JSON envelopes and metadata."""
    text = path.read_text(encoding="utf-8").strip()

    def from_json(candidate: str) -> Optional[str]:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            content = payload.get("content")
            if isinstance(content, dict) and isinstance(content.get("raw"), str):
                return content["raw"]
            if isinstance(payload.get("raw"), str):
                return scrub_value(payload)["raw"]
        return None

    raw = from_json(text)
    if raw:
        return scrub_text(raw)

    working = text
    for marker in ("**BEGIN**", "PASTE_TICKET"):
        idx = working.find(marker)
        if idx != -1:
            working = working[idx + len(marker) :]
    working = working.strip()
    raw = from_json(working)
    if raw:
        return scrub_text(raw)

    if working.startswith("Time Stamp"):
        working = "\n".join(working.splitlines()[1:])
    return scrub_text(working.strip())


def split_lines(text: str) -> List[str]:
    return [line.rstrip("\r") for line in text.splitlines()]


def normalized(line: str) -> str:
    cleaned = line.strip().lower()
    cleaned = cleaned.strip("*#>-| ")
    cleaned = re.sub(r"[:：\-]+$", "", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def canonical_heading(label: str) -> str:
    norm = normalized(label)
    if not norm:
        return norm
    if norm in SECTION_ALIAS_LOOKUP:
        return SECTION_ALIAS_LOOKUP[norm]
    for alias, canonical in SECTION_ALIAS_LOOKUP.items():
        if norm.startswith(alias):
            return canonical
    return norm


def is_section_break(label: str) -> bool:
    return canonical_heading(label) in SECTION_BREAKS


def clean_value(value: str, clamp_inline: bool = False) -> str:
    if not value:
        return ""
    trimmed = value.strip().strip("|").strip()
    parts = re.split(r"\s+\|\s+|\s{2,}|	", trimmed, maxsplit=1)
    trimmed = parts[0].strip()
    trimmed = re.sub(r"\(preferred\)$", "", trimmed, flags=re.I).strip()
    if clamp_inline:
        trimmed = trimmed.splitlines()[0].strip()
        trimmed = re.split(r"[|;,]", trimmed, maxsplit=1)[0].strip()
        trimmed = re.sub(
            r"\s*\((?:preferred|active|inactive|primary|secondary|local|dynamic|static)\)\s*$",
            "",
            trimmed,
            flags=re.I,
        ).strip()
        lowered = trimmed.lower()
        for token in INLINE_STOP_PHRASES:
            idx = lowered.find(token)
            if idx != -1:
                trimmed = trimmed[:idx].strip()
                lowered = trimmed.lower()
        trimmed = trimmed.rstrip("-:,")
    return trimmed


def harvest_key_values(lines: List[str]) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    for raw_line in lines:
        if not raw_line:
            continue
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("**"):
            continue
        low = stripped.lower()
        if low.startswith("attachment |") or low.startswith("ticket note |"):
            continue
        matches = []
        for match in RE_INLINE_KEYVALUE.finditer(stripped):
            start = match.start()
            if start > 0 and stripped[start - 1].isalnum():
                continue
            after = stripped[match.end() : match.end() + 1]
            if after in {"/", "\\"}:
                continue
            matches.append(match)
        if not matches:
            continue
        for idx, match in enumerate(matches):
            key = normalized(match.group(1))
            if not key or key.startswith("http") or key in SECTION_BREAKS:
                continue
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(stripped)
            value = clean_value(stripped[start:end])
            if not value:
                continue
            kv.setdefault(key, value)
    return kv


def pick_kv(kv: Dict[str, str], keys: List[str], clamp_inline: bool = False) -> str:
    for key in keys:
        value = kv.get(key)
        if value:
            return clean_value(value, clamp_inline=clamp_inline)
    return ""


def find_labeled_value(lines: List[str], labels: List[str], clamp_inline: bool = False) -> str:
    for line in lines:
        for label in labels:
            pattern = rf"^\s*{re.escape(label)}\s*[:=]\s*(.+)$"
            match = re.match(pattern, line, re.I)
            if match:
                value = clean_value(match.group(1), clamp_inline=clamp_inline)
                if value:
                    return value
    return ""


def find_value_after_label(lines: List[str], labels: List[str], clamp_inline: bool = False) -> str:
    label_set = {normalized(label) for label in labels}
    for idx, line in enumerate(lines):
        if normalized(line) in label_set:
            for nxt in lines[idx + 1 :]:
                stripped = nxt.strip()
                if not stripped:
                    continue
                if is_section_break(nxt) or RE_INLINE_FIELD.match(stripped):
                    break
                value = clean_value(nxt, clamp_inline=clamp_inline)
                if value:
                    return value
    return ""


def find_ipv4(lines: List[str]) -> str:
    for line in lines:
        low = line.lower()
        if "ipv4" in low or "ip address" in low:
            match = RE_IPV4.search(line)
            if match:
                return match.group(0)
    for line in lines:
        match = RE_IPV4.search(line)
        if match:
            return match.group(0)
    return ""


def find_ticket_id_and_title(lines: List[str]) -> Tuple[Optional[str], Optional[str]]:
    for line in lines:
        match = RE_TICKET_ID.search(line)
        if match:
            ticket_id = match.group(1)
            title = None
            if " - " in line:
                title = line.split(" - ", 1)[1].strip() or None
            else:
                tail = line[match.end() :].strip(" -")
                title = tail or None
            return ticket_id, title
    return None, None


def extract_block(lines: List[str], heading: str) -> List[str]:
    heading_lower = canonical_heading(heading)
    for idx, line in enumerate(lines):
        if canonical_heading(line) != heading_lower:
            continue
        start = idx + 1
        while start < len(lines) and canonical_heading(lines[start]) == heading_lower:
            start += 1
        block: List[str] = []
        for current in lines[start:]:
            cur_heading = canonical_heading(current)
            if cur_heading and is_section_break(current) and cur_heading != heading_lower:
                break
            block.append(current.strip())
            if cur_heading and cur_heading == heading_lower:
                break
        while block and not block[0]:
            block.pop(0)
        while block and not block[-1]:
            block.pop()
        return block
    return []


def extract_description(lines: List[str]) -> str:
    for idx, line in enumerate(lines):
        if canonical_heading(line) != "description":
            continue
        start = idx + 1
        while start < len(lines) and canonical_heading(lines[start]) in {"", "description"}:
            start += 1
        collected: List[str] = []
        for current in lines[start:]:
            cur_norm = canonical_heading(current)
            if cur_norm and (
                cur_norm in DESCRIPTION_STOPS or any(cur_norm.startswith(prefix) for prefix in DESCRIPTION_STOPS)
            ):
                break
            if is_reply_marker(current):
                break
            collected.append(current.rstrip())
        return "\n".join(collected).strip()
    return ""


def extract_ticket_notes(lines: List[str], max_notes: int = 5) -> List[Dict[str, str]]:
    """Extract ticket notes from the document.

    Scans for 'Ticket Note |' headings and captures metadata (timestamp/author)
    plus the note body until the next note or section break.

    Args:
        lines: Document lines to scan.
        max_notes: Maximum number of notes to extract (default 5, most recent kept).

    Returns:
        List of dicts with keys: timestamp, author, body.
    """
    notes: List[Dict[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        low = line.lower()
        if not low.startswith("ticket note |"):
            i += 1
            continue

        # Parse header: "Ticket Note | <timestamp> | <author>" or variants
        header_parts = [part.strip() for part in line.split("|")]
        timestamp = ""
        author = ""
        if len(header_parts) >= 2:
            # Second part is usually timestamp
            timestamp = header_parts[1].strip()
        if len(header_parts) >= 3:
            # Third part is usually author
            author = header_parts[2].strip()

        # Collect body until next note or section break
        body_lines: List[str] = []
        j = i + 1
        while j < len(lines):
            next_line = lines[j]
            next_low = next_line.strip().lower()
            # Stop at next ticket note
            if next_low.startswith("ticket note |"):
                break
            # Stop at attachment
            if next_low.startswith("attachment |"):
                break
            # Stop at section breaks
            cur_norm = canonical_heading(next_line)
            if cur_norm and cur_norm in SECTION_BREAKS:
                break
            body_lines.append(next_line.rstrip())
            j += 1

        body = "\n".join(body_lines).strip()
        if body:  # Only include notes with actual content
            notes.append(
                {
                    "timestamp": timestamp,
                    "author": author,
                    "body": body,
                }
            )
        i = j

    # Keep most recent notes if we exceed max_notes
    if len(notes) > max_notes:
        notes = notes[-max_notes:]

    return notes


def extract_manual_overrides(notes: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[str]]:
    overrides: List[Dict[str, str]] = []
    pack_ids: List[str] = []
    for note in notes:
        body = note.get("body", "")
        if not body:
            continue
        for line in body.splitlines():
            match = RE_MANUAL_OVERRIDE.search(line)
            if not match:
                continue
            pack_id = match.group(1).strip().lower()
            if not pack_id:
                continue
            pack_ids.append(pack_id)
            overrides.append(
                {
                    "pack_id": pack_id,
                    "author": note.get("author", ""),
                    "timestamp": note.get("timestamp", ""),
                    "raw_command": match.group(0).strip(),
                }
            )
    return overrides, pack_ids


def format_notes_for_rolling(notes: List[Dict[str, str]]) -> str:
    """Format extracted notes into a string for notes.rolling field.

    Args:
        notes: List of note dicts with timestamp, author, body keys.

    Returns:
        Formatted string with bracketed timestamps and authors.
    """
    if not notes:
        return ""

    formatted: List[str] = []
    for note in notes:
        prefix_parts = []
        if note.get("timestamp"):
            prefix_parts.append(note["timestamp"])
        if note.get("author"):
            prefix_parts.append(note["author"])

        if prefix_parts:
            prefix = f"[{' - '.join(prefix_parts)}]"
            formatted.append(f"{prefix} {note['body']}")
        else:
            formatted.append(note["body"])

    return "\n\n".join(formatted)


def extract_note_observations(
    notes: List[Dict[str, str]],
    existing_observations: List[str],
    max_additions: int = 3,
) -> List[str]:
    """Extract key observations from notes, avoiding duplicates.

    Args:
        notes: List of note dicts with body content.
        existing_observations: Already-extracted observations to avoid duplicating.
        max_additions: Maximum new observations to add from notes.

    Returns:
        List of new observation strings to add.
    """
    if not notes:
        return []

    # Build set of existing content for deduplication (normalized)
    existing_lower = {obs.lower().strip() for obs in existing_observations}

    new_observations: List[str] = []
    for note in notes:
        body = note.get("body", "")
        if not body:
            continue
        # Take first non-empty line as potential observation
        for line in body.splitlines():
            cleaned = line.strip(" -*\t")
            if not cleaned:
                continue
            # Skip if too short or matches existing
            if len(cleaned) < 10:
                continue
            if cleaned.lower() in existing_lower:
                continue
            # Skip common non-informative lines
            lower = cleaned.lower()
            if lower.startswith(("thanks", "click here", "this message", "sent from", "hi ", "hello")):
                continue
            new_observations.append(cleaned)
            existing_lower.add(cleaned.lower())
            if len(new_observations) >= max_additions:
                return new_observations
            break  # Only take first line from each note

    return new_observations


def parse_contact(lines: List[str], raw_text: str, kv: Dict[str, str]) -> Dict[str, str]:
    block = extract_block(lines, "contact")
    name = None
    email = None
    phone = None

    for entry in block:
        cleaned = entry.strip("* ").strip()
        if not cleaned:
            continue
        email_match = RE_EMAIL.search(cleaned)
        if email_match and not email:
            email = email_match.group(1)
            continue
        phone_match = RE_PHONE.search(cleaned)
        if phone_match and not phone:
            phone = phone_match.group(1).strip()
            continue
        if not name and not RE_INLINE_FIELD.match(cleaned):
            name = cleaned

    inline_name = extract_inline_field(raw_text, "Your name")
    inline_email = extract_inline_field(raw_text, "Your email")
    inline_phone = extract_inline_field(raw_text, "Your phone number")

    name = (
        name
        or inline_name
        or pick_kv(
            kv,
            [
                "requester",
                "requester name",
                "requestor",
                "requestor name",
                "contact",
                "contact name",
                "name",
            ],
        )
    )
    email = (
        email
        or inline_email
        or pick_kv(
            kv,
            ["email", "email address", "contact email", "requester email", "requestor email"],
        )
    )
    phone = (
        phone
        or inline_phone
        or pick_kv(
            kv,
            ["phone", "phone number", "contact phone", "mobile", "mobile phone"],
        )
    )

    info = {"name": name or "Unknown"}
    if email:
        info["email"] = email
    if phone:
        info["phone"] = phone
    return info


def extract_inline_field(text: str, label: str) -> Optional[str]:
    label_pattern = re.compile(rf"^\s*{re.escape(label)}\s*:\s*(.*)$", re.I)
    other_labels = [lbl for lbl in INLINE_LABELS if lbl.lower() != label.lower()]
    section_names = {section.lower() for section in SECTION_BREAKS}

    capturing = False
    value_lines: List[str] = []
    for raw_line in text.splitlines():
        if not capturing:
            match = label_pattern.match(raw_line)
            if match:
                remainder = match.group(1).strip()
                if remainder:
                    value_lines.append(remainder)
                capturing = True
            continue

        stripped = raw_line.strip()
        lower_stripped = stripped.lower()
        if not stripped:
            break
        if lower_stripped in section_names or lower_stripped.rstrip(":") in section_names:
            break
        if any(lower_stripped.startswith(other) for other in other_labels):
            break
        value_lines.append(stripped)
        if len(value_lines) >= 3:
            break

    value = " ".join(value_lines).strip()
    return value or None


def parse_environment(lines: List[str], kv: Dict[str, str]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    company_block = extract_block(lines, "company")
    if company_block:
        env["company"] = company_block[0]
    location_block = extract_block(lines, "location")
    if location_block:
        env["site"] = location_block[0]
        if len(location_block) > 1:
            env["site_address_raw"] = "\n".join(location_block[1:]).strip()

    if not env.get("company"):
        env["company"] = pick_kv(kv, ["company", "account", "client", "customer", "organization"])
    if not env.get("site"):
        env["site"] = pick_kv(kv, ["site", "location", "site/location", "site details", "address"]) or env.get(
            "site", ""
        )

    return env


def parse_impact(raw_text: str) -> Dict[str, str]:
    impact: Dict[str, str] = {}
    urgency = extract_inline_field(raw_text, "How urgent is your request?")
    scope = extract_inline_field(raw_text, "Who is impacted?")
    business = extract_inline_field(raw_text, "How is the business impacted?")
    if urgency:
        impact["urgency"] = urgency
    if scope:
        impact["scope"] = scope
    if business:
        impact["business_impact"] = business
    return impact


def extract_observations(description: str) -> List[str]:
    if not description:
        return []
    observations: List[str] = []
    for line in description.splitlines():
        cleaned = line.strip(" -*\t")
        if not cleaned:
            continue
        lower = cleaned.lower()
        if lower.startswith(("thanks", "click here", "this message", "sent from")):
            break
        observations.append(cleaned)
        if len(observations) >= 5:
            break
    if not observations:
        observations.append(description.strip())
    return observations


def parse_symptoms(description: str) -> Dict[str, object]:
    symptoms: Dict[str, object] = {}
    observations = extract_observations(description)
    if observations:
        symptoms["observations"] = observations
    error_codes = RE_ERROR_CODE.findall(description)
    if error_codes:
        symptoms["error_codes"] = sorted(set(code.upper() for code in error_codes))
        symptoms["error_messages"] = [f"Error code {code}" for code in symptoms["error_codes"]]
    return symptoms


def parse_assets(lines: List[str]) -> List[Dict[str, str]]:
    assets: List[Dict[str, str]] = []
    current: Dict[str, str] = {}

    def flush() -> None:
        nonlocal current
        if current:
            assets.append({k: v for k, v in current.items() if v})
            current = {}

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        low = line.lower()
        if low in {"asset", "configuration item"}:
            flush()
            if i + 1 < len(lines):
                next_value = lines[i + 1].strip()
                if next_value and normalized(next_value) not in SECTION_BREAKS:
                    current["asset_id"] = next_value
                    i += 2
                    continue
        elif low == "asset reference name":
            if i + 1 < len(lines):
                candidate = lines[i + 1].strip()
                if candidate and normalized(candidate) not in SECTION_BREAKS:
                    current["name"] = candidate
                    i += 2
                    continue
        elif low == "asset serial number":
            if i + 1 < len(lines):
                candidate = lines[i + 1].strip()
                if candidate and normalized(candidate) not in SECTION_BREAKS:
                    current["serial"] = candidate
                    i += 2
                    continue
        elif low in SECTION_BREAKS:
            flush()
        i += 1
    flush()
    return [asset for asset in assets if asset]


def parse_attachments(lines: List[str]) -> List[Dict[str, str]]:
    attachments: List[Dict[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line.lower().startswith("attachment |"):
            i += 1
            continue
        header_parts = [part.strip() for part in line.split("|")]
        captured_at = header_parts[-1] if len(header_parts) >= 3 else None
        name = None
        url = None
        j = i + 1
        while j < len(lines):
            label = normalized(lines[j])
            if label == "name" and j + 1 < len(lines):
                name = lines[j + 1].strip()
                j += 2
                continue
            if label.startswith("file name") and j + 1 < len(lines):
                url = lines[j + 1].strip()
                j += 2
                continue
            if label in SECTION_BREAKS or lines[j].strip().lower().startswith("attachment |"):
                break
            j += 1
        if name:
            attachment: Dict[str, str] = {"name": name}
            if url:
                attachment["url_or_path"] = url
            if captured_at:
                attachment["captured_at"] = captured_at
            ext = Path(name).suffix.lower().lstrip(".")
            if ext in {"png", "jpg", "jpeg", "gif", "bmp"}:
                attachment["type"] = "screenshot"
            attachments.append(attachment)
        i = j
    return attachments


def parse_current_state(lines: List[str]) -> Dict[str, str]:
    state: Dict[str, str] = {}
    status_block = extract_block(lines, "status")
    if status_block:
        for val in status_block:
            if val:
                state["status"] = val
                break
    last_activity = extract_block(lines, "last activity")
    if last_activity:
        for val in last_activity:
            if val:
                state["last_updated_at_raw"] = val
                break
    return state


def parse_created_at(lines: List[str]) -> str:
    for heading in ("created", "report date", "time stamp"):
        block = extract_block(lines, heading)
        for val in block:
            if val:
                return val
    return ""


def parse_issue_type(lines: List[str]) -> str:
    """Extract the PSA Issue Type field specifically."""
    block = extract_block(lines, "issue type")
    for val in block:
        if val:
            return val
    return ""


def parse_sub_issue_type(lines: List[str]) -> str:
    """Extract the PSA Sub-Issue Type field specifically."""
    block = extract_block(lines, "sub-issue type")
    for val in block:
        if val:
            return val
    return ""


def parse_category(lines: List[str]) -> str:
    """Extract category, preferring Issue Type for taxonomy routing."""
    # First try Issue Type (for taxonomy-based routing)
    issue_type = parse_issue_type(lines)
    if issue_type:
        return issue_type
    # Fall back to other category fields
    for heading in ("ticket category", "ticket type"):
        block = extract_block(lines, heading)
        for val in block:
            if val:
                return val
    return ""


def parse_service(lines: List[str]) -> str:
    """Extract service, preferring Sub-Issue Type for taxonomy routing."""
    # First try Sub-Issue Type (for taxonomy-based routing)
    sub_issue_type = parse_sub_issue_type(lines)
    if sub_issue_type:
        return sub_issue_type
    # Fall back to other service fields
    for heading in ("work type", "service level agreement", "contract"):
        block = extract_block(lines, heading)
        for val in block:
            if val:
                return val
    return ""


def normalize_priority(raw: str) -> str:
    if not raw:
        return ""
    lowered = raw.lower()
    if "p1" in lowered or "critical" in lowered or "sev1" in lowered or "severe" in lowered:
        return "P1"
    if "p2" in lowered or "high" in lowered or "sev2" in lowered:
        return "P2"
    if "p3" in lowered or "medium" in lowered or "sev3" in lowered:
        return "P3"
    if "p4" in lowered or "low" in lowered or "sev4" in lowered:
        return "P4"
    if "p5" in lowered or "minor" in lowered or "sev5" in lowered:
        return "P5"
    return ""


def parse_priority(lines: List[str]) -> str:
    block = extract_block(lines, "priority")
    raw = ""
    for val in block:
        if val:
            raw = val
            break
    normalized_priority = normalize_priority(raw)
    return normalized_priority or "UNKNOWN"


def find_first_match(text: str, patterns: List[str], clamp_inline: bool = False) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.MULTILINE)
        if match:
            value = clean_value(match.group(1), clamp_inline=clamp_inline)
            if value:
                return value
    return ""


def parse_device_details(lines: List[str], raw_text: str, kv: Dict[str, str]) -> Dict[str, str]:
    hostname = (
        find_labeled_value(
            lines,
            ["Host Name", "Hostname", "Computer Name", "Device Name", "Machine Name", "Name"],
            clamp_inline=True,
        )
        or find_value_after_label(
            lines,
            ["Host Name", "Hostname", "Computer Name", "Device Name", "Machine Name"],
            clamp_inline=True,
        )
        or find_first_match(raw_text, [r"Machine:[^\s]*\\([A-Za-z0-9._-]+)"], clamp_inline=True)
        or find_first_match(raw_text, SYSTEMINFO_PATTERNS.get("hostname", []), clamp_inline=True)
        or pick_kv(
            kv,
            ["host name", "hostname", "computer name", "device name", "machine name"],
            clamp_inline=True,
        )
    )

    os_name = (
        find_labeled_value(lines, ["OS Name", "Operating System", "OS Version"], clamp_inline=True)
        or find_value_after_label(lines, ["OS Name", "Operating System"], clamp_inline=True)
        or find_first_match(raw_text, SYSTEMINFO_PATTERNS.get("os", []), clamp_inline=True)
        or pick_kv(kv, ["operating system", "os name", "os version"], clamp_inline=True)
    )

    internal_ip = (
        pick_kv(
            kv,
            ["internal ip", "private network address", "ipv4 address", "ip address"],
            clamp_inline=True,
        )
        or find_first_match(raw_text, SYSTEMINFO_PATTERNS.get("internal_ip", []), clamp_inline=True)
        or find_ipv4(lines)
    )
    external_ip = pick_kv(
        kv,
        ["external ip", "public ip", "network address", "internet ip", "wan ip"],
        clamp_inline=True,
    ) or find_first_match(raw_text, SYSTEMINFO_PATTERNS.get("external_ip", []), clamp_inline=True)

    serial = (
        find_labeled_value(lines, ["Serial Number", "System Serial Number", "Serial"], clamp_inline=True)
        or find_value_after_label(lines, ["Serial Number", "System Serial Number", "Serial"], clamp_inline=True)
        or find_first_match(raw_text, SYSTEMINFO_PATTERNS.get("serial", []), clamp_inline=True)
        or pick_kv(kv, ["serial", "serial number", "system serial number"], clamp_inline=True)
    )

    asset_tag = (
        find_labeled_value(
            lines,
            ["Asset Tag", "Asset", "Asset ID", "Asset Reference Name"],
            clamp_inline=True,
        )
        or find_value_after_label(
            lines,
            ["Asset Tag", "Asset", "Asset ID", "Asset Reference Name"],
            clamp_inline=True,
        )
        or find_first_match(raw_text, SYSTEMINFO_PATTERNS.get("asset_tag", []), clamp_inline=True)
        or pick_kv(kv, ["asset tag", "asset", "asset id", "asset reference name"], clamp_inline=True)
    )

    return {
        "hostname": hostname,
        "os": os_name,
        "ip": internal_ip or external_ip,
        "serial": serial,
        "asset_tag": asset_tag or hostname,
    }


def parse_user_details(lines: List[str], raw_text: str, kv: Dict[str, str]) -> Dict[str, str]:
    username = (
        find_labeled_value(lines, ["User Name", "Logged On User", "Last User", "Username"], clamp_inline=True)
        or find_value_after_label(lines, ["User Name", "Logged On User", "Last User", "Username"], clamp_inline=True)
        or find_first_match(raw_text, USER_PATTERNS.get("username", []), clamp_inline=True)
        or pick_kv(kv, ["user name", "username", "logged on user", "last user"], clamp_inline=True)
    )
    domain = (
        find_labeled_value(lines, ["Domain", "Logon Domain"], clamp_inline=True)
        or find_value_after_label(lines, ["Domain", "Logon Domain"], clamp_inline=True)
        or find_first_match(raw_text, USER_PATTERNS.get("domain", []), clamp_inline=True)
        or pick_kv(kv, ["domain", "logon domain"], clamp_inline=True)
    )
    if username and "\\" in username and not domain:
        potential_domain, potential_user = username.split("\\", 1)
        if potential_domain and potential_user:
            domain = potential_domain
            username = potential_user
    return {
        "username": username,
        "domain": domain,
    }


def build_payload(raw_text: str) -> Dict[str, object]:
    lines = split_lines(raw_text)
    kv = harvest_key_values(lines)
    parse_warnings: List[str] = []
    ticket_id, title = find_ticket_id_and_title(lines)
    description_raw = extract_description(lines)
    sanitization = sanitize_description(description_raw or "")
    description = sanitization["cleaned_text"] or description_raw or ""
    if sanitization["cutoff_reason"] != "none" or sanitization["removed_char_count"] > 0:
        markers = ",".join(sanitization["detected_markers"]) or "none"
        parse_warnings.append(
            f"description_sanitized:{sanitization['cutoff_reason']}:removed={sanitization['removed_char_count']}:markers={markers}"
        )
    contact = parse_contact(lines, raw_text, kv)
    environment = parse_environment(lines, kv)
    impact = parse_impact(raw_text)
    symptoms = parse_symptoms(description)
    assets = parse_assets(lines)
    attachments = parse_attachments(lines)

    observations = extract_observations(description)
    error_codes = symptoms.get("error_codes", []) if isinstance(symptoms, dict) else []
    screenshots = [a["name"] for a in attachments if a.get("type") == "screenshot"]

    # Extract ticket notes and format for payload
    ticket_notes = extract_ticket_notes(lines)
    notes_rolling = format_notes_for_rolling(ticket_notes)
    note_observations = extract_note_observations(ticket_notes, observations)
    manual_overrides, override_pack_ids = extract_manual_overrides(ticket_notes)

    created_at = parse_created_at(lines) or pick_kv(
        kv,
        ["created", "created date", "date created", "opened", "opened date", "report date", "time stamp"],
    )
    category = parse_category(lines) or pick_kv(
        kv,
        ["ticket category", "category", "issue type", "issue category", "ticket type"],
    )
    service = parse_service(lines) or pick_kv(
        kv,
        ["work type", "service level agreement", "contract", "service", "service type"],
    )
    priority = parse_priority(lines)
    if priority == "UNKNOWN":
        priority = normalize_priority(pick_kv(kv, ["priority", "urgency", "severity"])) or "UNKNOWN"

    ticket_summary = title or (observations[0] if observations else "No summary")
    if ticket_summary and ticket_summary not in observations:
        observations.insert(0, ticket_summary)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    session_id = ticket_id or "UNSPECIFIED"

    first_asset = assets[0] if assets else {}
    device = parse_device_details(lines, raw_text, kv)
    user = parse_user_details(lines, raw_text, kv)

    payload: Dict[str, object] = {
        "meta": {
            "schema_version": "1.3.1",
            "session_id": session_id,
            "last_updated": now,
            "timezone": "America/Chicago",
            "parse_warnings": parse_warnings,
        },
        "ticket": {
            "id": ticket_id or "UNSPECIFIED",
            "created_at": created_at or "",
            "company": environment.get("company", ""),
            "site": environment.get("site", ""),
            "priority": priority,
            "category": category,
            "service": service,
            "summary": ticket_summary,
            "raw_dump": "[REDACTED]",
            "requester": {
                "name": "[REDACTED]",
                "contact": "[REDACTED]",
                "phone": "[REDACTED]" if contact.get("phone") else "",
                "email": "[REDACTED]" if contact.get("email") else "",
            },
        },
        "quickfix": {
            "timebox_minutes": 15,
            "hard_stop_minutes": 30,
            "time_spent_minutes": 0,
            "remaining_minutes": 15,
            "allowed_scope": "quick_fix",
            "escalation_paths": ["time", "skill"],
            "timer": {
                "start_time": now,
                "elapsed_minutes": 0,
                "minutes_since_first_payload_estimate": 0,
            },
        },
        "environment": {
            "target_device": {
                "hostname": "[REDACTED]" if device.get("hostname") else "UNKNOWN",
                "os": device.get("os") or "UNKNOWN",
                "ip": "[REDACTED]" if device.get("ip") else "UNKNOWN",
                "on_domain": True if user.get("domain") else None,
                "asset_tag": "[REDACTED]" if (device.get("asset_tag") or first_asset.get("asset_id")) else "",
                "serial_number": "[REDACTED]" if (device.get("serial") or first_asset.get("serial")) else "",
            },
            "user_context": {
                "username": "[REDACTED]" if user.get("username") else "UNKNOWN",
                "is_admin": None,
                "is_remote": None,
            },
            "network": {
                "connection_type": "",
                "dns_servers": [],
                "vpn": None,
            },
            "execution_context": {
                "tooling": "ScreenConnect",
                "run_as": "SYSTEM",
                "privilege": "localadmin",
                "sandbox_prepped": False,
            },
        },
        "problem": {
            "symptoms": observations,
            "impact": {
                "who": impact.get("scope", "UNKNOWN"),
                "how_bad": impact.get("business_impact") or impact.get("urgency") or "UNKNOWN",
                "work_stopped": None,
            },
            "scope": {
                "single_user": None,
                "multi_user": None,
                "single_device": None,
                "service_wide": None,
            },
            "start_time": "",
            "last_known_good": "",
            "recent_changes": [],
        },
        "constraints": {
            "cannot_reboot": None,
            "cannot_disconnect": None,
            "change_freeze": None,
            "security_sensitivity": "",
            "security_controls": {
                "threatlocker_present": None,
                "threatlocker_notes": "",
            },
        },
        "evidence": {
            "observations": observations + note_observations,
            "tests_run": [],
            "results": [],
            "artifacts": {
                "screenshots": screenshots,
                "logs": [],
                "error_codes": error_codes,
            },
            "discriminating_test": "",
        },
        "branches": {
            "active_hypotheses": [],
            "collapsed_hypotheses": [],
            "current_best_guess": "",
            "source_pack": [],
        },
        "plan": {
            "next_3_actions": [],
            "best_branch_collapse_test": "",
        },
        "css": {
            "score": 0,
            "target": 90,
            "domain_scores": {},
            "missing_fields": [],
            "contradictions": [],
            "confidence_notes": "",
        },
        "decision": {
            "status": "triage",
            "recommended_outcome": "",
            "reasoning": [],
            "if_escalate": {
                "type": "",
                "to_team": "",
                "handoff_pack": {},
            },
            "escalation_gate": {
                "eligible": False,
                "blocked_reason": "CALL not attempted yet",
            },
        },
        "notes": {
            "rolling": notes_rolling,
            "final": "",
            "escalation": "",
        },
    }
    extra_kv = {key: value for key, value in kv.items() if key not in KNOWN_KV_KEYS}
    if extra_kv:
        payload["ticket"]["user_defined_fields"] = extra_kv

    branch_seed = select_branch_pack_seed(
        ticket_summary,
        raw_text,
        issue_type=category,  # category now contains Issue Type
        sub_issue_type=service,  # service now contains Sub-Issue Type
        manual_override_packs=override_pack_ids or None,
    )
    if branch_seed["pack_ids"]:
        payload["branches"]["source_pack"] = branch_seed["pack_ids"]
    if branch_seed["hypotheses"]:
        payload["branches"]["active_hypotheses"] = branch_seed["hypotheses"]
    if branch_seed.get("routing_method"):
        payload["branches"]["routing_method"] = branch_seed["routing_method"]
    if branch_seed.get("routing_metadata"):
        payload["branches"]["routing_metadata"] = branch_seed["routing_metadata"]
    if manual_overrides:
        payload["branches"]["manual_overrides"] = manual_overrides

    return scrub_value(payload)


def write_audit_log(payload: Dict[str, object], audit_dir: Path) -> None:
    """Write the payload to an audit log directory for decision tracing."""
    audit_dir.mkdir(parents=True, exist_ok=True)
    meta = payload.get("meta", {})
    session_id = meta.get("session_id") or "UNSPECIFIED"
    timestamp = meta.get("last_updated") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_ts = timestamp.replace(":", "").replace("-", "").replace("T", "_").replace("Z", "").strip()
    filename = f"{session_id}_{safe_ts or 'audit'}.json"
    target = audit_dir / filename
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a raw ticket file into the QF_Wiz context payload schema.")
    parser.add_argument("input", type=Path, help="Path to the raw ticket text")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional output path; defaults to stdout",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output (default is compact)",
    )
    parser.add_argument(
        "--audit-log-dir",
        type=Path,
        help="Optional directory to write an audit log copy of the payload.",
    )
    args = parser.parse_args()

    raw_text = load_ticket_text(args.input)
    payload = build_payload(raw_text)
    if args.audit_log_dir:
        write_audit_log(payload, args.audit_log_dir)
    indent = 2 if args.pretty else None
    json_output = json.dumps(payload, indent=indent)
    if args.output:
        args.output.write_text(json_output + ("\n" if args.pretty else ""), encoding="utf-8")
    else:
        print(json_output)


if __name__ == "__main__":
    main()
