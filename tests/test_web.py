import json
from pathlib import Path

from forensic_triage.web import (
    EVIDENCE_PATTERN,
    QUARANTINED_DEVICES,
    _device_ejectable,
    clear_absent_quarantines,
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
