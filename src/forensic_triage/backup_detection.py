"""Structural detection of local device backups on media inventories.

Detection is based on path and filename patterns only.  No backup contents are
opened, decrypted or parsed.  A match therefore means „this directory structure
looks like a known backup format“, not „user data has been recovered".
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any


class _InventoryIndex:
    """Lightweight index over a file/directory inventory for fast matching."""

    def __init__(self, files: list[dict[str, Any]], directories: list[dict[str, Any]]) -> None:
        self.paths: set[str] = set()
        self.filenames: set[str] = set()
        self.extensions: set[str] = set()
        self.dir_paths: set[str] = set()
        for item in files:
            path = str(item.get("path", "")).replace("\\", "/")
            self.paths.add(path)
            self.filenames.add(Path(path).name)
            ext = str(item.get("extension", "")).casefold().lstrip(".")
            if ext:
                self.extensions.add(ext)
        for item in directories:
            path = str(item.get("path", "")).replace("\\", "/")
            self.dir_paths.add(path)
            self.paths.add(path)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Cf").casefold()


def _path_matches(pattern: str, path: str) -> bool:
    """Case-insensitive whole-segment or substring matching for paths."""
    pattern_fold = _fold(pattern).replace("\\", "/")
    path_fold = _fold(path).replace("\\", "/")
    if pattern_fold in path_fold:
        return True
    # Also allow simple glob-style segment matching, e.g. "Backup/*".
    regex = pattern_fold.replace(".", r"\.").replace("*", r"[^/]*").replace("?", r"[^/]")
    return bool(re.search(regex, path_fold))


def _evaluate_rule(rule: dict[str, Any], index: _InventoryIndex) -> dict[str, Any] | None:
    if not rule.get("enabled", True):
        return None
    required_paths = rule.get("required_paths", [])
    required_files = rule.get("required_files", [])
    required_extensions = rule.get("required_extensions", [])

    path_hits = [p for p in required_paths if any(_path_matches(p, path) for path in index.paths)]
    file_hits = [f for f in required_files if any(_fold(f) == _fold(name) for name in index.filenames)]
    ext_hits = [e for e in required_extensions if e.lstrip(".").casefold() in index.extensions]

    confidence = rule.get("confidence", "medium")

    # Structural backup detection needs at least one path indicator; without it
    # a single generic filename would create too many false positives.
    if not path_hits:
        return None

    # High-confidence rules need multiple structural indicators.
    if confidence == "high":
        score = len(file_hits) + len(ext_hits)
        if score < 1 and len(required_files) + len(required_extensions) > 0:
            return None
        if len(required_files) >= 2 and len(file_hits) < max(1, len(required_files) // 2):
            return None
    elif confidence == "medium":
        if not file_hits and not ext_hits and (required_files or required_extensions):
            return None
    else:  # low
        if not file_hits and not ext_hits and (required_files or required_extensions):
            return None

    matched_indicators = []
    if path_hits:
        matched_indicators.append(f"Pfade: {', '.join(path_hits[:3])}")
    if file_hits:
        matched_indicators.append(f"Dateien: {', '.join(file_hits[:3])}")
    if ext_hits:
        matched_indicators.append(f"Endungen: {', '.join(ext_hits[:3])}")

    # Report one representative path: the shortest matching path that contains
    # the first matched path indicator.
    representative = ""
    if path_hits:
        indicator = path_hits[0]
        matches = [p for p in index.paths if _path_matches(indicator, p)]
        if matches:
            representative = min(matches, key=len)

    return {
        "id": rule["id"],
        "name": rule["name"],
        "platform": rule.get("platform", ""),
        "confidence": confidence,
        "status": rule.get("status", "active"),
        "matched_indicators": matched_indicators,
        "path": representative,
        "source": rule.get("source", ""),
        "last_verified": rule.get("last_verified", ""),
        "comment": rule.get("comment", ""),
    }


def find_backup_hints(
    files: list[dict[str, Any]],
    directories: list[dict[str, Any]],
    rules: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return backup hints for a media inventory without reading contents."""
    index = _InventoryIndex(files, directories)
    hints: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for rule in rules.get("backup_rules", []):
        hit = _evaluate_rule(rule, index)
        if hit is None:
            continue
        # Avoid duplicate reports for the same rule at the same path.
        key = (hit["id"], hit["path"])
        if key in seen_paths:
            continue
        seen_paths.add(key)
        hints.append(hit)
    return hints


def summarize_backup_hints(hints: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce a compact summary for summary.json."""
    by_confidence: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for hint in hints:
        by_confidence[hint.get("confidence", "medium")] = by_confidence.get(hint.get("confidence", "medium"), 0) + 1
    return {
        "total": len(hints),
        "by_confidence": by_confidence,
    }
