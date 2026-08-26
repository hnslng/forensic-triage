"""Read-only orchestration of the metadata inventory."""

from __future__ import annotations

import logging
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .device import enforce_read_only, inspect_device
from .filesystem import filesystem_type, parse_fls
from .fast_inventory import partition_path_for_start, readonly_mount_inventory
from .keywords import build_hits, load_profile
from .partitions import parse_mmls
from .reporting import write_files_csv, write_json
from .statistics import summarize
from .validation import compare_expected


def _command(args: list[str]) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return result.stdout


def scan(
    device: Path,
    profile_path: Path,
    evidence: str,
    results_root: Path,
    expected_path: Path | None = None,
    mode: str = "fast",
) -> Path:
    started = time.monotonic()
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
    safe_evidence = "".join(char if char.isalnum() or char in "-_" else "_" for char in evidence)
    result_dir = results_root / f"{timestamp}_{safe_evidence}"
    raw_dir = result_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=False)

    logging.basicConfig(
        filename=result_dir / "scan.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )
    logging.info("scan start evidence=%s device=%s", evidence, device)

    device_info = inspect_device(device)
    enforce_read_only(device)
    device_info["read_only_verified"] = True
    device_info["evidence"] = evidence
    device_info["scan_mode"] = mode
    write_json(result_dir / "device.json", device_info)

    mmls_output = _command(["mmls", str(device)])
    (raw_dir / "mmls.txt").write_text(mmls_output, encoding="utf-8")
    partitions = parse_mmls(mmls_output)

    all_files: list[dict[str, Any]] = []
    all_directories: list[dict[str, Any]] = []
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
        except subprocess.CalledProcessError as exc:
            partition["scan_status"] = "unsupported_or_error"
            partition["error"] = exc.stderr.strip()
            logging.warning("partition %s skipped: %s", slot, exc.stderr.strip())

    profile = load_profile(profile_path)
    hits = build_hits(all_files, profile["keywords"])
    hits["profile"] = {"version": profile["version"], "sha256": profile["sha256"]}
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
            logging.error("fixture validation failed: %s", validation["mismatches"])
            raise ValueError(f"fixture validation failed; see {result_dir / 'validation.json'}")
    logging.info("scan complete files=%d directories=%d", len(all_files), len(all_directories))
    return result_dir
