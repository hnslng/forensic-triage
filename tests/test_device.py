import json
from pathlib import Path

from forensic_triage import device


def test_external_optical_drive_is_an_allowed_whole_medium(monkeypatch) -> None:
    monkeypatch.setattr(Path, "resolve", lambda self: Path("/dev/sr0"))
    monkeypatch.setattr(device, "_run", lambda *_args: json.dumps({
        "blockdevices": [{
            "path": "/dev/sr0", "type": "rom", "tran": "usb", "mountpoints": [None],
        }],
    }))

    assert device.inspect_device(Path("/dev/sr0"))["type"] == "rom"
