"""Durable operator settings and reproducible extension-catalog snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .classifier import CATEGORY_EXTENSIONS, extension_for
from .keywords import PROFILE_ID_PATTERN, load_profile


class SettingsConflict(ValueError):
    pass


def atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def validate_categories(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict) or not 1 <= len(value) <= 40:
        raise ValueError("Der Katalog benötigt 1–40 Kategorien.")
    result: dict[str, list[str]] = {}
    used: dict[str, str] = {}
    names: set[str] = set()
    for name, extensions in value.items():
        if not isinstance(name, str) or not re.fullmatch(r"[\wÄÖÜäöüß /()-]{1,50}", name) or name != name.strip():
            raise ValueError("Kategoriename: 1–50 Buchstaben, Ziffern, Leerzeichen, Unterstrich oder /()-.")
        if name.casefold() == "unbekannt" or name.casefold() in names:
            raise ValueError("Kategorien dürfen nicht doppelt sein; Unbekannt bleibt automatisch.")
        names.add(name.casefold())
        if not isinstance(extensions, list) or len(extensions) > 250:
            raise ValueError(f"{name}: höchstens 250 Endungen als Liste.")
        normalized = []
        for item in extensions:
            if not isinstance(item, str):
                raise ValueError("Endungen müssen Text sein.")
            extension = item.strip().removeprefix(".").casefold()
            if not re.fullmatch(r"[a-z0-9]{1,16}", extension):
                raise ValueError(f"Ungültige Endung: {item[:30]}")
            if extension in used:
                raise ValueError(f".{extension} ist doppelt zugeordnet ({used[extension]} / {name}).")
            used[extension] = name
            normalized.append(extension)
        result[name] = sorted(normalized)
    if not used or len(used) > 2000:
        raise ValueError("Der Katalog benötigt 1–2000 eindeutige Endungen.")
    return result


def catalog_snapshot(categories: Any, version: Any = 1) -> dict[str, Any]:
    if type(version) is not int or version < 1:
        raise ValueError("Ungültige Katalogversion.")
    data = {"version": version, "categories": validate_categories(categories)}
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {**data, "sha256": hashlib.sha256(raw).hexdigest()}


def default_catalog() -> dict[str, Any]:
    return catalog_snapshot({name: sorted(values) for name, values in CATEGORY_EXTENSIONS.items()})


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    if path is None or not path.exists():
        return default_catalog()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Ungültiges Dateityp-Katalogformat.")
    snapshot = catalog_snapshot(data.get("categories"), data.get("version"))
    if data.get("sha256") != snapshot["sha256"]:
        raise ValueError("Dateityp-Katalog ist beschädigt oder außerhalb der Einstellungen verändert.")
    return snapshot


def save_catalog(path: Path, categories: Any, base_sha256: str) -> dict[str, Any]:
    current = load_catalog(path)
    if base_sha256 != current["sha256"]:
        raise SettingsConflict("Katalog wurde inzwischen geändert. Einstellungen schließen und erneut öffnen.")
    normalized = validate_categories(categories)
    if normalized == current["categories"]:
        return current
    updated = catalog_snapshot(normalized, current["version"] + 1)
    atomic_write(path, (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode())
    return updated


def apply_catalog(files: list[dict[str, Any]], containers: dict[str, Any], catalog: dict[str, Any]) -> None:
    """Apply one immutable scan-start snapshot to outer and virtual entries."""
    mapping = {ext: name for name, values in catalog["categories"].items() for ext in values}
    for item in files:
        extension = extension_for(str(item["path"]))
        item.update(extension=extension, category=mapping.get(extension, "Unbekannt"))
    for container in containers.get("containers", []):
        for item in container.get("entries", []):
            if item.get("kind") == "file":
                extension = extension_for(str(item["path"]))
                item.update(extension=extension, category=mapping.get(extension, "Unbekannt"))


def prepare_profiles(root: Path, source: Path) -> Path:
    """Seed durable profiles once, without replacing any saved operator file."""
    destination = root / "profiles"
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path in sorted(source.parent.glob("*.yaml")):
        target = destination / path.name
        if PROFILE_ID_PATTERN.fullmatch(path.stem) and not target.exists():
            load_profile(path)
            atomic_write(target, path.read_bytes())
    result = destination / source.name
    if not result.is_file():
        raise ValueError("Startprofil fehlt. Lokale Profilkonfiguration prüfen.")
    return result
