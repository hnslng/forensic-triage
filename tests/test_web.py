import json
from pathlib import Path

from forensic_triage.web import (
    EVIDENCE_PATTERN,
    QUARANTINED_DEVICES,
    clear_absent_quarantines,
    ejected_usb_paths,
    latest_result,
    parse_media_devices,
    parser,
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

    assert ejected_usb_paths(nodes) == ["/dev/sdb"]


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
