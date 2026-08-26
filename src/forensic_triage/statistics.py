"""Deterministic summary calculations."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def summarize(files: list[dict[str, Any]], directories: list[dict[str, Any]]) -> dict[str, Any]:
    extensions: Counter[str] = Counter()
    category_count: Counter[str] = Counter()
    category_bytes: dict[str, int] = defaultdict(int)

    for item in files:
        extension = str(item.get("extension", ""))
        category = str(item.get("category", "Unbekannt"))
        size = int(item.get("size", 0) or 0)
        extensions[extension or "(ohne Endung)"] += 1
        category_count[category] += 1
        category_bytes[category] += size

    largest = sorted(
        ({"path": item["path"], "size": int(item.get("size", 0) or 0)} for item in files),
        key=lambda item: (-item["size"], item["path"]),
    )[:5]

    return {
        "file_count": len(files),
        "directory_count": len(directories),
        "total_file_bytes": sum(int(item.get("size", 0) or 0) for item in files),
        "extensions": dict(sorted(extensions.items())),
        "categories_by_count": dict(sorted(category_count.items())),
        "categories_by_bytes": dict(sorted(category_bytes.items())),
        "largest_files": largest,
    }
