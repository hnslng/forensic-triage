"""Local-only web operator interface for the triage scanner."""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .casefiles import CaseStore
from .scanner import scan


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEB_ROOT = PROJECT_ROOT / "web"
EVIDENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
OPERATOR_PATTERN = re.compile(r"^[^\x00-\x1f]{0,120}$")
SCAN_LOCK = threading.Lock()


def _mountpoints(node: dict[str, Any]) -> list[str]:
    points = [point for point in (node.get("mountpoints") or []) if point]
    for child in node.get("children") or []:
        points.extend(_mountpoints(child))
    return points


def discover_usb_devices() -> list[dict[str, Any]]:
    """Return unmounted whole USB disks that the scanner can safely inspect."""
    completed = subprocess.run(
        [
            "lsblk", "--json", "--bytes", "--output",
            "NAME,PATH,TYPE,TRAN,SIZE,VENDOR,MODEL,SERIAL,RO,MOUNTPOINTS",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    nodes = json.loads(completed.stdout).get("blockdevices", [])
    return [
        {
            "path": node.get("path"),
            "size": node.get("size", 0),
            "vendor": (node.get("vendor") or "").strip(),
            "model": (node.get("model") or "").strip(),
            "serial": (node.get("serial") or "").strip(),
            "read_only": bool(node.get("ro")),
        }
        for node in nodes
        if node.get("type") == "disk"
        and node.get("tran") == "usb"
        and node.get("path") != "/dev/sda"
        and not _mountpoints(node)
    ]


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

    def do_GET(self) -> None:  # noqa: N802
        route = urlsplit(self.path).path
        if route == "/api/status":
            try:
                devices = discover_usb_devices()
                latest = self.server.case_store.latest_media() or latest_result(self.server.results_root)
                self._json(HTTPStatus.OK, {
                    "devices": devices,
                    "latest": latest,
                    "cases": self.server.case_store.list_cases(),
                    "scan_running": SCAN_LOCK.locked(),
                })
            except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Systemstatus nicht verfügbar: {exc}"})
            return
        if route == "/api/cases":
            self._json(HTTPStatus.OK, {"cases": self.server.case_store.list_cases()})
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
        if route == "/api/scans":
            self._post_scan()
            return
        decision_match = re.fullmatch(r"/api/media/(\d+)/decision", route)
        if decision_match:
            self._post_decision(int(decision_match.group(1)))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

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
            evidence_number = str(payload.get("evidence_number", "")).strip()
            operator = str(payload.get("operator", "")).strip()
        except (ValueError, json.JSONDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Ungültige Anfrage."})
            return
        if not EVIDENCE_PATTERN.fullmatch(case_number) or not EVIDENCE_PATTERN.fullmatch(evidence_number):
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Fall- und Beweismittelnummer: 1–80 Zeichen; erlaubt sind Buchstaben, Ziffern, Punkt, Minus und Unterstrich."},
            )
            return
        if not OPERATOR_PATTERN.fullmatch(operator):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Ungültiges Bearbeiterkürzel."})
            return
        if not SCAN_LOCK.acquire(blocking=False):
            self._json(HTTPStatus.CONFLICT, {"error": "Eine Grobsichtung läuft bereits."})
            return
        try:
            devices = discover_usb_devices()
            if len(devices) != 1:
                message = "Kein geeigneter USB-Datenträger erkannt." if not devices else "Mehrere USB-Datenträger erkannt; bitte nur das Untersuchungsmedium anschließen."
                self._json(HTTPStatus.CONFLICT, {"error": message})
                return
            result_dir = scan(
                Path(devices[0]["path"]),
                self.server.profile_path,
                evidence_number,
                self.server.case_store.scan_root(case_number, evidence_number),
                mode="fast",
            )
            record = self.server.case_store.record_scan(
                case_number, evidence_number, operator, devices[0], result_dir,
            )
            record["cases"] = self.server.case_store.list_cases()
            self._json(HTTPStatus.CREATED, record)
        except Exception as exc:  # Scanner errors must reach the operator cleanly.
            logging.exception("scan request failed")
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        finally:
            SCAN_LOCK.release()

    def _post_decision(self, media_id: int) -> None:
        try:
            payload = self._read_payload()
            record = self.server.case_store.record_decision(
                media_id,
                str(payload.get("decision", "")),
                str(payload["reason_code"]) if payload.get("reason_code") else None,
                str(payload.get("reason_note", "")),
                str(payload.get("operator", "")),
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
