"""Case-period validation and B/M/C/A timestamp evaluation."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Any

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
    if start_date > end_date:
        raise ValueError("Zeitraum von darf nicht nach Zeitraum bis liegen.")
    return start, end


def evaluate_file_period(file_record: dict[str, Any], case_period: dict[str, Any] | None) -> dict[str, Any]:
    start_text, end_text = validate_period(
        (case_period or {}).get("date_from"), (case_period or {}).get("date_to")
    )
    result = {"in_period": None, "period_matches": "", "latest_period_timestamp": None,
              "latest_period_timestamp_type": None}
    if not start_text:
        return result
    start, end = date.fromisoformat(start_text), date.fromisoformat(end_text)
    matches: list[tuple[str, str, int]] = []
    for field, label in TIMESTAMP_TYPES:
        raw = file_record.get(field)
        if raw in (None, "", "null"):
            continue
        try:
            value = float(raw)
            zone_name = str((case_period or {}).get("timezone") or "")
            zone = ZoneInfo(zone_name) if zone_name and "/" in zone_name else None
            local_date = datetime.fromtimestamp(value, zone).date() if zone else datetime.fromtimestamp(value).date()
        except (TypeError, ValueError, OverflowError, OSError):
            continue
        if start <= local_date <= end:
            matches.append((label, field, value))
    result["in_period"] = bool(matches)
    result["period_matches"] = "+".join(label for label, _field, _value in matches)
    if matches:
        newest = max(value for _label, _field, value in matches)
        result["latest_period_timestamp"] = int(newest) if newest.is_integer() else newest
        result["latest_period_timestamp_type"] = "+".join(label for label, _field, value in matches if value == newest)
    return result


def period_timezone() -> str:
    try:
        import os
        zone = os.environ.get("TZ")
        if zone and "/" in zone:
            ZoneInfo(zone)
            return zone
    except Exception:
        pass
    try:
        target = os.path.realpath("/etc/localtime")
        marker = "/zoneinfo/"
        if marker in target:
            zone = target.split(marker, 1)[1]
            ZoneInfo(zone)
            return zone
    except Exception:
        pass
    try:
        from tzlocal import get_localzone_name  # type: ignore
        return str(get_localzone_name())
    except Exception:
        return datetime.now().astimezone().tzname() or "local"
