"""Bounded, metadata-only iPhone triage through normal Apple USB services."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import plistlib
import re
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from .commands import run_command
from .container_inventory import empty_catalog
from .crypto_rules import CRYPTO_CATEGORIES, classify_app as classify_app_rule, classify_file as classify_file_rule
from .keywords import build_hits, load_profile
from .reporting import write_files_csv, write_json
from .settings import apply_catalog, catalog_snapshot, load_catalog
from .statistics import summarize


REQUIRED_TOOLS = ("idevice_id", "ideviceinfo", "idevicepair", "ideviceinstaller", "ifuse")


def _limit(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


def tools_available() -> bool:
    return all(shutil.which(name) for name in REQUIRED_TOOLS)


def _run(args: list[str], *, timeout: float = 10, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_command(args, check=check, capture_output=True, timeout=timeout)


def _plist(raw: str) -> Any:
    start = raw.find("<?xml")
    if start < 0:
        start = raw.find("bplist00")
    if start < 0:
        raise ValueError("Werkzeug lieferte keine lesbaren Apple-Metadaten.")
    return plistlib.loads(raw[start:].encode("utf-8", errors="replace"))


def list_iphone_udids() -> list[str]:
    if not shutil.which("idevice_id"):
        return []
    result = _run(["idevice_id", "-l"], timeout=3, check=False)
    return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})


def _friendly_connection_error(text: str) -> tuple[str, str]:
    lowered = text.casefold()
    if "password protected" in lowered or "locked" in lowered:
        return "locked", "iPhone entsperren und Bildschirm eingeschaltet lassen."
    if "trust" in lowered or "pair" in lowered or "invalid host" in lowered:
        return "trust_required", "iPhone entsperren und „Diesem Computer vertrauen“ bestätigen."
    return "unavailable", "iPhone-Verbindung prüfen, entsperren und Vertrauen bestätigen."


def probe_iphone(udid: str) -> dict[str, Any]:
    validate = _run(["idevicepair", "-u", udid, "validate"], timeout=4, check=False)
    connection_state = "paired" if validate.returncode == 0 else _friendly_connection_error(
        f"{validate.stdout}\n{validate.stderr}"
    )[0]
    info: dict[str, Any] = {}
    if connection_state == "paired":
        response = _run(["ideviceinfo", "-u", udid, "-x"], timeout=5, check=False)
        if response.returncode == 0:
            try:
                loaded = _plist(response.stdout)
                if isinstance(loaded, dict):
                    info = loaded
            except (ValueError, plistlib.InvalidFileException):
                connection_state = "unavailable"
        else:
            connection_state = _friendly_connection_error(f"{response.stdout}\n{response.stderr}")[0]
    available = tools_available()
    reason = "" if connection_state == "paired" else _friendly_connection_error(
        f"{validate.stdout}\n{validate.stderr}"
    )[1]
    if not available:
        reason = "iPhone-Unterstützung unvollständig installiert; Systempakete prüfen."
    product_type = str(info.get("ProductType", "iPhone"))
    name = str(info.get("DeviceName", "iPhone"))
    reported_serial = str(info.get("SerialNumber") or "")
    return {
        "path": f"iphone:{udid}", "size": 0, "vendor": "Apple", "model": product_type,
        "device_name": name, "serial": reported_serial, "udid": udid,
        "model_number": str(info.get("ModelNumber") or ""),
        "hardware_model": str(info.get("HardwareModel") or ""),
        "ios_version": str(info.get("ProductVersion", "")),
        "build_version": str(info.get("BuildVersion", "")),
        "connection_state": connection_state, "media_type": "iphone", "mounted": False,
        "read_only": False, "scan_supported": available, "unavailable_reason": reason,
    }


def discover_iphones() -> list[dict[str, Any]]:
    return [probe_iphone(udid) for udid in list_iphone_udids()]


def ensure_paired(udid: str) -> dict[str, Any]:
    current = probe_iphone(udid)
    if current["connection_state"] == "paired":
        return current
    deadline = time.monotonic() + _limit("FORENSIC_TRIAGE_IPHONE_PAIR_TIMEOUT_SECONDS", 45)
    last = ""
    while time.monotonic() < deadline:
        result = _run(["idevicepair", "-u", udid, "pair"], timeout=6, check=False)
        last = f"{result.stdout}\n{result.stderr}"
        device = probe_iphone(udid)
        if device["connection_state"] == "paired":
            return device
        time.sleep(1.5)
    state, guidance = _friendly_connection_error(last)
    raise RuntimeError(f"PAIRING FEHLGESCHLAGEN ({state.upper()}): {guidance}")


def _application_plist(udid: str) -> tuple[list[dict[str, Any]], str]:
    commands = [
        ["ideviceinstaller", "-u", udid, "list", "--user", "--xml"],
        ["ideviceinstaller", "-u", udid, "-l", "-o", "list_user", "-o", "xml"],
    ]
    errors = []
    for command in commands:
        result = _run(command, timeout=20, check=False)
        if result.returncode:
            errors.append((result.stderr or result.stdout).strip())
            continue
        try:
            data = _plist(result.stdout)
        except (ValueError, plistlib.InvalidFileException) as exc:
            errors.append(str(exc))
            continue
        rows = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
        return [item for item in rows if isinstance(item, dict)], "complete"
    return [], "incomplete: " + (errors[-1] if errors else "App-Liste nicht verfügbar")


def file_sharing_bundle_ids(udid: str) -> tuple[set[str], str]:
    """Return the app IDs that ifuse reports as regular File Sharing targets."""
    result = _run(["ifuse", "--udid", udid, "--list-apps"], timeout=15, check=False)
    if result.returncode:
        return set(), "incomplete: " + ((result.stderr or result.stdout).strip() or "File-Sharing-Liste nicht verfügbar")
    try:
        data = _plist(result.stdout)
        rows = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
        return {
            str(item.get("CFBundleIdentifier") or item.get("bundle_id") or "")
            for item in rows if isinstance(item, dict) and (item.get("CFBundleIdentifier") or item.get("bundle_id"))
        }, "complete"
    except (ValueError, plistlib.InvalidFileException):
        # Some ifuse builds use a simple tabular list. Bundle identifiers do
        # not contain whitespace; take the first bundle-shaped field only.
        return set(re.findall(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+", result.stdout)), "complete"


def load_rules(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("app_rules"), list) or not isinstance(data.get("file_rules"), list):
        raise ValueError("Ungültige iPhone-Erkennungsregeln.")
    return data


def classify_app(app: dict[str, Any], rules: dict[str, Any]) -> list[dict[str, str]]:
    bundle = str(app.get("bundle_id", ""))
    name = str(app.get("name", "")).casefold()
    matches = []
    for rule in rules["app_rules"]:
        exact = bundle in rule.get("bundle_ids", [])
        prefix = any(bundle.startswith(value) for value in rule.get("bundle_prefixes", []))
        named = any(value.casefold() in name for value in rule.get("name_contains", []))
        if exact or prefix or named:
            matches.append({"id": str(rule["id"]), "category": str(rule["category"])})
    return matches


def normalize_apps(rows: list[dict[str, Any]], rules: dict[str, Any]) -> list[dict[str, Any]]:
    apps = []
    for row in rows:
        app = {
            "name": str(row.get("CFBundleDisplayName") or row.get("CFBundleName") or row.get("CFBundleIdentifier") or "Unbekannte App"),
            "bundle_id": str(row.get("CFBundleIdentifier") or ""),
            "version": str(row.get("CFBundleShortVersionString") or row.get("CFBundleVersion") or ""),
            "file_sharing": bool(row.get("UIFileSharingEnabled") or row.get("UISupportsDocumentBrowser")),
        }
        app["matches"] = classify_app_rule(app, rules) if "sha256" in rules else classify_app(app, rules)
        apps.append(app)
    return sorted(apps, key=lambda item: (item["name"].casefold(), item["bundle_id"]))


def classify_file_hint(path: str, extension: str, rules: dict[str, Any]) -> list[dict[str, str]]:
    folded = path.casefold()
    matches = []
    for rule in rules["file_rules"]:
        path_match = any(value.casefold() in folded for value in rule.get("path_contains", []))
        extension_match = extension.casefold() in {str(value).casefold() for value in rule.get("extensions", [])}
        if path_match and extension_match:
            matches.append({"id": str(rule["id"]), "label": str(rule["label"])})
    return matches


def _mount_is_read_only(mountpoint: Path) -> bool:
    target = str(mountpoint.resolve()).replace("\\040", " ")
    try:
        for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
            before, separator, _after = line.partition(" - ")
            fields = before.split()
            if separator and len(fields) >= 6 and fields[4].replace("\\040", " ") == target:
                return "ro" in fields[5].split(",")
    except OSError:
        return False
    return False


@contextmanager
def readonly_ifuse(udid: str, documents: str | None = None) -> Iterator[Path]:
    mountpoint = Path(tempfile.mkdtemp(prefix="triage-iphone-"))
    command = ["ifuse", "--udid", udid]
    if documents:
        command.extend(["--documents", documents])
    command.extend(["-o", "ro", str(mountpoint)])
    try:
        result = _run(command, timeout=15, check=False)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout).strip() or "iPhone-Dateibereich nicht zugänglich.")
        if not _mount_is_read_only(mountpoint):
            raise RuntimeError("Nur-Lese-Einbindung konnte nicht verifiziert werden; Bereich wurde nicht untersucht.")
        yield mountpoint
    finally:
        for binary in ("fusermount3", "fusermount"):
            if shutil.which(binary):
                _run([binary, "-u", str(mountpoint)], timeout=5, check=False)
                break
        try:
            mountpoint.rmdir()
        except OSError:
            # Never recursively delete a mountpoint: a failed unmount must not
            # turn cleanup into writes against the connected device.
            pass


def inventory_tree(root: Path, prefix: str, rules: dict[str, Any], *, deadline: float, max_files: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], bool]:
    files: list[dict[str, Any]] = []
    directories: list[dict[str, Any]] = []
    hints: list[dict[str, Any]] = []
    truncated = False
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort(key=str.casefold)
        filenames.sort(key=str.casefold)
        relative_dir = Path(current).relative_to(root)
        for dirname in dirnames:
            directories.append({"partition_slot": "IPHONE", "path": str(Path(prefix) / relative_dir / dirname)})
        for filename in filenames:
            if len(files) >= max_files or time.monotonic() >= deadline:
                truncated = True
                return files, directories, hints, truncated
            path = Path(current) / filename
            try:
                stat = path.lstat()
            except OSError:
                continue
            if not path.is_file() or path.is_symlink():
                continue
            logical = (Path(prefix) / relative_dir / filename).as_posix()
            extension = Path(filename).suffix.removeprefix(".").casefold()
            item = {
                "partition_slot": "IPHONE", "path": logical, "source": "iphone_accessible_metadata",
                "size": stat.st_size, "original_extension": Path(filename).suffix.removeprefix("."),
                "extension": extension, "mtime": int(stat.st_mtime), "atime": "", "ctime": "", "crtime": "",
                "uid": "", "gid": "", "metadata_address": "", "tsk_type": "r/r",
            }
            files.append(item)
            matches = classify_file_rule(logical, extension, rules) if "sha256" in rules else classify_file_hint(logical, extension, rules)
            for match in matches:
                hints.append({"path": logical, "size": stat.st_size, **match})
    return files, directories, hints, truncated


def scan_iphone(request: dict[str, Any]) -> Path:
    started = time.monotonic()
    udid = str(request["udid"])
    evidence = str(request["evidence"])
    results_root = Path(request["results_root"])
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
    safe_evidence = "".join(char if char.isalnum() or char in "-_" else "_" for char in evidence)
    result_dir = results_root / f"{timestamp}_{safe_evidence}"
    raw_dir = result_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=False)
    logger = logging.getLogger(f"forensic-triage.iphone.{timestamp}.{safe_evidence}")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(result_dir / "scan.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    try:
        logger.info("iPhone metadata scan start evidence=%s udid=%s", evidence, udid)
        rules = request.get("crypto_rules") or request["iphone_rules"]
        catalog = catalog_snapshot(request["filetype_catalog"]["categories"], request["filetype_catalog"]["version"])
        device = ensure_paired(udid)
        device.update({
            "evidence": evidence, "scan_mode": "iphone_metadata", "read_only_verified": False,
            "access_mode": "apple_services_metadata_read_only", "write_operations_performed": False,
        })
        write_json(result_dir / "device.json", device)
        write_json(result_dir / "filetype-catalog.json", catalog)
        write_json(result_dir / "crypto-rules.json", rules)
        app_rows, app_status = _application_plist(udid)
        app_limit = _limit("FORENSIC_TRIAGE_IPHONE_MAX_APPS", 500)
        if len(app_rows) > app_limit:
            app_status = f"incomplete: App-Limit {app_limit} erreicht"
        apps = normalize_apps(app_rows[:app_limit], rules)
        shared_bundles, file_sharing_status = file_sharing_bundle_ids(udid)
        for app in apps:
            app["file_sharing"] = app["file_sharing"] or app["bundle_id"] in shared_bundles
        files: list[dict[str, Any]] = []
        directories: list[dict[str, Any]] = []
        file_hints: list[dict[str, Any]] = []
        areas: list[dict[str, Any]] = []
        deadline = time.monotonic() + _limit("FORENSIC_TRIAGE_IPHONE_METADATA_SECONDS", 60)
        max_files = _limit("FORENSIC_TRIAGE_IPHONE_MAX_FILES", 20000)

        targets: list[tuple[str, str | None]] = [("AFC_MEDIA", None)]
        targets.extend(
            (f"APP_DOKUMENTE/{app['bundle_id']}", app["bundle_id"])
            for app in apps if app["file_sharing"] and app["bundle_id"]
        )
        for prefix, bundle_id in targets[:1 + _limit("FORENSIC_TRIAGE_IPHONE_MAX_SHARED_APPS", 50)]:
            if time.monotonic() >= deadline or len(files) >= max_files:
                areas.append({"area": prefix, "status": "not_checked_limit", "message": "Triage-Limit erreicht."})
                continue
            try:
                with readonly_ifuse(udid, bundle_id) as mountpoint:
                    found, found_dirs, hints, truncated = inventory_tree(
                        mountpoint, prefix, rules, deadline=deadline, max_files=max_files - len(files),
                    )
                files.extend(found); directories.extend(found_dirs); file_hints.extend(hints)
                areas.append({"area": prefix, "status": "partial" if truncated else "complete", "file_count": len(found)})
            except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                logger.warning("area unavailable %s: %s", prefix, exc)
                areas.append({"area": prefix, "status": "unavailable", "message": str(exc)[:300]})

        containers = empty_catalog("not_opened_on_iphone")
        apply_catalog(files, containers, catalog)
        keywords = list(request.get("keywords") or [])
        hits = build_hits(files, keywords)
        sources = list(request.get("profile_sources") or [])
        if not sources:
            profile = load_profile(Path(request["profile_path"]))
            sources = [{key: profile[key] for key in ("id", "name", "version", "sha256")}]
        hits["profile"] = {"version": "combined" if len(sources) > 1 else sources[0]["version"], "sha256": hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(), "sources": sources, "selected_keywords": keywords}
        app_hints = [
            {"name": app["name"], "bundle_id": app["bundle_id"], "version": app["version"], **match}
            for app in apps for match in app["matches"] if match.get("category") in CRYPTO_CATEGORIES
        ]
        crypto_file_hints = [hint for hint in file_hints if hint.get("category") in CRYPTO_CATEGORIES]
        write_json(result_dir / "crypto-hints.json", {
            "rules": {"version": rules.get("version"), "sha256": rules.get("sha256")},
            "app_hints": app_hints, "file_hints": crypto_file_hints,
        })
        complete = app_status == "complete" and file_sharing_status == "complete" and all(area["status"] == "complete" for area in areas)
        assessment = "Relevante Hinweise vorhanden – weitere Untersuchung empfohlen" if app_hints or file_hints else (
            "Keine relevanten Hinweise in den zugänglichen Metadaten" if complete else "Erfassung unvollständig – keine abschließende Aussage möglich"
        )
        iphone = {
            "device": {key: device.get(key, "") for key in ("device_name", "model", "model_number", "hardware_model", "serial", "ios_version", "build_version", "udid", "connection_state")},
            "apps": apps, "apps_status": app_status, "file_sharing_status": file_sharing_status, "app_hints": app_hints,
            "file_hints": crypto_file_hints, "areas": areas, "complete": complete, "assessment": assessment,
            "notice": "App- und Dateihinweise sind Triage-Indikatoren und kein Nachweis für Vermögenswerte oder Dateiinhalte.",
        }
        summary = summarize(files, directories)
        summary.update({
            "evidence": evidence, "scan_started_utc": timestamp, "duration_seconds": round(time.monotonic() - started, 3),
            "scan_mode": "iphone_metadata", "filetype_catalog": {"version": catalog["version"], "sha256": catalog["sha256"]},
            "keyword_matches": hits["total_matches"], "archive_encryption": {"total": 0, "encrypted": 0, "unknown": 0},
            "container_index": {"status": "not_opened_on_iphone", "containers_seen": 0, "containers_indexed": 0, "entries_indexed": 0, "duration_seconds": 0, "truncated": False},
            "iphone": {"app_hint_count": len(app_hints), "file_hint_count": len(crypto_file_hints), "complete": complete, "assessment": assessment},
            "crypto_rules": {"version": rules.get("version"), "sha256": rules.get("sha256")},
            "crypto_file_hints": len(crypto_file_hints),
        })
        write_json(result_dir / "iphone.json", iphone)
        write_json(result_dir / "apps.json", {"status": app_status, "apps": apps})
        write_json(result_dir / "partitions.json", [])
        write_json(result_dir / "container-index.json", containers)
        write_files_csv(result_dir / "files.csv", files)
        write_json(result_dir / "hits.json", hits)
        write_json(result_dir / "summary.json", summary)
        logger.info(
            "iPhone metadata scan complete apps=%d files=%d app_hints=%d file_hints=%d complete=%s",
            len(apps), len(files), len(app_hints), len(file_hints), complete,
        )
        return result_dir
    finally:
        logger.removeHandler(handler)
        handler.close()
