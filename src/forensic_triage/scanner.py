"""Read-only orchestration of the metadata inventory."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .commands import run_command
from .container_inventory import (
    ContainerLimits,
    archive_encryption_summary,
    empty_catalog,
    merge_catalogs,
    virtual_files,
)
from .backup_detection import find_backup_hints, summarize_backup_hints
from .crypto_rules import bundled_rules, find_file_hints
from .device import SafetyError, enforce_read_only, inspect_device
from .filesystem import filesystem_type, parse_fls
from .fast_inventory import partition_path_for_start, readonly_mount_inventory
from .keywords import build_hits, load_profile
from .partitions import parse_mmls
from .reporting import write_files_csv, write_json
from .statistics import summarize
from .validation import compare_expected
from .settings import apply_catalog, catalog_snapshot, load_catalog
from .period import evaluate_file_period, period_snapshot, timestamp_coverage


def _command(args: list[str]) -> str:
    result = run_command(args, capture_output=True)
    return result.stdout


def _inventory_optical_medium(
    device: Path, mode: str, raw_dir: Path,
    case_period: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
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
            containers = empty_catalog("unavailable_in_tsk_mode")
        elif mode == "fast":
            if case_period:
                files, directories, mount_info, containers = readonly_mount_inventory(device, "OPT", case_period=case_period)
            else:
                files, directories, mount_info, containers = readonly_mount_inventory(device, "OPT")
            write_json(raw_dir / "fast_mount_OPT.json", mount_info)
            partition["partition_device"] = str(device)
            partition["inventory_method"] = "kernel_readonly_mount"
        else:
            raise ValueError(f"unsupported scan mode: {mode}")
        partition["scan_status"] = "ok"
        return files, directories, [partition], containers
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
    filetype_catalog: dict[str, Any] | None = None,
    crypto_rules: dict[str, Any] | None = None,
    case_period: dict[str, Any] | None = None,
) -> Path:
    case_period = period_snapshot(
        (case_period or {}).get("date_from"), (case_period or {}).get("date_to"),
        {key: (case_period or {}).get(key) for key in ("timezone", "timezone_source", "timezone_reproducible")
         if (case_period or {}).get(key) is not None} or None,
    )
    started = time.monotonic()
    catalog = (catalog_snapshot(filetype_catalog.get("categories"), filetype_catalog.get("version"))
               if filetype_catalog is not None else load_catalog(
                   Path(os.environ["FORENSIC_TRIAGE_SETTINGS_ROOT"]) / "filetypes.json"
                   if os.environ.get("FORENSIC_TRIAGE_SETTINGS_ROOT") else None))
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
        write_json(result_dir / "filetype-catalog.json", catalog)

        device_info = inspect_device(device)
        enforce_read_only(device)
        device_info["read_only_verified"] = True
        device_info["evidence"] = evidence
        device_info["scan_mode"] = mode
        write_json(result_dir / "device.json", device_info)

        if device_info.get("type") == "rom":
            all_files, all_directories, partitions, container_catalog = _inventory_optical_medium(device, mode, raw_dir, case_period)
        else:
            mmls_output = _command(["mmls", str(device)])
            (raw_dir / "mmls.txt").write_text(mmls_output, encoding="utf-8")
            partitions = parse_mmls(mmls_output)

            all_files = []
            all_directories = []
            container_catalogs: list[dict[str, Any]] = []
            configured_container_limits = ContainerLimits.from_environment()
            container_deadline = time.monotonic() + configured_container_limits.seconds
            indexed_containers = 0
            indexed_entries = 0
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
                        containers = empty_catalog("unavailable_in_tsk_mode")
                    elif mode == "fast":
                        partition_device = partition_path_for_start(device, partition["start_sector"])
                        remaining_limits = ContainerLimits(
                            seconds=max(0.0, container_deadline - time.monotonic()),
                            max_containers=max(0, configured_container_limits.max_containers - indexed_containers),
                            max_entries_per_container=configured_container_limits.max_entries_per_container,
                            max_total_entries=max(0, configured_container_limits.max_total_entries - indexed_entries),
                        )
                        files, directories, mount_info, containers = readonly_mount_inventory(
                            partition_device, slot, remaining_limits, case_period,
                        )
                        write_json(raw_dir / f"fast_mount_{slot}.json", mount_info)
                        partition["partition_device"] = str(partition_device)
                        partition["inventory_method"] = "kernel_readonly_mount"
                    else:
                        raise ValueError(f"unsupported scan mode: {mode}")
                    all_files.extend(files)
                    if mode == "tsk" and case_period:
                        for file_record in files:
                            file_record.update(evaluate_file_period(file_record, case_period))
                    all_directories.extend(directories)
                    container_catalogs.append(containers)
                    indexed_containers += int(containers.get("containers_indexed", 0))
                    indexed_entries += int(containers.get("entries_indexed", 0))
                    partition["scan_status"] = "ok"
                except subprocess.TimeoutExpired:
                    raise
                except (OSError, ValueError, SafetyError, subprocess.SubprocessError) as exc:
                    partition["scan_status"] = "unsupported_or_error"
                    partition["error"] = str(exc)
                    scan_logger.warning("partition %s skipped: %s", slot, exc)
            container_catalog = merge_catalogs(container_catalogs)

        apply_catalog(all_files, container_catalog, catalog)
        rule_snapshot = crypto_rules or bundled_rules()
        crypto_files = find_file_hints([*all_files, *virtual_files(container_catalog)], rule_snapshot)
        backup_hints = find_backup_hints(
            [*all_files, *virtual_files(container_catalog)],
            all_directories,
            rule_snapshot,
        )
        write_json(result_dir / "crypto-rules.json", rule_snapshot)
        write_json(result_dir / "crypto-hints.json", {
            "rules": {"version": rule_snapshot["version"], "sha256": rule_snapshot["sha256"]},
            "app_hints": [], "file_hints": crypto_files,
        })
        write_json(result_dir / "backup-hints.json", {
            "rules": {"version": rule_snapshot["version"], "sha256": rule_snapshot["sha256"]},
            "backup_hints": backup_hints,
            "summary": summarize_backup_hints(backup_hints),
        })
        # Web requests already froze keywords and profile provenance before I/O.
        profile = (load_profile(profile_path) if keywords is None or not profile_sources
                   else {**profile_sources[0], "keywords": keywords})
        selected_keywords = profile["keywords"] if keywords is None else keywords
        hits = build_hits([*all_files, *virtual_files(container_catalog)], selected_keywords)
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
        period_files = [item for item in all_files if item.get("in_period") is True]
        if case_period:
            coverage = timestamp_coverage(all_files, case_period)
            latest = sorted((item for item in period_files if item.get("latest_period_timestamp") is not None),
                            key=lambda item: (-float(item["latest_period_timestamp"]), str(item.get("path", ""))))[:10]
            summary.update({"case_period": case_period, "period_evaluation": "configured",
                            "period_file_count": len(period_files), "categories_in_period": summarize(period_files, []).get("categories_by_count", {}),
                            "timestamp_coverage": coverage,
                            "latest_period_files": [{key: item.get(key) for key in ("path", "category", "latest_period_timestamp", "latest_period_timestamp_type", "period_matches")} for item in latest]})
        else:
            summary.update({"case_period": None, "period_evaluation": "not_configured", "period_file_count": None,
                            "categories_in_period": {}, "timestamp_coverage": {}, "latest_period_files": []})
        summary["archive_encryption"] = archive_encryption_summary(all_files, container_catalog)
        summary.update(
            {
                "evidence": evidence,
                "scan_started_utc": timestamp,
                "duration_seconds": round(time.monotonic() - started, 3),
                "scan_mode": mode,
                "filetype_catalog": {"version": catalog["version"], "sha256": catalog["sha256"]},
                "crypto_rules": {"version": rule_snapshot["version"], "sha256": rule_snapshot["sha256"]},
                "crypto_file_hints": len(crypto_files),
                "backup_hints": summarize_backup_hints(backup_hints),
                "keyword_matches": hits["total_matches"],
                "container_index": {
                    "status": container_catalog.get("status", "ok"),
                    "containers_seen": container_catalog.get("containers_seen", 0),
                    "containers_indexed": container_catalog.get("containers_indexed", 0),
                    "entries_indexed": container_catalog.get("entries_indexed", 0),
                    "duration_seconds": container_catalog.get("duration_seconds", 0),
                    "truncated": container_catalog.get("truncated", False),
                },
            }
        )

        write_json(result_dir / "partitions.json", partitions)
        write_files_csv(result_dir / "files.csv", all_files)
        write_json(result_dir / "container-index.json", container_catalog)
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
