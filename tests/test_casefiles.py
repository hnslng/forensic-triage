import json

import pytest

from forensic_triage.casefiles import CaseStore, safe_component


def make_result(store: CaseStore, case: str, evidence: str):
    result = store.scan_root(case, evidence) / "2026-08-26T120000Z_BM-001"
    result.mkdir(parents=True)
    (result / "summary.json").write_text(json.dumps({
        "evidence": evidence, "file_count": 12, "directory_count": 3,
        "keyword_matches": 2, "duration_seconds": 0.5,
    }), encoding="utf-8")
    (result / "hits.json").write_text(json.dumps({
        "by_keyword": {"rechnung": {"count": 2, "paths": ["a", "b"]}},
    }), encoding="utf-8")
    (result / "files.csv").write_text("path,size\na,1\n", encoding="utf-8")
    return result


def test_case_archive_records_scan_and_decision(tmp_path) -> None:
    store = CaseStore(tmp_path / "casefiles")
    result_dir = make_result(store, "FALL-2026-1", "BM-001")
    recorded = store.record_scan(
        "FALL-2026-1", "BM-001", "HL",
        {"path": "/dev/sdb", "vendor": "USB", "model": "Test", "serial": "123", "size": 1000},
        result_dir,
    )
    media_id = recorded["media"]["id"]

    decided = store.record_decision(media_id, "not_selected", "no_indicators", "Keine Treffer.", "HL")

    assert decided["media"]["decision"] == "not_selected"
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
    result_dir = make_result(store, "FALL-1", "BM-1")
    media_id = store.record_scan("FALL-1", "BM-1", "", {"path": "/dev/sdb"}, result_dir)["media"]["id"]

    with pytest.raises(ValueError, match="Begründung"):
        store.record_decision(media_id, "not_selected", None, "", "HL")


def test_safe_component_refuses_path_escape() -> None:
    assert safe_component("FALL/2026") == "FALL-2026"
    with pytest.raises(ValueError):
        safe_component("../")
