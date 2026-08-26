import json

from forensic_triage.web import EVIDENCE_PATTERN, latest_result, parse_media_devices


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


def test_media_discovery_supports_multiple_usb_and_marks_optical_pending() -> None:
    devices = parse_media_devices([
        {"path": "/dev/sdb", "type": "disk", "tran": "usb", "size": 100, "model": "One", "mountpoints": [None]},
        {"path": "/dev/sdc", "type": "disk", "tran": "usb", "size": 200, "model": "Two", "mountpoints": [None]},
        {"path": "/dev/sdd", "type": "disk", "tran": "usb", "size": 300, "model": "Mounted", "mountpoints": ["/media/x"]},
        {"path": "/dev/sr0", "type": "rom", "tran": "usb", "size": 0, "model": "DVD", "mountpoints": [None]},
        {"path": "/dev/sr1", "type": "rom", "tran": "sata", "size": 4194304, "model": "System DVD", "mountpoints": [None]},
        {"path": "/dev/nvme0n1", "type": "disk", "tran": "nvme", "size": 999},
    ])

    assert [item["path"] for item in devices] == ["/dev/sdb", "/dev/sdc", "/dev/sdd", "/dev/sr0"]
    assert [item["scan_supported"] for item in devices] == [True, True, False, False]
    assert devices[-1]["media_type"] == "optical"
