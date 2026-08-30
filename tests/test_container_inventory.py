from io import BytesIO
from pathlib import Path
import zipfile

import pycdlib

from forensic_triage.container_inventory import ContainerLimits, index_containers, virtual_files


LIMITS = ContainerLimits(seconds=5, max_containers=5, max_entries_per_container=100, max_total_entries=200)


def test_zip_index_lists_names_without_extracting(tmp_path, monkeypatch) -> None:
    archive_path = tmp_path / "Belege.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("2026/Rechnung.pdf", b"payload is never decompressed")
        archive.writestr("2026/Notiz.txt", b"text")

    monkeypatch.setattr(zipfile.ZipFile, "extract", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("extract called")))
    monkeypatch.setattr(zipfile.ZipFile, "read", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("read called")))
    catalog = index_containers(
        tmp_path, [{"path": "Belege.zip", "extension": "zip"}], "001", LIMITS,
    )

    assert catalog["status"] == "ok"
    assert catalog["containers"][0]["entry_count"] == 2
    assert catalog["containers"][0]["entries"][0]["path"] == "2026/Rechnung.pdf"
    assert virtual_files(catalog)[0]["path"] == "Belege.zip › 2026/Rechnung.pdf"


def test_iso_index_prefers_human_readable_joliet_names(tmp_path) -> None:
    iso_path = tmp_path / "Ablage.iso"
    image = pycdlib.PyCdlib()
    image.new(joliet=3)
    image.add_directory("/DOCS", joliet_path="/Dokumente")
    image.add_fp(
        BytesIO(b"abc"), 3, "/DOCS/REPORT.TXT;1", joliet_path="/Dokumente/Bericht.txt",
    )
    image.write(str(iso_path))
    image.close()

    catalog = index_containers(
        tmp_path, [{"path": "Ablage.iso", "extension": "iso"}], "001", LIMITS,
    )

    container = catalog["containers"][0]
    assert container["namespace"] == "joliet"
    assert [item["path"] for item in container["entries"]] == [
        "Dokumente", "Dokumente/Bericht.txt",
    ]
    assert container["entries"][1]["category"] == "Text/Logs"


def test_container_limits_stop_large_directory_catalog(tmp_path) -> None:
    archive_path = tmp_path / "large.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for index in range(10):
            archive.writestr(f"file-{index}.txt", b"x")

    limits = ContainerLimits(seconds=5, max_containers=2, max_entries_per_container=3, max_total_entries=3)
    catalog = index_containers(
        tmp_path, [{"path": "large.zip", "extension": "zip"}], "001", limits,
    )

    assert catalog["status"] == "limit_reached"
    assert catalog["truncated"] is True
    assert catalog["entries_indexed"] == 3


def test_bad_zip_is_recorded_instead_of_failing_media_scan(tmp_path) -> None:
    (tmp_path / "broken.zip").write_bytes(b"not a zip")

    catalog = index_containers(
        tmp_path, [{"path": "broken.zip", "extension": "zip"}], "001", LIMITS,
    )

    assert catalog["containers"][0]["status"] == "invalid_or_unsupported"
    assert catalog["containers"][0]["entries"] == []


def test_nested_archive_is_only_a_listed_entry(tmp_path) -> None:
    archive_path = tmp_path / "outer.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("inner.zip", b"not inspected")

    catalog = index_containers(
        tmp_path, [{"path": "outer.zip", "extension": "zip"}], "001", LIMITS,
    )

    assert catalog["containers_indexed"] == 1
    assert catalog["containers"][0]["entries"][0]["path"] == "inner.zip"
