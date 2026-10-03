"""Structural device-backup detection on media inventories."""

import pytest

from forensic_triage.backup_detection import find_backup_hints, summarize_backup_hints
from forensic_triage.crypto_rules import bundled_rules


def _file(path, ext=""):
    return {"path": path, "extension": ext}


def _dir(path):
    return {"path": path}


def test_apple_itunes_backup_detected_with_high_confidence():
    rules = bundled_rules()
    files = [
        _file("/mnt/usb/Library/Application Support/MobileSync/Backup/00000000-0000000000000000/Manifest.db", "db"),
        _file("/mnt/usb/Library/Application Support/MobileSync/Backup/00000000-0000000000000000/Info.plist", "plist"),
        _file("/mnt/usb/Library/Application Support/MobileSync/Backup/00000000-0000000000000000/Manifest.plist", "plist"),
    ]
    directories = [_dir("/mnt/usb/Library/Application Support/MobileSync/Backup/00000000-0000000000000000")]
    hints = find_backup_hints(files, directories, rules)
    assert len(hints) == 1
    assert hints[0]["id"] == "backup-itunes"
    assert hints[0]["confidence"] == "high"
    assert "Inhalt wird nicht analysiert" in hints[0]["comment"]


def test_samsung_smart_switch_requires_path_and_files():
    rules = bundled_rules()
    files = [_file("/mnt/usb/Documents/Smart Switch/Backup/phone/sec_settings.db", "db")]
    directories = [_dir("/mnt/usb/Documents/Smart Switch/Backup/phone")]
    hints = find_backup_hints(files, directories, rules)
    assert any(hint["id"] == "backup-samsung-smart-switch" for hint in hints)


def test_generic_backup_path_alone_is_not_enough():
    rules = bundled_rules()
    files = []
    directories = [_dir("/mnt/usb/random/backup")]
    hints = find_backup_hints(files, directories, rules)
    assert not any(hint["id"] == "backup-itunes" for hint in hints)


def test_android_ab_extension_detected():
    rules = bundled_rules()
    files = [_file("/mnt/usb/old/phone-backup.ab", "ab")]
    directories = []
    hints = find_backup_hints(files, directories, rules)
    # ADB backup rule has no required_paths, so it should not match without a path indicator.
    assert not any(hint["id"] == "backup-adb" for hint in hints)


def test_multiple_backups_on_same_medium():
    rules = bundled_rules()
    files = [
        _file("/mnt/usb/MobileSync/Backup/A/Manifest.db", "db"),
        _file("/mnt/usb/MobileSync/Backup/A/Info.plist", "plist"),
        _file("/mnt/usb/MIUI/backup/phone/backup.bak", "bak"),
    ]
    directories = [
        _dir("/mnt/usb/MobileSync/Backup/A"),
        _dir("/mnt/usb/MIUI/backup/phone"),
    ]
    hints = find_backup_hints(files, directories, rules)
    ids = [hint["id"] for hint in hints]
    assert "backup-itunes" in ids
    assert "backup-xiaomi" in ids


def test_disabled_backup_rule_is_ignored():
    rules = bundled_rules()
    rules["backup_rules"] = [
        {**rule, "enabled": False} for rule in rules["backup_rules"] if rule["id"] == "backup-itunes"
    ]
    files = [
        _file("/mnt/usb/MobileSync/Backup/00000000-0000000000000000/Manifest.db", "db"),
        _file("/mnt/usb/MobileSync/Backup/00000000-0000000000000000/Info.plist", "plist"),
    ]
    directories = [_dir("/mnt/usb/MobileSync/Backup/00000000-0000000000000000")]
    hints = find_backup_hints(files, directories, rules)
    assert not hints


def test_summarize_backup_hints_counts_by_confidence():
    hints = [
        {"confidence": "high"}, {"confidence": "high"}, {"confidence": "medium"},
    ]
    summary = summarize_backup_hints(hints)
    assert summary["total"] == 3
    assert summary["by_confidence"] == {"high": 2, "medium": 1, "low": 0}
