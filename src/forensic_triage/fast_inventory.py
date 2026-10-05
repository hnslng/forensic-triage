"""Fast active-file inventory through a kernel-enforced read-only mount."""

from __future__ import annotations

import json
import os
import tempfile
import ctypes
import errno
from pathlib import Path
from typing import Any

from .classifier import classify, original_extension_for
from .commands import run_command
from .container_inventory import ContainerLimits, index_containers
from .device import SafetyError, enforce_read_only
from .period import evaluate_file_period


class _StatxTimestamp(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_int64), ("tv_nsec", ctypes.c_uint32), ("reserved", ctypes.c_int32)]


class _Statx(ctypes.Structure):
    _fields_ = [
        ("mask", ctypes.c_uint32), ("blksize", ctypes.c_uint32), ("attributes", ctypes.c_uint64),
        ("nlink", ctypes.c_uint32), ("uid", ctypes.c_uint32), ("gid", ctypes.c_uint32),
        ("mode", ctypes.c_uint16), ("spare0", ctypes.c_uint16), ("ino", ctypes.c_uint64),
        ("size", ctypes.c_uint64), ("blocks", ctypes.c_uint64), ("attributes_mask", ctypes.c_uint64),
        ("atime", _StatxTimestamp), ("btime", _StatxTimestamp), ("ctime", _StatxTimestamp),
        ("mtime", _StatxTimestamp), ("rdev_major", ctypes.c_uint32), ("rdev_minor", ctypes.c_uint32),
        ("dev_major", ctypes.c_uint32), ("dev_minor", ctypes.c_uint32), ("mnt_id", ctypes.c_uint64),
        ("dio_mem_align", ctypes.c_uint32), ("dio_offset_align", ctypes.c_uint32),
        ("spare3", ctypes.c_uint64 * 12),
    ]


STATX_BASIC_STATS = 0x07FF
STATX_BTIME = 0x0800
STATX_SIZE = 0x0200
STATX_UID = 0x0008
STATX_GID = 0x0010
STATX_ATIME = 0x0020
STATX_MTIME = 0x0040
STATX_CTIME = 0x0080
STATX_INVENTORY_FIELDS = STATX_SIZE | STATX_UID | STATX_GID | STATX_ATIME | STATX_MTIME | STATX_CTIME
AT_SYMLINK_NOFOLLOW = 0x0100


def _stat_metadata(path: Path) -> dict[str, Any]:
    """Read common metadata in one Linux statx call where libc supports it."""
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        function = getattr(libc, "statx")
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint, ctypes.POINTER(_Statx)]
        function.restype = ctypes.c_int
        value = _Statx()
        result = function(-100, os.fsencode(path), AT_SYMLINK_NOFOLLOW,
                          STATX_BASIC_STATS | STATX_BTIME, ctypes.byref(value))
        if result == 0 and (value.mask & STATX_INVENTORY_FIELDS) == STATX_INVENTORY_FIELDS:
            btime = int(value.btime.tv_sec) if value.mask & STATX_BTIME else None
            return {"size": int(value.size), "uid": int(value.uid), "gid": int(value.gid),
                    "atime": int(value.atime.tv_sec), "mtime": int(value.mtime.tv_sec),
                    "ctime": int(value.ctime.tv_sec), "crtime": btime, "stat_method": "statx"}
        error = ctypes.get_errno()
        if error not in (0, errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
            raise OSError(error, os.strerror(error), str(path))
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    stat = path.stat(follow_symlinks=False)
    return {"size": stat.st_size, "uid": stat.st_uid, "gid": stat.st_gid,
            "atime": int(stat.st_atime), "mtime": int(stat.st_mtime), "ctime": int(stat.st_ctime),
            "crtime": None, "stat_method": "os.stat"}


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


def inventory_tree(root: Path, partition_slot: str, case_period: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
            stat = _stat_metadata(path)
            extension, category = classify(relative)
            record = {
                    "partition_slot": partition_slot,
                    "path": relative,
                    "metadata_address": "",
                    "tsk_type": "r/r",
                    "source": "readonly_mount",
                    "size": stat["size"],
                    "original_extension": original_extension_for(relative),
                    "extension": extension,
                    "category": category,
                    "uid": stat["uid"],
                    "gid": stat["gid"],
                    "atime": stat["atime"],
                    "mtime": stat["mtime"],
                    "ctime": stat["ctime"],
                    "crtime": stat["crtime"],
                }
            if case_period:
                record.update(evaluate_file_period(record, case_period))
            files.append(record)
    return files, directories


def readonly_mount_inventory(
    partition_device: Path, partition_slot: str, container_limits: ContainerLimits | None = None,
    case_period: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Mount an already read-only partition defensively, inventory, and unmount."""
    if os.geteuid() != 0:
        raise SafetyError("root privileges are required for read-only mount inventory")
    # Verify the exact block node that will be mounted, including child partitions.
    enforce_read_only(partition_device)
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
        files, directories = inventory_tree(mountpoint, partition_slot, case_period)
        containers = index_containers(mountpoint, files, partition_slot, container_limits)
        return files, directories, mount_info, containers
    finally:
        if mounted:
            run_command(["umount", str(mountpoint)])
        mountpoint.rmdir()
