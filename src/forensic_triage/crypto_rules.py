"""Versioned metadata rules shared by phone app lists and file inventories."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from importlib.resources import files as package_files
from pathlib import Path
from typing import Any

from .settings import SettingsConflict, atomic_write


CATEGORIES = {
    "wallet": "Self-Custody Wallet",
    "hardware_wallet": "Hardware-Wallet-App",
    "exchange": "Kryptobörse / Broker",
    "portfolio": "Steuer / Portfolio",
    "payment": "Krypto-Zahlungsdienst",
    "market": "Kurse / Markt",
    "messenger": "Messenger",
    "cloud": "Cloudspeicher",
    "banking": "Banking / Finanzen",
}
CRYPTO_CATEGORIES = frozenset(("wallet", "hardware_wallet", "exchange", "portfolio", "payment", "market"))
RELEVANCE = frozenset(("high", "medium", "low", "neutral"))
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")


def _text(value: Any, field: str, *, max_length: int = 120) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length or any(ord(c) < 32 for c in value):
        raise ValueError(f"Ungültiges Regelfeld: {field}.")
    return value.strip()


def _strings(value: Any, field: str, *, limit: int = 30) -> list[str]:
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"{field}: Liste mit höchstens {limit} Einträgen erwartet.")
    items = [_text(item, field) for item in value]
    if len({item.casefold() for item in items}) != len(items):
        raise ValueError(f"{field}: doppelte Einträge.")
    return items


def snapshot(value: Any, version: Any = 1) -> dict[str, Any]:
    if type(version) is not int or version < 1 or not isinstance(value, dict):
        raise ValueError("Ungültige Regelversion oder Regelsammlung.")
    apps = value.get("app_rules")
    files = value.get("file_rules")
    if not isinstance(apps, list) or not isinstance(files, list) or len(apps) > 150 or len(files) > 100:
        raise ValueError("Zu viele oder ungültige App-/Dateiregeln.")
    seen: set[str] = set()
    normalized: dict[str, list[dict[str, Any]]] = {"app_rules": [], "file_rules": []}
    for kind, entries in (("app_rules", apps), ("file_rules", files)):
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Eine Regel muss ein Objekt sein.")
            rule_id = _text(entry.get("id"), "id", max_length=50)
            if not ID_PATTERN.fullmatch(rule_id) or rule_id in seen:
                raise ValueError(f"Ungültige oder doppelte Regel-ID: {rule_id}.")
            seen.add(rule_id)
            category = _text(entry.get("category"), "category")
            relevance = _text(entry.get("relevance"), "relevance")
            if category not in CATEGORIES or relevance not in RELEVANCE:
                raise ValueError(f"{rule_id}: Kategorie oder Hinweisstärke ungültig.")
            if category not in CRYPTO_CATEGORIES and relevance != "neutral":
                raise ValueError(f"{rule_id}: Messenger, Cloud und Banking sind keine Krypto-Hinweise.")
            if kind == "app_rules" and category in {"wallet", "hardware_wallet", "exchange"} and relevance != "high":
                raise ValueError(f"{rule_id}: Wallets und Börsen benötigen Hinweisstärke hoch.")
            if type(entry.get("enabled")) is not bool:
                raise ValueError(f"{rule_id}: aktiv muss ja oder nein sein.")
            common = {
                "id": rule_id, "name": _text(entry.get("name"), "name"),
                "category": category, "relevance": relevance, "enabled": entry["enabled"],
                "comment": str(entry.get("comment", ""))[:300],
            }
            if kind == "app_rules":
                common.update({
                    "bundle_ids": _strings(entry.get("bundle_ids", []), "bundle_ids"),
                    "aliases": _strings(entry.get("aliases", []), "aliases"),
                    "terms": _strings(entry.get("terms", []), "terms"),
                })
                if not (common["bundle_ids"] or common["name"] or common["aliases"]):
                    raise ValueError(f"{rule_id}: App ohne Namen oder Bundle-ID.")
            else:
                common.update({
                    "filename_equals": _strings(entry.get("filename_equals", []), "filename_equals"),
                    "terms": _strings(entry.get("terms", []), "terms"),
                    "context_terms": _strings(entry.get("context_terms", []), "context_terms"),
                    "extensions": [item.lstrip(".").casefold() for item in _strings(entry.get("extensions", []), "extensions")],
                })
                if not (common["filename_equals"] or common["terms"]):
                    raise ValueError(f"{rule_id}: Dateiregel ohne Suchmerkmal.")
            normalized[kind].append(common)
    data = {"version": version, **normalized}
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {**data, "sha256": hashlib.sha256(raw).hexdigest()}


def bundled_rules() -> dict[str, Any]:
    raw = package_files("forensic_triage").joinpath("data/crypto-rules.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    return snapshot(data, data.get("version"))


def load_rules(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    result = snapshot(data, data.get("version"))
    if data.get("sha256") != result["sha256"]:
        raise ValueError("Krypto-Regeln wurden außerhalb der Einstellungen verändert oder sind beschädigt.")
    return result


def save_rules(path: Path, value: Any, base_sha256: str) -> dict[str, Any]:
    current = load_rules(path)
    if current["sha256"] != base_sha256:
        raise SettingsConflict("Regeln wurden inzwischen geändert. Einstellungen neu laden.")
    updated = snapshot(value, current["version"] + 1)
    atomic_write(path, (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode())
    return updated


def seed_rules(path: Path, legacy_path: Path | None = None) -> None:
    if path.exists():
        return
    base = bundled_rules()
    if legacy_path and legacy_path.is_file():
        try:
            old = json.loads(legacy_path.read_text(encoding="utf-8"))
            old_defaults = json.loads(package_files("forensic_triage").joinpath("data/iphone-triage.json").read_text(encoding="utf-8"))
            default_by_id = {item["id"]: item for item in old_defaults.get("app_rules", [])}
            default_files_by_id = {item["id"]: item for item in old_defaults.get("file_rules", [])}
            by_id = {rule["id"]: rule for rule in base["app_rules"]}
            if any(
                any(word in str(item.get("category", "")).casefold() for word in ("messenger", "cloud", "bank"))
                for item in old.get("app_rules", []) if isinstance(item, dict)
            ):
                by_id = {key: value for key, value in by_id.items() if value["category"] in CRYPTO_CATEGORIES}
            for item in old.get("app_rules", []):
                if not isinstance(item, dict):
                    continue
                rule_id = str(item.get("id", ""))
                if not ID_PATTERN.fullmatch(rule_id):
                    continue
                category = str(item.get("category", "")).casefold()
                target = by_id.get(rule_id)
                if target:
                    # Old bundled IDs were not independently verified. Carry over only
                    # IDs the operator actually changed in the local legacy file.
                    if item.get("bundle_ids", []) != default_by_id.get(rule_id, {}).get("bundle_ids", []):
                        target["bundle_ids"] = item.get("bundle_ids", [])
                    target["aliases"] = item.get("name_contains", target["aliases"])
                elif "messenger" in category or "cloud" in category or "bank" in category:
                    mapped = "messenger" if "messenger" in category else "cloud" if "cloud" in category else "banking"
                    by_id[rule_id] = {
                        "id": rule_id, "name": rule_id.replace("-", " ").title(),
                        "category": mapped, "relevance": "neutral", "enabled": True,
                        "bundle_ids": item.get("bundle_ids", []),
                        "aliases": item.get("name_contains", []), "terms": [],
                        "comment": "Aus bisheriger iPhone-Regel übernommen",
                    }
                elif rule_id not in by_id:
                    mapped = "exchange" if "börse" in category or "exchange" in category else "wallet" if "wallet" in category else "portfolio"
                    aliases = item.get("name_contains", [])
                    by_id[rule_id] = {
                        "id": rule_id, "name": aliases[0] if isinstance(aliases, list) and aliases else rule_id.replace("-", " ").title(),
                        "category": mapped, "relevance": "high" if mapped in {"wallet", "exchange"} else "medium",
                        "enabled": True, "bundle_ids": item.get("bundle_ids", []),
                        "aliases": aliases[1:] if isinstance(aliases, list) else [], "terms": [],
                        "comment": "Aus älterer lokaler iPhone-Regel übernommen; bitte fachlich prüfen",
                    }
            file_rules = list(base["file_rules"])
            for item in old.get("file_rules", []):
                if not isinstance(item, dict) or item == default_files_by_id.get(item.get("id")):
                    continue
                rule_id = str(item.get("id", ""))
                if not ID_PATTERN.fullmatch(rule_id) or any(rule["id"] == rule_id for rule in file_rules):
                    continue
                terms = item.get("path_contains", [])
                if not isinstance(terms, list) or not terms:
                    continue
                category = "wallet" if any(word in rule_id for word in ("wallet", "seed", "key")) else "portfolio"
                file_rules.append({
                    "id": rule_id, "name": str(item.get("label") or rule_id), "category": category,
                    "relevance": "medium", "enabled": True, "filename_equals": [], "terms": terms,
                    "context_terms": [], "extensions": item.get("extensions", []),
                    "comment": "Aus älterer lokaler iPhone-Regel übernommen; bitte fachlich prüfen",
                })
            base = snapshot({"app_rules": list(by_id.values()), "file_rules": file_rules}, base["version"])
        except (OSError, ValueError, KeyError, TypeError):
            # A damaged legacy file must not prevent the new default rules.
            base = bundled_rules()
    atomic_write(path, (json.dumps(base, ensure_ascii=False, indent=2) + "\n").encode())


def _fold(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _term_in_path(term: str, path: str) -> bool:
    term = _fold(term).replace("_", " ").replace("-", " ")
    path = _fold(path).replace("_", " ").replace("-", " ")
    return bool(re.search(r"(?<!\w)" + re.escape(term).replace(r"\ ", r"\s+") + r"(?!\w)", path))


def classify_app(app: dict[str, Any], rules: dict[str, Any]) -> list[dict[str, str]]:
    bundle = _fold(str(app.get("bundle_id", "")))
    name = _fold(str(app.get("name", "")))
    matches = []
    for rule in rules["app_rules"]:
        if not rule["enabled"]:
            continue
        reason = ""
        if bundle and bundle in {_fold(value) for value in rule["bundle_ids"]}:
            reason = f"Bundle-ID: {bundle}"
        elif name and name in {_fold(value) for value in [rule["name"], *rule["aliases"]]}:
            reason = f"App-Name: {app['name']}"
        elif any(_term_in_path(term, name) for term in rule["terms"]):
            reason = f"Suchbegriff im App-Namen: {app['name']}"
        if reason:
            matches.append({key: str(rule[key]) for key in ("id", "name", "category", "relevance")} | {"reason": reason})
    return matches


def classify_file(path: str, extension: str, rules: dict[str, Any]) -> list[dict[str, str]]:
    name = path.rsplit("/", 1)[-1]
    matches = []
    for rule in rules["file_rules"]:
        if not rule["enabled"] or (rule["extensions"] and extension.casefold() not in rule["extensions"]):
            continue
        exact = any(_fold(name) == _fold(value) for value in rule["filename_equals"])
        term = next((value for value in rule["terms"] if _term_in_path(value, path)), "")
        context = next((value for value in rule["context_terms"] if _term_in_path(value, path)), "")
        if not exact and not term:
            continue
        if rule["context_terms"] and not context:
            continue
        reason = f"Dateiname: {name}" if exact else f"Begriff: {term}"
        if context:
            reason += f" · Kontext: {context}"
        if rule["extensions"]:
            reason += f" · Endung: .{extension}"
        matches.append({key: str(rule[key]) for key in ("id", "name", "category", "relevance")} | {"reason": reason})
    return matches


def find_file_hints(files: list[dict[str, Any]], rules: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"path": str(item["path"]), "source": str(item.get("source", "medium")), "matches": matches}
        for item in files
        if (matches := classify_file(str(item["path"]), str(item.get("extension", "")), rules))
    ]
