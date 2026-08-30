"""Fast active-file inventory through a kernel-enforced read-only mount."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .classifier import classify, original_extension_for
from .commands import run_command
from .container_inventory import ContainerLimits, index_containers
from .device import SafetyError


def _run(*args: str) -> str:
    return run_command(args, capture_output=True).stdout


def find_partition_path(lsblk_data: dict[str, Any], start_sector: int) -> Path:
    """Map an mmls offset to a current child partition device."""

    def visit(nodes: list[dict[str, Any]]) -> Path | None:
        for node in nodes:
            if node.get("type") == "part" and int(node.get("start") or -1) == start_sector:
                return Path(str(node["path"]))
            found = visit(node.get("children") or [])
            if found is not None:
                return found
        return None

    result = visit(lsblk_data.get("blockdevices") or [])
    if result is None:
        raise SafetyError(f"no child partition starts at sector {start_sector}")
    return result


def partition_path_for_start(device: Path, start_sector: int) -> Path:
    data = json.loads(_run("lsblk", "--json", "--output", "NAME,PATH,TYPE,START", str(device)))
    return find_partition_path(data, start_sector)


def inventory_tree(root: Path, partition_slot: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect active file metadata without opening file contents."""
    files: list[dict[str, Any]] = []
    directories: list[dict[str, Any]] = []
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        current_path = Path(current)
        for name in sorted(dirnames):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            directories.append(
                {
                    "partition_slot": partition_slot,
                    "path": relative,
                    "metadata_address": "",
                    "tsk_type": "d/d",
                    "source": "readonly_mount",
                }
            )
        for name in sorted(filenames):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            stat = path.stat(follow_symlinks=False)
            extension, category = classify(relative)
            files.append(
                {
                    "partition_slot": partition_slot,
                    "path": relative,
                    "metadata_address": "",
                    "tsk_type": "r/r",
                    "source": "readonly_mount",
                    "size": stat.st_size,
                    "original_extension": original_extension_for(relative),
                    "extension": extension,
                    "category": category,
                    "uid": stat.st_uid,
                    "gid": stat.st_gid,
                    "atime": int(stat.st_atime),
                    "mtime": int(stat.st_mtime),
                    "ctime": int(stat.st_ctime),
                    "crtime": None,
                }
            )
    return files, directories


def readonly_mount_inventory(
    partition_device: Path, partition_slot: str, container_limits: ContainerLimits | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Mount an already read-only partition defensively, inventory, and unmount."""
    if os.geteuid() != 0:
        raise SafetyError("root privileges are required for read-only mount inventory")
    mountpoint = Path(tempfile.mkdtemp(prefix="forensic-triage-", dir="/mnt"))
    mounted = False
    try:
        run_command(
            ["mount", "-o", "ro,nosuid,nodev,noexec", str(partition_device), str(mountpoint)],
        )
        mounted = True
        info = json.loads(
            _run("findmnt", "--json", "--mountpoint", str(mountpoint), "--output", "SOURCE,FSTYPE,OPTIONS")
        )
        filesystems = info.get("filesystems") or []
        if len(filesystems) != 1:
            raise SafetyError(f"could not verify mount at {mountpoint}")
        mount_info = filesystems[0]
        options = set(str(mount_info.get("options", "")).split(","))
        if "ro" not in options:
            raise SafetyError(f"mount is not read-only: {mount_info.get('options')}")
        files, directories = inventory_tree(mountpoint, partition_slot)
        containers = index_containers(mountpoint, files, partition_slot, container_limits)
        return files, directories, mount_info, containers
    finally:
        if mounted:
            run_command(["umount", str(mountpoint)])
        mountpoint.rmdir()
