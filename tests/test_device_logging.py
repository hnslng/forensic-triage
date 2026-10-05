"""Device-logging tests: events for Android candidates, ADB states, media (Alpha 70)."""


import subprocess

import pytest

from forensic_triage import android
from forensic_triage import diagnostics as diag
from forensic_triage.web import log_device_changes


@pytest.fixture(autouse=True)
def fresh_diagnostics():
    diag.reset_state()
    diag.install(stream=False)
    yield
    diag.reset_state()


def events():
    entries, _ = diag.recent()
    return entries


def android_device(serial="R58V", connection_state="debugging_required"):
    return {
        "path": f"android:{serial}", "serial": serial, "vendor": "Samsung",
        "model": "Galaxy S23", "media_type": "android", "connection_state": connection_state,
        "mounted": False, "read_only": False,
    }


def test_first_snapshot_logs_connected_devices_once() -> None:
    log_device_changes([android_device()])
    messages = [entry["message"] for entry in events()]
    assert any("verbunden" in message for message in messages)


def test_unchanged_snapshot_logs_nothing() -> None:
    devices = [android_device()]
    log_device_changes(devices)
    count = len(events())
    for _ in range(5):
        log_device_changes(devices)
    assert len(events()) == count


def test_adb_state_transition_is_logged_exactly() -> None:
    log_device_changes([android_device(serial="R58V", connection_state="debugging_required")])
    log_device_changes([android_device(serial="R58V", connection_state="authorization_required")])
    log_device_changes([android_device(serial="R58V", connection_state="authorized")])
    transitions = [entry["message"] for entry in events() if entry["category"] == "ANDROID"]
    transitions = [message for message in transitions if "Status" in message or "geändert" in message]
    assert len(transitions) == 2
    assert any("debugging_required → authorization_required" in message for message in transitions)
    assert any("authorization_required → authorized" in message for message in transitions)


def test_phone_serials_are_hidden_in_normal_device_events() -> None:
    log_device_changes([android_device(serial="SECRET-SERIAL")])
    assert "SECRET-SERIAL" not in str(events())


def test_disconnected_device_logs_once() -> None:
    log_device_changes([android_device()])
    log_device_changes([android_device()])
    log_device_changes([])
    texts = [entry["message"] for entry in events()]
    assert any("getrennt" in text for text in texts)


def test_media_mount_change_logs_as_usb() -> None:
    stick = {
        "path": "/dev/sdb", "vendor": "Kingston", "model": "DataTraveler",
        "serial": "ABC123", "media_type": "usb",
        "connection_state": "", "mounted": False, "read_only": True,
    }
    log_device_changes([stick])
    stick = dict(stick, mounted=True)
    log_device_changes([stick])
    messages = [entry for entry in events() if entry["category"] == "USB"]
    assert any("eingebunden" in entry["message"] for entry in messages)


def test_android_discovery_logs_candidates_and_states_without_flood(monkeypatch) -> None:
    diag.set_mode("debug")
    monkeypatch.setattr(android, "_usb_candidates", lambda: [{
        "sysfs_name": "9-1", "vendor_id": "04e8", "product_id": "6860",
        "vendor": "Samsung", "model": "Galaxy S23", "serial": "R58V",
    }])
    monkeypatch.setattr(android.shutil, "which", lambda name: None)
    monkeypatch.setattr(android, "_adb_rows", lambda: [])

    android.discover_androids()
    first_count = len(events())
    android.discover_androids()
    assert len(events()) == first_count  # Kein tägliches Wiederholen ohne Änderung

    monkeypatch.setattr(android, "_adb_rows", lambda: [
        {"serial": "R58V", "adb_state": "unauthorized"},
    ])
    android.discover_androids()
    new_messages = [entry["message"] for entry in events()[first_count:]]
    assert any("ADB-Zustand" in message and "unauthorized" in message for message in new_messages)


def test_serial_presence_is_reported_as_boolean_fact(monkeypatch) -> None:
    """serial only as presence/no-presence; no PII in the message line."""
    diag.set_mode("debug")
    monkeypatch.setattr(android, "_usb_candidates", lambda: [{
        "sysfs_name": "9-1", "vendor_id": "04e8", "product_id": "6860",
        "vendor": "Samsung", "model": "Galaxy S23", "serial": "GEHEIM-123456-789",
    }])
    monkeypatch.setattr(android.shutil, "which", lambda name: None)
    monkeypatch.setattr(android, "_adb_rows", lambda: [])
    android.discover_androids()
    entries, _ = diag.recent()
    candidate_lines = [entry for entry in entries if "USB-Kandidat" in entry["message"]]
    assert candidate_lines, "Kandidaten-Zeile fehlt"
    message = candidate_lines[-1]["message"]
    assert "GEHEIM" not in message
    joined = " ".join(str(entry.get("details") or "") for entry in candidate_lines)
    assert "GEHEIM" not in joined
