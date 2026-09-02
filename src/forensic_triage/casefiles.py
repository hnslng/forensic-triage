"""Durable local case archive and append-only decision audit."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .container_inventory import empty_catalog, virtual_files
from .pdf_report import build_case_pdf
from .keywords import match_keywords


DECISIONS = {"open", "secure", "not_selected"}
REASONS = {
    "no_indicators",
    "known_media",
    "empty",
    "duplicate",
    "out_of_scope",
    "technical",
    "other",
}
DECISION_LABELS = {
    "open": "Entscheidung offen",
    "secure": "Zur Sicherung ausgewählt",
    "not_selected": "Nicht zur Sicherung ausgewählt",
    "review": "Entscheidung offen (historischer Status)",
}
REASON_LABELS = {
    "no_indicators": "Keine fallbezogenen Indikatoren",
    "known_media": "Bekanntes Installations-/Systemmedium",
    "empty": "Leer / keine zugänglichen Dateien",
    "duplicate": "Duplikat eines anderen Mediums",
    "out_of_scope": "Außerhalb des Untersuchungsumfangs",
    "technical": "Technische Grobsichtung nicht möglich",
    "other": "Sonstige Begründung",
}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_component(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_." else "-" for char in value.strip())
    safe = safe.strip("-.")
    if not safe:
        raise ValueError("Kennung darf nicht leer sein.")
    return safe[:80]


class CaseStore:
    """SQLite index plus human-readable, independently verifiable case files."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = root / "case-index.sqlite3"
        self._export_lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        migrated_cases: list[str] = []
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY,
                    case_number TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    next_sighting_sequence INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            case_columns = {row["name"] for row in connection.execute("PRAGMA table_info(cases)")}
            if "next_sighting_sequence" not in case_columns:
                connection.execute(
                    "ALTER TABLE cases ADD COLUMN next_sighting_sequence INTEGER NOT NULL DEFAULT 1"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS media (
                    id INTEGER PRIMARY KEY,
                    case_id INTEGER NOT NULL REFERENCES cases(id),
                    evidence_number TEXT NOT NULL,
                    sighting_number TEXT NOT NULL,
                    scan_id TEXT NOT NULL,
                    result_path TEXT NOT NULL,
                    scanned_at TEXT NOT NULL,
                    device_path TEXT NOT NULL,
                    vendor TEXT NOT NULL,
                    model TEXT NOT NULL,
                    serial TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    file_count INTEGER NOT NULL,
                    directory_count INTEGER NOT NULL,
                    keyword_matches INTEGER NOT NULL,
                    duration_seconds REAL NOT NULL,
                    decision TEXT NOT NULL DEFAULT 'open',
                    reason_code TEXT,
                    reason_note TEXT,
                    decision_operator TEXT,
                    decided_at TEXT,
                    UNIQUE(case_id, evidence_number, scan_id)
                )
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(media)")}
            if "sighting_number" not in columns:
                connection.execute("ALTER TABLE media ADD COLUMN sighting_number TEXT")
                case_ids = [int(row["case_id"]) for row in connection.execute("SELECT DISTINCT case_id FROM media")]
                for case_id in case_ids:
                    migrated_cases.append(
                        str(connection.execute("SELECT case_number FROM cases WHERE id=?", (case_id,)).fetchone()["case_number"])
                    )
                    rows = connection.execute(
                        "SELECT id, decision, evidence_number FROM media WHERE case_id=? ORDER BY id",
                        (case_id,),
                    ).fetchall()
                    for sequence, row in enumerate(rows, start=1):
                        connection.execute(
                            "UPDATE media SET sighting_number=?, evidence_number=? WHERE id=?",
                            (
                                f"SICHT-{sequence:03d}",
                                row["evidence_number"] if row["decision"] == "secure" else "",
                                int(row["id"]),
                            ),
                        )
            if "next_sighting_sequence" not in case_columns:
                connection.execute(
                    "UPDATE cases SET next_sighting_sequence=("
                    "SELECT COUNT(*) + 1 FROM media WHERE media.case_id=cases.id)"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY,
                    case_id INTEGER NOT NULL REFERENCES cases(id),
                    media_id INTEGER REFERENCES media(id),
                    occurred_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    operator TEXT,
                    details_json TEXT NOT NULL
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_media_case_scanned ON media(case_id, scanned_at)")
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_media_case_sighting ON media(case_id, sighting_number)")
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_media_case_evidence ON media(case_id, evidence_number) "
                "WHERE evidence_number != ''"
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_case_time ON audit_events(case_id, occurred_at)")
            connection.execute("PRAGMA optimize")
        for case_number in migrated_cases:
            self.refresh_exports(case_number)

    def next_sighting_number(self, case_number: str) -> str:
        """Preview the next number; allocation must use allocate_sighting_number()."""
        case_number = safe_component(case_number)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT next_sighting_sequence FROM cases WHERE case_number=?",
                (case_number,),
            ).fetchone()
        return f"SICHT-{int(row['next_sighting_sequence']) if row else 1:03d}"

    def start_case(self, case_number: str, operator: str) -> dict[str, Any]:
        """Create or reopen a case and record the explicit operator session start."""
        case_number = safe_component(case_number)
        now = utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO cases(case_number, created_at, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(case_number) DO UPDATE SET updated_at=excluded.updated_at",
                (case_number, now, now),
            )
            row = connection.execute(
                "SELECT id FROM cases WHERE case_number=?", (case_number,),
            ).fetchone()
            connection.execute(
                "INSERT INTO audit_events(case_id, media_id, occurred_at, event_type, operator, details_json) "
                "VALUES (?, NULL, ?, 'case_started', ?, ?)",
                (int(row["id"]), now, operator.strip()[:120] or None, "{}"),
            )
        self.refresh_exports(case_number)
        return self.case_detail(case_number) or {}

    def allocate_sighting_number(
        self,
        case_number: str,
        operator: str,
        device_path: str,
    ) -> str:
        """Atomically reserve one sighting number for concurrent media scans."""
        case_number = safe_component(case_number)
        now = utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO cases(case_number, created_at, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(case_number) DO UPDATE SET updated_at=excluded.updated_at",
                (case_number, now, now),
            )
            row = connection.execute(
                "SELECT id, next_sighting_sequence FROM cases WHERE case_number=?",
                (case_number,),
            ).fetchone()
            case_id = int(row["id"])
            sequence = int(row["next_sighting_sequence"])
            sighting_number = f"SICHT-{sequence:03d}"
            connection.execute(
                "UPDATE cases SET next_sighting_sequence=? WHERE id=?",
                (sequence + 1, case_id),
            )
            connection.execute(
                "INSERT INTO audit_events(case_id, media_id, occurred_at, event_type, operator, details_json) "
                "VALUES (?, NULL, ?, 'sighting_reserved', ?, ?)",
                (
                    case_id,
                    now,
                    operator.strip()[:120] or None,
                    json.dumps(
                        {"sighting_number": sighting_number, "device_path": device_path},
                        ensure_ascii=False,
                    ),
                ),
            )
        return sighting_number

    def record_scan_failure(
        self,
        case_number: str,
        sighting_number: str,
        operator: str,
        device_path: str,
        error: str,
    ) -> None:
        """Keep failed attempts visible in the append-only case audit."""
        case_number = safe_component(case_number)
        now = utc_now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM cases WHERE case_number=?", (case_number,)
            ).fetchone()
            if row is None:
                return
            connection.execute(
                "UPDATE cases SET updated_at=? WHERE id=?", (now, int(row["id"]))
            )
            connection.execute(
                "INSERT INTO audit_events(case_id, media_id, occurred_at, event_type, operator, details_json) "
                "VALUES (?, NULL, ?, 'scan_failed', ?, ?)",
                (
                    int(row["id"]),
                    now,
                    operator.strip()[:120] or None,
                    json.dumps(
                        {
                            "sighting_number": sighting_number,
                            "device_path": device_path,
                            "error": error[:1000],
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
        self.refresh_exports(case_number)

    def scan_root(self, case_number: str, sighting_number: str) -> Path:
        return self.case_path(case_number) / "media" / safe_component(sighting_number) / "scans"

    def case_path(self, case_number: str) -> Path:
        return self.root / safe_component(case_number)

    def record_scan(
        self,
        case_number: str,
        sighting_number: str,
        operator: str,
        device: dict[str, Any],
        result_dir: Path,
    ) -> dict[str, Any]:
        summary = json.loads((result_dir / "summary.json").read_text(encoding="utf-8"))
        now = utc_now()
        case_number = safe_component(case_number)
        sighting_number = safe_component(sighting_number)
        relative_result = result_dir.resolve().relative_to(self.root.resolve()).as_posix()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO cases(case_number, created_at, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(case_number) DO UPDATE SET updated_at=excluded.updated_at",
                (case_number, now, now),
            )
            case_id = int(connection.execute("SELECT id FROM cases WHERE case_number=?", (case_number,)).fetchone()["id"])
            if sighting_number.startswith("SICHT-") and sighting_number[6:].isdigit():
                next_sequence = int(sighting_number[6:]) + 1
                connection.execute(
                    "UPDATE cases SET next_sighting_sequence=MAX(next_sighting_sequence, ?) WHERE id=?",
                    (next_sequence, case_id),
                )
            cursor = connection.execute(
                """
                INSERT INTO media(
                    case_id, evidence_number, sighting_number, scan_id, result_path, scanned_at,
                    device_path, vendor, model, serial, size, file_count,
                    directory_count, keyword_matches, duration_seconds
                ) VALUES (?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id, sighting_number, result_dir.name, relative_result, now,
                    str(device.get("path", "")), str(device.get("vendor", "")),
                    str(device.get("model", "")), str(device.get("serial", "")),
                    int(device.get("size", 0) or 0), int(summary.get("file_count", 0)),
                    int(summary.get("directory_count", 0)), int(summary.get("keyword_matches", 0)),
                    float(summary.get("duration_seconds", 0)),
                ),
            )
            media_id = int(cursor.lastrowid)
            connection.execute(
                "INSERT INTO audit_events(case_id, media_id, occurred_at, event_type, operator, details_json) "
                "VALUES (?, ?, ?, 'scan_completed', ?, ?)",
                (
                    case_id, media_id, now, operator or None,
                    json.dumps({
                        "scan_id": result_dir.name,
                        "sighting_number": sighting_number,
                        "container_index": summary.get("container_index", {}),
                    }, ensure_ascii=False),
                ),
            )
        self.refresh_exports(case_number)
        result = self.media_detail(media_id)
        if result is None:
            raise RuntimeError("Medienakte konnte nicht geladen werden.")
        return result

    def record_decision(
        self,
        media_id: int,
        decision: str,
        reason_code: str | None,
        reason_note: str,
        operator: str,
        evidence_number: str | None = None,
    ) -> dict[str, Any]:
        if decision not in DECISIONS - {"open"}:
            raise ValueError("Unbekannter Entscheidungsstatus.")
        if decision == "not_selected" and reason_code not in REASONS:
            raise ValueError("Für eine Nichtauswahl ist eine Begründung erforderlich.")
        if reason_code and reason_code not in REASONS:
            raise ValueError("Unbekannte Begründung.")
        official_evidence = safe_component(evidence_number or "") if evidence_number else ""
        if decision == "secure" and not official_evidence:
            raise ValueError("Für die Sicherung ist eine Beweismittelnummer erforderlich.")
        if decision != "secure":
            official_evidence = ""
        now = utc_now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT media.id, media.case_id, cases.case_number FROM media "
                "JOIN cases ON cases.id=media.case_id WHERE media.id=?",
                (media_id,),
            ).fetchone()
            if row is None:
                raise KeyError("Medienakte nicht gefunden.")
            try:
                connection.execute(
                    "UPDATE media SET decision=?, evidence_number=?, reason_code=?, reason_note=?, decision_operator=?, decided_at=? WHERE id=?",
                    (decision, official_evidence, reason_code, reason_note.strip()[:1000] or None, operator.strip()[:120] or None, now, media_id),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Diese Beweismittelnummer ist in diesem Fall bereits vergeben.") from exc
            connection.execute("UPDATE cases SET updated_at=? WHERE id=?", (now, int(row["case_id"])))
            connection.execute(
                "INSERT INTO audit_events(case_id, media_id, occurred_at, event_type, operator, details_json) "
                "VALUES (?, ?, ?, 'decision_recorded', ?, ?)",
                (
                    int(row["case_id"]), media_id, now, operator.strip()[:120] or None,
                    json.dumps(
                        {
                            "decision": decision,
                            "evidence_number": official_evidence or None,
                            "reason_code": reason_code,
                            "reason_note": reason_note.strip()[:1000],
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            case_number = str(row["case_number"])
        self.refresh_exports(case_number)
        result = self.media_detail(media_id)
        if result is None:
            raise RuntimeError("Medienakte konnte nicht geladen werden.")
        return result

    def media_detail(self, media_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT media.*, cases.case_number FROM media JOIN cases ON cases.id=media.case_id WHERE media.id=?",
                (media_id,),
            ).fetchone()
        if row is None:
            return None
        result_dir = self.root / str(row["result_path"])
        summary = json.loads((result_dir / "summary.json").read_text(encoding="utf-8"))
        hits_data = json.loads((result_dir / "hits.json").read_text(encoding="utf-8"))
        device: dict[str, Any] = {}
        try:
            stored_device = json.loads((result_dir / "device.json").read_text(encoding="utf-8"))
            if isinstance(stored_device, dict):
                device = stored_device
        except (OSError, json.JSONDecodeError):
            # Older or incomplete records remain readable from their database fields.
            pass
        return {
            "media": self._media_dict(row),
            "device": device,
            "summary": summary,
            "hits": {word: int(value.get("count", 0)) for word, value in hits_data.get("by_keyword", {}).items()},
            "archive": self._archive_info(str(row["case_number"]), result_dir),
        }

    def latest_media(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT id FROM media ORDER BY id DESC LIMIT 1").fetchone()
        return self.media_detail(int(row["id"])) if row else None

    def file_inventory(
        self,
        media_id: int,
        query: str = "",
        limit: int = 250,
        category: str = "",
        keyword: str = "",
        offset: int = 0,
        exact_path: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_path FROM media WHERE id=?",
                (media_id,),
            ).fetchone()
        if row is None:
            raise KeyError("Medienakte nicht gefunden.")
        inventory_path = self.root / str(row["result_path"]) / "files.csv"
        needle = query.casefold().strip()
        selected_category = category.casefold().strip()
        selected_keyword = keyword.strip()
        keyword_paths: set[str] | None = None
        if selected_keyword:
            hits_path = inventory_path.with_name("hits.json")
            hits_data = json.loads(hits_path.read_text(encoding="utf-8"))
            keyword_details = hits_data.get("by_keyword", {}).get(selected_keyword, {})
            keyword_paths = {str(path) for path in keyword_details.get("paths", [])}
        matches: list[dict[str, Any]] = []
        total = 0
        start = max(0, offset)
        capped = max(1, min(limit, 500))
        catalog = self._load_container_catalog(inventory_path.parent)
        container_records = list(catalog.get("containers", []))

        def inventory_items():
            with inventory_path.open(encoding="utf-8", newline="") as handle:
                yield from csv.DictReader(handle)
            yield from virtual_files(catalog)

        for item in inventory_items():
            path = str(item.get("path", ""))
            if exact_path is not None and path != exact_path:
                continue
            if needle and needle not in path.casefold():
                continue
            if selected_category and str(item.get("category", "Unbekannt")).casefold() != selected_category:
                continue
            if keyword_paths is not None and path not in keyword_paths:
                continue
            total += 1
            if total <= start:
                continue
            if len(matches) < capped:
                record = {
                    "path": path,
                    "size": int(item.get("size", 0) or 0),
                    "extension": item.get("extension", ""),
                    "category": item.get("category", "Unbekannt"),
                    "mtime": item.get("mtime", ""),
                    "source": item.get("source", "media_inventory"),
                    "container_format": item.get("container_format", ""),
                    "size_known": item.get("size_known", True),
                }
                if str(item.get("source", "media_inventory")) != "container_index":
                    partition_slot = str(item.get("partition_slot", ""))
                    container = next((
                        candidate for candidate in container_records
                        if str(candidate.get("path", "")) == path
                        and (
                            not candidate.get("partition_slot")
                            or str(candidate.get("partition_slot")) == partition_slot
                        )
                    ), None)
                    if container:
                        record.update({
                            "container_id": container.get("id", container.get("path", path)),
                            "container_status": container.get("status", "unknown"),
                            "entry_count": int(
                                container.get("entry_count", len(container.get("entries", [])))
                            ),
                            "encrypted": bool(container.get("encrypted", False)),
                            "truncated": bool(container.get("truncated", False)),
                        })
                container_format = str(item.get("container_format", ""))
                if selected_keyword:
                    normalized = path.replace("\\", "/")
                    parent, separator, filename = normalized.rpartition("/")
                    if match_keywords(filename if separator else normalized, [selected_keyword]):
                        record["match_source"] = "DATEINAME"
                    elif parent and match_keywords(parent, [selected_keyword]):
                        record["match_source"] = "ORDNERPFAD"
                    else:
                        record["match_source"] = "PFAD"
                    if container_format:
                        record["match_source"] += f" · {container_format}-INHALT"
                elif container_format:
                    record["match_source"] = f"{container_format}-INHALT"
                matches.append(record)
        next_offset = start + len(matches)
        return {
            "total": total,
            "shown": len(matches),
            "offset": start,
            "next_offset": next_offset,
            "has_more": next_offset < total,
            "files": matches,
        }

    def directory_inventory(self, media_id: int, prefix: str = "", limit: int = 300, offset: int = 0) -> dict[str, Any]:
        """Return one directory level for the lazy web explorer."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_path FROM media WHERE id=?",
                (media_id,),
            ).fetchone()
        if row is None:
            raise KeyError("Medienakte nicht gefunden.")
        normalized_prefix = "/".join(part for part in prefix.replace("\\", "/").split("/") if part)
        if any(part in {".", ".."} for part in normalized_prefix.split("/") if part):
            raise ValueError("Ungültiger Verzeichnispfad.")
        inventory_path = self.root / str(row["result_path"]) / "files.csv"
        catalog = self._load_container_catalog(inventory_path.parent)
        container_records = list(catalog.get("containers", []))
        folders: dict[str, dict[str, Any]] = {}
        files: list[dict[str, Any]] = []
        base = f"{normalized_prefix}/" if normalized_prefix else ""
        with inventory_path.open(encoding="utf-8", newline="") as handle:
            for item in csv.DictReader(handle):
                path = str(item.get("path", "")).replace("\\", "/").strip("/")
                if base and not path.startswith(base):
                    continue
                remainder = path[len(base):] if base else path
                if not remainder:
                    continue
                first, separator, _rest = remainder.partition("/")
                child_path = f"{base}{first}" if base else first
                size = int(item.get("size", 0) or 0)
                if separator:
                    folder = folders.setdefault(child_path, {
                        "kind": "directory", "name": first, "path": child_path,
                        "file_count": 0, "size": 0,
                    })
                    folder["file_count"] += 1
                    folder["size"] += size
                else:
                    partition_slot = str(item.get("partition_slot", ""))
                    container = next((
                        record for record in container_records
                        if str(record.get("path", "")) == child_path
                        and (not record.get("partition_slot") or str(record.get("partition_slot")) == partition_slot)
                    ), None)
                    files.append({
                        "kind": "container" if container else "file", "name": first, "path": child_path,
                        "size": size, "extension": item.get("extension", ""),
                        "category": item.get("category", "Unbekannt"),
                        **({
                            "container_format": container.get("format", "container"),
                            "container_id": container.get("id", container.get("path", child_path)),
                            "container_status": container.get("status", "unknown"),
                            "entry_count": int(container.get("entry_count", 0)),
                            "encrypted": bool(container.get("encrypted", False)),
                            "truncated": bool(container.get("truncated", False)),
                        } if container else {}),
                    })
        entries = sorted(folders.values(), key=lambda entry: entry["name"].casefold())
        entries.extend(sorted(files, key=lambda entry: entry["name"].casefold()))
        capped = max(1, min(limit, 500))
        start = max(0, offset)
        page = entries[start:start + capped]
        next_offset = start + len(page)
        return {
            "prefix": normalized_prefix, "total": len(entries), "shown": len(page),
            "offset": start, "next_offset": next_offset,
            "has_more": next_offset < len(entries), "entries": page,
        }

    def container_inventory(
        self,
        media_id: int,
        container_path: str,
        prefix: str = "",
        limit: int = 300,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return one virtual directory level from a bounded container index."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_path FROM media WHERE id=?", (media_id,),
            ).fetchone()
        if row is None:
            raise KeyError("Medienakte nicht gefunden.")
        result_dir = self.root / str(row["result_path"])
        catalog = self._load_container_catalog(result_dir)
        container = next(
            (
                item for item in catalog.get("containers", [])
                if str(item.get("id", "")) == container_path or str(item.get("path", "")) == container_path
            ),
            None,
        )
        if container is None:
            raise KeyError("Container-Verzeichnis nicht gefunden.")
        normalized_prefix = "/".join(part for part in prefix.replace("\\", "/").split("/") if part)
        if any(part in {".", ".."} for part in normalized_prefix.split("/") if part):
            raise ValueError("Ungültiger Containerpfad.")

        folders: dict[str, dict[str, Any]] = {}
        files: list[dict[str, Any]] = []
        base = f"{normalized_prefix}/" if normalized_prefix else ""
        for item in container.get("entries", []):
            path = str(item.get("path", "")).replace("\\", "/").strip("/")
            if base and not path.startswith(base):
                continue
            remainder = path[len(base):] if base else path
            if not remainder:
                continue
            first, separator, _rest = remainder.partition("/")
            child_path = f"{base}{first}" if base else first
            size = int(item.get("size", 0) or 0)
            if separator or item.get("kind") == "directory":
                folders.setdefault(child_path, {
                    "kind": "directory", "name": first, "path": child_path,
                    "file_count": 0, "size": 0,
                })
            else:
                files.append({
                    "kind": "file", "name": first, "path": child_path,
                    "size": size, "extension": item.get("extension", ""),
                    "category": item.get("category", "Unbekannt"),
                    "encrypted": bool(item.get("encrypted", False)),
                    "size_known": bool(item.get("size_known", True)),
                })
        # Aggregate descendant file counts and sizes independently of explicit directory records.
        for folder in folders.values():
            folder_prefix = f"{folder['path']}/"
            descendants = [
                item for item in container.get("entries", [])
                if item.get("kind") == "file" and str(item.get("path", "")).startswith(folder_prefix)
            ]
            folder["file_count"] = len(descendants)
            folder["size"] = sum(int(item.get("size", 0) or 0) for item in descendants)
            folder["size_known"] = all(bool(item.get("size_known", True)) for item in descendants)

        entries = sorted(folders.values(), key=lambda entry: entry["name"].casefold())
        entries.extend(sorted(files, key=lambda entry: entry["name"].casefold()))
        capped = max(1, min(limit, 500))
        start = max(0, offset)
        page = entries[start:start + capped]
        next_offset = start + len(page)
        return {
            "container_path": str(container.get("path", container_path)),
            "container_id": str(container.get("id", container_path)),
            "container_format": container.get("format", "container"),
            "container_status": container.get("status", "unknown"),
            "truncated": bool(container.get("truncated", False)),
            "prefix": normalized_prefix,
            "total": len(entries), "shown": len(page), "offset": start,
            "next_offset": next_offset, "has_more": next_offset < len(entries),
            "entries": page,
        }

    @staticmethod
    def _load_container_catalog(result_dir: Path) -> dict[str, Any]:
        path = result_dir / "container-index.json"
        if not path.is_file():
            return empty_catalog("not_available_for_older_scan")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return empty_catalog("invalid_index")
        return data if isinstance(data, dict) else empty_catalog("invalid_index")

    def list_cases(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT cases.case_number, cases.created_at, cases.updated_at,
                       COUNT(media.id) AS media_count,
                       SUM(CASE WHEN media.decision='secure' THEN 1 ELSE 0 END) AS secure_count,
                       SUM(CASE WHEN media.decision='not_selected' THEN 1 ELSE 0 END) AS not_selected_count,
                       SUM(CASE WHEN media.decision IN ('open','review') THEN 1 ELSE 0 END) AS open_count
                FROM cases LEFT JOIN media ON media.case_id=cases.id
                GROUP BY cases.id ORDER BY cases.updated_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def archive_case(self, case_number: str) -> dict[str, Any]:
        """Remove a case from active records while retaining a recoverable local copy."""
        safe_case = safe_component(case_number)
        with self._export_lock:
            with self._connect() as connection:
                case = connection.execute("SELECT id FROM cases WHERE case_number=?", (safe_case,)).fetchone()
            if case is None:
                raise KeyError("Fallakte nicht gefunden.")
            case_dir = self.case_path(safe_case)
            archived_path: Path | None = None
            if case_dir.exists():
                trash_dir = self.root / ".trash"
                trash_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                archived_path = trash_dir / f"{stamp}-{safe_case}"
                sequence = 1
                while archived_path.exists():
                    archived_path = trash_dir / f"{stamp}-{safe_case}-{sequence}"
                    sequence += 1
                shutil.move(str(case_dir), str(archived_path))
            try:
                with self._connect() as connection:
                    case_id = int(case["id"])
                    connection.execute("DELETE FROM audit_events WHERE case_id=?", (case_id,))
                    connection.execute("DELETE FROM media WHERE case_id=?", (case_id,))
                    connection.execute("DELETE FROM cases WHERE id=?", (case_id,))
            except Exception:
                if archived_path is not None and archived_path.exists():
                    shutil.move(str(archived_path), str(case_dir))
                raise
        return {"case_number": safe_case, "archived": True, "recoverable": archived_path is not None}

    def case_detail(self, case_number: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            case = connection.execute("SELECT * FROM cases WHERE case_number=?", (safe_component(case_number),)).fetchone()
            if case is None:
                return None
            rows = connection.execute(
                "SELECT media.*, cases.case_number FROM media JOIN cases ON cases.id=media.case_id "
                "WHERE media.case_id=? ORDER BY media.id DESC",
                (int(case["id"]),),
            ).fetchall()
        return {"case": dict(case), "media": [self._media_dict(row) for row in rows], "archive": self._archive_info(str(case["case_number"]))}

    def _media_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        keys = {
            "id", "case_number", "sighting_number", "evidence_number", "scan_id", "scanned_at", "device_path",
            "vendor", "model", "serial", "size", "file_count", "directory_count",
            "keyword_matches", "duration_seconds", "decision", "reason_code", "reason_note",
            "decision_operator", "decided_at",
        }
        return {key: row[key] for key in keys if key in row.keys()}

    def refresh_exports(self, case_number: str) -> None:
        with self._export_lock:
            self._refresh_exports(case_number)

    def _refresh_exports(self, case_number: str) -> None:
        case_number = safe_component(case_number)
        case_dir = self.case_path(case_number)
        case_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            case = connection.execute("SELECT * FROM cases WHERE case_number=?", (case_number,)).fetchone()
            media = connection.execute(
                "SELECT media.*, cases.case_number FROM media JOIN cases ON cases.id=media.case_id "
                "WHERE media.case_id=? ORDER BY media.id",
                (int(case["id"]),),
            ).fetchall()
            audit = connection.execute(
                "SELECT occurred_at, event_type, media_id, operator, details_json FROM audit_events "
                "WHERE case_id=? ORDER BY id",
                (int(case["id"]),),
            ).fetchall()
        (case_dir / "case.json").write_text(
            json.dumps({"case_number": case_number, "created_at": case["created_at"], "updated_at": case["updated_at"], "media_count": len(media)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        fields = [
            "id", "sighting_number", "evidence_number", "scan_id", "scanned_at", "vendor", "model", "serial", "size",
            "file_count", "directory_count", "keyword_matches", "duration_seconds", "decision",
            "reason_code", "reason_note", "decision_operator", "decided_at",
        ]
        with (case_dir / "media-register.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in media:
                writer.writerow({field: row[field] for field in fields})
        with (case_dir / "audit.log").open("w", encoding="utf-8") as handle:
            for event in audit:
                handle.write(json.dumps({**dict(event), "details": json.loads(event["details_json"])}, ensure_ascii=False) + "\n")
        report_lines = [
            "TRIAGE//BOX FALLPROTOKOLL",
            "=" * 72,
            f"Fallnummer: {case_number}",
            f"Erstellt: {case['created_at']}",
            f"Zuletzt aktualisiert: {case['updated_at']}",
            f"Erfasste Medien: {len(media)}",
            "",
        ]
        for row in media:
            report_lines.extend(
                [
                    f"SICHTUNGSMEDIUM: {row['sighting_number']}",
                    f"BEWEISMITTEL / ASSERVAT: {row['evidence_number'] or 'nicht vergeben'}",
                    f"Medium: {str(row['vendor']).strip()} {str(row['model']).strip()}",
                    f"Seriennummer: {row['serial'] or 'nicht gemeldet'}",
                    f"Größe (Byte): {row['size']}",
                    f"Scan: {row['scanned_at']} · {row['duration_seconds']} s",
                    f"Dateien / Ordner / Treffer: {row['file_count']} / {row['directory_count']} / {row['keyword_matches']}",
                    f"Entscheidung: {DECISION_LABELS.get(str(row['decision']), str(row['decision']))}",
                    f"Begründung: {REASON_LABELS.get(str(row['reason_code']), str(row['reason_code'] or '—'))}",
                    f"Notiz: {row['reason_note'] or '—'}",
                    f"Bearbeiter / Zeitpunkt: {row['decision_operator'] or '—'} / {row['decided_at'] or '—'}",
                    "-" * 72,
                ]
            )
        report_lines.extend(
            [
                "HINWEIS",
                "Dieses Protokoll dokumentiert eine Metadaten-Grobsichtung und keine",
                "abschließende forensische Inhaltsanalyse oder fachliche Relevanzentscheidung.",
            ]
        )
        (case_dir / "case-report.txt").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        for row in media:
            media_dir = case_dir / "media" / safe_component(str(row["sighting_number"])) / "records"
            media_dir.mkdir(parents=True, exist_ok=True)
            (media_dir / f"{safe_component(str(row['scan_id']))}.json").write_text(
                json.dumps(self._media_dict(row), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        build_case_pdf(
            case_dir / "case-report.pdf",
            dict(case),
            [dict(row) for row in media],
            [dict(event) for event in audit],
            self.root,
        )
        self._write_manifest(case_dir)

    def _write_manifest(self, case_dir: Path) -> None:
        lines = []
        for path in sorted(item for item in case_dir.rglob("*") if item.is_file() and item.name != "manifest.sha256"):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(case_dir).as_posix()}")
        (case_dir / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _archive_info(self, case_number: str, result_dir: Path | None = None) -> dict[str, Any]:
        case_dir = self.case_path(case_number)
        manifest = case_dir / "manifest.sha256"
        return {
            "case_path": str(case_dir),
            "result_path": str(result_dir) if result_dir else None,
            "container_index": str(result_dir / "container-index.json") if result_dir else None,
            "database": str(self.db_path),
            "media_register": str(case_dir / "media-register.csv"),
            "case_report": str(case_dir / "case-report.txt"),
            "pdf_report": str(case_dir / "case-report.pdf"),
            "audit_log": str(case_dir / "audit.log"),
            "manifest": str(manifest),
            "manifest_entries": len(manifest.read_text(encoding="utf-8").splitlines()) if manifest.is_file() else 0,
        }
