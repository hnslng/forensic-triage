import json
import logging

from forensic_triage import scanner


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
