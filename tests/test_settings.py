import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.client import HTTPConnection

import pytest

from forensic_triage import scanner
from forensic_triage import web as web_module
from forensic_triage.classifier import classify
from forensic_triage.settings import (
    SettingsConflict, catalog_snapshot, default_catalog, load_catalog,
    prepare_profiles, save_catalog,
)
from forensic_triage.web import TriageHTTPServer


def test_expanded_defaults_are_unique_and_ambiguous_types_are_neutral():
    default_catalog()  # Also validates unique ownership across all defaults.
    for name, category in {
        "photo.CR3": "Bilder", "report.DOCM": "Dokumente", "table.xlsb": "Tabellen",
        "capture.m2ts": "Video", "voice.opus": "Audio", "disk.E01": "Datenträger-/Backup-Images",
        "old.tar.zst": "Archive", "mail.emlx": "E-Mail", "system.evtx": "Systemartefakte",
        "data.bak": "Sicherungskopien", "data.raw": "Mehrdeutig", "data.key": "Mehrdeutig",
        "passwords.kdbx": "Schutz-/Schlüsseldateien", "file.strange": "Unbekannt",
    }.items():
        assert classify(name)[1] == category


@pytest.mark.parametrize("categories", [
    {"Bilder": ["jpg"], "Dokumente": [".JPG"]},
    {"Bilder": ["jpg", "JPG"]}, {"Unbekannt": ["xyz"]},
    {"Bilder": ["tar.gz"]}, {"Bilder": ["../jpg"]},
    {"Bilder": ["jpg"], "bilder": ["png"]}, {"X": []},
])
def test_invalid_catalog_is_rejected_without_overwriting(tmp_path, categories):
    path = tmp_path / "filetypes.json"
    before = save_catalog(path, {"Fotos": ["jpg"]}, default_catalog()["sha256"])
    original = path.read_bytes()
    with pytest.raises(ValueError):
        save_catalog(path, categories, before["sha256"])
    assert path.read_bytes() == original


def test_catalog_versions_conflict_and_standard_reset(tmp_path):
    path = tmp_path / "filetypes.json"
    standard = default_catalog()
    saved = save_catalog(path, {"Eigene Bilder": [" .JPG ", "png"]}, standard["sha256"])
    assert saved["categories"] == {"Eigene Bilder": ["jpg", "png"]}
    assert saved["version"] == 2
    assert load_catalog(path) == saved
    assert save_catalog(path, saved["categories"], saved["sha256"]) == saved
    with pytest.raises(SettingsConflict):
        save_catalog(path, {"Veraltet": ["jpg"]}, standard["sha256"])
    restored = save_catalog(path, standard["categories"], saved["sha256"])
    assert restored["version"] == 3
    assert restored["categories"] == standard["categories"]
    path.write_text('{"categories": {}, "version": 3}')
    with pytest.raises(ValueError):
        load_catalog(path)


def test_profile_migration_preserves_edits_and_custom_profiles(tmp_path):
    source = tmp_path / "release-1" / "profiles"
    source.mkdir(parents=True)
    (source / "default.yaml").write_text('name: Test\nversion: "1.0"\nkeywords: [rechnung]\n')
    (source / "custom.yaml").write_text('name: Spezial\nkeywords: [wallet]\n')
    root = tmp_path / "persistent"
    profile = prepare_profiles(root, source / "default.yaml")
    custom = (root / "profiles/custom.yaml").read_bytes()
    profile.write_text('name: Lokal\nkeywords: [kunden]\n')
    second = tmp_path / "release-2/profiles"
    second.mkdir(parents=True)
    (second / "default.yaml").write_text('name: Neue Version\nkeywords: [neu]\n')
    assert prepare_profiles(root, second / "default.yaml") == profile
    assert "kunden" in profile.read_text()
    assert (root / "profiles/custom.yaml").read_bytes() == custom


def test_first_start_migrates_profiles_from_newest_prior_release(tmp_path, monkeypatch):
    releases = tmp_path / "releases"
    prior = releases / "v0.2.0-alpha.43" / "profiles"
    prior.mkdir(parents=True)
    (prior / "default.yaml").write_text('name: Lokal angepasst\nkeywords: [eigener-begriff]\n')
    (prior / "custom.yaml").write_text('name: Eigene Suche\nkeywords: [wallet]\n')
    current_root = releases / "v0.2.0-alpha.44"
    current = current_root / "profiles"
    current.mkdir(parents=True)
    (current / "default.yaml").write_text('name: Neuer Standard\nkeywords: [standard]\n')
    original = tmp_path / "install" / "profiles"
    original.mkdir(parents=True)
    (original / "default.yaml").write_text('name: Alter Standard\nkeywords: [alt]\n')
    settings_root = tmp_path / "settings"
    monkeypatch.setenv("FORENSIC_TRIAGE_SETTINGS_ROOT", str(settings_root))
    monkeypatch.setenv("FORENSIC_TRIAGE_RELEASES_ROOT", str(releases))
    monkeypatch.setattr(web_module, "PROJECT_ROOT", current_root)

    server = TriageHTTPServer(("127.0.0.1", 0), tmp_path, tmp_path / "results",
                              original / "default.yaml", tmp_path / "install/casefiles", 180, 15)
    try:
        assert "eigener-begriff" in server.profile_path.read_text()
        assert "wallet" in (server.profile_path.parent / "custom.yaml").read_text()
    finally:
        server.server_close()


@contextmanager
def settings_server(tmp_path, monkeypatch):
    monkeypatch.setenv("FORENSIC_TRIAGE_SETTINGS_ROOT", str(tmp_path / "local-settings"))
    profiles = tmp_path / "code/profiles"
    profiles.mkdir(parents=True)
    (profiles / "default.yaml").write_text('name: Allgemein\nversion: "1.0"\nkeywords: [rechnung]\n')
    server = TriageHTTPServer(("127.0.0.1", 0), tmp_path, tmp_path / "results",
                             profiles / "default.yaml", tmp_path / "casefiles", 180, 15)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def request(server, method, path, payload=None):
    connection = HTTPConnection(*server.server_address, timeout=5)
    try:
        connection.request(method, path, json.dumps(payload) if payload is not None else None,
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def test_api_serializes_competing_catalog_writes_and_keeps_profiles_outside_code(tmp_path, monkeypatch):
    with settings_server(tmp_path, monkeypatch) as server:
        status, data = request(server, "GET", "/api/settings/filetypes")
        assert status == 200
        payloads = [{"categories": {name: ["jpg"]}, "base_sha256": data["catalog"]["sha256"]}
                    for name in ("Fotos", "Bilddateien")]
        with ThreadPoolExecutor(max_workers=2) as pool:
            replies = list(pool.map(lambda body: request(server, "POST", "/api/settings/filetypes", body), payloads))
        assert sorted(reply[0] for reply in replies) == [200, 409]
        status, data = request(server, "POST", "/api/profiles", {"id": None, "name": "Spezial", "keywords": ["wallet"]})
        assert status == 201
        assert (server.profile_path.parent / f"{data['profile']['id']}.yaml").is_file()
        assert not (tmp_path / "code/profiles/spezial.yaml").exists()
        status, updated = request(server, "POST", "/api/profiles", {"id": "default", "name": "Allgemein / Wirtschaft", "keywords": ["kunden"]})
        assert status == 201
        assert updated["profile"]["name"] == "Allgemein / Wirtschaft"
        assert "kunden" in server.profile_path.read_text()
        assert "rechnung" in (tmp_path / "code/profiles/default.yaml").read_text()
        assert server.case_store.list_cases() == []


def test_scan_catalog_snapshot_applies_to_files_containers_and_preserves_history(tmp_path, monkeypatch):
    catalog = catalog_snapshot({"Fotos": ["heic"], "Archive": ["zip"], "Meine Dokumente": ["docm"]}, 7)
    containers = {"status": "ok", "containers": [{"id": "OPT:Test.zip", "path": "Test.zip", "format": "zip",
                    "partition_slot": "OPT", "status": "ok", "entries": [
                        {"path": "inner.docm", "kind": "file", "size": 1, "category": "Unbekannt"}]}]}
    monkeypatch.setattr(scanner, "inspect_device", lambda path: {"type": "rom"})
    monkeypatch.setattr(scanner, "enforce_read_only", lambda path: None)
    monkeypatch.setattr(scanner, "_inventory_optical_medium", lambda *args: (
        [{"path": "photo.HEIC", "size": 3}, {"path": "Test.zip", "size": 9}], [], [], copy.deepcopy(containers)))
    # The selected profile is a scan-start snapshot; no mutable profile reread.
    monkeypatch.setattr(scanner, "load_profile", lambda path: pytest.fail("profile reread during scan"))
    result = scanner.scan(tmp_path / "device", tmp_path / "profile", "SICHT-001", tmp_path / "results",
                          keywords=["inner"], profile_sources=[{"id": "default", "name": "Test", "version": "1", "sha256": "test"}],
                          filetype_catalog=catalog)
    summary = json.loads((result / "summary.json").read_text())
    assert summary["categories_by_count"] == {"Fotos": 1, "Archive": 1}
    assert summary["filetype_catalog"] == {"version": 7, "sha256": catalog["sha256"]}
    assert json.loads((result / "filetype-catalog.json").read_text()) == catalog
    indexed = json.loads((result / "container-index.json").read_text())
    assert indexed["containers"][0]["entries"][0]["category"] == "Meine Dokumente"
    assert json.loads((result / "hits.json").read_text())["total_matches"] == 1
    original = {path.name: path.read_bytes() for path in result.iterdir() if path.is_file()}
    save_catalog(tmp_path / "settings/filetypes.json", {"Neu": ["heic"]}, default_catalog()["sha256"])
    assert {path.name: path.read_bytes() for path in result.iterdir() if path.is_file()} == original
