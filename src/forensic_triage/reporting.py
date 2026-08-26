"""Atomic-ish result directory serialization."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_files_csv(path: Path, files: list[dict[str, Any]]) -> None:
    fields = [
        "partition_slot", "path", "metadata_address", "tsk_type", "size", "original_extension",
        "extension", "category",
        "uid", "gid", "atime", "mtime", "ctime", "crtime",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(files)
