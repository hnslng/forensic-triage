import json
from pathlib import Path

import pytest

from forensic_triage import device


def test_external_optical_drive_is_an_allowed_whole_medium(monkeypatch) -> None:
    monkeypatch.setattr(Path, "resolve", lambda self: Path("/dev/sr0"))
    monkeypatch.setattr(device, "_run", lambda *_args: json.dumps({
        "blockdevices": [{
            "path": "/dev/sr0", "type": "rom", "tran": "usb", "mountpoints": [None],
        }],
    }))

    assert device.inspect_device(Path("/dev/sr0"))["type"] == "rom"


def test_unmounted_usb_sda_is_allowed_when_it_is_not_the_system_disk(monkeypatch) -> None:
    monkeypatch.setattr(Path, "resolve", lambda self: Path("/dev/sda"))
    monkeypatch.setattr(device, "_run", lambda *_args: json.dumps({
        "blockdevices": [{
            "path": "/dev/sda", "type": "disk", "tran": "usb", "mountpoints": [None],
            "children": [{"path": "/dev/sda1", "type": "part", "mountpoints": [None]}],
        }],
    }))

    assert device.inspect_device(Path("/dev/sda"))["path"] == "/dev/sda"


def test_mounted_root_disk_is_rejected_independent_of_device_name(monkeypatch) -> None:
    monkeypatch.setattr(Path, "resolve", lambda self: Path("/dev/sdb"))
    monkeypatch.setattr(device, "_run", lambda *_args: json.dumps({
        "blockdevices": [{
            "path": "/dev/sdb", "type": "disk", "tran": "usb", "mountpoints": [None],
            "children": [{"path": "/dev/sdb2", "type": "part", "mountpoints": ["/"]}],
        }],
    }))

    with pytest.raises(device.SafetyError, match="mounted"):
        device.inspect_device(Path("/dev/sdb"))
