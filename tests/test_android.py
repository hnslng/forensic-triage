import json
import subprocess
from pathlib import Path

import pytest

from forensic_triage import android
from forensic_triage.crypto_rules import snapshot


def completed(args, stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)


def usb_device(root: Path, name: str, *, vendor: str, product_id: str = "0001",
               manufacturer: str = "", product: str = "", serial: str = "",
               device_class: str = "00", interface=("06", "01", "01", "MTP")) -> Path:
    device = root / name
    device.mkdir()
    values = {
        "idVendor": vendor, "idProduct": product_id, "manufacturer": manufacturer,
        "product": product, "serial": serial, "bDeviceClass": device_class,
    }
    for filename, value in values.items():
        if value:
            (device / filename).write_text(value + "\n")
    if interface:
        iface = root / f"{name}:1.0"
        iface.mkdir()
        for filename, value in zip(
            ("bInterfaceClass", "bInterfaceSubClass", "bInterfaceProtocol", "interface"), interface,
        ):
            (iface / filename).write_text(value + "\n")
    return device


def test_usb_candidate_recognizes_android_vendor_without_adb(tmp_path: Path):
    usb_device(tmp_path, "1-1", vendor="04e8", product_id="6860", manufacturer="SAMSUNG",
               product="Galaxy Test", serial="SERIAL1")
    assert android._usb_candidates(tmp_path) == [{
        "sysfs_name": "1-1", "vendor_id": "04e8", "product_id": "6860",
        "vendor": "SAMSUNG", "model": "Galaxy Test", "serial": "SERIAL1",
        "device_class": "00",
        "interfaces": [{"name": "1-1:1.0", "class": "06", "subclass": "01", "protocol": "01", "label": "MTP"}],
        "confidence": "high", "evidence": "known_android_vendor",
    }]


def test_google_pixel_vendor_is_visible_before_adb(tmp_path: Path):
    usb_device(tmp_path, "2-3", vendor="18d1", manufacturer="Google", product="Pixel 9")
    candidate = android._usb_candidates(tmp_path)[0]
    assert candidate["vendor"] == "Google"
    assert candidate["confidence"] == "high"


def test_real_tcl_a1_alpha_21_is_visible_before_adb(tmp_path: Path):
    usb_device(
        tmp_path, "1-1.2", vendor="1bbb", product_id="0168", manufacturer="TCL",
        product="A1 Alpha 21", device_class="00", interface=("06", "01", "01", "MTP"),
    )
    candidates = android._usb_candidates(tmp_path)
    assert len(candidates) == 1
    assert candidates[0]["vendor"] == "TCL"
    assert candidates[0]["model"] == "A1 Alpha 21"
    assert candidates[0]["confidence"] == "medium"
    assert candidates[0]["evidence"] == "known_phone_brand_with_mtp_ptp"


@pytest.mark.parametrize("manufacturer", ["Alcatel", "Nokia", "HMD", "realme", "ZTE"])
def test_additional_phone_brands_with_mtp_are_candidates(tmp_path: Path, manufacturer: str):
    usb_device(
        tmp_path, "6-1", vendor="3344", manufacturer=manufacturer, product="Provider handset",
        interface=("06", "01", "01", "MTP"),
    )
    candidates = android._usb_candidates(tmp_path)
    assert len(candidates) == 1
    assert candidates[0]["confidence"] == "medium"
    assert candidates[0]["evidence"] == "known_phone_brand_with_mtp_ptp"


def test_tcl_without_phone_usb_evidence_is_not_accepted(tmp_path: Path):
    usb_device(
        tmp_path, "7-1", vendor="3344", manufacturer="TCL", product="USB Hub",
        interface=("09", "00", "00", "Hub"),
    )
    assert android._usb_candidates(tmp_path) == []


def test_normal_usb_drive_is_not_android(tmp_path: Path):
    usb_device(tmp_path, "3-1", vendor="0951", manufacturer="Kingston", product="DataTraveler",
               interface=("08", "06", "50", "Mass Storage"))
    assert android._usb_candidates(tmp_path) == []


def test_camera_ptp_is_not_blindly_android(tmp_path: Path):
    usb_device(tmp_path, "4-1", vendor="04a9", manufacturer="Canon", product="Digital Camera",
               interface=("06", "01", "01", "PTP"))
    assert android._usb_candidates(tmp_path) == []


def test_unknown_vendor_phone_with_mtp_evidence_is_candidate(tmp_path: Path):
    usb_device(tmp_path, "5-1", vendor="3344", manufacturer="Acme Mobile",
               product="Android Phone", interface=("06", "01", "01", "MTP"))
    candidate = android._usb_candidates(tmp_path)[0]
    assert candidate["confidence"] == "medium"
    assert candidate["evidence"] == "phone_identity_with_mtp_ptp_or_composite_usb"


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

    monkeypatch.setattr(android, "_adb_rows", lambda: [{"serial": "SERIAL1", "adb_state": "device", "model": "Galaxy"}])
    device = android.discover_androids()[0]
    assert device["connection_state"] == "authorized"
    assert device["scan_supported"] is True


def test_real_tcl_discovery_without_adb_is_debugging_required(monkeypatch):
    monkeypatch.setattr(android.shutil, "which", lambda _name: "/usr/bin/adb")
    monkeypatch.setattr(android, "_usb_candidates", lambda: [{
        "sysfs_name": "1-1.2", "vendor_id": "1bbb", "product_id": "0168",
        "vendor": "TCL", "model": "A1 Alpha 21", "serial": "",
        "confidence": "medium", "evidence": "known_phone_brand_with_mtp_ptp",
    }])
    monkeypatch.setattr(android, "_adb_rows", lambda: [])
    device = android.discover_androids()[0]
    assert device["connection_state"] == "debugging_required"
    assert device["scan_supported"] is False
    assert device["guidance"]


def test_usb_topology_keeps_identity_without_usb_serial(monkeypatch):
    monkeypatch.setattr(android.shutil, "which", lambda _name: "/usr/bin/adb")
    candidate = {
        "sysfs_name": "9-1", "vendor_id": "04e8", "product_id": "6860",
        "vendor": "Samsung", "model": "Galaxy", "serial": "",
    }
    monkeypatch.setattr(android, "_usb_candidates", lambda: [candidate])
    monkeypatch.setattr(android, "_adb_rows", lambda: [])
    before = android.discover_androids()[0]
    monkeypatch.setattr(android, "_adb_rows", lambda: [
        {"serial": "R58-ADB", "adb_state": "unauthorized", "usb": "9-1"},
    ])
    after = android.discover_androids()[0]
    assert before["path"] == after["path"] == "android:usb-9-1"
    assert after["identity_source"] == "usb_topology"
    assert len(android.discover_androids()) == 1


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
