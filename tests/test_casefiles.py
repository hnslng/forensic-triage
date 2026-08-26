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
    assert "decision_recorded" in (case / "audit.log").read_text(encoding="utf-8")
    assert len((case / "manifest.sha256").read_text(encoding="utf-8").splitlines()) >= 7
    inventory = store.file_inventory(media_id, "a")
    assert inventory == {
        "total": 1,
        "shown": 1,
        "files": [{"path": "a", "size": 1, "extension": "", "category": "Unbekannt", "mtime": ""}],
    }


def test_non_selection_requires_reason(tmp_path) -> None:
    store = CaseStore(tmp_path / "casefiles")
    result_dir = make_result(store, "FALL-1", "SICHT-001")
    media_id = store.record_scan("FALL-1", "SICHT-001", "", {"path": "/dev/sdb"}, result_dir)["media"]["id"]

    with pytest.raises(ValueError, match="Begründung"):
        store.record_decision(media_id, "not_selected", None, "", "HL")


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
