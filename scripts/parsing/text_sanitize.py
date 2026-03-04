"""Utilities for sanitizing ticket description text before parsing."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

ORIGINAL_MESSAGE_RE = re.compile(r"-+\s*original message\s*-+", re.I)
HEADER_LABEL_RE = re.compile(
    r"^\s*(from|sent|to|subject|cc|bcc|date|de|envoy[ée]|objet|von|gesendet|para)\s*[:\-]",
    re.I,
)
ON_DATE_WROTE_RE = re.compile(
    r"^\s*(on|am|le|el)\s+.+?(wrote|schrieb|écrit|escrib[ií]o)\s*:?\s*$",
    re.I,
)
QUOTE_LINE_RE = re.compile(r"^\s*>+\s?")

DEFAULT_MIN_KEEP_CHARS = 200
DEFAULT_MIN_NONEMPTY_LINES = 5
QUOTE_CHAIN_MIN_LINES = 3
MIN_PARAGRAPH_LEN = 20


def _line_offsets(text: str) -> Tuple[List[str], List[int]]:
    lines_with_endings = text.splitlines(keepends=True)
    if not lines_with_endings and text:
        lines_with_endings = [text]
    if not lines_with_endings:
        lines_with_endings = [""]
    offsets: List[int] = []
    cleaned_lines: List[str] = []
    idx = 0
    for chunk in lines_with_endings:
        offsets.append(idx)
        cleaned_lines.append(chunk.rstrip("\r\n"))
        idx += len(chunk)
    return cleaned_lines, offsets


def _ensure_min_keep_index(text: str, offsets: List[int], min_chars: int, min_lines: int) -> int:
    target_chars = max(min_chars or 0, 0)
    target_lines = max(min_lines or 0, 0)
    if target_lines <= 0:
        return min(len(text), target_chars)
    idx_after_lines = len(text)
    seen = 0
    for line_idx, start in enumerate(offsets):
        end = offsets[line_idx + 1] if line_idx + 1 < len(offsets) else len(text)
        if text[start:end].strip():
            seen += 1
            if seen >= target_lines:
                idx_after_lines = end
                break
    return min(len(text), max(target_chars, idx_after_lines))


def _find_original_marker(lines: List[str]) -> Optional[int]:
    for idx, line in enumerate(lines):
        if ORIGINAL_MESSAGE_RE.search(line):
            return idx
    return None


def _find_header_block(lines: List[str]) -> Optional[int]:
    block_start: Optional[int] = None
    consecutive = 0
    for idx, line in enumerate(lines):
        if HEADER_LABEL_RE.match(line):
            if block_start is None:
                block_start = idx
            consecutive += 1
            continue
        if block_start is not None:
            if consecutive >= 3:
                return block_start
            block_start = None
            consecutive = 0
    if block_start is not None and consecutive >= 3:
        return block_start
    return None


def _find_on_date_wrote(lines: List[str]) -> Optional[int]:
    for idx, line in enumerate(lines):
        if ON_DATE_WROTE_RE.match(line.strip()):
            return idx
    return None


def _find_quoted_chain(lines: List[str]) -> Optional[int]:
    run_start: Optional[int] = None
    run_count = 0
    for idx, line in enumerate(lines):
        if QUOTE_LINE_RE.match(line):
            if run_start is None:
                run_start = idx
            run_count += 1
        else:
            if run_start is not None and run_count >= QUOTE_CHAIN_MIN_LINES:
                return run_start
            run_start = None
            run_count = 0
    if run_start is not None and run_count >= QUOTE_CHAIN_MIN_LINES:
        return run_start
    return None


def _char_index_for_line(offsets: List[int], line_idx: int, text_length: int) -> int:
    if line_idx < 0:
        return 0
    if line_idx >= len(offsets):
        return text_length
    return offsets[line_idx]


def _collapse_duplicate_paragraphs(text: str) -> Tuple[str, bool]:
    paragraphs = text.split("\n\n")
    seen: set[str] = set()
    keep: List[str] = []
    duplicates_found = False
    for paragraph in paragraphs:
        normalized = re.sub(r"\s+", " ", paragraph.strip().lower())
        if len(normalized) >= MIN_PARAGRAPH_LEN:
            if normalized in seen:
                duplicates_found = True
                continue
            seen.add(normalized)
        keep.append(paragraph)
    rebuilt = "\n\n".join(keep)
    if text.endswith("\n") and not rebuilt.endswith("\n"):
        rebuilt += "\n"
    return rebuilt or text, duplicates_found


def sanitize_description(
    text: str,
    *,
    min_keep_chars: int = DEFAULT_MIN_KEEP_CHARS,
    max_keep_chars: Optional[int] = None,
    min_nonempty_lines: int = DEFAULT_MIN_NONEMPTY_LINES,
) -> Dict[str, object]:
    original = text or ""
    if not original:
        return {
            "cleaned_text": "",
            "cutoff_reason": "none",
            "removed_char_count": 0,
            "detected_markers": [],
        }

    lines, offsets = _line_offsets(original)
    text_length = len(original)
    cutoff_idx: Optional[int] = None
    cutoff_reason = "none"
    detected_markers: List[str] = []

    rule_checks = [
        ("original_message", _find_original_marker),
        ("headers_block", _find_header_block),
        ("on_date_wrote", _find_on_date_wrote),
        ("quoted_lines", _find_quoted_chain),
    ]

    for reason, finder in rule_checks:
        line_idx = finder(lines)
        if line_idx is not None:
            cutoff_idx = _char_index_for_line(offsets, line_idx, text_length)
            cutoff_reason = reason
            if reason not in detected_markers:
                detected_markers.append(reason)
            break

    keep_floor = _ensure_min_keep_index(original, offsets, min_keep_chars, min_nonempty_lines)
    if cutoff_idx is not None:
        cleaned = original[:cutoff_idx]
    else:
        cleaned = original

    if max_keep_chars is not None and len(cleaned) > max_keep_chars:
        if "max_keep" not in detected_markers:
            detected_markers.append("max_keep")
        if cutoff_reason == "none":
            cutoff_reason = "max_keep"
        target = max(max_keep_chars, keep_floor)
        cleaned = cleaned[: min(target, len(cleaned))]

    cleaned, duplicates_removed = _collapse_duplicate_paragraphs(cleaned)
    if duplicates_removed:
        if "duplicate_block" not in detected_markers:
            detected_markers.append("duplicate_block")
        if cutoff_reason == "none":
            cutoff_reason = "duplicate_block"

    if not cleaned.strip():
        cleaned = original
        cutoff_reason = "none"
        detected_markers = []

    removed_char_count = max(0, len(original) - len(cleaned))

    return {
        "cleaned_text": cleaned,
        "cutoff_reason": cutoff_reason,
        "removed_char_count": removed_char_count,
        "detected_markers": detected_markers,
    }
