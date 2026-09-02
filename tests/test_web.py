import json
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from forensic_triage.web import (
    EVIDENCE_PATTERN,
    QUARANTINED_DEVICES,
    cached_media_discovery,
    _device_ejectable,
    clear_absent_quarantines,
    device_discovery_backoff_seconds,
    device_discovery_timeout_seconds,
    ejected_usb_paths,
    latest_result,
    parse_media_devices,
    parser,
    read_update_status,
    update_job_states,
)


def test_evidence_number_is_strict() -> None:
    assert EVIDENCE_PATTERN.fullmatch("BM-2026_014.2")
    assert not EVIDENCE_PATTERN.fullmatch("../escape")
    assert not EVIDENCE_PATTERN.fullmatch("")


def test_latest_complete_result(tmp_path) -> None:
    incomplete = tmp_path / "2026-08-26T130000Z_NEW"
    incomplete.mkdir()
    (incomplete / "summary.json").write_text("{}", encoding="utf-8")
    complete = tmp_path / "2026-08-26T120000Z_OLD"
    complete.mkdir()
    (complete / "summary.json").write_text(json.dumps({"evidence": "BM-1"}), encoding="utf-8")
    (complete / "hits.json").write_text(
        json.dumps({"by_keyword": {"rechnung": {"count": 2, "paths": []}}}),
        encoding="utf-8",
    )

    result = latest_result(tmp_path)

    assert result == {
        "id": complete.name,
        "summary": {"evidence": "BM-1"},
        "hits": {"rechnung": 2},
    }


def test_media_discovery_supports_usb_and_loaded_optical_media() -> None:
    devices = parse_media_devices([
        {"path": "/dev/sdb", "type": "disk", "tran": "usb", "size": 100, "model": "One", "mountpoints": [None]},
        {"path": "/dev/sdc", "type": "disk", "tran": "usb", "size": 200, "model": "Two", "mountpoints": [None]},
        {"path": "/dev/sdd", "type": "disk", "tran": "usb", "size": 300, "model": "Mounted", "mountpoints": ["/media/x"]},
        {"path": "/dev/sde", "type": "disk", "tran": "usb", "size": 0, "model": "Ejected", "mountpoints": [None]},
        {"path": "/dev/sr0", "type": "rom", "tran": "usb", "size": 0, "model": "DVD", "mountpoints": [None]},
        {"path": "/dev/sr2", "type": "rom", "tran": "usb", "size": 4194304, "model": "Loaded DVD", "serial": "DRIVE-1", "uuid": "DISC-9", "label": "EVIDENCE", "mountpoints": [None]},
        {"path": "/dev/sr1", "type": "rom", "tran": "sata", "size": 4194304, "model": "System DVD", "mountpoints": [None]},
        {"path": "/dev/nvme0n1", "type": "disk", "tran": "nvme", "size": 999},
    ])

    assert [item["path"] for item in devices] == ["/dev/sdb", "/dev/sdc", "/dev/sdd", "/dev/sr0", "/dev/sr2"]
    assert [item["scan_supported"] for item in devices] == [True, True, False, False, True]
    assert "/dev/sde" not in [item["path"] for item in devices]
    assert devices[-1]["media_type"] == "optical"
    assert devices[-1]["serial"] == "OPTICAL:DISC-9:EVIDENCE:4194304"
    assert devices[3]["mounted"] is False


def test_empty_optical_drive_can_open_tray_but_mounted_media_cannot() -> None:
    assert _device_ejectable({"media_type": "optical", "mounted": False, "scan_supported": False})
    assert not _device_ejectable({"media_type": "optical", "mounted": True, "scan_supported": False})
    assert not _device_ejectable({"media_type": "usb", "mounted": False, "scan_supported": False})


def test_media_discovery_excludes_actual_root_disk_not_device_name() -> None:
    devices = parse_media_devices([
        {
            "path": "/dev/sdb", "type": "disk", "tran": "usb", "size": 500,
            "model": "System SSD", "mountpoints": [None],
            "children": [
                {"path": "/dev/sdb1", "type": "part", "mountpoints": ["/boot/firmware"]},
                {"path": "/dev/sdb2", "type": "part", "mountpoints": ["/"]},
            ],
        },
        {"path": "/dev/sda", "type": "disk", "tran": "usb", "size": 100, "model": "Evidence USB", "mountpoints": [None]},
    ])

    assert [item["path"] for item in devices] == ["/dev/sda"]
    assert devices[0]["model"] == "Evidence USB"


def test_timed_out_device_stays_quarantined_until_absent() -> None:
    QUARANTINED_DEVICES.clear()
    QUARANTINED_DEVICES.add("/dev/sdb")
    clear_absent_quarantines([{"path": "/dev/sdb"}])
    assert QUARANTINED_DEVICES == {"/dev/sdb"}
    clear_absent_quarantines([{"path": "/dev/sdc"}])
    assert QUARANTINED_DEVICES == set()


def test_only_valid_zero_byte_usb_disks_are_reactivated() -> None:
    nodes = [
        {"path": "/dev/sdb", "type": "disk", "tran": "usb", "size": 0},
        {"path": "/dev/sdc", "type": "disk", "tran": "usb", "size": 10},
        {"path": "/dev/sda", "type": "disk", "tran": "usb", "size": 0},
        {"path": "/dev/nvme0n1", "type": "disk", "tran": "usb", "size": 0},
        {"path": "/dev/sdd", "type": "disk", "tran": "sata", "size": 0},
    ]

    assert ejected_usb_paths(nodes) == ["/dev/sdb", "/dev/sda"]


def test_web_configuration_can_come_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("FORENSIC_TRIAGE_WEB_HOST", "10.77.0.1")
    monkeypatch.setenv("FORENSIC_TRIAGE_WEB_PORT", "8877")
    monkeypatch.setenv("FORENSIC_TRIAGE_RESULTS_ROOT", "/srv/triage/results")
    monkeypatch.setenv("FORENSIC_TRIAGE_CASEFILES_ROOT", "/srv/triage/cases")
    monkeypatch.setenv("FORENSIC_TRIAGE_WEB_ROOT", "/opt/triage/web")
    monkeypatch.setenv("FORENSIC_TRIAGE_PROFILE", "/etc/forensic-triage/default.yaml")
    monkeypatch.setenv("FORENSIC_TRIAGE_SCAN_TIMEOUT_SECONDS", "90")
    monkeypatch.setenv("FORENSIC_TRIAGE_COMMAND_TIMEOUT_SECONDS", "7")

    args = parser().parse_args([])

    assert args.host == "10.77.0.1"
    assert args.port == 8877
    assert args.results == Path("/srv/triage/results")
    assert args.casefiles == Path("/srv/triage/cases")
    assert args.web_root == Path("/opt/triage/web")
    assert args.profile == Path("/etc/forensic-triage/default.yaml")
    assert args.scan_timeout == 90
    assert args.command_timeout == 7


def test_device_discovery_timeouts_can_come_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("FORENSIC_TRIAGE_DEVICE_DISCOVERY_TIMEOUT_SECONDS", "1.5")
    monkeypatch.setenv("FORENSIC_TRIAGE_DEVICE_DISCOVERY_BACKOFF_SECONDS", "4")

    assert device_discovery_timeout_seconds() == 1.5
    assert device_discovery_backoff_seconds() == 4


def test_cached_media_discovery_returns_stale_state_during_backoff(monkeypatch) -> None:
    import forensic_triage.web as web

    monkeypatch.setattr(web, "DEVICE_DISCOVERY_UNHEALTHY_UNTIL", 0.0)
    monkeypatch.setattr(web, "LAST_DEVICE_DISCOVERY", [{"path": "/dev/sdb"}])
    monkeypatch.setattr(web, "LAST_DEVICE_DISCOVERY_ERROR", "")
    monkeypatch.setattr(web, "device_discovery_backoff_seconds", lambda: 30.0)
    clock = [100.0]
    monkeypatch.setattr(web.time, "monotonic", lambda: clock[0])
    calls = []

    def fail_discovery():
        calls.append(True)
        raise subprocess.TimeoutExpired(["lsblk"], 2)

    monkeypatch.setattr(web, "discover_media_devices", fail_discovery)

    devices, error, reactivated = cached_media_discovery()

    assert devices == [{"path": "/dev/sdb"}]
    assert "Datenträgererkennung" in error
    assert reactivated == []
    assert cached_media_discovery(reactivate=True) == (devices, error, [])
    assert len(calls) == 1  # Neither polling nor manual refresh retries during backoff.
    devices[0]["path"] = "changed by caller"
    assert cached_media_discovery()[0] == [{"path": "/dev/sdb"}]

    clock[0] = 131.0
    monkeypatch.setattr(web, "discover_media_devices", lambda: [])
    assert cached_media_discovery() == ([], "", [])


def test_parallel_status_does_not_wait_for_running_discovery(monkeypatch) -> None:
    import forensic_triage.web as web

    lock = threading.Lock()
    monkeypatch.setattr(web, "DEVICE_DISCOVERY_LOCK", lock)
    monkeypatch.setattr(web, "LAST_DEVICE_DISCOVERY", [])
    lock.acquire()
    try:
        devices, error, _ = cached_media_discovery()
        assert devices == []
        assert "läuft noch" in error
    finally:
        lock.release()


def test_failed_discovery_keeps_case_status_and_quarantine(monkeypatch) -> None:
    import forensic_triage.web as web

    monkeypatch.setattr(web, "cached_media_discovery", lambda: ([], "USB antwortet nicht", []))
    monkeypatch.setattr(web, "QUARANTINED_DEVICES", {"/dev/sr0"})
    monkeypatch.setattr(web, "read_update_status", lambda: {})
    monkeypatch.setattr(web, "latest_result", lambda _: None)
    handler = web.TriageHandler.__new__(web.TriageHandler)
    handler.path = "/api/status"
    handler.server = SimpleNamespace(
        results_root=None,
        case_store=SimpleNamespace(latest_media=lambda: None, list_cases=lambda: [{"case_number": "TEST"}]),
    )
    responses = []
    handler._json = lambda status, body: responses.append((status, body))
    handler.do_GET()
    status, body = responses[0]
    assert status == 200
    assert body["cases"] == [{"case_number": "TEST"}]
    assert body["device_error"] == "USB antwortet nicht"
    assert body["quarantined_devices"] == ["/dev/sr0"]


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "0", "invalid"])
def test_invalid_discovery_timeout_uses_bounded_default(monkeypatch, value) -> None:
    monkeypatch.setenv("FORENSIC_TRIAGE_DEVICE_DISCOVERY_TIMEOUT_SECONDS", value)
    assert device_discovery_timeout_seconds() == 2.0


def test_block_device_inventory_passes_short_timeout(monkeypatch) -> None:
    import forensic_triage.web as web

    seen = []
    def fake_command(args, **kwargs):
        seen.append(kwargs["timeout"])
        return subprocess.CompletedProcess(args, 0, '{"blockdevices": []}')
    monkeypatch.setattr(web, "run_command", fake_command)
    monkeypatch.setenv("FORENSIC_TRIAGE_DEVICE_DISCOVERY_TIMEOUT_SECONDS", "1.5")
    assert web.list_block_devices() == []
    assert seen == [1.5]


def test_update_status_defaults_without_state_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FORENSIC_TRIAGE_UPDATE_STATE_FILE", str(tmp_path / "missing.env"))
    status = read_update_status()
    assert status["state"] == "unknown"
    assert status["message"] == "UPDATE NOCH NICHT GEPRÜFT"


def test_update_status_reads_shell_escaped_values(monkeypatch, tmp_path) -> None:
    state_file = tmp_path / "update-status.env"
    state_file.write_text(
        "STATE=available\nMESSAGE=UPDATE\\ IST\\ BEREIT\\ ZUR\\ INSTALLATION\nAVAILABLE_VERSION=v0.2.0-alpha.24\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FORENSIC_TRIAGE_UPDATE_STATE_FILE", str(state_file))
    status = read_update_status()
    assert status["state"] == "available"
    assert status["message"] == "UPDATE IST BEREIT ZUR INSTALLATION"
    assert status["available_version"] == "v0.2.0-alpha.24"


def test_update_status_keeps_running_version_when_error_file_has_no_version(monkeypatch, tmp_path) -> None:
    state_file = tmp_path / "update-status.env"
    state_file.write_text(
        "STATE=error\nMESSAGE=PRÜFUNG\\ FEHLGESCHLAGEN\nCURRENT_VERSION=\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FORENSIC_TRIAGE_UPDATE_STATE_FILE", str(state_file))

    status = read_update_status()

    assert status["state"] == "error"
    assert status["current_version"].startswith("0.2.0a")


def test_update_job_states_reports_each_systemd_worker(monkeypatch) -> None:
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command[-1])
        return type("Result", (), {"returncode": 0 if "@check.service" in command[-1] else 3})()

    monkeypatch.setattr("forensic_triage.web.subprocess.run", fake_run)

    assert update_job_states() == {"check": True, "install": False}
    assert calls == [
        "forensic-triage-update@check.service",
        "forensic-triage-update@install.service",
    ]


def test_dashboard_offers_only_secure_or_not_secure_decisions() -> None:
    html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    script = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")

    assert html.count('data-decision="') == 2
    assert 'data-decision="secure"' in html
    assert 'data-decision="not_selected"' in html
    assert 'data-decision="review"' not in html
    assert 'id="evidenceDeviceSerial"' in html
    assert 'id="evidenceDeviceReadOnly"' in html
    assert "FAST · NUR LESEN" in html
    assert "FAST/RO · NUR LESEN" not in html
    assert '"NUR GESICHTET"' not in script
    assert "CD/DVD AUSWERFEN" in script
