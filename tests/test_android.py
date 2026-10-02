import json
import subprocess
from pathlib import Path

from forensic_triage import android
from forensic_triage.crypto_rules import snapshot


def completed(args, stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)


def test_usb_candidate_recognizes_android_vendor_without_adb(tmp_path: Path):
    device = tmp_path / "1-1"
    device.mkdir()
    (device / "idVendor").write_text("04e8\n")
    (device / "idProduct").write_text("6860\n")
    (device / "manufacturer").write_text("SAMSUNG\n")
    (device / "product").write_text("Galaxy Test\n")
    (device / "serial").write_text("SERIAL1\n")
    assert android._usb_candidates(tmp_path) == [{
        "sysfs_name": "1-1", "vendor_id": "04e8", "product_id": "6860",
        "vendor": "SAMSUNG", "model": "Galaxy Test", "serial": "SERIAL1",
    }]


def test_discovery_distinguishes_debugging_and_authorization(monkeypatch):
    monkeypatch.setattr(android.shutil, "which", lambda _name: "/usr/bin/adb")
    monkeypatch.setattr(android, "_usb_candidates", lambda: [{
        "sysfs_name": "1-1", "vendor_id": "04e8", "product_id": "6860",
        "vendor": "Samsung", "model": "Galaxy", "serial": "SERIAL1",
    }])
    monkeypatch.setattr(android, "_adb_rows", lambda: [])
    device = android.discover_androids()[0]
    assert device["connection_state"] == "debugging_required"
    assert device["scan_supported"] is False
    assert any("Softwareinformationen" in step for step in device["guidance"])

    monkeypatch.setattr(android, "_adb_rows", lambda: [{"serial": "SERIAL1", "adb_state": "unauthorized", "model": "Galaxy"}])
    device = android.discover_androids()[0]
    assert device["connection_state"] == "authorization_required"
    assert device["scan_supported"] is False


def test_discovery_explains_missing_adb_package(monkeypatch):
    monkeypatch.setattr(android.shutil, "which", lambda _name: None)
    monkeypatch.setattr(android, "_usb_candidates", lambda: [{
        "sysfs_name": "1-1", "vendor_id": "04e8", "product_id": "6860",
        "vendor": "Samsung", "model": "Galaxy", "serial": "SERIAL1",
    }])
    device = android.discover_androids()[0]
    assert device["connection_state"] == "support_missing"
    assert "adb installieren" in device["unavailable_reason"]
    assert any("apt-get install" in step for step in device["guidance"])


def test_android_quick_scan_checks_all_visible_profiles_and_no_files(tmp_path: Path, monkeypatch):
    def fake_adb(_serial, *args, timeout=12):
        joined = " ".join(args)
        if joined == "get-state":
            return completed(args, "device\n")
        if joined.startswith("shell getprop"):
            values = {
                "ro.serialno": "SERIAL1", "ro.product.manufacturer": "Samsung",
                "ro.product.model": "Galaxy Test", "ro.build.version.release": "16",
                "ro.build.display.id": "TESTBUILD",
            }
            return completed(args, values.get(args[-1], "") + "\n")
        if joined == "shell pm list users":
            return completed(args, "Users:\n\tUserInfo{0:Owner:13} running\n\tUserInfo{10:Work:30}\n")
        if "package list packages" in joined:
            user = args[args.index("--user") + 1]
            package = "io.metamask" if user == "0" else "com.example.work"
            return completed(args, f"package:{package}\n")
        if "dumpsys package io.metamask" in joined:
            return completed(args, "versionName=7.50.0\n")
        return completed(args, returncode=1, stderr="unexpected")

    monkeypatch.setattr(android, "_adb", fake_adb)
    rules = snapshot({
        "app_rules": [{"id": "metamask", "name": "MetaMask", "category": "wallet", "relevance": "high",
                       "enabled": True, "ios_bundle_ids": [], "android_package_ids": ["io.metamask"],
                       "aliases": [], "terms": []}],
        "file_rules": [],
    })
    result = android.scan_android({
        "adb_serial": "SERIAL1", "evidence": "SICHT-001", "results_root": str(tmp_path / "results"),
        "profile_path": str(tmp_path / "unused.yaml"), "profile_sources": [{"id": "test", "name": "TEST", "version": "1", "sha256": "abc"}],
        "filetype_catalog": {"version": 1, "categories": {"Bilder": ["jpg"]}}, "crypto_rules": rules,
    })
    phone = json.loads((result / "phone.json").read_text())
    summary = json.loads((result / "summary.json").read_text())
    assert [profile["id"] for profile in phone["profiles"]] == ["0", "10"]
    assert phone["app_hints"][0]["package_id"] == "io.metamask"
    assert phone["app_hints"][0]["version"] == "7.50.0"
    assert phone["coverage"][-1]["status"] == "unknown"
    assert summary["file_count"] == 0
    assert summary["scan_mode"] == "phone_crypto_quick"
    assert (result / "files.csv").read_text().count("\n") == 1
