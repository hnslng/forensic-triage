"""Versioned inventory quality and conservative, read-only legacy interpretation."""
from __future__ import annotations

from typing import Any

LABELS = {
    "complete": "SCAN VOLLSTÄNDIG",
    "partial": "SICHTUNG UNVOLLSTÄNDIG",
    "failed": "SICHTUNG FEHLGESCHLAGEN",
    "unknown": "SCANQUALITÄT NICHT BEWERTBAR",
}
INCOMPLETE_NOTICE = "Die Sichtung ist unvollständig. Nicht erfasste Dateien und Inhalte können nicht ausgeschlossen werden."
NO_INVENTORY = "Kein auswertbares Dateiinventar erstellt."


class InventoryErrors:
    """Count every error, retaining at most 50 relative-path examples."""
    def __init__(self, limit: int = 50) -> None:
        self.limit = min(50, max(0, limit))
        self.counts = {"file": 0, "directory": 0, "other": 0}
        self.examples: list[dict[str, Any]] = []
        self.root_read = False
        self.successful_entries = 0

    def record(self, kind: str, path: str, exc: OSError) -> None:
        kind = kind if kind in self.counts else "other"
        self.counts[kind] += 1
        if len(self.examples) < self.limit:
            self.examples.append({"access": kind, "path": path, "errno": exc.errno,
                                  "error": exc.strerror or "Inventarisierungsfehler"})

    def snapshot(self) -> dict[str, Any]:
        total = sum(self.counts.values())
        return {"read_errors": self.examples, "read_error_counts": {**self.counts, "total": total},
                "read_error_count": total, "read_errors_truncated": total > len(self.examples),
                "inventory_root_read": self.root_read,
                "inventory_successful_entries": self.successful_entries}


def partition_status(info: dict[str, Any]) -> str:
    errors = int(info.get("read_error_count", len(info.get("read_errors") or [])))
    if info.get("inventory_root_read") is False:
        return "failed"
    if errors:
        if info.get("inventory_successful_entries") == 0:
            return "failed"
        return "partial"
    return "ok"


def apply_scan_quality(summary: dict[str, Any], partitions: list[dict[str, Any]], *, historical: bool = False) -> None:
    """Annotate an in-memory summary; never persist or upgrade an adverse status."""
    mode = str(summary.get("scan_mode") or "")
    if mode.startswith(("phone_", "iphone_", "android_")):
        phone = summary.get("phone") or summary.get("iphone") or summary.get("android") or {}
        complete = phone.get("complete", phone.get("apps_complete"))
        status = "complete" if complete is True else "partial" if complete is False else "unknown"
        summary.update(scan_status=status, scan_quality_scope="phone", scan_quality_label=LABELS[status])
        return
    allocated = [p for p in partitions if p.get("allocated")]
    warnings: list[dict[str, Any]] = []
    counts = {"file": 0, "directory": 0, "other": 0, "total": 0}
    statuses = []
    for part in allocated:
        status = part.get("scan_status", "unknown")
        if "inventory_root_read" in part or "read_error_count" in part:
            if status in {"ok", "partial"}:
                status = partition_status(part)
        statuses.append(status)
        detail = part.get("read_error_counts") or {}
        total = int(part.get("read_error_count", len(part.get("read_errors") or [])))
        for kind in ("file", "directory", "other"):
            counts[kind] += int(detail.get(kind, total if kind == "other" and not detail else 0))
        counts["total"] += total
        if status != "ok" or part.get("cleanup_failed"):
            if (not total and status != "unknown") or part.get("cleanup_failed"):
                counts["other"] += 1
                counts["total"] += 1
            warnings.append({"partition_slot": part.get("slot"),
                             "error": "Partition nicht vollständig erfasst." if status != "unknown" else "Partitionsqualität nicht dokumentiert.",
                             "read_error_count": total, "read_errors": (part.get("read_errors") or [])[:50],
                             "read_errors_truncated": bool(part.get("read_errors_truncated")),
                             "cleanup_failed": bool(part.get("cleanup_failed"))})
    if not allocated:
        status = "unknown" if historical else "failed"
        warnings.append({"error": "Keine auswertbare Partition dokumentiert.", "read_errors": []})
    elif all(s == "ok" for s in statuses):
        status = "complete"
    elif any(s in {"ok", "partial"} for s in statuses):
        status = "partial"
    elif "unknown" in statuses:
        status = "unknown"
    else:
        status = "failed"
    stored = summary.get("scan_status")
    if stored in {"partial", "failed", "unknown"} and status == "complete":
        status = stored
    elif not allocated and historical and stored in LABELS:
        status = stored
    if summary.get("scan_cleanup_failed") or summary.get("scan_interrupted"):
        status = "partial" if any(s in {"ok", "partial"} for s in statuses) else "failed"
    if stored == "failed":
        status = "failed"
    if status != "complete" and not warnings:
        warnings.append({"error": "Kein verlässlich vollständiger Abschluss dokumentiert.", "read_errors": []})
    affected = [str(p.get("slot", "?")) for p in allocated if p.get("scan_status") != "ok" or p.get("cleanup_failed")]
    summary.update(scan_status=status, scan_quality_label=LABELS[status], scan_quality_scope="filesystem",
                   scan_warnings=warnings, scan_error_count=counts["total"], scan_error_counts=counts,
                   scan_affected_partitions=affected,
                   scan_inventory_present=summary.get("scan_inventory_present", True),
                   scan_quality_message="" if status == "complete" else INCOMPLETE_NOTICE,
                   scan_quality_action="Verbindung prüfen und eine erneute Sichtung in Betracht ziehen." if status != "complete" else "")


def quality_fields(summary: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in summary.items() if k.startswith("scan_")}


def load_scan_quality(result_dir) -> dict[str, Any]:
    """Read existing artifacts without initializing a case store or migrating files."""
    import json
    try:
        summary = json.loads((result_dir / "summary.json").read_text(encoding="utf-8"))
        if not isinstance(summary, dict):
            raise ValueError("Invalid summary")
    except (OSError, ValueError):
        summary = {"scan_status": "unknown", "scan_inventory_present": False}
    try:
        partitions = json.loads((result_dir / "partitions.json").read_text(encoding="utf-8"))
        if not isinstance(partitions, list):
            partitions = []
        else:
            partitions = [part for part in partitions if isinstance(part, dict)]
    except (OSError, ValueError):
        partitions = []
    if not (result_dir / "files.csv").is_file():
        summary["scan_inventory_present"] = False
        # A summary alone is not an available inventory, even if an older
        # process once claimed a successful completion.
        if summary.get("scan_status") == "complete":
            summary["scan_status"] = "unknown"
    apply_scan_quality(summary, partitions, historical=True)
    if summary.get("scan_inventory_present") is False and summary.get("scan_status") == "complete":
        summary.update(scan_status="unknown", scan_quality_label=LABELS["unknown"],
                       scan_quality_message=NO_INVENTORY)
    return summary
