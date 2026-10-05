import plistlib
import subprocess
import json
from contextlib import contextmanager
from pathlib import Path

from forensic_triage import iphone
from forensic_triage.crypto_rules import snapshot


RULES = {
    "app_rules": [
        {"id": "wallet", "category": "Kryptowährung / Wallet", "bundle_ids": ["io.test.wallet"], "name_contains": ["wallet"]},
    ],
    "file_rules": [
        {"id": "backup", "label": "Mögliches Wallet-Backup", "path_contains": ["wallet"], "extensions": ["json"]},
    ],
}


def completed(args, stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


def test_probe_iphone_reports_paired_metadata(monkeypatch):
    info = plistlib.dumps({
        "DeviceName": "Testtelefon", "ProductType": "iPhone15,4", "ProductVersion": "18.6",
    }).decode()

    def fake_run(args, **_kwargs):
        if "validate" in args:
            return completed(args, "SUCCESS: Validated pairing")
        return completed(args, info)

    monkeypatch.setattr(iphone, "_run", fake_run)
    monkeypatch.setattr(iphone, "tools_available", lambda: True)
    device = iphone.probe_iphone("000-test")
    assert device["connection_state"] == "paired"
    assert device["device_name"] == "Testtelefon"
    assert device["ios_version"] == "18.6"
    assert device["path"] == "iphone:000-test"


def test_probe_iphone_explains_missing_trust(monkeypatch):
    monkeypatch.setattr(iphone, "_run", lambda args, **kwargs: completed(args, stderr="ERROR: Please trust this computer", returncode=1))
    monkeypatch.setattr(iphone, "tools_available", lambda: True)
    device = iphone.probe_iphone("000-test")
    assert device["connection_state"] == "trust_required"
    assert "vertrauen" in device["unavailable_reason"].casefold()


def test_app_and_file_rules_are_metadata_only():
    apps = iphone.normalize_apps([{
        "CFBundleDisplayName": "Test Wallet", "CFBundleIdentifier": "io.test.wallet",
        "CFBundleShortVersionString": "1.2", "UIFileSharingEnabled": True,
    }], RULES)
    assert apps[0]["matches"] == [{"id": "wallet", "category": "Kryptowährung / Wallet"}]
    assert iphone.classify_file_hint("Dokumente/wallet-backup.json", "json", RULES)[0]["id"] == "backup"
    assert iphone.classify_file_hint("Dokumente/wallet-backup.txt", "txt", RULES) == []


def test_inventory_reads_only_filesystem_metadata(tmp_path: Path, monkeypatch):
    folder = tmp_path / "Dokumente"
    folder.mkdir()
    target = folder / "wallet-backup.json"
    target.write_text("SECRET CONTENT MUST NOT BE READ", encoding="utf-8")
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path == target:
            raise AssertionError("file content was opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    files, directories, hints, truncated = iphone.inventory_tree(
        tmp_path, "AFC_MEDIA", RULES, deadline=float("inf"), max_files=20,
    )
    assert not truncated
    assert files[0]["path"] == "AFC_MEDIA/Dokumente/wallet-backup.json"
    assert files[0]["size"] == len("SECRET CONTENT MUST NOT BE READ")
    assert hints[0]["id"] == "backup"
    assert directories


def test_inventory_limit_is_explicit(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    files, _directories, _hints, truncated = iphone.inventory_tree(
        tmp_path, "AFC_MEDIA", RULES, deadline=float("inf"), max_files=1,
    )
    assert len(files) == 1
    assert truncated


def test_simulated_quick_scan_writes_app_only_case_bundle(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(iphone, "ensure_paired", lambda udid: {
        "path": f"iphone:{udid}", "media_type": "iphone", "vendor": "Apple",
        "model": "iPhone15,4", "device_name": "Testtelefon", "serial": udid, "udid": udid,
        "ios_version": "18.6", "build_version": "22G86", "connection_state": "paired",
        "size": 0, "mounted": False, "read_only": False, "scan_supported": True,
    })
    monkeypatch.setattr(iphone, "_application_plist", lambda udid: ([{
        "CFBundleDisplayName": "Test Wallet", "CFBundleIdentifier": "io.test.wallet",
        "CFBundleShortVersionString": "1.2", "UIFileSharingEnabled": True,
    }], "complete"))
    monkeypatch.setattr(iphone, "readonly_ifuse", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Quick scan must not mount files")))
    current_rules = snapshot({"app_rules": [{"id": "wallet", "name": "Test Wallet", "category": "wallet", "relevance": "high", "enabled": True,
        "bundle_ids": ["io.test.wallet"], "aliases": [], "terms": []}],
        "file_rules": [{"id": "backup", "name": "Wallet-Backup", "category": "wallet", "relevance": "high", "enabled": True,
        "filename_equals": [], "terms": ["wallet"], "context_terms": [], "extensions": ["json"]}]})
    result = iphone.scan_iphone({
        "udid": "000-test", "evidence": "SICHT-001", "results_root": str(tmp_path / "results"),
        "profile_path": str(tmp_path / "unused.yaml"), "keywords": ["wallet"],
        "profile_sources": [{"id": "test", "name": "TEST", "version": "1", "sha256": "abc"}],
        "filetype_catalog": {"version": 1, "categories": {"Web-Dateien": ["json"]}},
        "crypto_rules": current_rules,
        "case_period": {"date_from": "2026-01-01", "date_to": "2026-06-30", "timezone": "UTC", "timezone_source": "test", "timezone_reproducible": True},
    })
    summary = json.loads((result / "summary.json").read_text())
    detail = json.loads((result / "iphone.json").read_text())
    device = json.loads((result / "device.json").read_text())
    assert summary["file_count"] == 0
    assert summary["scan_mode"] == "phone_crypto_quick"
    assert summary["case_period"]["date_from"] == "2026-01-01"
    assert summary["period_evaluation"] == "not_applicable"
    assert summary["period_file_count"] is None
    assert summary["categories_in_period"] == {}
    assert summary["latest_period_files"] == []
    assert (result / "files.csv").read_text().count("\n") == 1
    assert summary["timings"]["application_inventory_seconds"] >= 0
    assert summary["iphone"]["app_hint_count"] == 1
    assert summary["iphone"]["apps_complete"] is True
    assert summary["iphone"]["files_complete"] is False
    assert summary["crypto_file_hints"] == 0
    assert detail["app_hints"][0]["name"] == "Test Wallet"
    assert detail["file_hints"] == []
    assert detail["notice"].startswith("App-Treffer")
    assert device["write_operations_performed"] is False
    assert device["access_mode"] == "apple_application_metadata"
    for name in ("files.csv", "hits.json", "partitions.json", "container-index.json", "apps.json", "crypto-rules.json", "crypto-hints.json"):
        assert (result / name).is_file()
