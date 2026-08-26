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
        scanner.scan(tmp_path / "device", tmp_path / "profile", "BM-1", tmp_path / "results")
        assert root_handler in root_logger.handlers
    finally:
        root_logger.removeHandler(root_handler)
