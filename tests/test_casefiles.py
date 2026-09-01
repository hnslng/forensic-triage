import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from forensic_triage.casefiles import CaseStore, safe_component


def make_result(store: CaseStore, case: str, sighting: str):
    result = store.scan_root(case, sighting) / f"2026-08-26T120000Z_{sighting}"
    result.mkdir(parents=True)
    (result / "summary.json").write_text(json.dumps({
        "evidence": sighting, "file_count": 12, "directory_count": 3,
        "keyword_matches": 2, "duration_seconds": 0.5,
        "total_file_bytes": 4096,
        "categories_by_count": {"Dokumente": 8, "Bilder": 4},
    }), encoding="utf-8")
    (result / "hits.json").write_text(json.dumps({
        "by_keyword": {"rechnung": {"count": 2, "paths": ["a", "b"]}},
    }), encoding="utf-8")
    (result / "files.csv").write_text("path,size\na,1\n", encoding="utf-8")
    return result


def test_case_archive_records_scan_and_decision(tmp_path) -> None:
    store = CaseStore(tmp_path / "casefiles")
    result_dir = make_result(store, "FALL-2026-1", "SICHT-001")
    recorded = store.record_scan(
        "FALL-2026-1", "SICHT-001", "HL",
        {"path": "/dev/sdb", "vendor": "USB", "model": "Test", "serial": "123", "size": 1000},
        result_dir,
    )
    media_id = recorded["media"]["id"]

    decided = store.record_decision(media_id, "not_selected", "no_indicators", "Keine Treffer.", "HL")

    assert decided["media"]["decision"] == "not_selected"
    assert decided["media"]["sighting_number"] == "SICHT-001"
    assert decided["media"]["evidence_number"] == ""
    assert store.list_cases()[0]["media_count"] == 1
    case = store.case_path("FALL-2026-1")
    assert (case / "media-register.csv").is_file()
    assert "Nicht zur Sicherung ausgewählt" in (case / "case-report.txt").read_text(encoding="utf-8")
    assert (case / "case-report.pdf").read_bytes().startswith(b"%PDF")
    assert "decision_recorded" in (case / "audit.log").read_text(encoding="utf-8")
    manifest = (case / "manifest.sha256").read_text(encoding="utf-8")
    assert "case-report.pdf" in manifest
    assert len(manifest.splitlines()) >= 8
    inventory = store.file_inventory(media_id, "a")
    assert inventory == {
        "total": 1,
        "shown": 1,
        "offset": 0,
        "next_offset": 1,
        "has_more": False,
        "files": [{"path": "a", "size": 1, "extension": "", "category": "Unbekannt", "mtime": "", "source": "media_inventory", "container_format": "", "size_known": True}],
    }


def test_case_is_created_only_by_explicit_start(tmp_path) -> None:
    store = CaseStore(tmp_path / "casefiles")

    started = store.start_case("FALL-NEU", "HL")

    assert started["case"]["case_number"] == "FALL-NEU"
    assert started["media"] == []
    assert store.list_cases()[0]["media_count"] == 0
    assert '"event_type": "case_started"' in (
        store.case_path("FALL-NEU") / "audit.log"
    ).read_text(encoding="utf-8")


def test_non_selection_requires_reason(tmp_path) -> None:
    store = CaseStore(tmp_path / "casefiles")
    result_dir = make_result(store, "FALL-1", "SICHT-001")
    media_id = store.record_scan("FALL-1", "SICHT-001", "", {"path": "/dev/sdb"}, result_dir)["media"]["id"]

    with pytest.raises(ValueError, match="Begründung"):
        store.record_decision(media_id, "not_selected", None, "", "HL")


def test_legacy_review_status_cannot_be_recorded_again(tmp_path) -> None:
    store = CaseStore(tmp_path / "casefiles")
    result_dir = make_result(store, "FALL-1", "SICHT-001")
    media_id = store.record_scan("FALL-1", "SICHT-001", "", {"path": "/dev/sdb"}, result_dir)["media"]["id"]

    with pytest.raises(ValueError, match="Entscheidungsstatus"):
        store.record_decision(media_id, "review", None, "", "HL")


def test_directory_inventory_returns_one_lazy_tree_level(tmp_path) -> None:
    store = CaseStore(tmp_path / "casefiles")
    result_dir = make_result(store, "FALL-TREE", "SICHT-001")
    (result_dir / "files.csv").write_text(
        "path,size,extension,category\n"
        "partition_001/docs/report.pdf,10,.pdf,Dokumente\n"
        "partition_001/docs/note.txt,2,.txt,Dokumente\n"
        "partition_001/photo.jpg,5,.jpg,Bilder\n",
        encoding="utf-8",
    )
    (result_dir / "hits.json").write_text(json.dumps({
        "by_keyword": {"docs": {"count": 2, "paths": [
            "partition_001/docs/report.pdf", "partition_001/docs/note.txt",
        ]}},
    }), encoding="utf-8")
    media_id = store.record_scan(
        "FALL-TREE", "SICHT-001", "HL", {"path": "/dev/sdb"}, result_dir,
    )["media"]["id"]

    root = store.directory_inventory(media_id)
    assert root["entries"] == [{
        "kind": "directory", "name": "partition_001", "path": "partition_001",
        "file_count": 3, "size": 17,
    }]
    partition = store.directory_inventory(media_id, "partition_001")
    assert [entry["name"] for entry in partition["entries"]] == ["docs", "photo.jpg"]
    assert partition["entries"][0]["file_count"] == 2
    assert store.file_inventory(media_id, category="Bilder")["files"][0]["path"] == "partition_001/photo.jpg"
    keyword_files = store.file_inventory(media_id, keyword="docs")["files"]
    assert len(keyword_files) == 2
    assert {item["match_source"] for item in keyword_files} == {"ORDNERPFAD"}
    paged_files = store.file_inventory(media_id, category="Dokumente", limit=1, offset=1)
    assert paged_files["shown"] == 1
    assert paged_files["offset"] == 1
    assert paged_files["has_more"] is False
    paged = store.directory_inventory(media_id, "partition_001", limit=1)
    assert paged["has_more"] is True
    assert store.directory_inventory(media_id, "partition_001", limit=1, offset=1)["entries"][0]["name"] == "photo.jpg"


def test_container_inventory_is_expandable_and_searchable_without_changing_counts(tmp_path) -> None:
    store = CaseStore(tmp_path / "casefiles")
    result_dir = make_result(store, "FALL-CONTAINER", "SICHT-001")
    (result_dir / "files.csv").write_text(
        "path,size,extension,category\n"
        "Ablage.zip,100,zip,Archive\n",
        encoding="utf-8",
    )
    (result_dir / "container-index.json").write_text(json.dumps({
        "status": "ok",
        "containers": [{
            "path": "Ablage.zip", "format": "zip", "status": "ok", "entry_count": 2,
            "encrypted": True,
            "truncated": False,
            "entries": [
                {"path": "Dokumente", "kind": "directory", "size": 0, "category": "Ordner", "extension": ""},
                {"path": "Dokumente/Rechnung.pdf", "kind": "file", "size": 42, "category": "Dokumente", "extension": "pdf"},
            ],
        }],
    }), encoding="utf-8")
    (result_dir / "hits.json").write_text(json.dumps({
        "by_keyword": {"rechnung": {"count": 1, "paths": ["Ablage.zip › Dokumente/Rechnung.pdf"]}},
    }), encoding="utf-8")
    media_id = store.record_scan(
        "FALL-CONTAINER", "SICHT-001", "HL", {"path": "/dev/sdb"}, result_dir,
    )["media"]["id"]

    root = store.directory_inventory(media_id)
    assert root["entries"][0]["kind"] == "container"
    assert root["entries"][0]["entry_count"] == 2
    assert root["entries"][0]["encrypted"] is True
    archive_filter = store.file_inventory(media_id, category="Archive")["files"][0]
    assert archive_filter["container_id"] == "Ablage.zip"
    assert archive_filter["container_status"] == "ok"
    assert archive_filter["entry_count"] == 2
    container_root = store.container_inventory(media_id, "Ablage.zip")
    assert container_root["entries"][0]["name"] == "Dokumente"
    assert store.container_inventory(media_id, "Ablage.zip", "Dokumente")["entries"][0]["name"] == "Rechnung.pdf"
    search = store.file_inventory(media_id, query="rechnung")
    assert search["files"][0]["match_source"] == "ZIP-INHALT"
    assert search["files"][0]["path"] == "Ablage.zip › Dokumente/Rechnung.pdf"


def test_archive_case_removes_active_record_and_keeps_recoverable_copy(tmp_path) -> None:
    store = CaseStore(tmp_path / "casefiles")
    result_dir = make_result(store, "FALL-DELETE", "SICHT-001")
    store.record_scan("FALL-DELETE", "SICHT-001", "HL", {"path": "/dev/sdb"}, result_dir)

    result = store.archive_case("FALL-DELETE")

    assert result == {"case_number": "FALL-DELETE", "archived": True, "recoverable": True}
    assert store.case_detail("FALL-DELETE") is None
    archived = list((store.root / ".trash").glob("*-FALL-DELETE"))
    assert len(archived) == 1
    assert (archived[0] / "case-report.txt").is_file()
    assert (archived[0] / "case-report.pdf").is_file()


def test_evidence_number_is_assigned_only_when_secured(tmp_path) -> None:
    store = CaseStore(tmp_path / "casefiles")
    assert store.next_sighting_number("FALL-1") == "SICHT-001"
    result_dir = make_result(store, "FALL-1", "SICHT-001")
    media_id = store.record_scan("FALL-1", "SICHT-001", "HL", {"path": "/dev/sdb"}, result_dir)["media"]["id"]

    with pytest.raises(ValueError, match="Beweismittelnummer"):
        store.record_decision(media_id, "secure", None, "", "HL")

    decided = store.record_decision(media_id, "secure", None, "", "HL", "BM-007")
    assert decided["media"]["evidence_number"] == "BM-007"
    assert store.next_sighting_number("FALL-1") == "SICHT-002"


def test_sighting_numbers_are_reserved_atomically(tmp_path) -> None:
    store = CaseStore(tmp_path / "casefiles")
    with ThreadPoolExecutor(max_workers=6) as pool:
        numbers = list(pool.map(
            lambda index: store.allocate_sighting_number("FALL-PARALLEL", "HL", f"/dev/sd{index}"),
            range(6),
        ))

    assert sorted(numbers) == [f"SICHT-{index:03d}" for index in range(1, 7)]
    assert store.next_sighting_number("FALL-PARALLEL") == "SICHT-007"
    store.refresh_exports("FALL-PARALLEL")
    audit = (store.case_path("FALL-PARALLEL") / "audit.log").read_text(encoding="utf-8")
    assert audit.count('"event_type": "sighting_reserved"') == 6


def test_safe_component_refuses_path_escape() -> None:
    assert safe_component("FALL/2026") == "FALL-2026"
    with pytest.raises(ValueError):
        safe_component("../")


def test_existing_archive_gets_neutral_sighting_numbers(tmp_path) -> None:
    root = tmp_path / "casefiles"
    root.mkdir()
    database = root / "case-index.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE cases (id INTEGER PRIMARY KEY, case_number TEXT UNIQUE, created_at TEXT, updated_at TEXT)")
        connection.execute(
            """CREATE TABLE media (
                id INTEGER PRIMARY KEY, case_id INTEGER, evidence_number TEXT NOT NULL, scan_id TEXT NOT NULL,
                result_path TEXT NOT NULL, scanned_at TEXT NOT NULL, device_path TEXT NOT NULL, vendor TEXT NOT NULL,
                model TEXT NOT NULL, serial TEXT NOT NULL, size INTEGER NOT NULL, file_count INTEGER NOT NULL,
                directory_count INTEGER NOT NULL, keyword_matches INTEGER NOT NULL, duration_seconds REAL NOT NULL,
                decision TEXT NOT NULL DEFAULT 'open', reason_code TEXT, reason_note TEXT,
                decision_operator TEXT, decided_at TEXT, UNIQUE(case_id, evidence_number, scan_id))"""
        )
        connection.execute("INSERT INTO cases VALUES (1, 'FALL-ALT', 't', 't')")
        connection.execute(
            "INSERT INTO media VALUES (1, 1, 'BM-ALT', 'scan-1', 'path', 't', '/dev/sdb', '', '', '', 0, 0, 0, 0, 0, 'not_selected', NULL, NULL, NULL, NULL)"
        )

    store = CaseStore(root)
    with store._connect() as connection:
        row = connection.execute("SELECT sighting_number, evidence_number FROM media WHERE id=1").fetchone()
    assert dict(row) == {"sighting_number": "SICHT-001", "evidence_number": ""}
    report = (root / "FALL-ALT" / "case-report.txt").read_text(encoding="utf-8")
    assert "SICHTUNGSMEDIUM: SICHT-001" in report
    assert "BEWEISMITTEL / ASSERVAT: nicht vergeben" in report
