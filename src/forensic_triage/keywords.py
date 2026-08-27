"""Keyword profile loading and path matching."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml


PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


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
        "id": path.stem,
        "name": str(data.get("name", path.stem.replace("-", " ").upper())).strip(),
        "version": str(data.get("version", "unversioned")),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "keywords": normalized,
    }


def list_profiles(directory: Path) -> list[dict[str, Any]]:
    """Return all valid local profiles without exposing filesystem paths."""
    profiles: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.yaml")):
        if not PROFILE_ID_PATTERN.fullmatch(path.stem):
            continue
        profile = load_profile(path)
        profiles.append({
            "id": profile["id"],
            "name": profile["name"],
            "version": profile["version"],
            "keyword_count": len(profile["keywords"]),
        })
    return profiles


def save_profile(directory: Path, profile_id: str | None, name: str, keywords: list[str]) -> dict[str, Any]:
    """Create or update a small local keyword profile."""
    clean_name = name.strip()
    if not clean_name or len(clean_name) > 40 or not re.fullmatch(r"[A-Za-z0-9ÄÖÜäöüß _-]+", clean_name):
        raise ValueError("Profilname: 1–40 Zeichen; erlaubt sind Buchstaben, Ziffern, Leerzeichen, Minus und Unterstrich.")
    normalized = [word.strip() for word in keywords if isinstance(word, str) and word.strip()]
    if not normalized:
        raise ValueError("Ein Profil benötigt mindestens ein Stichwort.")
    if len(normalized) > 250 or any(len(word) > 120 for word in normalized):
        raise ValueError("Zu viele oder zu lange Stichwörter.")
    if len({word.casefold() for word in normalized}) != len(normalized):
        raise ValueError("Das Profil enthält doppelte Stichwörter.")

    if profile_id is None:
        base = re.sub(r"[^a-z0-9]+", "-", clean_name.casefold()).strip("-") or "profil"
        candidate = base[:40]
        suffix = 2
        while (directory / f"{candidate}.yaml").exists():
            tail = f"-{suffix}"
            candidate = f"{base[:40 - len(tail)]}{tail}"
            suffix += 1
        profile_id = candidate
        version = "1.0"
    else:
        if not PROFILE_ID_PATTERN.fullmatch(profile_id):
            raise ValueError("Ungültiges Profil.")
        path = directory / f"{profile_id}.yaml"
        if not path.is_file():
            raise ValueError("Profil nicht gefunden.")
        current = load_profile(path)
        try:
            major, minor = (int(part) for part in current["version"].split(".", 1))
            version = f"{major}.{minor + 1}"
        except (TypeError, ValueError):
            version = "1.1"

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{profile_id}.yaml"
    raw = yaml.safe_dump(
        {"name": clean_name, "version": version, "keywords": normalized},
        allow_unicode=True,
        sort_keys=False,
    )
    path.write_text(raw, encoding="utf-8")
    return load_profile(path)


def match_keywords(path: str, keywords: list[str]) -> list[str]:
    def forms(value: str) -> tuple[str, str]:
        folded = unicodedata.normalize("NFKC", value).casefold()
        german = folded.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        compact = "".join(character for character in german if character.isalnum())
        return german, compact

    folded_path, compact_path = forms(path)
    matches: list[str] = []
    for keyword in keywords:
        folded_keyword, compact_keyword = forms(keyword)
        if folded_keyword in folded_path or (compact_keyword and compact_keyword in compact_path):
            matches.append(keyword)
    return matches


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
