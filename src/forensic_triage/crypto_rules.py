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
STATUS = frozenset(("active", "legacy"))
PLATFORM_ID_STATUS = frozenset(("verified", "unverified", "not_applicable"))
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")
MAX_APP_RULES = 2000
MAX_FILE_RULES = 500
MAX_BACKUP_RULES = 200


def _text(value: Any, field: str, *, max_length: int = 120) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length or any(ord(c) < 32 for c in value):
        raise ValueError(f"Ungültiges Regelfeld: {field}.")
    return value.strip()


def _optional_text(value: Any, field: str, *, max_length: int = 240) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str) or len(value) > max_length or any(ord(c) < 32 for c in value):
        raise ValueError(f"Ungültiges Regelfeld: {field}.")
    return value.strip()


def _strings(value: Any, field: str, *, limit: int = 30) -> list[str]:
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"{field}: Liste mit höchstens {limit} Einträgen erwartet.")
    items = [_text(item, field) for item in value]
    if len({item.casefold() for item in items}) != len(items):
        raise ValueError(f"{field}: doppelte Einträge.")
    return items


def _optional_strings(value: Any, field: str, *, limit: int = 30) -> list[str]:
    if value is None:
        return []
    return _strings(value, field, limit=limit)


def _date(value: Any, field: str) -> str:
    text = _optional_text(value, field, max_length=16)
    if text and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValueError(f"{field}: Datum im Format YYYY-MM-DD erwartet.")
    return text


def _bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field}: Wahrheitswert erwartet.")
    return value


def snapshot(value: Any, version: Any = 1) -> dict[str, Any]:
    if type(version) is not int or version < 1 or not isinstance(value, dict):
        raise ValueError("Ungültige Regelversion oder Regelsammlung.")
    apps = value.get("app_rules", [])
    files = value.get("file_rules", [])
    backups = value.get("backup_rules", [])
    if not isinstance(apps, list) or not isinstance(files, list) or not isinstance(backups, list):
        raise ValueError("Ungültige App-/Datei-/Backup-Regeln.")
    if len(apps) > MAX_APP_RULES or len(files) > MAX_FILE_RULES or len(backups) > MAX_BACKUP_RULES:
        raise ValueError(
            f"Zu viele Regeln (max. {MAX_APP_RULES} Apps, "
            f"{MAX_FILE_RULES} Dateien, {MAX_BACKUP_RULES} Backups)."
        )
    deleted_default_rule_ids = _optional_strings(value.get("deleted_default_rule_ids", []), "deleted_default_rule_ids", limit=MAX_APP_RULES + MAX_FILE_RULES + MAX_BACKUP_RULES)
    seen: set[str] = set()
    normalized: dict[str, list[dict[str, Any]]] = {"app_rules": [], "file_rules": [], "backup_rules": []}
    for kind, entries in (("app_rules", apps), ("file_rules", files), ("backup_rules", backups)):
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Eine Regel muss ein Objekt sein.")
            rule_id = _text(entry.get("id"), "id", max_length=50)
            if not ID_PATTERN.fullmatch(rule_id) or rule_id in seen:
                raise ValueError(f"Ungültige oder doppelte Regel-ID: {rule_id}.")
            seen.add(rule_id)
            if kind == "backup_rules":
                normalized["backup_rules"].append(_normalize_backup_rule(entry, rule_id))
                continue
            category = _text(entry.get("category"), "category")
            relevance = _text(entry.get("relevance"), "relevance")
            if category not in CATEGORIES or relevance not in RELEVANCE:
                raise ValueError(f"{rule_id}: Kategorie oder Hinweisstärke ungültig.")
            if category not in CRYPTO_CATEGORIES and relevance != "neutral":
                raise ValueError(f"{rule_id}: Messenger, Cloud und Banking sind keine Krypto-Hinweise.")
            # Wallet, hardware wallet and exchange rules usually carry high relevance,
            # but a deliberately conservative unknown-candidate rule may be low.
            if type(entry.get("enabled")) is not bool:
                raise ValueError(f"{rule_id}: aktiv muss ja oder nein sein.")
            common = {
                "id": rule_id,
                "name": _text(entry.get("name"), "name"),
                "category": category,
                "relevance": relevance,
                "enabled": entry["enabled"],
                "comment": str(entry.get("comment", ""))[:300],
                "status": _text(entry.get("status", "active"), "status"),
                "verified": _bool(entry.get("verified", False), "verified"),
                "source": _optional_text(entry.get("source", ""), "source"),
                "last_verified": _date(entry.get("last_verified", ""), "last_verified"),
                "regions": _optional_strings(entry.get("regions", []), "regions", limit=20),
            }
            if common["status"] not in STATUS:
                raise ValueError(f"{rule_id}: Status muss active oder legacy sein.")
            if kind == "app_rules":
                legacy_bundle_ids = entry.get("bundle_ids", [])
                ios_bundle_ids = entry.get("ios_bundle_ids", legacy_bundle_ids)
                aliases = _optional_strings(entry.get("aliases", []), "aliases")
                former_names = _optional_strings(entry.get("former_names", []), "former_names")
                normalized_ios_ids = _strings(ios_bundle_ids, "ios_bundle_ids")
                normalized_android_ids = _optional_strings(entry.get("android_package_ids", []), "android_package_ids")
                ios_id_status = _text(
                    entry.get("ios_id_status", "verified" if normalized_ios_ids and common["verified"] else "unverified"),
                    "ios_id_status",
                )
                android_id_status = _text(
                    entry.get("android_id_status", "verified" if normalized_android_ids and common["verified"] else "unverified"),
                    "android_id_status",
                )
                if ios_id_status not in PLATFORM_ID_STATUS or android_id_status not in PLATFORM_ID_STATUS:
                    raise ValueError(f"{rule_id}: Plattform-ID-Status ungültig.")
                if ios_id_status == "verified" and not normalized_ios_ids:
                    raise ValueError(f"{rule_id}: iOS-ID kann ohne Bundle-ID nicht verifiziert sein.")
                if android_id_status == "verified" and not normalized_android_ids:
                    raise ValueError(f"{rule_id}: Android-ID kann ohne Package-ID nicht verifiziert sein.")
                if ios_id_status == "not_applicable" and normalized_ios_ids:
                    raise ValueError(f"{rule_id}: iOS kann mit vorhandener Bundle-ID nicht unzutreffend sein.")
                if android_id_status == "not_applicable" and normalized_android_ids:
                    raise ValueError(f"{rule_id}: Android kann mit vorhandener Package-ID nicht unzutreffend sein.")
                common.update({
                    "ios_bundle_ids": normalized_ios_ids,
                    "android_package_ids": normalized_android_ids,
                    "ios_id_status": ios_id_status,
                    "android_id_status": android_id_status,
                    "ios_id_note": _optional_text(entry.get("ios_id_note", ""), "ios_id_note", max_length=500),
                    "android_id_note": _optional_text(entry.get("android_id_note", ""), "android_id_note", max_length=500),
                    "aliases": aliases,
                    "former_names": former_names,
                    "terms": _optional_strings(entry.get("terms", []), "terms"),
                })
                # bundle_ids remains in the serialized snapshot for backwards compatibility.
                common["bundle_ids"] = list(common["ios_bundle_ids"])
                all_names = [common["name"], *aliases, *former_names]
                if not (common["ios_bundle_ids"] or common["android_package_ids"] or any(all_names)):
                    raise ValueError(f"{rule_id}: App ohne Namen oder Bundle-ID.")
            else:
                common.update({
                    "filename_equals": _optional_strings(entry.get("filename_equals", []), "filename_equals"),
                    "terms": _optional_strings(entry.get("terms", []), "terms"),
                    "context_terms": _optional_strings(entry.get("context_terms", []), "context_terms"),
                    "extensions": [item.lstrip(".").casefold() for item in _optional_strings(entry.get("extensions", []), "extensions")],
                })
                if not (common["filename_equals"] or common["terms"]):
                    raise ValueError(f"{rule_id}: Dateiregel ohne Suchmerkmal.")
            normalized[kind].append(common)
    data = {"version": version, "deleted_default_rule_ids": deleted_default_rule_ids, **normalized}
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {**data, "sha256": hashlib.sha256(raw).hexdigest()}


def _normalize_backup_rule(entry: dict[str, Any], rule_id: str) -> dict[str, Any]:
    if type(entry.get("enabled")) is not bool:
        raise ValueError(f"{rule_id}: aktiv muss ja oder nein sein.")
    confidence = _text(entry.get("confidence", "medium"), "confidence")
    if confidence not in {"high", "medium", "low"}:
        raise ValueError(f"{rule_id}: Erkennungssicherheit ungültig.")
    return {
        "id": rule_id,
        "name": _text(entry.get("name"), "name"),
        "platform": _optional_text(entry.get("platform", ""), "platform"),
        "status": _text(entry.get("status", "active"), "status"),
        "confidence": confidence,
        "enabled": entry["enabled"],
        "required_paths": _optional_strings(entry.get("required_paths", []), "required_paths", limit=50),
        "required_files": _optional_strings(entry.get("required_files", []), "required_files", limit=50),
        "required_extensions": [item.lstrip(".").casefold() for item in _optional_strings(entry.get("required_extensions", []), "required_extensions")],
        "typical_paths": _optional_strings(entry.get("typical_paths", []), "typical_paths", limit=20),
        "source": _optional_text(entry.get("source", ""), "source"),
        "last_verified": _date(entry.get("last_verified", ""), "last_verified"),
        "comment": str(entry.get("comment", ""))[:300],
    }


def bundled_rules() -> dict[str, Any]:
    raw = package_files("forensic_triage").joinpath("data/crypto-rules.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    return snapshot(data, data.get("version"))


def load_rules(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    result = snapshot(data, data.get("version"))
    if data.get("sha256") != result["sha256"]:
        # Alpha 59 and older stored only bundle_ids. Alpha 61 did not yet store
        # deleted_default_rule_ids. Both schema migrations are deterministic and
        # must not make an otherwise valid local rule file unusable.
        legacy_schema = bool(data.get("app_rules")) and all(
            isinstance(rule, dict) and "ios_bundle_ids" not in rule and "android_package_ids" not in rule
            for rule in data.get("app_rules", [])
        )
        platform_status_schema = all(
            isinstance(rule, dict)
            and "ios_id_status" not in rule
            and "android_id_status" not in rule
            and "ios_id_note" not in rule
            and "android_id_note" not in rule
            for rule in data.get("app_rules", [])
        )
        legacy_platform_data = json.loads(json.dumps({
            key: value for key, value in result.items() if key != "sha256"
        }, ensure_ascii=False))
        for rule in legacy_platform_data["app_rules"]:
            for field in ("ios_id_status", "android_id_status", "ios_id_note", "android_id_note"):
                rule.pop(field, None)
        legacy_platform_raw = json.dumps(
            legacy_platform_data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        valid_platform_migration = (
            platform_status_schema
            and data.get("sha256") == hashlib.sha256(legacy_platform_raw).hexdigest()
        )
        if not legacy_schema and not valid_platform_migration and int(data.get("version", 0)) >= 3:
            raise ValueError("Krypto-Regeln wurden außerhalb der Einstellungen verändert oder sind beschädigt.")
    return result


def save_rules(path: Path, value: Any, base_sha256: str, default_rule_ids: frozenset[str] | None = None) -> dict[str, Any]:
    current = load_rules(path)
    if current["sha256"] != base_sha256:
        raise SettingsConflict("Regeln wurden inzwischen geändert. Einstellungen neu laden.")
    payload_deleted = set(value.get("deleted_default_rule_ids", []))
    if default_rule_ids is not None:
        # If a previously deleted default rule is re-created by the operator, the
        # tombstone is removed so the rule can be kept intentionally.
        payload_deleted -= {rule["id"] for kind in ("app_rules", "file_rules", "backup_rules") for rule in value.get(kind, []) if rule["id"] in default_rule_ids}
    updated = snapshot({**value, "deleted_default_rule_ids": sorted(payload_deleted)}, current["version"] + 1)
    atomic_write(path, (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode())
    return updated


def merge_rules(local: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Merge bundled defaults into a local rule set.

    Rules present locally keep their local state. New default rules are added.
    Default rules the user explicitly deleted (tombstones) stay removed.
    User-created rules not present in defaults are preserved.
    """
    deleted = set(local.get("deleted_default_rule_ids", []))
    local_by_kind: dict[str, dict[str, dict[str, Any]]] = {
        kind: {rule["id"]: rule for rule in local.get(kind, [])}
        for kind in ("app_rules", "file_rules", "backup_rules")
    }
    default_by_kind: dict[str, dict[str, dict[str, Any]]] = {
        kind: {rule["id"]: rule for rule in defaults.get(kind, [])}
        for kind in ("app_rules", "file_rules", "backup_rules")
    }
    result: dict[str, Any] = {"deleted_default_rule_ids": sorted(deleted)}
    for kind in ("app_rules", "file_rules", "backup_rules"):
        merged: list[dict[str, Any]] = []
        # Keep local rules unless they are a deleted default rule.
        for rule_id, rule in local_by_kind[kind].items():
            if rule_id in default_by_kind[kind] and rule_id in deleted:
                continue
            merged.append(rule)
        # Add new default rules not present locally and not deleted.
        for rule_id, rule in default_by_kind[kind].items():
            if rule_id not in local_by_kind[kind] and rule_id not in deleted:
                merged.append(rule)
        result[kind] = merged
    return result


def _migrate_legacy_seed(path: Path) -> dict[str, Any] | None:
    """One-off migration from pre-Alpha 50 iphone-triage.json, if present."""
    legacy_path = path.with_name("iphone-triage.json")
    if not legacy_path.is_file():
        return None
    try:
        old = json.loads(legacy_path.read_text(encoding="utf-8"))
        old_defaults = json.loads(package_files("forensic_triage").joinpath("data/iphone-triage.json").read_text(encoding="utf-8"))
        default_by_id = {item["id"]: item for item in old_defaults.get("app_rules", [])}
        default_files_by_id = {item["id"]: item for item in old_defaults.get("file_rules", [])}
        base = bundled_rules()
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
                    target["ios_bundle_ids"] = item.get("bundle_ids", [])
                target["aliases"] = item.get("name_contains", target["aliases"])
            elif "messenger" in category or "cloud" in category or "bank" in category:
                mapped = "messenger" if "messenger" in category else "cloud" if "cloud" in category else "banking"
                by_id[rule_id] = {
                    "id": rule_id, "name": rule_id.replace("-", " ").title(),
                    "category": mapped, "relevance": "neutral", "enabled": True,
                    "bundle_ids": item.get("bundle_ids", []),
                    "ios_bundle_ids": item.get("bundle_ids", []), "android_package_ids": [],
                    "aliases": item.get("name_contains", []), "terms": [],
                    "comment": "Aus bisheriger iPhone-Regel übernommen",
                    "status": "active", "verified": False, "source": "", "last_verified": "", "regions": [],
                }
            elif rule_id not in by_id:
                mapped = "exchange" if "börse" in category or "exchange" in category else "wallet" if "wallet" in category else "portfolio"
                aliases = item.get("name_contains", [])
                by_id[rule_id] = {
                    "id": rule_id, "name": aliases[0] if isinstance(aliases, list) and aliases else rule_id.replace("-", " ").title(),
                    "category": mapped, "relevance": "high" if mapped in {"wallet", "exchange"} else "medium",
                    "enabled": True, "bundle_ids": item.get("bundle_ids", []),
                    "ios_bundle_ids": item.get("bundle_ids", []), "android_package_ids": [],
                    "aliases": aliases[1:] if isinstance(aliases, list) else [], "terms": [],
                    "comment": "Aus älterer lokaler iPhone-Regel übernommen; bitte fachlich prüfen",
                    "status": "active", "verified": False, "source": "", "last_verified": "", "regions": [],
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
                "status": "active", "verified": False, "source": "", "last_verified": "", "regions": [],
            })
        return snapshot({"app_rules": list(by_id.values()), "file_rules": file_rules, "backup_rules": base.get("backup_rules", [])}, base["version"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def seed_rules(path: Path, legacy_path: Path | None = None) -> dict[str, Any]:
    """Ensure local crypto-rules.json exists and contains current defaults.

    Called on every startup. Existing local rules are preserved; new bundled
    defaults are added; deleted defaults stay deleted (tombstones).
    """
    defaults = bundled_rules()
    if path.exists():
        needs_platform_migration = False
        try:
            raw_local = json.loads(path.read_text(encoding="utf-8"))
            needs_platform_migration = all(
                isinstance(rule, dict)
                and "ios_id_status" not in rule
                and "android_id_status" not in rule
                and "ios_id_note" not in rule
                and "android_id_note" not in rule
                for rule in raw_local.get("app_rules", [])
            )
            local = load_rules(path)
        except (OSError, ValueError, json.JSONDecodeError):
            local = snapshot({"app_rules": [], "file_rules": [], "backup_rules": []}, defaults["version"])
        merged = merge_rules(local, defaults)
        # Preserve local version if nothing changed to avoid unnecessary writes.
        if (
            not needs_platform_migration
            and
            {rule["id"] for kind in ("app_rules", "file_rules", "backup_rules") for rule in local.get(kind, [])}
            == {rule["id"] for kind in ("app_rules", "file_rules", "backup_rules") for rule in merged[kind]}
            and set(local.get("deleted_default_rule_ids", [])) == set(merged["deleted_default_rule_ids"])
            and len(merged["app_rules"]) == len(local.get("app_rules", []))
            and len(merged["file_rules"]) == len(local.get("file_rules", []))
            and len(merged["backup_rules"]) == len(local.get("backup_rules", []))
        ):
            return local
        updated = snapshot(merged, local["version"] + 1)
        atomic_write(path, (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode())
        return updated
    # First install: try legacy iphone-triage.json migration, otherwise use defaults.
    base = _migrate_legacy_seed(legacy_path or path.with_name("iphone-triage.json"))
    if base is None:
        base = defaults
    atomic_write(path, (json.dumps(base, ensure_ascii=False, indent=2) + "\n").encode())
    return base


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Cf").casefold()


def _term_in_path(term: str, path: str) -> bool:
    term = _fold(term).replace("_", " ").replace("-", " ")
    path = _fold(path).replace("_", " ").replace("-", " ")
    return bool(re.search(r"(?<!\w)" + re.escape(term).replace(r"\ ", r"\s+") + r"(?!\w)", path))


def classify_app(app: dict[str, Any], rules: dict[str, Any]) -> list[dict[str, str]]:
    platform = _fold(str(app.get("platform", "ios")))
    app_id = _fold(str(app.get("app_id") or app.get("package_id") or app.get("bundle_id", "")))
    name = _fold(str(app.get("name", "")))
    matches = []
    for rule in rules.get("app_rules", []):
        if not rule["enabled"]:
            continue
        reason = ""
        identifiers = rule.get("android_package_ids", []) if platform == "android" else rule.get("ios_bundle_ids", rule.get("bundle_ids", []))
        if app_id and app_id in {_fold(value) for value in identifiers}:
            label = "Package-ID" if platform == "android" else "Bundle-ID"
            reason = f"{label}: {app_id}"
        elif name and name in {_fold(value) for value in [rule["name"], *rule.get("aliases", []), *rule.get("former_names", [])]}:
            reason = f"App-Name: {app['name']}"
        elif any(_term_in_path(term, name) for term in rule.get("terms", [])):
            reason = f"Suchbegriff im App-Namen: {app['name']}"
        if reason:
            matches.append({key: str(rule[key]) for key in ("id", "name", "category", "relevance", "status")} | {"reason": reason})
    return matches


def classify_file(path: str, extension: str, rules: dict[str, Any]) -> list[dict[str, str]]:
    name = path.rsplit("/", 1)[-1]
    matches = []
    for rule in rules.get("file_rules", []):
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
        matches.append({key: str(rule[key]) for key in ("id", "name", "category", "relevance", "status")} | {"reason": reason})
    return matches


def find_file_hints(files: list[dict[str, Any]], rules: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"path": str(item["path"]), "source": str(item.get("source", "medium")), "matches": matches}
        for item in files
        if (matches := classify_file(str(item["path"]), str(item.get("extension", "")), rules))
    ]
