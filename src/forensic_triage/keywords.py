"""Keyword profile loading and path matching."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml


def load_profile(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    data = yaml.safe_load(raw) or {}
    keywords = data.get("keywords", [])
    if not isinstance(keywords, list) or not all(isinstance(item, str) for item in keywords):
        raise ValueError("profile 'keywords' must be a list of strings")
    normalized = [word.strip() for word in keywords if word.strip()]
    if len({word.casefold() for word in normalized}) != len(normalized):
        raise ValueError("profile contains duplicate keywords (case-insensitive)")
    return {
        "version": str(data.get("version", "unversioned")),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "keywords": normalized,
    }


def match_keywords(path: str, keywords: list[str]) -> list[str]:
    folded = path.casefold()
    return [keyword for keyword in keywords if keyword.casefold() in folded]


def build_hits(files: list[dict[str, Any]], keywords: list[str]) -> dict[str, Any]:
    by_keyword = {keyword: [] for keyword in keywords}
    for item in files:
        path = str(item["path"])
        for keyword in match_keywords(path, keywords):
            by_keyword[keyword].append(path)
    return {
        "total_matches": sum(len(paths) for paths in by_keyword.values()),
        "by_keyword": {
            keyword: {"count": len(paths), "paths": paths}
            for keyword, paths in by_keyword.items()
        },
    }
