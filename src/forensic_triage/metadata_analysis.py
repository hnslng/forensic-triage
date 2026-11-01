"""Bounded metadata-only analysis. Never opens a device or an original file.

The SQLite index contains derived metadata only. Original scan artifacts remain
byte-for-byte intact; persisted indexes are published by the case store.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sqlite3
import time
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .container_inventory import archive_encryption_state, archive_encryption_states, virtual_files
from .keywords import match_keywords
from .period import TIMESTAMP_TYPES, evaluate_file_period, optional_bool, parse_timestamp, require_iana_timezone

ANALYSIS_VERSION = 1
MAX_SOURCE_BYTES = 512 * 1024 * 1024
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_ROWS = 2_000_000
MAX_SECONDS = 120
MAX_LINKS = 2_000_000


def read_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    if path.is_symlink() or path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("Metadatenquelle ist unsicher oder überschreitet das JSON-Limit.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        expected = list if isinstance(default, list) else dict
        if not isinstance(value, expected):
            raise ValueError("Unerwartetes Metadatenformat.")
        return value
    except (ValueError, OSError, RecursionError) as exc:
        raise ValueError("Gespeicherte Metadaten sind nicht lesbar.") from exc


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_manifest(root: Path) -> dict[str, str]:
    """Hash all existing artifacts; never follow symlinks, including raw outputs."""
    result = {}
    total = 0
    started = time.monotonic()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Quell-Snapshot fehlt oder ist nicht freigegeben.")
    for path in root.rglob("*"):
        if time.monotonic() - started > MAX_SECONDS:
            raise ValueError("Zeitlimit bei der Quellenprüfung erreicht.")
        if path.is_symlink():
            raise ValueError("Symlinks sind in der Auswertungsquelle nicht zulässig.")
        if not path.is_file():
            continue
        if len(result) >= 4096:
            raise ValueError("Zu viele Quellartefakte.")
        total += path.stat().st_size
        if total > MAX_SOURCE_BYTES:
            raise ValueError("Quell-Snapshot überschreitet das Auswertungslimit (512 MiB).")
        digest = hashlib.sha256()
        before = path.stat()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                if time.monotonic() - started > MAX_SECONDS:
                    raise ValueError("Zeitlimit bei der Quellenprüfung erreicht.")
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError("Quell-Snapshot hat sich während der Prüfung verändert.")
        result[path.relative_to(root).as_posix()] = digest.hexdigest()
    if "files.csv" not in result:
        raise ValueError("Kein auswertbares Dateiinventar erstellt: files.csv fehlt.")
    return result


def scan_epoch(summary: dict) -> float | None:
    raw = summary.get("scan_started_utc")
    if not raw:
        return None
    for fmt in (None, "%Y-%m-%dT%H%M%SZ"):
        try:
            value = datetime.fromisoformat(str(raw).replace("Z", "+00:00")) if fmt is None else datetime.strptime(str(raw), fmt).replace(tzinfo=UTC)
            return value.timestamp() if value.tzinfo is not None else None
        except (ValueError, OverflowError, OSError):
            pass
    return None


def match_source(path: str, term: str, virtual: bool) -> str:
    if virtual:
        return "virtual"
    parent, _, name = path.replace("\\", "/").rpartition("/")
    filename = bool(match_keywords(name, [term]))
    folder = bool(parent and match_keywords(parent, [term]))
    return "both" if filename and folder else "filename" if filename else "folder" if folder else "path"


def empty_statistics(period: dict | None, summary: dict) -> dict:
    return {"files_total": 0, "in_period": 0, "out_of_period": 0, "undetermined": 0,
            "without_timestamps": 0, "multiple_matches": 0, "malformed_records": 0,
            "by_type": {label: {"matched": 0, "exclusive": 0, "available": 0, "missing": 0,
                                  "invalid": 0, "zero_epoch": 0, "after_scan": 0} for _, label in TIMESTAMP_TYPES},
            "categories": {}, "categories_in_period": {}, "period": period,
            "source_scan_status": summary.get("scan_status", "unknown"),
            "scope_notice": ("Die Auswertung umfasst nur den gespeicherten Bestand; die Originalsichtung war eingeschränkt. Weitere Dateien können vorhanden sein."
                             if summary.get("scan_status") != "complete" else "Gespeicherte Originaldateien; keine neue Sichtung und keine Inhaltsanalyse."),
            "timezone_uncertain": bool(period and (period.get("timezone_reproducible") is not True or period.get("timezone") == "local")),
            "scan_time_available": scan_epoch(summary) is not None}


def classify(item: dict, period: dict | None, *, original: bool, scan_time: float | None) -> tuple[dict, dict]:
    """Reuse the scan's OR rule; preserve original historical assignments."""
    parsed = {}
    flags = {"missing": [], "invalid": [], "zero_epoch": [], "after_scan": []}
    for field, label in TIMESTAMP_TYPES:
        # UTC is used ONLY to validate epochs, never to substitute a historical zone.
        stamp, status = parse_timestamp(item.get(field), {"timezone": "UTC"})
        if status != "valid":
            flags[status].append(label)
        else:
            value = float(item[field]); parsed[label] = value
            if value == 0:
                flags["zero_epoch"].append(label)
            if scan_time is not None and value > scan_time:
                flags["after_scan"].append(label)
    virtual = item.get("source") == "container_index"
    if virtual or not period or not parsed:
        assignment = {"in_period": None, "period_matches": "", "latest_period_timestamp": None,
                      "latest_period_timestamp_type": ""}
    elif original:
        # Historic values are evidence. Never silently recompute them in today's TZ.
        assignment = {"in_period": optional_bool(item.get("in_period")),
                      "period_matches": str(item.get("period_matches") or ""),
                      "latest_period_timestamp": number(item.get("latest_period_timestamp")),
                      "latest_period_timestamp_type": str(item.get("latest_period_timestamp_type") or "")}
    else:
        assignment = evaluate_file_period(item, period)
    state = "in" if assignment["in_period"] is True else "out" if assignment["in_period"] is False else "unknown"
    return {**assignment, "period_state": state, "timestamp_flags": flags,
            "timestamp_available": list(parsed),
            "period_assignment_basis": "virtual_unknown" if virtual else "stored_original" if original else "metadata_reevaluation"}, flags


def number(raw):
    if raw in (None, "", "null") or isinstance(raw, bool):
        return None
    try:
        result = float(raw)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


@contextmanager
def connect(path: Path, *, readonly=False):
    db = sqlite3.connect(f"{path.as_uri()}?mode=ro&immutable=1", uri=True) if readonly else sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    deadline = time.monotonic() + MAX_SECONDS
    db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
    if not readonly:
        db.execute("PRAGMA cache_size=-8192")
        db.execute("PRAGMA temp_store=FILE")
    try:
        with db:
            yield db
    finally:
        db.close()


def build_index(target: Path, source: Path, summary: dict, *, period: dict | None,
                original: bool, metadata: dict) -> dict:
    """Streaming CSV -> bounded disk index; no original content reads/processes."""
    started = time.monotonic()
    if not original:
        require_iana_timezone((period or {}).get("timezone"))
    hits = read_json(source / "hits.json")
    catalog = read_json(source / "container-index.json", {"containers": []})
    if not isinstance(catalog.get("containers", []), list) or any(
        not isinstance(c, dict) or not isinstance(c.get("entries", []), list)
        or any(not isinstance(entry, dict) for entry in c.get("entries", []))
        for c in catalog.get("containers", [])
    ):
        raise ValueError("Ungültiges gespeichertes Archivverzeichnis.")
    states = archive_encryption_states(catalog)
    containers = {(str(c.get("partition_slot", "")), str(c.get("path", ""))): c for c in catalog.get("containers", [])}
    stats = empty_statistics(period, summary)
    scanned_at = scan_epoch(summary)
    with connect(target) as db:
        db.executescript("""
            CREATE TABLE meta (data TEXT NOT NULL);
            CREATE TABLE files (id INTEGER PRIMARY KEY, original INTEGER NOT NULL, partition_slot TEXT,
              path TEXT, path_fold TEXT, category TEXT, category_fold TEXT, size INTEGER,
              period_state TEXT, match_mask INTEGER, missing_mask INTEGER, invalid_mask INTEGER,
              zero_mask INTEGER, future_mask INTEGER, latest REAL, record TEXT);
            CREATE TABLE links (term TEXT, file_id INTEGER, source TEXT, certainty TEXT,
              UNIQUE(term,file_id), FOREIGN KEY(file_id) REFERENCES files(id));
        """)
        def append(item, index):
            if index > MAX_ROWS or time.monotonic() - started > MAX_SECONDS:
                raise ValueError("Auswertungslimit erreicht (2 Mio. Einträge / 120 Sekunden); keine Auswertung gespeichert.")
            is_original = item.get("source") != "container_index"
            assignment, flags = classify(item, period, original=original, scan_time=scanned_at)
            path = str(item.get("path") or "")
            value = number(item.get("size"))
            if value is not None and not 0 <= value <= 2**63 - 1:
                value = None
            size = max(0, int(value)) if value is not None else 0
            category = str(item.get("category") or "Unbekannt")
            malformed = not path or item.get(None) is not None or (item.get("size") not in (None, "") and value is None)
            row = {**{k: v for k, v in item.items() if k is not None}, **assignment,
                   "timestamp_raw": {field: item.get(field) for field, _ in TIMESTAMP_TYPES},
                   "path": path, "size": size, "category": category, "extension": item.get("extension", ""),
                   "source": item.get("source", "media_inventory"), "container_format": item.get("container_format", ""),
                   "size_known": item.get("size_known", True), "partition_slot": str(item.get("partition_slot") or ""),
                   "original_file": is_original, "row_number": index, "record_warning": "Unvollständiger Metadatensatz" if malformed else ""}
            for field, _ in TIMESTAMP_TYPES:
                row[field] = number(item.get(field))
            encryption = archive_encryption_state(item, states)
            if encryption is not None:
                row["archive_encryption"] = encryption
            container = containers.get((row["partition_slot"], path)) or containers.get(("", path))
            if container and is_original:
                row.update(container_id=container.get("id", path), container_status=container.get("status", "unknown"),
                           entry_count=container.get("entry_count", len(container.get("entries", []))), encrypted=container.get("encrypted", False),
                           truncated=container.get("truncated", False))
            mask = lambda values: sum(1 << i for i, (_, label) in enumerate(TIMESTAMP_TYPES) if label in values)
            matched = assignment["period_matches"].split("+") if assignment["in_period"] is True else []
            db.execute("INSERT INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                index, int(is_original), row["partition_slot"], path, path.casefold(), category, category.casefold(), size,
                assignment["period_state"], mask(matched), mask(flags["missing"]), mask(flags["invalid"]),
                mask(flags["zero_epoch"]), mask(flags["after_scan"]), number(assignment["latest_period_timestamp"]),
                json.dumps(row, ensure_ascii=False)))
            if is_original:
                stats["files_total"] += 1
                stats[{"in": "in_period", "out": "out_of_period", "unknown": "undetermined"}[assignment["period_state"]]] += 1
                stats["without_timestamps"] += not bool(assignment["timestamp_available"])
                stats["multiple_matches"] += len(matched) > 1
                stats["malformed_records"] += malformed
                stats["categories"][category] = stats["categories"].get(category, 0) + 1
                if assignment["in_period"] is True:
                    stats["categories_in_period"][category] = stats["categories_in_period"].get(category, 0) + 1
                for _, label in TIMESTAMP_TYPES:
                    info = stats["by_type"][label]
                    info["available"] += label in assignment["timestamp_available"]
                    info["matched"] += label in matched
                    info["exclusive"] += matched == [label]
                    for flag in flags:
                        info[flag] += label in flags[flag]
        count = 0
        try:
            with (source / "files.csv").open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                if not reader.fieldnames or "path" not in reader.fieldnames:
                    raise ValueError("Dateiinventar hat keine gültige Pfadspalte.")
                for count, item in enumerate(reader, 1):
                    append(item, count)
            for item in virtual_files(catalog):
                count += 1
                # Historic container times are not verified independent file times.
                item = {**item, **{field: None for field, _ in TIMESTAMP_TYPES}}
                append(item, count)
        except (OSError, csv.Error, UnicodeError) as exc:
            raise ValueError("Dateiinventar konnte nicht vollständig ausgewertet werden.") from exc
        db.executescript("CREATE INDEX paths ON files(path); CREATE INDEX file_sort ON files(path_fold); CREATE INDEX categories ON files(category_fold);")
        keyword_stats = index_keywords(db, hits, started)
        db.executescript("CREATE INDEX keyword_files ON links(file_id); CREATE INDEX keyword_terms ON links(term);")
        stats["latest_period_files"] = [json.loads(row[0]) for row in db.execute("SELECT record FROM files WHERE original=1 AND period_state='in' ORDER BY latest IS NULL,latest DESC,path_fold,id LIMIT 10")]
        stats["duration_seconds"] = round(time.monotonic() - started, 6)
        stats["virtual_entries"] = count - stats["files_total"]
        result = {**metadata, "analysis_version": ANALYSIS_VERSION, "period": period, "statistics": stats,
                  "keyword_statistics": keyword_stats, "original_scan_quality": {k:v for k,v in summary.items() if k.startswith("scan_")},
                  "original_period": summary.get("case_period"), "original_period_file_count": summary.get("period_file_count"),
                  "original_keyword_matches": summary.get("keyword_matches"),
                  "filetype_categories": sorted(set(stats["categories"]) | set(read_json(source / "filetype-catalog.json").get("categories", {})))}
        db.execute("INSERT INTO meta VALUES (?)", (json.dumps(result, ensure_ascii=False),))
    target.chmod(0o600)
    return result


def index_keywords(db, hits: dict, started: float) -> dict:
    by_keyword = hits.get("by_keyword") or {}
    profile = hits.get("profile") or {}
    if not isinstance(by_keyword, dict) or not isinstance(profile, dict):
        raise ValueError("Ungültige historische Stichwortdaten.")
    selected = profile.get("selected_keywords")
    active = list(dict.fromkeys(str(x) for x in selected)) if isinstance(selected, list) else list(by_keyword)
    if len(active) > 10000:
        raise ValueError("Zu viele gespeicherte Stichwörter.")
    sources = Counter(); unresolved = 0; assignments = 0; links_count = 0; terms = []
    for term in active:
        details = by_keyword.get(term) or {}
        if not isinstance(details, dict):
            raise ValueError("Ungültiger historischer Stichworttreffer.")
        paths = details.get("paths") or []
        if not isinstance(paths, list):
            raise ValueError("Historische Trefferpfade sind ungültig.")
        term_sources = Counter()
        for path in paths:
            assignments += 1
            if assignments > MAX_LINKS or time.monotonic() - started > MAX_SECONDS:
                raise ValueError("Stichwort-Auswertungslimit erreicht.")
            if not isinstance(path, str):
                unresolved += 1; sources["unresolved"] += 1; continue
            candidate_count = db.execute("SELECT COUNT(*) FROM files WHERE path=?", (path,)).fetchone()[0]
            candidates = db.execute("SELECT id,original,path FROM files WHERE path=?", (path,))
            certainty = "certain" if candidate_count == 1 else "ambiguous" if candidate_count else "unresolved"
            if certainty != "certain":
                sources[certainty] += 1; term_sources[certainty] += 1
                unresolved += not candidate_count
            for row in candidates:
                links_count += 1
                if links_count > MAX_LINKS or time.monotonic() - started > MAX_SECONDS:
                    raise ValueError("Zu viele mehrdeutige historische Trefferzuordnungen.")
                source = match_source(path, term, not row["original"])
                db.execute("INSERT OR IGNORE INTO links VALUES (?,?,?,?)", (term, row["id"], source, certainty))
                if certainty == "certain":
                    sources[source] += 1; term_sources[source] += 1
        terms.append({"term": term, "stored_count": details.get("count"), "recorded_paths": len(paths), "sources": dict(term_sources)})
    definite = db.execute("SELECT original,COUNT(*) n FROM (SELECT DISTINCT f.original,f.partition_slot,f.path FROM files f JOIN links l ON f.id=l.file_id WHERE l.certainty='certain') GROUP BY original").fetchall()
    counts = {int(r["original"]):r["n"] for r in definite}
    return {"stored_total_matches": hits.get("total_matches"), "path_assignments": assignments,
            "unique_original_files": counts.get(1,0), "unique_virtual_entries": counts.get(0,0),
            "unique_counts_are_lower_bounds": bool(sources["ambiguous"] or unresolved),
            "terms_with_hits": sum(int(t.get("stored_count") or t["recorded_paths"]) > 0 for t in terms),
            "sources": dict(sources), "terms": terms, "historical_profile": profile,
            "profile_origin": "stored_scan_snapshot", "active_terms_known": bool(isinstance(selected,list) or by_keyword)}


def metadata(path: Path) -> dict:
    with connect(path, readonly=True) as db:
        return json.loads(db.execute("SELECT data FROM meta").fetchone()[0])


def query_index(path: Path, *, query="", category="", keyword="", hits_only=False, period_filter="", source_filter="",
                timestamp_filter="", sort_by="", offset=0, limit=250, exact_path=None, archive_status="", originals_only=False):
    if period_filter not in ("", "all", "in", "out", "unknown") or sort_by not in ("", "path", "size", "timestamp", "category"):
        raise ValueError("Ungültiger Zeitraumfilter oder Sortierung.")
    if source_filter not in ("", "filename", "folder", "both", "virtual", "path", "ambiguous") or archive_status not in ("", "encrypted", "unknown"):
        raise ValueError("Ungültige Trefferquelle oder Archivfilter.")
    if offset < 0 or offset > MAX_ROWS or not 1 <= limit <= 500:
        raise ValueError("Ungültige Seitengrenzen.")
    if any(len(str(value)) > 2048 for value in (query, category, keyword, exact_path or "")):
        raise ValueError("Dateifilter ist zu lang.")
    clauses=[];args=[]
    def add(sql,*values):clauses.append(sql);args.extend(values)
    if query:add("instr(f.path_fold,?)>0",query.casefold().strip())
    if category:add("f.category_fold=?",category.casefold().strip())
    if exact_path is not None:add("f.path=?",exact_path)
    if period_filter and period_filter!='all':add("f.period_state=?",period_filter)
    if originals_only:add("f.original=1")
    if archive_status:add("json_extract(f.record,'$.archive_encryption')=?",archive_status)
    if keyword or hits_only or source_filter:
        link=["l.file_id=f.id"];values=[]
        if keyword:link.append("l.term=?");values.append(keyword)
        if source_filter=='ambiguous':link.append("l.certainty='ambiguous'")
        elif source_filter:link.append("l.source=?");values.append(source_filter)
        add("EXISTS (SELECT 1 FROM links l WHERE "+" AND ".join(link)+")",*values)
    if timestamp_filter:
        if timestamp_filter=='multiple':add("f.match_mask NOT IN (0,1,2,4,8)")
        elif timestamp_filter=='no_timestamps':add("(f.missing_mask | f.invalid_mask)=15")
        else:
            parts=timestamp_filter.split(':');kind=parts[0];label=parts[-1]
            if label not in 'BMCA' or len(label)!=1 or kind not in ('matched','exclusive','missing','invalid','zero','future'):
                raise ValueError("Ungültige Zeitstempelgruppe.")
            bit=1 << 'BMCA'.index(label)
            column={'matched':'match_mask','exclusive':'match_mask','missing':'missing_mask','invalid':'invalid_mask','zero':'zero_mask','future':'future_mask'}[kind]
            add(f"f.{column}=?" if kind=='exclusive' else f"(f.{column} & ?) != 0",bit)
    order={"":"f.id","path":"f.path_fold,f.path,f.partition_slot,f.id","size":"f.size DESC,f.path_fold,f.partition_slot,f.id",
           "timestamp":"f.latest IS NULL,f.latest DESC,f.path_fold,f.partition_slot,f.id","category":"f.category_fold,f.path_fold,f.partition_slot,f.id"}[sort_by]
    where=" WHERE "+" AND ".join(clauses) if clauses else ""
    with connect(path,readonly=True) as db:
        total=db.execute("SELECT COUNT(*) FROM files f"+where,args).fetchone()[0]
        rows=db.execute("SELECT f.* FROM files f"+where+" ORDER BY "+order+" LIMIT ? OFFSET ?",[*args,limit,offset]).fetchall()
        files=[]
        for item in rows:
            row=json.loads(item['record'])
            links=db.execute("SELECT term,source,certainty FROM links WHERE file_id=?"+(" AND term=?" if keyword else ""),[item['id'],keyword] if keyword else [item['id']]).fetchall()
            row['keyword_terms']=[x['term'] for x in links];row['keyword_sources']=sorted({x['source'] for x in links});row['keyword_ambiguous']=any(x['certainty']=='ambiguous' for x in links)
            labels={'filename':'DATEINAME','folder':'ORDNERPFAD','both':'DATEINAME + ORDNERPFAD','virtual':'VIRTUELLER ARCHIVPFAD','path':'PFADÜBERGREIFEND'}
            row['match_source']=' · '.join(labels[x] for x in row['keyword_sources'])
            if row['keyword_ambiguous']:row['match_source']+=' · HISTORISCH MEHRDEUTIG'
            if not row['original_file']:row['period_notice']='Zeitraum nicht eigenständig bestimmbar'
            files.append(row)
    return {'files':files,'total':total,'shown':len(files),'offset':offset,'next_offset':offset+len(files),'has_more':offset+len(files)<total}
