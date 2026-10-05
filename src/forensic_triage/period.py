"""Validation and shared B/M/C/A timestamp interpretation for case periods."""
from __future__ import annotations

import math
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TIMESTAMP_TYPES = (("crtime", "B"), ("mtime", "M"), ("ctime", "C"), ("atime", "A"))


def validate_period(date_from: str | None, date_to: str | None) -> tuple[str | None, str | None]:
    start, end = (str(date_from or "").strip() or None), (str(date_to or "").strip() or None)
    if start is None and end is None:
        return None, None
    if start is None or end is None:
        raise ValueError("Zeitraum muss von und bis enthalten.")
    try:
        start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError as exc:
        raise ValueError("Ungültiges Zeitraumdatum.") from exc
    if start_date.isoformat() != start or end_date.isoformat() != end:
        raise ValueError("Zeitraumdaten müssen YYYY-MM-DD entsprechen.")
    if start_date > end_date:
        raise ValueError("Zeitraum von darf nicht nach Zeitraum bis liegen.")
    return start, end


def timestamp_zone(case_period: dict[str, Any] | None):
    name = str((case_period or {}).get("timezone") or "")
    if name:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return None


def parse_timestamp(raw: Any, case_period: dict[str, Any] | None = None) -> tuple[datetime | None, str]:
    """Return local datetime and status (valid, missing, invalid) for one raw epoch."""
    if raw is None or raw == "" or raw == "null":
        return None, "missing"
    if isinstance(raw, bool):
        return None, "invalid"
    try:
        value = float(raw)
        if not math.isfinite(value):
            return None, "invalid"
        zone = timestamp_zone(case_period)
        parsed = datetime.fromtimestamp(value, zone) if zone is not None else datetime.fromtimestamp(value)
        return parsed, "valid"
    except (TypeError, ValueError, OverflowError, OSError, ArithmeticError):
        return None, "invalid"


def evaluate_file_period(file_record: dict[str, Any], case_period: dict[str, Any] | None) -> dict[str, Any]:
    start_text, end_text = validate_period(
        (case_period or {}).get("date_from"), (case_period or {}).get("date_to")
    )
    result = {"in_period": None, "period_matches": "", "latest_period_timestamp": None,
              "latest_period_timestamp_type": None}
    if not start_text:
        return result
    start, end = date.fromisoformat(start_text), date.fromisoformat(end_text)
    matches: list[tuple[str, float]] = []
    for field, label in TIMESTAMP_TYPES:
        parsed, status = parse_timestamp(file_record.get(field), case_period)
        if status == "valid" and parsed is not None and start <= parsed.date() <= end:
            matches.append((label, float(file_record[field])))
    result["in_period"] = bool(matches)
    result["period_matches"] = "+".join(label for label, _value in matches)
    if matches:
        newest = max(value for _label, value in matches)
        result["latest_period_timestamp"] = int(newest) if newest.is_integer() else newest
        result["latest_period_timestamp_type"] = "+".join(label for label, value in matches if value == newest)
    return result


def timestamp_coverage(files: list[dict[str, Any]], case_period: dict[str, Any] | None) -> dict[str, int]:
    result = {"files_total": len(files), "files_with_any_timestamp": 0}
    for label in "B M C A".split():
        result[f"{label}_available"] = 0
        result[f"{label}_invalid"] = 0
    for item in files:
        any_valid = False
        for field, label in TIMESTAMP_TYPES:
            _parsed, status = parse_timestamp(item.get(field), case_period)
            if status == "valid":
                result[f"{label}_available"] += 1
                any_valid = True
            elif status == "invalid":
                result[f"{label}_invalid"] += 1
        result["files_with_any_timestamp"] += int(any_valid)
    return result


def period_timezone_info() -> dict[str, Any]:
    """Resolve a reproducible IANA timezone where system configuration exposes one."""
    candidates: list[tuple[str, str]] = []
    configured = os.environ.get("TZ", "").strip()
    if configured:
        candidates.append((configured.removeprefix(":"), "TZ"))
    try:
        target = os.path.realpath("/etc/localtime")
        marker = f"{os.sep}zoneinfo{os.sep}"
        if marker in target:
            candidates.append((target.split(marker, 1)[1], "/etc/localtime"))
    except OSError:
        pass
    try:
        text = Path("/etc/timezone").read_text(encoding="utf-8").strip()
        if text:
            candidates.append((text, "/etc/timezone"))
    except OSError:
        pass
    for name, source in candidates:
        try:
            ZoneInfo(name)
            return {"timezone": name, "timezone_source": source, "timezone_reproducible": True}
        except (ZoneInfoNotFoundError, ValueError):
            continue
    return {"timezone": "local", "timezone_source": "system-local-fallback", "timezone_reproducible": False}


def period_snapshot(date_from: str | None, date_to: str | None, timezone_info: dict[str, Any] | None = None) -> dict[str, Any] | None:
    start, end = validate_period(date_from, date_to)
    if start is None:
        return None
    info = timezone_info or period_timezone_info()
    normalized_info = {**info, "timezone_reproducible": (bool(info.get("timezone_reproducible"))
                                                        if info.get("timezone_reproducible") is not None else None)}
    return {"date_from": start, "date_to": end, **normalized_info, "inclusive": True}
