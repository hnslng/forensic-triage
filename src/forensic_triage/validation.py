"""Comparison of a fixture scan with its deterministic expected manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SUMMARY_KEYS = (
    "file_count",
    "directory_count",
    "total_file_bytes",
    "extensions",
    "categories_by_count",
    "categories_by_bytes",
    "largest_files",
)


def compare_expected(summary: dict[str, Any], hits: dict[str, Any], expected_path: Path) -> dict[str, Any]:
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    mismatches: list[dict[str, Any]] = []
    for key in SUMMARY_KEYS:
        if summary.get(key) != expected.get(key):
            mismatches.append({"field": key, "expected": expected.get(key), "actual": summary.get(key)})

    all_actual_hits = {
        keyword.casefold(): details["count"]
        for keyword, details in hits.get("by_keyword", {}).items()
    }
    expected_hits = {
        keyword.casefold(): count
        for keyword, count in expected.get("keyword_hits", {}).items()
    }
    actual_hits = {
        keyword: count
        for keyword, count in all_actual_hits.items()
        if count or keyword in expected_hits
    }
    if actual_hits != expected_hits:
        mismatches.append({"field": "keyword_hits", "expected": expected_hits, "actual": actual_hits})

    return {
        "passed": not mismatches,
        "expected_manifest": str(expected_path),
        "mismatches": mismatches,
    }
