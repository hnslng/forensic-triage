"""Bounded directory-only indexing for ZIP archives and ISO images."""

from __future__ import annotations

import os
import time
import zipfile
from dataclasses import dataclass
from itertools import chain
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import pycdlib

from .classifier import classify


SUPPORTED_CONTAINER_EXTENSIONS = {"zip": "zip", "iso": "iso"}


@dataclass(frozen=True)
class ContainerLimits:
    seconds: float = 3.0
    max_containers: int = 50
    max_entries_per_container: int = 2_000
    max_total_entries: int = 10_000

    @classmethod
    def from_environment(cls) -> "ContainerLimits":
        limits = cls(
            seconds=float(os.environ.get("FORENSIC_TRIAGE_CONTAINER_INDEX_SECONDS", "3")),
            max_containers=int(os.environ.get("FORENSIC_TRIAGE_CONTAINER_MAX_FILES", "50")),
            max_entries_per_container=int(
                os.environ.get("FORENSIC_TRIAGE_CONTAINER_MAX_ENTRIES", "2000")
            ),
            max_total_entries=int(
                os.environ.get("FORENSIC_TRIAGE_CONTAINER_MAX_TOTAL_ENTRIES", "10000")
            ),
        )
        if (
            limits.seconds <= 0
            or limits.max_containers <= 0
            or limits.max_entries_per_container <= 0
            or limits.max_total_entries <= 0
        ):
            raise ValueError("Container-Index-Limits müssen größer als null sein.")
        return limits


def empty_catalog(status: str = "ok") -> dict[str, Any]:
    return {
        "version": 1,
        "status": status,
        "duration_seconds": 0.0,
        "containers_seen": 0,
        "containers_indexed": 0,
        "entries_indexed": 0,
        "truncated": False,
        "containers": [],
    }


def _safe_internal_path(value: object) -> str | None:
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
    text = text.replace("\\", "/").strip("/")
    parts = [part for part in text.split("/") if part not in {"", "."}]
    if not parts or ".." in parts:
        return None
    clean = "/".join(parts)
    return clean[:2_000] if len(clean) <= 2_000 else None


def _entry(path: str, kind: str, size: int | None = None, encrypted: bool = False) -> dict[str, Any]:
    extension, category = classify(path)
    return {
        "path": path,
        "kind": kind,
        "size": max(0, int(size or 0)),
        "size_known": size is not None,
        "extension": extension,
        "category": category if kind == "file" else "Ordner",
        "encrypted": bool(encrypted),
    }


def _limit_reached(entries: list[dict[str, Any]], limits: ContainerLimits, total: int) -> bool:
    return len(entries) >= limits.max_entries_per_container or total + len(entries) >= limits.max_total_entries


def _index_zip(path: Path, limits: ContainerLimits, deadline: float, total: int) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    encrypted = False
    truncated = False
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            if time.monotonic() >= deadline or _limit_reached(entries, limits, total):
                truncated = True
                break
            internal = _safe_internal_path(item.filename)
            if internal is None:
                continue
            item_encrypted = bool(item.flag_bits & 0x1)
            encrypted = encrypted or item_encrypted
            entries.append(
                _entry(internal, "directory" if item.is_dir() else "file", item.file_size, item_encrypted)
            )
    return {
        "status": "limit_reached" if truncated else "ok",
        "encrypted": encrypted,
        "truncated": truncated,
        "entries": entries,
    }


def _iso_namespace(image: pycdlib.PyCdlib) -> tuple[str, str]:
    if image.has_rock_ridge():
        return "rr_path", "rock_ridge"
    if image.has_joliet():
        return "joliet_path", "joliet"
    if image.has_udf():
        return "udf_path", "udf"
    return "iso_path", "iso9660"


def _join_internal(directory: object, name: object) -> str | None:
    directory_text = _safe_internal_path(directory) or ""
    name_text = _safe_internal_path(name)
    if name_text is None:
        return None
    combined = f"{directory_text}/{name_text}" if directory_text else name_text
    # ISO9660 version suffixes are presentation noise, not part of the useful name.
    final = PurePosixPath(combined)
    clean_name = final.name.rsplit(";", 1)[0] if final.name.rsplit(";", 1)[-1].isdigit() else final.name
    return str(final.with_name(clean_name))


def _index_iso(path: Path, limits: ContainerLimits, deadline: float, total: int) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    truncated = False
    image = pycdlib.PyCdlib()
    opened = False
    namespace_name = "unknown"
    try:
        image.open(str(path))
        opened = True
        namespace_key, namespace_name = _iso_namespace(image)
        for directory, dirnames, filenames in image.walk(**{namespace_key: "/"}):
            for name, kind in chain(
                ((item, "directory") for item in dirnames),
                ((item, "file") for item in filenames),
            ):
                if time.monotonic() >= deadline or _limit_reached(entries, limits, total):
                    truncated = True
                    break
                internal = _join_internal(directory, name)
                if internal is not None:
                    # Walking the directory records does not read or extract file payloads.
                    entries.append(_entry(internal, kind))
            if truncated:
                break
    finally:
        if opened:
            image.close()
    return {
        "status": "limit_reached" if truncated else "ok",
        "namespace": namespace_name,
        "encrypted": False,
        "truncated": truncated,
        "entries": entries,
    }


def index_containers(
    root: Path,
    files: Iterable[dict[str, Any]],
    partition_slot: str,
    limits: ContainerLimits | None = None,
) -> dict[str, Any]:
    """Index only container directory metadata, with no extraction or recursion."""
    selected_limits = limits or ContainerLimits.from_environment()
    result = empty_catalog()
    started = time.monotonic()
    deadline = started + selected_limits.seconds
    candidates: list[tuple[str, str]] = []
    for item in files:
        relative = str(item.get("path", ""))
        container_format = SUPPORTED_CONTAINER_EXTENSIONS.get(str(item.get("extension", "")).casefold())
        if container_format:
            candidates.append((relative, container_format))
    result["containers_seen"] = len(candidates)

    for relative, container_format in candidates:
        if (
            time.monotonic() >= deadline
            or len(result["containers"]) >= selected_limits.max_containers
            or result["entries_indexed"] >= selected_limits.max_total_entries
        ):
            result["status"] = "limit_reached"
            result["truncated"] = True
            break
        record: dict[str, Any] = {
            "id": f"{partition_slot}:{relative}",
            "path": relative,
            "partition_slot": partition_slot,
            "format": container_format,
            "status": "ok",
            "encrypted": False,
            "truncated": False,
            "entries": [],
        }
        try:
            absolute = root / relative
            indexed = (
                _index_zip(absolute, selected_limits, deadline, int(result["entries_indexed"]))
                if container_format == "zip"
                else _index_iso(absolute, selected_limits, deadline, int(result["entries_indexed"]))
            )
            record.update(indexed)
        except (OSError, ValueError, zipfile.BadZipFile, pycdlib.pycdlibexception.PyCdlibException) as exc:
            record["status"] = "invalid_or_unsupported"
            record["error"] = f"{type(exc).__name__}: {exc}"[:300]
        record["entry_count"] = len(record["entries"])
        result["containers"].append(record)
        result["containers_indexed"] += 1
        result["entries_indexed"] += record["entry_count"]
        if record.get("truncated"):
            result["status"] = "limit_reached"
            result["truncated"] = True
            break

    result["duration_seconds"] = round(time.monotonic() - started, 3)
    result["policy"] = {
        "formats": ["zip", "iso"],
        "directory_metadata_only": True,
        "extract_files": False,
        "nested_containers": False,
        "seconds": selected_limits.seconds,
        "max_containers": selected_limits.max_containers,
        "max_entries_per_container": selected_limits.max_entries_per_container,
        "max_total_entries": selected_limits.max_total_entries,
    }
    return result


def merge_catalogs(catalogs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    merged = empty_catalog()
    policies: list[dict[str, Any]] = []
    for catalog in catalogs:
        merged["containers"].extend(catalog.get("containers", []))
        merged["containers_seen"] += int(catalog.get("containers_seen", 0))
        merged["containers_indexed"] += int(catalog.get("containers_indexed", 0))
        merged["entries_indexed"] += int(catalog.get("entries_indexed", 0))
        merged["duration_seconds"] += float(catalog.get("duration_seconds", 0))
        if catalog.get("status") != "ok":
            merged["status"] = str(catalog.get("status"))
        merged["truncated"] = bool(merged["truncated"] or catalog.get("truncated"))
        if catalog.get("policy"):
            policies.append(catalog["policy"])
    merged["duration_seconds"] = round(float(merged["duration_seconds"]), 3)
    if policies:
        merged["policy"] = policies[0]
    return merged


def virtual_files(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose indexed container filenames to keyword and free-path search only."""
    result: list[dict[str, Any]] = []
    for container in catalog.get("containers", []):
        outer_path = str(container.get("path", ""))
        container_id = str(container.get("id", outer_path))
        container_format = str(container.get("format", "container")).upper()
        for item in container.get("entries", []):
            if item.get("kind") != "file":
                continue
            result.append({
                **item,
                "path": f"{outer_path} › {item.get('path', '')}",
                "source": "container_index",
                "container_format": container_format,
                "container_path": outer_path,
                "container_id": container_id,
            })
    return result


def archive_encryption_summary(
    files: Iterable[dict[str, Any]], catalog: dict[str, Any],
) -> dict[str, int]:
    """Count archive encryption states without guessing about unsupported formats."""
    archive_keys = {
        (str(item.get("partition_slot", "")), str(item.get("path", "")))
        for item in files
        if str(item.get("category", "")).casefold() == "archive"
    }
    encrypted: set[tuple[str, str]] = set()
    clear: set[tuple[str, str]] = set()
    for container in catalog.get("containers", []):
        if str(container.get("format", "")).casefold() != "zip":
            continue
        key = (str(container.get("partition_slot", "")), str(container.get("path", "")))
        if key not in archive_keys:
            continue
        if container.get("encrypted"):
            encrypted.add(key)
        elif container.get("status") == "ok" and not container.get("truncated"):
            clear.add(key)
    clear -= encrypted
    return {
        "total": len(archive_keys),
        "encrypted": len(encrypted),
        "not_encrypted": len(clear),
        "unknown": max(0, len(archive_keys - encrypted - clear)),
    }
