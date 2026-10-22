import json
import logging
import pytest

from forensic_triage import scanner


@pytest.mark.parametrize("broken_partition", [False, True])
def test_scan_persists_incomplete_partition_status(tmp_path, monkeypatch, broken_partition):
    monkeypatch.setattr(scanner, "inspect_device", lambda _device: {})
    monkeypatch.setattr(scanner, "enforce_read_only", lambda _device: None)
    monkeypatch.setattr(scanner, "_command", lambda _args: "File System Type: NTFS\n")
    monkeypatch.setattr(scanner, "parse_mmls", lambda _output: [
        {"allocated": True, "slot": "002", "start_sector": 32}])
    monkeypatch.setattr(scanner, "partition_path_for_start", lambda *args: tmp_path / "partition")
    def inventory(*args):
        if broken_partition:
            raise OSError("partition unreadable")
        return ([{"path": "good.txt", "size": 4, "category": "Text/Logs", "extension": "txt"}], [],
                {"options": "ro", "read_errors": [{"path": "broken.jpg", "errno": 2, "error": "missing"}]},
                {"status": "ok", "containers": []})
    monkeypatch.setattr(scanner, "readonly_mount_inventory", inventory)
    monkeypatch.setattr(scanner, "load_profile", lambda _path: {"keywords": [], "version": "1", "sha256": "x"})
    result = scanner.scan(tmp_path / "device", tmp_path / "profile", "TEST", tmp_path / "results")
    summary = json.loads((result / "summary.json").read_text())
    assert summary["scan_status"] == ("failed" if broken_partition else "partial")
    assert summary["file_count"] == (0 if broken_partition else 1)
    assert summary["scan_warnings"]
    if not broken_partition:
        assert summary["scan_warnings"][0]["read_errors"][0]["path"] == "broken.jpg"


def test_scan_does_not_replace_root_logging(tmp_path, monkeypatch) -> None:
    root_handler = logging.NullHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(root_handler)
    monkeypatch.setattr(scanner, "inspect_device", lambda _device: {})
    monkeypatch.setattr(scanner, "enforce_read_only", lambda _device: None)
    monkeypatch.setattr(scanner, "_command", lambda args: "Units are in 512-byte sectors\n" if args[0] == "mmls" else "")
    monkeypatch.setattr(scanner, "parse_mmls", lambda _output: [])
    monkeypatch.setattr(scanner, "load_profile", lambda _path: {"keywords": [], "version": "1", "sha256": "x"})
    try:
        result = scanner.scan(
            tmp_path / "device", tmp_path / "profile", "BM-1", tmp_path / "results",
            keywords=["rechnung"],
        )
        assert root_handler in root_logger.handlers
        hits = json.loads((result / "hits.json").read_text(encoding="utf-8"))
        assert hits["profile"]["selected_keywords"] == ["rechnung"]
    finally:
        root_logger.removeHandler(root_handler)


def test_optical_medium_uses_whole_device_readonly_inventory(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(scanner, "_command", lambda _args: "File System Type: ISO9660\n")
    monkeypatch.setattr(
        scanner,
        "readonly_mount_inventory",
        lambda device, slot: (
            [{"path": "photos/image.jpg", "size": 5, "category": "Bilder"}],
            [{"path": "photos"}],
            {"source": str(device), "options": "ro"},
            {"status": "ok", "containers": []},
        ),
    )

    files, directories, partitions, containers = scanner._inventory_optical_medium(
        tmp_path / "sr0", "fast", tmp_path,
    )

    assert files[0]["path"] == "photos/image.jpg"
    assert directories[0]["path"] == "photos"
    assert containers["status"] == "ok"
    assert partitions == [{
        "slot": "OPT",
        "location": "whole_medium",
        "start_sector": 0,
        "description": "Optical medium",
        "allocated": True,
        "filesystem": "ISO9660",
        "partition_device": str(tmp_path / "sr0"),
        "inventory_method": "kernel_readonly_mount",
        "scan_status": "ok",
    }]


def test_fast_optical_inventory_survives_unsupported_fsstat(tmp_path, monkeypatch) -> None:
    import subprocess

    monkeypatch.setattr(
        scanner,
        "_command",
        lambda args: (_ for _ in ()).throw(subprocess.CalledProcessError(1, args)),
    )
    monkeypatch.setattr(
        scanner,
        "readonly_mount_inventory",
        lambda device, slot: ([], [], {"source": str(device), "options": "ro"}, {"status": "ok", "containers": []}),
    )

    _files, _directories, partitions, _containers = scanner._inventory_optical_medium(
        tmp_path / "sr0", "fast", tmp_path,
    )

    assert partitions[0]["filesystem"] == "unknown"
    assert partitions[0]["scan_status"] == "ok"
