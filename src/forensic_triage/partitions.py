"""Parser for The Sleuth Kit mmls output."""

from __future__ import annotations

import re
from typing import Any


ROW_RE = re.compile(
    r"^\s*(?P<slot>\d{3}):\s+(?P<location>\S+)\s+"
    r"(?P<start>\d+)\s+(?P<end>\d+)\s+(?P<length>\d+)\s+(?P<description>.+?)\s*$"
)


def parse_mmls(output: str) -> list[dict[str, Any]]:
    partitions: list[dict[str, Any]] = []
    for line in output.splitlines():
        match = ROW_RE.match(line)
        if not match:
            continue
        description = match.group("description")
        lowered = description.casefold()
        location = match.group("location")
        allocated = (
            location.casefold() != "meta"
            and not location.startswith("-")
            and not any(marker in lowered for marker in ("unallocated", "table", "safety table"))
        )
        partitions.append(
            {
                "slot": match.group("slot"),
                "location": location,
                "start_sector": int(match.group("start")),
                "end_sector": int(match.group("end")),
                "length_sectors": int(match.group("length")),
                "description": description,
                "allocated": allocated,
            }
        )
    if not partitions:
        raise ValueError("mmls output did not contain partition rows")
    return partitions
