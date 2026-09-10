"""Local-only web operator interface for the triage scanner."""

from __future__ import annotations

import argparse
import io
import json
import logging
import math
import os
import re
import shlex
import subprocess
import tempfile
import threading
import time
import zipfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from . import __version__
from .casefiles import CaseStore
from .commands import run_command
from .keywords import PROFILE_ID_PATTERN, list_profiles, load_profile, save_profile
from .scan_process import ScanTimeoutError, run_isolated_scan
from .settings import SettingsConflict, atomic_write, default_catalog, load_catalog, prepare_profiles, save_catalog


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEB_ROOT = PROJECT_ROOT / "web"
EVIDENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
OPERATOR_PATTERN = re.compile(r"^[^\x00-\x1f]{0,120}$")
ACTIVE_DEVICES_LOCK = threading.Lock()
ACTIVE_DEVICES: set[str] = set()
QUARANTINED_DEVICES: set[str] = set()
CASE_SESSION_LOCK = threading.Lock()
ACTIVE_CASE_SESSION: dict[str, str] | None = None
DEVICE_DISCOVERY_LOCK = threading.Lock()
DEVICE_DISCOVERY_UNHEALTHY_UNTIL = 0.0
LAST_DEVICE_DISCOVERY: list[dict[str, Any]] = []
LAST_DEVICE_DISCOVERY_ERROR = ""
POWER_STATUS_LOCK = threading.Lock()
LAST_POWER_STATUS: dict[str, Any] = {}
LAST_POWER_STATUS_AT = 0.0
LAST_LOGGED_POWER_STATE = ""
POWER_ACTION_LOCK = threading.Lock()
POWER_ACTION_REQUESTED = ""


def _env_float(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, ""))
    except ValueError:
        return default
    return value if math.isfinite(value) and value > 0 else default


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default


def parse_throttled_status(output: str) -> dict[str, Any]:
    """Turn Raspberry Pi's get_throttled bitmask into an honest UI state."""
    match = re.fullmatch(r"\s*throttled=(0x[0-9a-fA-F]+)\s*", output)
    if not match:
        raise ValueError("Ungültige Spannungsstatus-Antwort.")
    mask = int(match.group(1), 16)
    current = bool(mask & 1)
    occurred = bool(mask & (1 << 16))
    throttled = bool(mask & (1 << 2))
    throttled_before = bool(mask & (1 << 18))
    state = "danger" if current or throttled else "warning" if occurred or throttled_before else "ok"
    if current:
        label = "UNTERSPANNUNG AKTIV"
    elif throttled:
        label = "LEISTUNG GEDROSSELT"
    elif occurred:
        label = "UNTERSPANNUNG AUFGETRETEN"
    elif throttled_before:
        label = "DROSSELUNG AUFGETRETEN"
    else:
        label = "STROM OK"
    return {
        "state": state,
        "label": label,
        "current_undervoltage": current,
        "undervoltage_since_boot": occurred,
        "current_throttling": throttled,
        "throttling_since_boot": throttled_before,
        "raw": match.group(1).lower(),
    }


def read_power_status(force: bool = False) -> dict[str, Any]:
    """Read and briefly cache Pi power health without delaying every status poll."""
    global LAST_POWER_STATUS, LAST_POWER_STATUS_AT, LAST_LOGGED_POWER_STATE
    now = time.monotonic()
    with POWER_STATUS_LOCK:
        if not force and LAST_POWER_STATUS and now - LAST_POWER_STATUS_AT < 5:
            return dict(LAST_POWER_STATUS)
        try:
            completed = subprocess.run(
                ["/usr/bin/vcgencmd", "get_throttled"], check=True,
                capture_output=True, text=True, timeout=2,
            )
            status = parse_throttled_status(completed.stdout)
        except (OSError, ValueError, subprocess.SubprocessError):
            status = {
                "state": "unknown", "label": "STROMSTATUS UNBEKANNT",
                "current_undervoltage": None, "undervoltage_since_boot": None,
                "current_throttling": None, "throttling_since_boot": None, "raw": "",
            }
        state_key = f"{status['state']}:{status.get('raw', '')}"
        if state_key != LAST_LOGGED_POWER_STATE:
            log = logging.warning if status["state"] in {"danger", "warning"} else logging.info
            log("power health changed: %s (%s)", status["label"], status.get("raw") or "unavailable")
            LAST_LOGGED_POWER_STATE = state_key
        LAST_POWER_STATUS = status
        LAST_POWER_STATUS_AT = now
        return dict(status)


def _mountpoints(node: dict[str, Any]) -> list[str]:
    points = [point for point in (node.get("mountpoints") or []) if point]
    for child in node.get("children") or []:
        points.extend(_mountpoints(child))
    return points


def parse_media_devices(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert lsblk nodes into operator-facing removable media records."""
    devices: list[dict[str, Any]] = []
    # Linux device names depend on discovery order. Never assume that /dev/sda
    # is the operating-system disk: exclude the top-level device that actually
    # contains the mounted root filesystem instead.
    system_device_paths = {
        str(node.get("path", ""))
        for node in nodes
        if "/" in _mountpoints(node)
    }
    for node in nodes:
        device_type = str(node.get("type", ""))
        transport = str(node.get("tran", ""))
        is_usb = (
            device_type == "disk"
            and transport == "usb"
            and str(node.get("path", "")) not in system_device_paths
            and int(node.get("size") or 0) > 0
        )
        # The field unit uses external USB optical drives. Ignore internal or
        # VM system discs (for example Proxmox cloud-init media on SATA).
        is_optical = device_type == "rom" and transport == "usb"
        if not (is_usb or is_optical):
            continue
        mounted = bool(_mountpoints(node))
        has_medium = int(node.get("size") or 0) > 0
        supported = (is_usb or (is_optical and has_medium)) and not mounted
        reason = ""
        if is_optical and not has_medium:
            reason = "Kein lesbares Medium im CD/DVD-Laufwerk"
        elif mounted:
            reason = "Medium ist bereits eingehängt"
        reported_serial = (node.get("serial") or "").strip()
        if is_optical and has_medium:
            volume_id = (node.get("uuid") or "").strip()
            volume_label = (node.get("label") or "").strip()
            reported_serial = "OPTICAL:" + ":".join(
                part for part in (volume_id, volume_label, str(node.get("size") or 0)) if part
            )
        devices.append({
            "path": node.get("path"),
            "size": node.get("size", 0),
            "vendor": (node.get("vendor") or "").strip(),
            "model": (node.get("model") or "").strip(),
            "serial": reported_serial,
            "read_only": bool(node.get("ro")),
            "mounted": mounted,
            "media_type": "optical" if is_optical else "usb",
            "scan_supported": supported,
            "unavailable_reason": reason,
        })
    return devices


def device_discovery_timeout_seconds() -> float:
    """Return the short deadline for dashboard device inventory commands."""
    return _env_float("FORENSIC_TRIAGE_DEVICE_DISCOVERY_TIMEOUT_SECONDS", 2.0)


def device_discovery_backoff_seconds() -> float:
    """Return the pause after a timed-out device inventory command."""
    return _env_float("FORENSIC_TRIAGE_DEVICE_DISCOVERY_BACKOFF_SECONDS", 10.0)


def list_block_devices(timeout: float | None = None) -> list[dict[str, Any]]:
    """Read the current kernel block-device inventory."""
    completed = run_command(
        [
            "lsblk", "--json", "--bytes", "--output",
            "NAME,PATH,TYPE,TRAN,SIZE,VENDOR,MODEL,SERIAL,UUID,LABEL,RO,MOUNTPOINTS",
        ],
        check=True,
        text=True,
        capture_output=True,
        timeout=timeout if timeout is not None else device_discovery_timeout_seconds(),
    )
    return json.loads(completed.stdout).get("blockdevices", [])


def discover_media_devices() -> list[dict[str, Any]]:
    """Return USB media and visible optical drives without touching their contents."""
    return parse_media_devices(list_block_devices())


def cached_media_discovery(*, reactivate: bool = False) -> tuple[list[dict[str, Any]], str, list[str]]:
    """Return media inventory without hammering a blocked USB/SCSI stack."""
    global DEVICE_DISCOVERY_UNHEALTHY_UNTIL, LAST_DEVICE_DISCOVERY, LAST_DEVICE_DISCOVERY_ERROR
    if not DEVICE_DISCOVERY_LOCK.acquire(blocking=False):
        return [dict(item) for item in LAST_DEVICE_DISCOVERY], "Datenträgererkennung läuft noch; letzter bekannter Stand.", []
    try:
        if time.monotonic() < DEVICE_DISCOVERY_UNHEALTHY_UNTIL:
            return [dict(item) for item in LAST_DEVICE_DISCOVERY], LAST_DEVICE_DISCOVERY_ERROR, []
        reactivated = []
        try:
            if reactivate:
                for path in ejected_usb_paths(list_block_devices()):
                    run_command(["/usr/bin/eject", "-t", path], capture_output=True, timeout=2.0)
                    reactivated.append(path)
                if reactivated:
                    run_command(["/usr/bin/udevadm", "settle"], capture_output=True, timeout=2.0)
            devices = discover_media_devices()
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            LAST_DEVICE_DISCOVERY_ERROR = f"Datenträgererkennung blockiert oder nicht verfügbar: {exc}"
            DEVICE_DISCOVERY_UNHEALTHY_UNTIL = time.monotonic() + device_discovery_backoff_seconds()
            return [dict(item) for item in LAST_DEVICE_DISCOVERY], LAST_DEVICE_DISCOVERY_ERROR, reactivated
        LAST_DEVICE_DISCOVERY = [dict(item) for item in devices]
        LAST_DEVICE_DISCOVERY_ERROR = ""
        DEVICE_DISCOVERY_UNHEALTHY_UNTIL = 0.0
        return devices, "", reactivated
    finally:
        DEVICE_DISCOVERY_LOCK.release()


def ejected_usb_paths(nodes: list[dict[str, Any]]) -> list[str]:
    """Return validated USB disk nodes whose medium was software-ejected."""
    system_device_paths = {
        str(node.get("path", ""))
        for node in nodes
        if "/" in _mountpoints(node)
    }
    return [
        str(node["path"])
        for node in nodes
        if node.get("type") == "disk"
        and node.get("tran") == "usb"
        and int(node.get("size") or 0) == 0
        and re.fullmatch(r"/dev/sd[a-z]+", str(node.get("path", "")))
        and str(node.get("path", "")) not in system_device_paths
    ]


def _device_ejectable(device: dict[str, Any]) -> bool:
    """Allow an empty external optical tray to open without weakening USB checks."""
    if device.get("mounted"):
        return False
    return bool(device.get("scan_supported") or device.get("media_type") == "optical")


def active_device_paths() -> list[str]:
    with ACTIVE_DEVICES_LOCK:
        return sorted(ACTIVE_DEVICES)


def claim_device(path: str) -> bool:
    with ACTIVE_DEVICES_LOCK:
        if path in ACTIVE_DEVICES:
            return False
        ACTIVE_DEVICES.add(path)
        return True


def release_device(path: str) -> None:
    with ACTIVE_DEVICES_LOCK:
        ACTIVE_DEVICES.discard(path)


def quarantine_device(path: str) -> None:
    with ACTIVE_DEVICES_LOCK:
        QUARANTINED_DEVICES.add(path)


def quarantined_device_paths() -> list[str]:
    with ACTIVE_DEVICES_LOCK:
        return sorted(QUARANTINED_DEVICES)


def clear_absent_quarantines(devices: list[dict[str, Any]]) -> None:
    """A timed-out path becomes eligible again only after it disappeared once."""
    present = {str(device.get("path", "")) for device in devices}
    with ACTIVE_DEVICES_LOCK:
        QUARANTINED_DEVICES.intersection_update(present)


def active_case_session() -> dict[str, str] | None:
    with CASE_SESSION_LOCK:
        return dict(ACTIVE_CASE_SESSION) if ACTIVE_CASE_SESSION else None


def set_active_case_session(case_number: str, operator: str) -> None:
    global ACTIVE_CASE_SESSION
    with CASE_SESSION_LOCK:
        ACTIVE_CASE_SESSION = {"case_number": case_number, "operator": operator}


def clear_active_case_session() -> None:
    global ACTIVE_CASE_SESSION
    with CASE_SESSION_LOCK:
        ACTIVE_CASE_SESSION = None


def read_update_status() -> dict[str, str]:
    """Read the root-only updater result without evaluating its shell syntax."""
    state_file = Path(os.environ.get(
        "FORENSIC_TRIAGE_UPDATE_STATE_FILE", "/var/lib/forensic-triage/update-status.env",
    ))
    default = {
        "state": "unknown", "message": "UPDATE NOCH NICHT GEPRÜFT",
        "available_version": "", "current_version": __version__, "updated_at": "",
    }
    try:
        for line in state_file.read_text(encoding="utf-8").splitlines():
            if "=" not in line:
                continue
            parsed = shlex.split(line, comments=False, posix=True)
            if len(parsed) != 1 or "=" not in parsed[0]:
                continue
            key, value = parsed[0].split("=", 1)
            mapped = {
                "STATE": "state", "MESSAGE": "message", "AVAILABLE_VERSION": "available_version",
                "CURRENT_VERSION": "current_version", "UPDATED_AT": "updated_at",
            }.get(key)
            if mapped:
                if mapped == "current_version" and not value:
                    continue
                default[mapped] = value
    except (OSError, ValueError):
        pass
    return default


def update_job_states() -> dict[str, bool]:
    """Return whether a deliberate update worker is currently active."""
    states: dict[str, bool] = {}
    for action in ("check", "install", "offline"):
        try:
            completed = subprocess.run(
                ["/usr/bin/systemctl", "is-active", "--quiet", f"forensic-triage-update@{action}.service"],
                check=False, capture_output=True, timeout=2,
            )
            states[action] = completed.returncode == 0
        except (OSError, subprocess.SubprocessError):
            states[action] = False
    return states


def latest_result(results_root: Path) -> dict[str, Any] | None:
    """Load the newest complete result set, if one exists."""
    candidates = sorted(
        (path for path in results_root.iterdir() if path.is_dir()),
        reverse=True,
    ) if results_root.exists() else []
    for result_dir in candidates:
        summary_path = result_dir / "summary.json"
        hits_path = result_dir / "hits.json"
        if summary_path.is_file() and hits_path.is_file():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            hits_data = json.loads(hits_path.read_text(encoding="utf-8"))
            return {
                "id": result_dir.name,
                "summary": summary,
                "hits": {
                    word: int(details.get("count", 0))
                    for word, details in hits_data.get("by_keyword", {}).items()
                },
            }
    return None


class TriageHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        web_root: Path,
        results_root: Path,
        profile_path: Path,
        casefiles_root: Path,
        scan_timeout_seconds: float,
        command_timeout_seconds: float,
    ) -> None:
        super().__init__(address, TriageHandler)
        self.web_root = web_root
        self.results_root = results_root
        self.settings_root = Path(os.environ.get("FORENSIC_TRIAGE_SETTINGS_ROOT", str(casefiles_root.parent / "settings")))
        # The updater before Alpha 44 cannot run the new migration helper. On
        # first start, therefore, prefer profiles from the newest prior release
        # before falling back to the original checkout and bundled defaults.
        configured_profile_dir = profile_path.parent.resolve()
        current_release_profile_dir = (PROJECT_ROOT / "profiles").resolve()
        releases_value = os.environ.get("FORENSIC_TRIAGE_RELEASES_ROOT", "").strip()
        if releases_value:
            releases_root = Path(releases_value)
            if releases_root.is_dir() and releases_root != Path("/"):
                release_profile_dirs = sorted(
                    (
                        path
                        for path in releases_root.glob("*/profiles")
                        if path.is_dir()
                        and path.resolve() not in {configured_profile_dir, current_release_profile_dir}
                    ),
                    key=lambda path: path.stat().st_mtime_ns,
                    reverse=True,
                )
                for release_profile_dir in release_profile_dirs:
                    candidate = release_profile_dir / profile_path.name
                    if candidate.is_file():
                        prepare_profiles(self.settings_root, candidate)
        original = casefiles_root.parent / "profiles" / profile_path.name
        if (original.is_file() and original.parent != profile_path.parent
                and configured_profile_dir == current_release_profile_dir):
            prepare_profiles(self.settings_root, original)
        self.profile_path = prepare_profiles(self.settings_root, profile_path)
        self.catalog_path = self.settings_root / "filetypes.json"
        if not self.catalog_path.exists():
            atomic_write(self.catalog_path, json.dumps(default_catalog(), ensure_ascii=False, indent=2).encode())
        self.settings_lock = threading.Lock()
        self.offline_update_file = Path(os.environ.get(
            "FORENSIC_TRIAGE_OFFLINE_UPDATE_FILE", "/var/lib/forensic-triage/offline-update.tbu",
        ))
        self.offline_update_max_bytes = _env_int(
            "FORENSIC_TRIAGE_OFFLINE_UPDATE_MAX_BYTES", 256 * 1024 * 1024,
        )
        self.update_guard_file = Path(os.environ.get(
            "FORENSIC_TRIAGE_UPDATE_GUARD_FILE", "/run/forensic-triage-update-requested",
        ))
        self.case_store = CaseStore(casefiles_root)
        self.scan_timeout_seconds = scan_timeout_seconds
        self.command_timeout_seconds = command_timeout_seconds


class TriageHandler(BaseHTTPRequestHandler):
    server: TriageHTTPServer

    def log_message(self, format: str, *args: object) -> None:
        logging.info("web %s", format % args)

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'")
        self.end_headers()
        self.wfile.write(body)

    def _asset(self, filename: str, content_type: str) -> None:
        path = self.server.web_root / filename
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'")
        self.end_headers()
        self.wfile.write(body)

    def _case_zip(self, case_number: str) -> None:
        detail = self.server.case_store.case_detail(case_number)
        if detail is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "Fallakte nicht gefunden."})
            return
        safe_case = str(detail["case"]["case_number"])
        self.server.case_store.refresh_exports(safe_case)
        case_dir = self.server.case_store.case_path(safe_case)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(item for item in case_dir.rglob("*") if item.is_file()):
                archive.write(path, arcname=f"TRIAGE-{safe_case}/{path.relative_to(case_dir)}")
        body = buffer.getvalue()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="TRIAGE-{safe_case}.zip"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _case_pdf(self, case_number: str) -> None:
        detail = self.server.case_store.case_detail(case_number)
        if detail is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "Fallakte nicht gefunden."})
            return
        safe_case = str(detail["case"]["case_number"])
        self.server.case_store.refresh_exports(safe_case)
        report_path = self.server.case_store.case_path(safe_case) / "case-report.pdf"
        body = report_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", f'attachment; filename="TRIAGE-{safe_case}-BERICHT.pdf"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        route = urlsplit(self.path).path
        if route == "/api/status":
            try:
                devices, device_error, _ = cached_media_discovery()
                if not device_error:
                    clear_absent_quarantines(devices)
                latest = self.server.case_store.latest_media() or latest_result(self.server.results_root)
                self._json(HTTPStatus.OK, {
                    "devices": devices,
                    "device_error": device_error,
                    "latest": latest,
                    "cases": self.server.case_store.list_cases(),
                    "active_devices": active_device_paths(),
                    "quarantined_devices": quarantined_device_paths(),
                    "scan_running": bool(active_device_paths()),
                    "active_case": active_case_session(),
                    "update": read_update_status(),
                    "power": read_power_status(),
                })
            except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Systemstatus nicht verfügbar: {exc}"})
            return
        if route == "/api/cases":
            self._json(HTTPStatus.OK, {"cases": self.server.case_store.list_cases()})
            return
        if route == "/api/profiles":
            try:
                self._json(HTTPStatus.OK, {"profiles": list_profiles(self.server.profile_path.parent)})
            except (OSError, ValueError) as exc:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Profile nicht verfügbar: {exc}"})
            return
        if route == "/api/settings/filetypes":
            try:
                with self.server.settings_lock:
                    catalog = load_catalog(self.server.catalog_path)
                self._json(HTTPStatus.OK, {"catalog": catalog, "defaults": default_catalog()})
            except (OSError, ValueError) as exc:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        if route == "/api/updates":
            self._json(HTTPStatus.OK, {"update": read_update_status(), "jobs": update_job_states()})
            return
        if route == "/api/profile":
            try:
                profile_id = str(parse_qs(urlsplit(self.path).query).get("id", [self.server.profile_path.stem])[0])
                if not PROFILE_ID_PATTERN.fullmatch(profile_id):
                    raise ValueError("Ungültiges Profil.")
                profile = load_profile(self.server.profile_path.parent / f"{profile_id}.yaml")
                self._json(HTTPStatus.OK, {
                    "id": profile["id"],
                    "name": profile["name"],
                    "version": profile["version"],
                    "keywords": profile["keywords"],
                })
            except (OSError, ValueError) as exc:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Profil nicht verfügbar: {exc}"})
            return
        report_match = re.fullmatch(r"/api/cases/([^/]+)/report\.pdf", route)
        if report_match:
            try:
                self._case_pdf(report_match.group(1))
            except ValueError as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        export_match = re.fullmatch(r"/api/cases/([^/]+)/export\.zip", route)
        if export_match:
            try:
                self._case_zip(export_match.group(1))
            except ValueError as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route.startswith("/api/cases/"):
            case_number = route.removeprefix("/api/cases/")
            try:
                result = self.server.case_store.case_detail(case_number)
            except ValueError as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            if result is None:
                self._json(HTTPStatus.NOT_FOUND, {"error": "Fallakte nicht gefunden."})
            else:
                self._json(HTTPStatus.OK, result)
            return
        inventory_match = re.fullmatch(r"/api/media/(\d+)/files", route)
        if inventory_match:
            query = parse_qs(urlsplit(self.path).query)
            try:
                result = self.server.case_store.file_inventory(
                    int(inventory_match.group(1)),
                    str(query.get("q", [""])[0]),
                    int(query.get("limit", ["250"])[0]),
                    str(query.get("category", [""])[0]),
                    str(query.get("keyword", [""])[0]),
                    int(query.get("offset", ["0"])[0]),
                    exact_path=query.get("exact_path", [None])[0],
                    archive_status=str(query.get("archive_status", [""])[0]),
                )
                self._json(HTTPStatus.OK, result)
            except KeyError as exc:
                self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except ValueError:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "Ungültiger Dateifilter oder ungültiges Limit."})
            return
        tree_match = re.fullmatch(r"/api/media/(\d+)/tree", route)
        if tree_match:
            query = parse_qs(urlsplit(self.path).query)
            try:
                result = self.server.case_store.directory_inventory(
                    int(tree_match.group(1)),
                    str(query.get("prefix", [""])[0]),
                    int(query.get("limit", ["300"])[0]),
                    int(query.get("offset", ["0"])[0]),
                )
                self._json(HTTPStatus.OK, result)
            except KeyError as exc:
                self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except ValueError as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        container_match = re.fullmatch(r"/api/media/(\d+)/container", route)
        if container_match:
            query = parse_qs(urlsplit(self.path).query)
            try:
                result = self.server.case_store.container_inventory(
                    int(container_match.group(1)),
                    str(query.get("path", [""])[0]),
                    str(query.get("prefix", [""])[0]),
                    int(query.get("limit", ["300"])[0]),
                    int(query.get("offset", ["0"])[0]),
                )
                self._json(HTTPStatus.OK, result)
            except KeyError as exc:
                self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except ValueError as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        media_match = re.fullmatch(r"/api/media/(\d+)", route)
        if media_match:
            result = self.server.case_store.media_detail(int(media_match.group(1)))
            if result is None:
                self._json(HTTPStatus.NOT_FOUND, {"error": "Medienakte nicht gefunden."})
            else:
                self._json(HTTPStatus.OK, result)
            return
        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
        }
        if route not in assets:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._asset(*assets[route])

    def do_POST(self) -> None:  # noqa: N802
        route = urlsplit(self.path).path
        if route == "/api/settings/filetypes":
            self._post_filetypes()
            return
        if route == "/api/profiles":
            self._post_profile()
            return
        if route == "/api/cases/start":
            self._post_case_start()
            return
        if route == "/api/cases/stop":
            self._post_case_stop()
            return
        if route in {"/api/updates/check", "/api/updates/install"}:
            self._post_update(route.rsplit("/", 1)[-1])
            return
        if route == "/api/updates/offline":
            self._post_offline_update()
            return
        if route == "/api/system/power":
            self._post_power()
            return
        if route == "/api/scans":
            self._post_scan()
            return
        if route == "/api/devices/eject":
            self._post_eject()
            return
        if route == "/api/devices/refresh":
            self._post_device_refresh()
            return
        decision_match = re.fullmatch(r"/api/media/(\d+)/decision", route)
        if decision_match:
            self._post_decision(int(decision_match.group(1)))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _post_filetypes(self) -> None:
        try:
            payload = self._read_payload(max_bytes=65536)
            with self.server.settings_lock:
                catalog = save_catalog(self.server.catalog_path, payload.get("categories"), str(payload.get("base_sha256", "")))
            self._json(HTTPStatus.OK, {"catalog": catalog})
        except SettingsConflict as exc:
            self._json(HTTPStatus.CONFLICT, {"error": str(exc)})
        except (OSError, ValueError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _post_profile(self) -> None:
        try:
            payload = self._read_payload(max_bytes=65536)
            profile_id = payload.get("id")
            if profile_id is not None and not isinstance(profile_id, str):
                raise ValueError("Ungültiges Profil.")
            name = str(payload.get("name", ""))
            keywords = payload.get("keywords", [])
            if not isinstance(keywords, list):
                raise ValueError("Stichwörter müssen als Liste übergeben werden.")
            with self.server.settings_lock:
                profile = save_profile(self.server.profile_path.parent, profile_id, name, keywords)
            self._json(HTTPStatus.CREATED, {
                "profile": {
                    "id": profile["id"], "name": profile["name"],
                    "version": profile["version"], "keywords": profile["keywords"],
                },
                "profiles": list_profiles(self.server.profile_path.parent),
            })
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _post_case_start(self) -> None:
        if self.server.update_guard_file.exists():
            self.close_connection = True
            self._json(HTTPStatus.CONFLICT, {"error": "FALLSTART WÄHREND EINER UPDATE-INSTALLATION GESPERRT"})
            return
        try:
            payload = self._read_payload()
            case_number = str(payload.get("case_number", "")).strip()
            operator = str(payload.get("operator", "")).strip()
        except (ValueError, json.JSONDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Ungültige Anfrage."})
            return
        if not EVIDENCE_PATTERN.fullmatch(case_number):
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Fallnummer: 1–80 Zeichen; erlaubt sind Buchstaben, Ziffern, Punkt, Minus und Unterstrich."},
            )
            return
        if not operator or not OPERATOR_PATTERN.fullmatch(operator):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Bearbeiterkürzel ist erforderlich."})
            return
        try:
            result = self.server.case_store.start_case(case_number, operator)
            set_active_case_session(result["case"]["case_number"], operator)
            self._json(HTTPStatus.OK, result)
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _post_case_stop(self) -> None:
        if active_device_paths():
            self._json(HTTPStatus.CONFLICT, {"error": "Ein Scan läuft noch."})
            return
        clear_active_case_session()
        self._json(HTTPStatus.OK, {"active_case": None})

    def _post_power(self) -> None:
        global POWER_ACTION_REQUESTED
        try:
            payload = self._read_payload()
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        action = str(payload.get("action", ""))
        if action not in {"reboot", "poweroff"}:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "UNGÜLTIGE SYSTEMAKTION"})
            return
        if active_device_paths():
            self._json(HTTPStatus.CONFLICT, {"error": "SYSTEMAKTION WÄHREND EINES SCANS GESPERRT"})
            return
        if active_case_session():
            self._json(HTTPStatus.CONFLICT, {"error": "FALL ZUERST BEENDEN"})
            return
        if self.server.update_guard_file.exists() or any(update_job_states().values()):
            self._json(HTTPStatus.CONFLICT, {"error": "SYSTEMAKTION WÄHREND EINES UPDATES GESPERRT"})
            return
        with POWER_ACTION_LOCK:
            if POWER_ACTION_REQUESTED:
                self._json(HTTPStatus.CONFLICT, {"error": "SYSTEMAKTION WURDE BEREITS ANGEFORDERT"})
                return
            POWER_ACTION_REQUESTED = action
        try:
            # The transient root unit survives the web process and gives the
            # accepted response time to reach the browser before shutdown.
            subprocess.run(
                [
                    "/usr/bin/systemd-run", "--quiet", "--collect",
                    "--unit=triagebox-power-action", "--on-active=3s",
                    "/usr/bin/systemctl", "--no-wall", action,
                ],
                check=True, capture_output=True, text=True, timeout=5,
            )
            logging.warning("operator requested system power action: %s", action)
            self._json(HTTPStatus.ACCEPTED, {"action": action, "scheduled_in_seconds": 3})
        except (OSError, subprocess.SubprocessError) as exc:
            with POWER_ACTION_LOCK:
                POWER_ACTION_REQUESTED = ""
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": f"SYSTEMAKTION NICHT VERFÜGBAR: {exc}"})

    def _post_update(self, action: str) -> None:
        guard_claimed = False
        if action == "install":
            if active_device_paths():
                self._json(HTTPStatus.CONFLICT, {"error": "UPDATE WÄHREND EINES SCANS GESPERRT"})
                return
            if active_case_session():
                self._json(HTTPStatus.CONFLICT, {"error": "FALL ZUERST BEENDEN, DANN UPDATE INSTALLIEREN"})
                return
            try:
                self.server.update_guard_file.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                descriptor = os.open(self.server.update_guard_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(descriptor)
                guard_claimed = True
            except FileExistsError:
                self._json(HTTPStatus.CONFLICT, {"error": "EINE UPDATE-INSTALLATION WURDE BEREITS ANGEFORDERT"})
                return
            except OSError as exc:
                self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": f"UPDATE-SPERRE NICHT VERFÜGBAR: {exc}"})
                return
        try:
            subprocess.run(
                ["/usr/bin/systemctl", "start", "--no-block", f"forensic-triage-update@{action}.service"],
                check=True, capture_output=True, text=True, timeout=5,
            )
            self._json(HTTPStatus.ACCEPTED, {"update": read_update_status(), "action": action})
        except (OSError, subprocess.SubprocessError) as exc:
            if guard_claimed:
                self.server.update_guard_file.unlink(missing_ok=True)
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": f"UPDATE-DIENST NICHT VERFÜGBAR: {exc}"})

    def _post_offline_update(self) -> None:
        if active_device_paths():
            self.close_connection = True
            self._json(HTTPStatus.CONFLICT, {"error": "UPDATE WÄHREND EINES SCANS GESPERRT"})
            return
        if active_case_session():
            self.close_connection = True
            self._json(HTTPStatus.CONFLICT, {"error": "FALL ZUERST BEENDEN, DANN UPDATE INSTALLIEREN"})
            return
        if any(update_job_states().values()):
            self.close_connection = True
            self._json(HTTPStatus.CONFLICT, {"error": "EINE UPDATE-AKTION LÄUFT BEREITS"})
            return
        temporary: Path | None = None
        worker_started = False
        guard_claimed = False
        try:
            try:
                self.server.update_guard_file.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                descriptor = os.open(self.server.update_guard_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(descriptor)
                guard_claimed = True
            except FileExistsError:
                self.close_connection = True
                self._json(HTTPStatus.CONFLICT, {"error": "EINE UPDATE-INSTALLATION WURDE BEREITS ANGEFORDERT"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= self.server.offline_update_max_bytes:
                self.close_connection = True
                maximum = self.server.offline_update_max_bytes // (1024 * 1024)
                raise ValueError(f"OFFLINE-PAKET IST LEER ODER GRÖSSER ALS {maximum} MB")
            target = self.server.offline_update_file
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
            descriptor, name = tempfile.mkstemp(prefix=".offline-update-", dir=target.parent)
            temporary = Path(name)
            remaining = length
            with os.fdopen(descriptor, "wb") as stream:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("UPLOAD WURDE VORZEITIG UNTERBROCHEN")
                    stream.write(chunk)
                    remaining -= len(chunk)
                stream.flush()
                os.fsync(stream.fileno())
            with temporary.open("rb") as stream:
                signature = stream.read(4)
            if signature != b"PK\x03\x04":
                raise ValueError("DATEI IST KEIN TRIAGE//BOX-UPDATEPAKET")
            temporary.chmod(0o600)
            os.replace(temporary, target)
            temporary = None
            try:
                subprocess.run(
                    ["/usr/bin/systemctl", "start", "--no-block", "forensic-triage-update@offline.service"],
                    check=True, capture_output=True, text=True, timeout=5,
                )
            except (OSError, subprocess.SubprocessError):
                target.unlink(missing_ok=True)
                raise
            worker_started = True
            self._json(HTTPStatus.ACCEPTED, {"update": read_update_status(), "action": "offline"})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except (OSError, subprocess.SubprocessError) as exc:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": f"OFFLINE-UPDATE NICHT VERFÜGBAR: {exc}"})
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            if guard_claimed and not worker_started:
                self.server.update_guard_file.unlink(missing_ok=True)

    def do_DELETE(self) -> None:  # noqa: N802
        route = urlsplit(self.path).path
        case_match = re.fullmatch(r"/api/cases/([^/]+)", route)
        if not case_match:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_payload()
            case_number = case_match.group(1)
            if str(payload.get("confirmation", "")) != case_number:
                self._json(HTTPStatus.CONFLICT, {"error": "Fallentfernung wurde nicht eindeutig bestätigt."})
                return
            result = self.server.case_store.archive_case(case_number)
            self._json(HTTPStatus.OK, result)
        except KeyError as exc:
            self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _post_eject(self) -> None:
        try:
            payload = self._read_payload()
            path = str(payload.get("device_path", ""))
            device = next((item for item in discover_media_devices() if item.get("path") == path), None)
            if device is None:
                self._json(HTTPStatus.NOT_FOUND, {"error": "Datenträger ist nicht mehr online."})
                return
            if path in active_device_paths():
                self._json(HTTPStatus.CONFLICT, {"error": "Scan läuft noch; Datenträger nicht abziehen."})
                return
            if path in quarantined_device_paths():
                self._json(HTTPStatus.CONFLICT, {"error": "Datenträger reagierte nicht. Vor dem Auswerfen physisch trennen und erneut verbinden."})
                return
            if not _device_ejectable(device):
                self._json(HTTPStatus.CONFLICT, {"error": "Datenträger ist noch eingebunden oder nicht auswerfbar."})
                return
            run_command(["sync"])
            run_command(["/usr/bin/eject", path], capture_output=True)
            self._json(HTTPStatus.OK, {
                "device_path": path,
                "media_type": device.get("media_type", "usb"),
                "ejected": True,
            })
        except (OSError, subprocess.SubprocessError) as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Auswerfen fehlgeschlagen: {exc}"})
        except (json.JSONDecodeError, ValueError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _post_device_refresh(self) -> None:
        """Reactivate software-ejected USB media, then return fresh hardware state."""
        try:
            devices, device_error, paths = cached_media_discovery(reactivate=True)
            if not device_error:
                clear_absent_quarantines(devices)
            self._json(HTTPStatus.OK, {
                "devices": devices,
                "device_error": device_error,
                "reactivated": paths,
                "active_devices": active_device_paths(),
                "quarantined_devices": quarantined_device_paths(),
            })
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Datenträger konnten nicht aktualisiert werden: {exc}"})

    def _read_payload(self, max_bytes: int = 8192) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 <= length <= max_bytes:
            self.close_connection = True
            raise ValueError("Anfrage ist zu groß.")
        payload = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(payload, dict):
            raise ValueError("Ungültige Anfrage.")
        return payload

    def _post_scan(self) -> None:
        if self.server.update_guard_file.exists():
            self.close_connection = True
            self._json(HTTPStatus.CONFLICT, {"error": "SCANSTART WÄHREND EINER UPDATE-INSTALLATION GESPERRT"})
            return
        try:
            payload = self._read_payload()
            case_number = str(payload.get("case_number", "")).strip()
            operator = str(payload.get("operator", "")).strip()
            device_path = str(payload.get("device_path", "")).strip()
            requested_keywords = payload.get("keywords")
            requested_profiles = payload.get("profiles")
        except (ValueError, json.JSONDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Ungültige Anfrage."})
            return
        if not EVIDENCE_PATTERN.fullmatch(case_number):
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Fallnummer: 1–80 Zeichen; erlaubt sind Buchstaben, Ziffern, Punkt, Minus und Unterstrich."},
            )
            return
        if not OPERATOR_PATTERN.fullmatch(operator):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Ungültiges Bearbeiterkürzel."})
            return
        if requested_profiles is None:
            profile_ids = [self.server.profile_path.stem]
        elif (
            not isinstance(requested_profiles, list)
            or not requested_profiles
            or len(requested_profiles) > 20
            or not all(isinstance(item, str) and PROFILE_ID_PATTERN.fullmatch(item) for item in requested_profiles)
            or len(requested_profiles) != len(set(requested_profiles))
        ):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Ungültige Sichtungsprofile."})
            return
        else:
            profile_ids = sorted(requested_profiles)
        try:
            loaded_profiles = [
                load_profile(self.server.profile_path.parent / f"{profile_id}.yaml")
                for profile_id in profile_ids
            ]
            configured_keywords = []
            seen_keywords: set[str] = set()
            for profile in loaded_profiles:
                for keyword in profile["keywords"]:
                    key = keyword.casefold()
                    if key not in seen_keywords:
                        configured_keywords.append(keyword)
                        seen_keywords.add(key)
        except (OSError, ValueError) as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Profil nicht verfügbar: {exc}"})
            return
        if requested_keywords is None:
            selected_keywords = configured_keywords
        elif (
            not isinstance(requested_keywords, list)
            or not all(isinstance(item, str) for item in requested_keywords)
            or len(requested_keywords) != len(set(requested_keywords))
            or any(item not in configured_keywords for item in requested_keywords)
        ):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Ungültige Stichwortauswahl."})
            return
        else:
            selected_keywords = requested_keywords
        try:
            with self.server.settings_lock:
                filetype_catalog = load_catalog(self.server.catalog_path)
            devices = discover_media_devices()
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Datenträgerstatus nicht verfügbar: {exc}"})
            return
        device = next(
            (item for item in devices if item.get("path") == device_path and item.get("scan_supported")),
            None,
        )
        if device is None:
            self._json(HTTPStatus.CONFLICT, {"error": "Datenträger ist nicht mehr verfügbar oder nicht scanbereit."})
            return
        if device_path in quarantined_device_paths():
            self._json(
                HTTPStatus.CONFLICT,
                {"error": "Datenträger ist nach einem Zeitlimit gesperrt. Medium abziehen und neu verbinden."},
            )
            return
        if not claim_device(device_path):
            self._json(HTTPStatus.CONFLICT, {"error": "Dieser Datenträger wird bereits gesichtet."})
            return
        sighting_number = ""
        try:
            sighting_number = self.server.case_store.allocate_sighting_number(
                case_number, operator, device_path,
            )
            result_dir = run_isolated_scan({
                "device": device_path,
                "profile_path": str(self.server.profile_path.parent / f"{profile_ids[0]}.yaml"),
                "evidence": sighting_number,
                "results_root": str(self.server.case_store.scan_root(case_number, sighting_number)),
                "mode": "fast",
                "keywords": selected_keywords,
                "filetype_catalog": filetype_catalog,
                "profile_sources": [{
                    "id": profile["id"], "name": profile["name"],
                    "version": profile["version"], "sha256": profile["sha256"],
                } for profile in loaded_profiles],
            }, timeout_seconds=self.server.scan_timeout_seconds,
                command_timeout_seconds=self.server.command_timeout_seconds)
            record = self.server.case_store.record_scan(
                case_number, sighting_number, operator, device, result_dir,
            )
            record["cases"] = self.server.case_store.list_cases()
            self._json(HTTPStatus.CREATED, record)
        except ScanTimeoutError as exc:
            quarantine_device(device_path)
            logging.exception("scan request timed out")
            if sighting_number:
                self.server.case_store.record_scan_failure(
                    case_number, sighting_number, operator, device_path, str(exc),
                )
            self._json(HTTPStatus.GATEWAY_TIMEOUT, {"error": str(exc), "timed_out": True})
        except Exception as exc:  # Scanner errors must reach the operator cleanly.
            logging.exception("scan request failed")
            if sighting_number:
                self.server.case_store.record_scan_failure(
                    case_number, sighting_number, operator, device_path, str(exc),
                )
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        finally:
            release_device(device_path)

    def _post_decision(self, media_id: int) -> None:
        try:
            payload = self._read_payload()
            record = self.server.case_store.record_decision(
                media_id,
                str(payload.get("decision", "")),
                str(payload["reason_code"]) if payload.get("reason_code") else None,
                str(payload.get("reason_note", "")),
                str(payload.get("operator", "")),
                str(payload.get("evidence_number", "")) or None,
            )
            record["cases"] = self.server.case_store.list_cases()
            self._json(HTTPStatus.OK, record)
        except KeyError as exc:
            self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})


def serve(
    host: str, port: int, web_root: Path, results_root: Path, profile_path: Path,
    casefiles_root: Path, scan_timeout_seconds: float, command_timeout_seconds: float,
) -> None:
    if not web_root.is_dir():
        raise FileNotFoundError(f"web interface not found: {web_root}")
    server = TriageHTTPServer(
        (host, port), web_root, results_root, profile_path, casefiles_root,
        scan_timeout_seconds, command_timeout_seconds,
    )
    print(f"TRIAGE//BOX ready at http://{host}:{port}")
    server.serve_forever()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="forensic-triage-web")
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    result.add_argument("--host", default=os.environ.get("FORENSIC_TRIAGE_WEB_HOST", "127.0.0.1"))
    result.add_argument("--port", type=int, default=os.environ.get("FORENSIC_TRIAGE_WEB_PORT", "8787"))
    result.add_argument(
        "--web-root", type=Path,
        default=Path(os.environ.get("FORENSIC_TRIAGE_WEB_ROOT", DEFAULT_WEB_ROOT)),
    )
    result.add_argument(
        "--results", type=Path,
        default=Path(os.environ.get("FORENSIC_TRIAGE_RESULTS_ROOT", PROJECT_ROOT / "results")),
    )
    result.add_argument(
        "--casefiles", type=Path,
        default=Path(os.environ.get("FORENSIC_TRIAGE_CASEFILES_ROOT", PROJECT_ROOT / "casefiles")),
    )
    result.add_argument(
        "--profile", type=Path,
        default=Path(os.environ.get("FORENSIC_TRIAGE_PROFILE", PROJECT_ROOT / "profiles/default.yaml")),
    )
    result.add_argument(
        "--scan-timeout", type=float,
        default=float(os.environ.get("FORENSIC_TRIAGE_SCAN_TIMEOUT_SECONDS", "180")),
        help="maximum wall-clock seconds for one complete media scan",
    )
    result.add_argument(
        "--command-timeout", type=float,
        default=float(os.environ.get("FORENSIC_TRIAGE_COMMAND_TIMEOUT_SECONDS", "15")),
        help="maximum seconds for one external device command",
    )
    return result


def main() -> None:
    args = parser().parse_args()
    if args.scan_timeout <= 0 or args.command_timeout <= 0:
        raise SystemExit("Zeitlimits müssen größer als null sein.")
    serve(
        args.host, args.port, args.web_root, args.results, args.profile, args.casefiles,
        args.scan_timeout, args.command_timeout,
    )


if __name__ == "__main__":
    main()
