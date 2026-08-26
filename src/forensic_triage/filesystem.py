"""The Sleuth Kit filesystem output parsing."""

from __future__ import annotations

from typing import Any

from .classifier import classify, original_extension_for


EXFAT_METADATA_PATHS = {"$ALLOC_BITMAP", "$UPCASE_TABLE", "$VOLUME_GUID", "$TEX_FAT"}


def is_non_user_entry(path: str, mode: str) -> bool:
    """Identify deleted, TSK-virtual, and exFAT bookkeeping entries."""
    normalized = path.removeprefix("/")
    return (
        normalized.endswith(" (deleted)")
        or normalized.endswith(" (deleted-realloc)")
        or normalized.endswith(" (Volume Label Entry)")
        or normalized == "$OrphanFiles"
        or normalized.startswith("$OrphanFiles/")
        or normalized in EXFAT_METADATA_PATHS
        or mode.startswith(("v/", "V/"))
    )


def parse_fls(output: str, partition_slot: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse `fls -r -p -m /` bodyfile output without reading file contents."""
    files: list[dict[str, Any]] = []
    directories: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        right_fields = raw_line.rsplit("|", 9)
        if len(right_fields) != 10 or "|" not in right_fields[0]:
            continue
        _, path = right_fields[0].split("|", 1)
        metadata_address, mode, uid, gid, size_text, atime, mtime, ctime, crtime = right_fields[1:]
        if is_non_user_entry(path, mode):
            continue
        if not path or path in {".", ".."}:
            continue
        path = path.removeprefix("/")
        size = int(size_text) if size_text.isdigit() else 0
        record: dict[str, Any] = {
            "partition_slot": partition_slot,
            "path": path,
            "metadata_address": metadata_address,
            "tsk_type": mode,
            "uid": uid,
            "gid": gid,
            "atime": int(atime) if atime.lstrip("-").isdigit() else None,
            "mtime": int(mtime) if mtime.lstrip("-").isdigit() else None,
            "ctime": int(ctime) if ctime.lstrip("-").isdigit() else None,
            "crtime": int(crtime) if crtime.lstrip("-").isdigit() else None,
        }
        if mode.startswith("d/") or mode.startswith("d"):
            directories.append(record)
        else:
            extension, category = classify(path)
            record.update({
                "size": size,
                "original_extension": original_extension_for(path),
                "extension": extension,
                "category": category,
            })
            files.append(record)
    return files, directories


def filesystem_type(fsstat_output: str) -> str:
    for line in fsstat_output.splitlines():
        if line.casefold().startswith("file system type:"):
            return line.split(":", 1)[1].strip()
    return "unknown"
