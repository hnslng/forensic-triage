"""Inventory coverage, also derived for older scans without changing evidence files."""

from typing import Any


def apply_scan_quality(summary: dict[str, Any], partitions: list[dict[str, Any]]) -> None:
    allocated = [part for part in partitions if part.get("allocated")]
    warnings = []
    for part in allocated:
        if part.get("scan_status") != "ok":
            warnings.append({"partition_slot": part.get("slot"),
                             "error": part.get("error") or "Partition nur unvollständig erfasst.",
                             "read_errors": part.get("read_errors", [])})
    if not allocated:
        warnings.append({"error": "Keine auswertbare Partition erkannt.", "read_errors": []})
    summary["scan_status"] = ("partial" if any(part.get("scan_status") in {"ok", "partial"}
                                              for part in allocated) else "failed") if warnings else "complete"
    summary["scan_warnings"] = warnings
