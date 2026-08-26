#!/usr/bin/env python3
"""Create the deterministic metadata-only TRIAGE_TESTDATA fixture."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from forensic_triage.classifier import classify  # noqa: E402
from forensic_triage.keywords import build_hits  # noqa: E402
from forensic_triage.statistics import summarize  # noqa: E402


SPECS = [
    ("Bilder", "jpg", 300), ("Bilder", "gif", 200), ("Bilder", "png", 100),
    ("Audio", "mp3", 150), ("Audio", "flac", 30),
    ("Video", "mp4", 10),
    ("Dokumente", "pdf", 70), ("Dokumente", "docx", 30),
    ("Tabellen", "xlsx", 25), ("Tabellen", "csv", 10),
    ("Archive", "zip", 10), ("Archive", "rar", 5), ("Archive", "7z", 3),
    ("Datenbanken", "sqlite", 3), ("Datenbanken", "db", 2),
    ("Email", "eml", 3), ("Email", "pst", 2),
]
KEYWORD_COUNTS = {
    "Rechnung": 20,
    "Buchhaltung": 10,
    "FIBU": 5,
    "DATEV": 3,
    "Kunden": 15,
    "Kassabuch": 4,
    "Steuerberater": 3,
}
LARGE_VIDEO_SIZES = [200, 150, 100, 50, 25]


def planned_files() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for folder, extension, count in SPECS:
        for index in range(1, count + 1):
            size = ((index - 1) % 5 + 1) * 1024
            if folder == "Video" and index <= len(LARGE_VIDEO_SIZES):
                size = LARGE_VIDEO_SIZES[index - 1] * 1024 * 1024
            records.append({
                "path": f"{folder}/{folder.casefold()}_{index:04d}.{extension}",
                "size": size,
            })
    for index in range(1, 8):
        suffix = "" if index <= 3 else f".unbekannt{index}"
        records.append({"path": f"Sonstige/artefakt_{index:04d}{suffix}", "size": index * 777})

    cursor = 0
    spellings = ["Rechnung", "BUCHHALTUNG", "fibu", "Datev", "KUNDEN", "kassabuch", "SteuerBerater"]
    for (keyword, count), spelling in zip(KEYWORD_COUNTS.items(), spellings, strict=True):
        for local_index in range(count):
            record = records[cursor]
            original_name = Path(str(record["path"])).name
            if local_index % 2:
                original_name = f"{spelling}_{original_name}"
            record["path"] = f"KeywordTreffer/{spelling}/{original_name}"
            cursor += 1
    return records


def write_sized_file(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.truncate(size)


def build_manifest(records: list[dict[str, object]], dataset_root: Path) -> dict[str, object]:
    file_rows = []
    directories = {dataset_root.name}
    for record in records:
        relative = str(record["path"])
        extension, category = classify(relative)
        file_rows.append({
            "path": f"{dataset_root.name}/{relative}",
            "size": record["size"],
            "extension": extension,
            "category": category,
        })
        parent = Path(relative).parent
        while str(parent) != ".":
            directories.add(f"{dataset_root.name}/{parent.as_posix()}")
            parent = parent.parent
    summary = summarize(file_rows, [{"path": item} for item in sorted(directories)])
    hits = build_hits(file_rows, list(KEYWORD_COUNTS))
    return {
        "schema_version": 1,
        **summary,
        "keyword_hits": {key: value["count"] for key, value in hits["by_keyword"].items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True, help="existing mounted TRIAGE_TEST volume root")
    parser.add_argument("--manifest", type=Path, default=ROOT / "tests/fixtures/expected.json")
    args = parser.parse_args()
    if not args.target.is_dir():
        parser.error("--target must be an existing directory")
    dataset_root = args.target / "TRIAGE_TESTDATA"
    if dataset_root.exists():
        parser.error(f"refusing to overwrite existing fixture: {dataset_root}")

    records = planned_files()
    for record in records:
        write_sized_file(dataset_root / str(record["path"]), int(record["size"]))
    manifest = build_manifest(records, dataset_root)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"created {manifest['file_count']} files in {dataset_root}")
    print(f"manifest: {args.manifest}")


if __name__ == "__main__":
    main()
