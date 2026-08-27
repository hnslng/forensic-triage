"""Local-only web operator interface for the triage scanner."""

from __future__ import annotations

import argparse
import hmac
import io
import json
import logging
import os
import re
import subprocess
import threading
import zipfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from . import __version__
from .casefiles import CaseStore
from .keywords import PROFILE_ID_PATTERN, list_profiles, load_profile, save_profile
from .scanner import scan


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEB_ROOT = PROJECT_ROOT / "web"
EVIDENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
OPERATOR_PATTERN = re.compile(r"^[^\x00-\x1f]{0,120}$")
ACTIVE_DEVICES_LOCK = threading.Lock()
ACTIVE_DEVICES: set[str] = set()
DELETE_PASSWORD = os.environ.get("FORENSIC_TRIAGE_DELETE_PASSWORD", "123")


def _mountpoints(node: dict[str, Any]) -> list[str]:
    points = [point for point in (node.get("mountpoints") or []) if point]
    for child in node.get("children") or []:
        points.extend(_mountpoints(child))
    return points


def parse_media_devices(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert lsblk nodes into operator-facing removable media records."""
    devices: list[dict[str, Any]] = []
    for node in nodes:
        device_type = str(node.get("type", ""))
        transport = str(node.get("tran", ""))
        is_usb = (
            device_type == "disk"
            and transport == "usb"
            and node.get("path") != "/dev/sda"
            and int(node.get("size") or 0) > 0
        )
        # The field unit uses external USB optical drives. Ignore internal or
        # VM system discs (for example Proxmox cloud-init media on SATA).
        is_optical = device_type == "rom" and transport == "usb"
        if not (is_usb or is_optical):
            continue
        mounted = bool(_mountpoints(node))
        supported = is_usb and not mounted
        reason = ""
        if is_optical:
            reason = "CD/DVD erkannt · Scan folgt nach Hardwaretest"
        elif mounted:
            reason = "Medium ist bereits eingehängt"
        devices.append({
            "path": node.get("path"),
            "size": node.get("size", 0),
            "vendor": (node.get("vendor") or "").strip(),
            "model": (node.get("model") or "").strip(),
            "serial": (node.get("serial") or "").strip(),
            "read_only": bool(node.get("ro")),
            "media_type": "optical" if is_optical else "usb",
            "scan_supported": supported,
            "unavailable_reason": reason,
        })
    return devices


def list_block_devices() -> list[dict[str, Any]]:
    """Read the current kernel block-device inventory."""
    completed = subprocess.run(
        [
            "lsblk", "--json", "--bytes", "--output",
            "NAME,PATH,TYPE,TRAN,SIZE,VENDOR,MODEL,SERIAL,RO,MOUNTPOINTS",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout).get("blockdevices", [])


def discover_media_devices() -> list[dict[str, Any]]:
    """Return USB media and visible optical drives without touching their contents."""
    return parse_media_devices(list_block_devices())


def ejected_usb_paths(nodes: list[dict[str, Any]]) -> list[str]:
    """Return validated USB disk nodes whose medium was software-ejected."""
    return [
        str(node["path"])
        for node in nodes
        if node.get("type") == "disk"
        and node.get("tran") == "usb"
        and int(node.get("size") or 0) == 0
        and re.fullmatch(r"/dev/sd[a-z]+", str(node.get("path", "")))
        and node.get("path") != "/dev/sda"
    ]


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
    ) -> None:
        super().__init__(address, TriageHandler)
        self.web_root = web_root
        self.results_root = results_root
        self.profile_path = profile_path
        self.case_store = CaseStore(casefiles_root)


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

    def do_GET(self) -> None:  # noqa: N802
        route = urlsplit(self.path).path
        if route == "/api/status":
            try:
                devices = discover_media_devices()
                latest = self.server.case_store.latest_media() or latest_result(self.server.results_root)
                self._json(HTTPStatus.OK, {
                    "devices": devices,
                    "latest": latest,
                    "cases": self.server.case_store.list_cases(),
                    "active_devices": active_device_paths(),
                    "scan_running": bool(active_device_paths()),
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
                )
                self._json(HTTPStatus.OK, result)
            except KeyError as exc:
                self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except ValueError:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "Ungültiges Limit."})
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
        if route == "/api/profiles":
            self._post_profile()
            return
        if route == "/api/cases/start":
            self._post_case_start()
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

    def _post_profile(self) -> None:
        try:
            payload = self._read_payload()
            profile_id = payload.get("id")
            if profile_id is not None and not isinstance(profile_id, str):
                raise ValueError("Ungültiges Profil.")
            name = str(payload.get("name", ""))
            keywords = payload.get("keywords", [])
            if not isinstance(keywords, list):
                raise ValueError("Stichwörter müssen als Liste übergeben werden.")
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
            self._json(HTTPStatus.OK, result)
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def do_DELETE(self) -> None:  # noqa: N802
        route = urlsplit(self.path).path
        case_match = re.fullmatch(r"/api/cases/([^/]+)", route)
        if not case_match:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_payload()
            password = str(payload.get("password", ""))
            if not hmac.compare_digest(password, DELETE_PASSWORD):
                self._json(HTTPStatus.FORBIDDEN, {"error": "Passwort ist nicht korrekt."})
                return
            result = self.server.case_store.archive_case(case_match.group(1))
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
            if not device.get("scan_supported"):
                self._json(HTTPStatus.CONFLICT, {"error": "Datenträger ist noch eingebunden oder nicht auswerfbar."})
                return
            subprocess.run(["sync"], check=True)
            subprocess.run(["/usr/bin/eject", path], check=True, text=True, capture_output=True)
            self._json(HTTPStatus.OK, {"device_path": path, "ejected": True})
        except (OSError, subprocess.SubprocessError) as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Auswerfen fehlgeschlagen: {exc}"})
        except (json.JSONDecodeError, ValueError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _post_device_refresh(self) -> None:
        """Reactivate software-ejected USB media, then return fresh hardware state."""
        try:
            paths = ejected_usb_paths(list_block_devices())
            for path in paths:
                subprocess.run(["/usr/bin/eject", "-t", path], check=False, text=True, capture_output=True)
            subprocess.run(["/usr/bin/udevadm", "settle"], check=True, text=True, capture_output=True)
            self._json(HTTPStatus.OK, {
                "devices": discover_media_devices(),
                "reactivated": paths,
                "active_devices": active_device_paths(),
            })
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Datenträger konnten nicht aktualisiert werden: {exc}"})

    def _read_payload(self) -> dict[str, Any]:
        length = min(int(self.headers.get("Content-Length", "0")), 8192)
        payload = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(payload, dict):
            raise ValueError("Ungültige Anfrage.")
        return payload

    def _post_scan(self) -> None:
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
            devices = discover_media_devices()
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Datenträgerstatus nicht verfügbar: {exc}"})
            return
        device = next(
            (item for item in devices if item.get("path") == device_path and item.get("scan_supported")),
            None,
        )
        if device is None:
            self._json(HTTPStatus.CONFLICT, {"error": "Datenträger ist nicht mehr verfügbar oder nicht scanbereit."})
            return
        if not claim_device(device_path):
            self._json(HTTPStatus.CONFLICT, {"error": "Dieser Datenträger wird bereits gesichtet."})
            return
        sighting_number = ""
        try:
            sighting_number = self.server.case_store.allocate_sighting_number(
                case_number, operator, device_path,
            )
            result_dir = scan(
                Path(device_path),
                self.server.profile_path.parent / f"{profile_ids[0]}.yaml",
                sighting_number,
                self.server.case_store.scan_root(case_number, sighting_number),
                mode="fast",
                keywords=selected_keywords,
                profile_sources=[{
                    "id": profile["id"], "name": profile["name"],
                    "version": profile["version"], "sha256": profile["sha256"],
                } for profile in loaded_profiles],
            )
            record = self.server.case_store.record_scan(
                case_number, sighting_number, operator, device, result_dir,
            )
            record["cases"] = self.server.case_store.list_cases()
            self._json(HTTPStatus.CREATED, record)
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


def serve(host: str, port: int, web_root: Path, results_root: Path, profile_path: Path, casefiles_root: Path) -> None:
    if not web_root.is_dir():
        raise FileNotFoundError(f"web interface not found: {web_root}")
    server = TriageHTTPServer((host, port), web_root, results_root, profile_path, casefiles_root)
    print(f"TRIAGE//BOX ready at http://{host}:{port}")
    server.serve_forever()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="forensic-triage-web")
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    result.add_argument("--host", default="127.0.0.1")
    result.add_argument("--port", type=int, default=8787)
    result.add_argument("--web-root", type=Path, default=DEFAULT_WEB_ROOT)
    result.add_argument("--results", type=Path, default=PROJECT_ROOT / "results")
    result.add_argument("--casefiles", type=Path, default=PROJECT_ROOT / "casefiles")
    result.add_argument("--profile", type=Path, default=PROJECT_ROOT / "profiles/default.yaml")
    return result


def main() -> None:
    args = parser().parse_args()
    serve(args.host, args.port, args.web_root, args.results, args.profile, args.casefiles)


if __name__ == "__main__":
    main()
