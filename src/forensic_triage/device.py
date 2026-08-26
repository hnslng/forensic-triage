"""Strict block-device identity, mount and read-only checks."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


class SafetyError(RuntimeError):
    """Raised when a forensic safety invariant is not satisfied."""


def _run(*args: str) -> str:
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout


def inspect_device(device: Path) -> dict[str, Any]:
    resolved = device.resolve()
    if not str(resolved).startswith("/dev/"):
        raise SafetyError(f"not a /dev path: {resolved}")
    data = json.loads(
        _run(
            "lsblk", "--json", "--bytes",
            "--output", "NAME,PATH,TYPE,TRAN,SIZE,VENDOR,MODEL,SERIAL,RO,MOUNTPOINTS",
            str(resolved),
        )
    )
    devices = data.get("blockdevices", [])
    if len(devices) != 1:
        raise SafetyError(f"could not uniquely identify {resolved}")
    info = devices[0]
    if info.get("type") != "disk":
        raise SafetyError(f"target is not a whole disk: {resolved}")
    if str(resolved) == "/dev/sda":
        raise SafetyError("refusing explicit system-disk sentinel /dev/sda")
    if info.get("tran") != "usb":
        raise SafetyError(f"target transport is not USB: {info.get('tran')!r}")

    def mounted(node: dict[str, Any]) -> list[str]:
        points = [point for point in (node.get("mountpoints") or []) if point]
        for child in node.get("children") or []:
            points.extend(mounted(child))
        return points

    mountpoints = mounted(info)
    if mountpoints:
        raise SafetyError(f"target or child partition is mounted: {mountpoints}")
    return info


def enforce_read_only(device: Path) -> None:
    if os.geteuid() != 0:
        raise SafetyError("root privileges are required to set block-device read-only mode")
    subprocess.run(["blockdev", "--setro", str(device)], check=True)
    state = _run("blockdev", "--getro", str(device)).strip()
    if state != "1":
        raise SafetyError(f"read-only verification failed for {device}: {state!r}")
