import sys

import pytest

from forensic_triage import scan_process


def test_isolated_scan_returns_worker_result(tmp_path, monkeypatch) -> None:
    result_dir = tmp_path / "complete"
    result_dir.mkdir()
    script = f"import sys; sys.stdin.read(); print('{{\"ok\": true, \"result_dir\": \"{result_dir}\"}}')"
    monkeypatch.setattr(scan_process, "worker_command", lambda: [sys.executable, "-c", script])

    result = scan_process.run_isolated_scan(
        {"device": "/dev/test"}, timeout_seconds=2, command_timeout_seconds=1,
    )

    assert result == result_dir


def test_isolated_scan_times_out_without_blocking_caller(monkeypatch) -> None:
    script = "import sys, time; sys.stdin.read(); time.sleep(30)"
    monkeypatch.setattr(scan_process, "worker_command", lambda: [sys.executable, "-c", script])

    with pytest.raises(scan_process.ScanTimeoutError, match="Zeitlimit"):
        scan_process.run_isolated_scan(
            {"device": "/dev/test"}, timeout_seconds=0.05, command_timeout_seconds=1,
        )


def test_worker_command_timeout_is_reported_as_media_timeout(monkeypatch) -> None:
    script = "import sys; sys.stdin.read(); print('{\"ok\": false, \"timed_out\": true, \"error\": \"Befehl zu langsam.\"}'); raise SystemExit(2)"
    monkeypatch.setattr(scan_process, "worker_command", lambda: [sys.executable, "-c", script])

    with pytest.raises(scan_process.ScanTimeoutError, match="Befehl zu langsam"):
        scan_process.run_isolated_scan(
            {"device": "/dev/test"}, timeout_seconds=2, command_timeout_seconds=1,
        )
