"""Read-only orchestration of the metadata inventory."""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .commands import run_command
from .device import SafetyError, enforce_read_only, inspect_device
from .filesystem import filesystem_type, parse_fls
from .fast_inventory import partition_path_for_start, readonly_mount_inventory
from .keywords import build_hits, load_profile
from .partitions import parse_mmls
from .reporting import write_files_csv, write_json
from .statistics import summarize
from .validation import compare_expected


def _command(args: list[str]) -> str:
    result = run_command(args, capture_output=True)
    return result.stdout


def _inventory_optical_medium(
    device: Path, mode: str, raw_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Inventory a CD/DVD filesystem that lives directly on the drive node."""
    partition: dict[str, Any] = {
        "slot": "OPT",
        "location": "whole_medium",
        "start_sector": 0,
        "description": "Optical medium",
        "allocated": True,
    }
    try:
        try:
            fsstat_output = _command(["fsstat", str(device)])
            (raw_dir / "fsstat_OPT.txt").write_text(fsstat_output, encoding="utf-8")
            partition["filesystem"] = filesystem_type(fsstat_output)
        except subprocess.TimeoutExpired:
            raise
        except subprocess.SubprocessError as exc:
            # Linux may still mount an optical UDF variant that this TSK build
            # cannot describe. Keep fast-mode inventory available and record it.
            partition["filesystem"] = "unknown"
            partition["fsstat_error"] = str(exc)
        if mode == "tsk":
            fls_output = _command(["fls", "-r", "-p", "-u", "-m", "/", str(device)])
            (raw_dir / "fls_OPT.txt").write_text(fls_output, encoding="utf-8")
            files, directories = parse_fls(fls_output, "OPT")
            partition["inventory_method"] = "tsk_fls"
        elif mode == "fast":
            files, directories, mount_info = readonly_mount_inventory(device, "OPT")
            write_json(raw_dir / "fast_mount_OPT.json", mount_info)
            partition["partition_device"] = str(device)
            partition["inventory_method"] = "kernel_readonly_mount"
        else:
            raise ValueError(f"unsupported scan mode: {mode}")
        partition["scan_status"] = "ok"
        return files, directories, [partition]
    except Exception as exc:
        partition["scan_status"] = "unsupported_or_error"
        partition["error"] = str(exc)
        raise


def scan(
    device: Path,
    profile_path: Path,
    evidence: str,
    results_root: Path,
    expected_path: Path | None = None,
    mode: str = "fast",
    keywords: list[str] | None = None,
    profile_sources: list[dict[str, str]] | None = None,
) -> Path:
    started = time.monotonic()
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
    safe_evidence = "".join(char if char.isalnum() or char in "-_" else "_" for char in evidence)
    result_dir = results_root / f"{timestamp}_{safe_evidence}"
    raw_dir = result_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=False)

    scan_logger = logging.Logger(f"forensic-triage.scan.{timestamp}.{safe_evidence}", logging.INFO)
    handler = logging.FileHandler(result_dir / "scan.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    scan_logger.addHandler(handler)
    try:
        scan_logger.info("scan start evidence=%s device=%s", evidence, device)

        device_info = inspect_device(device)
        enforce_read_only(device)
        device_info["read_only_verified"] = True
        device_info["evidence"] = evidence
        device_info["scan_mode"] = mode
        write_json(result_dir / "device.json", device_info)

        if device_info.get("type") == "rom":
            all_files, all_directories, partitions = _inventory_optical_medium(device, mode, raw_dir)
        else:
            mmls_output = _command(["mmls", str(device)])
            (raw_dir / "mmls.txt").write_text(mmls_output, encoding="utf-8")
            partitions = parse_mmls(mmls_output)

            all_files = []
            all_directories = []
            for partition in partitions:
                if not partition["allocated"]:
                    continue
                slot = partition["slot"]
                offset = str(partition["start_sector"])
                try:
                    fsstat_output = _command(["fsstat", "-o", offset, str(device)])
                    (raw_dir / f"fsstat_{slot}.txt").write_text(fsstat_output, encoding="utf-8")
                    partition["filesystem"] = filesystem_type(fsstat_output)
                    if mode == "tsk":
                        fls_output = _command(["fls", "-r", "-p", "-u", "-m", "/", "-o", offset, str(device)])
                        (raw_dir / f"fls_{slot}.txt").write_text(fls_output, encoding="utf-8")
                        files, directories = parse_fls(fls_output, slot)
                        partition["inventory_method"] = "tsk_fls"
                    elif mode == "fast":
                        partition_device = partition_path_for_start(device, partition["start_sector"])
                        files, directories, mount_info = readonly_mount_inventory(partition_device, slot)
                        write_json(raw_dir / f"fast_mount_{slot}.json", mount_info)
                        partition["partition_device"] = str(partition_device)
                        partition["inventory_method"] = "kernel_readonly_mount"
                    else:
                        raise ValueError(f"unsupported scan mode: {mode}")
                    all_files.extend(files)
                    all_directories.extend(directories)
                    partition["scan_status"] = "ok"
                except subprocess.TimeoutExpired:
                    raise
                except (OSError, ValueError, SafetyError, subprocess.SubprocessError) as exc:
                    partition["scan_status"] = "unsupported_or_error"
                    partition["error"] = str(exc)
                    scan_logger.warning("partition %s skipped: %s", slot, exc)

        profile = load_profile(profile_path)
        selected_keywords = profile["keywords"] if keywords is None else keywords
        hits = build_hits(all_files, selected_keywords)
        sources = profile_sources or [{
            "id": str(profile.get("id", profile_path.stem)),
            "name": str(profile.get("name", profile_path.stem.upper())),
            "version": profile["version"], "sha256": profile["sha256"],
        }]
        combined_hash = hashlib.sha256(
            json.dumps(sources, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        hits["profile"] = {
            "version": sources[0]["version"] if len(sources) == 1 else "combined",
            "sha256": sources[0]["sha256"] if len(sources) == 1 else combined_hash,
            "sources": sources,
            "selected_keywords": selected_keywords,
        }
        summary = summarize(all_files, all_directories)
        summary.update(
            {
                "evidence": evidence,
                "scan_started_utc": timestamp,
                "duration_seconds": round(time.monotonic() - started, 3),
                "scan_mode": mode,
                "keyword_matches": hits["total_matches"],
            }
        )

        write_json(result_dir / "partitions.json", partitions)
        write_files_csv(result_dir / "files.csv", all_files)
        write_json(result_dir / "hits.json", hits)
        write_json(result_dir / "summary.json", summary)
        if expected_path is not None:
            validation = compare_expected(summary, hits, expected_path)
            write_json(result_dir / "validation.json", validation)
            if not validation["passed"]:
                scan_logger.error("fixture validation failed: %s", validation["mismatches"])
                raise ValueError(f"fixture validation failed; see {result_dir / 'validation.json'}")
        scan_logger.info("scan complete files=%d directories=%d", len(all_files), len(all_directories))
        return result_dir
    finally:
        scan_logger.removeHandler(handler)
        handler.close()
