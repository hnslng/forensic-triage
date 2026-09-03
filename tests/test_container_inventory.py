from io import BytesIO
from pathlib import Path
import subprocess
import zipfile

import pycdlib

from forensic_triage.container_inventory import (
    ContainerLimits,
    _iso_namespace,
    archive_encryption_summary,
    index_containers,
    parse_7zip_slt,
    virtual_files,
)


LIMITS = ContainerLimits(seconds=5, max_containers=5, max_entries_per_container=100, max_total_entries=200)


def test_iso_namespace_prefers_joliet_when_hybrid_metadata_is_present() -> None:
    class HybridImage:
        @staticmethod
        def has_joliet() -> bool:
            return True

        @staticmethod
        def has_rock_ridge() -> bool:
            return True

        @staticmethod
        def has_udf() -> bool:
            return False

    assert _iso_namespace(HybridImage()) == ("joliet_path", "joliet")


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


def test_7zip_slt_parser_lists_names_and_encryption_state() -> None:
    output = """Path = sample.7z
Type = 7z

----------
Path = Dokumente
Size = 0
Attributes = D drwxr-xr-x
Encrypted = -

Path = Dokumente/Geheim.txt
Size = 42
Attributes = A -rw-r--r--
Encrypted = +
"""

    parsed = parse_7zip_slt(output, 100, 100)

    assert [item["path"] for item in parsed["entries"]] == [
        "Dokumente", "Dokumente/Geheim.txt",
    ]
    assert parsed["entries"][0]["kind"] == "directory"
    assert parsed["entries"][1]["size"] == 42
    assert parsed["encrypted"] is True
    assert parsed["truncated"] is False


def test_7zip_and_rar_are_listed_with_bounded_external_tool(tmp_path, monkeypatch) -> None:
    (tmp_path / "Ablage.7z").write_bytes(b"container")
    output = """----------
Path = Datei.txt
Size = 12
Attributes = A
Encrypted = -
"""
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert kwargs["timeout"] <= LIMITS.seconds
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr("forensic_triage.container_inventory._seven_zip_binary", lambda: "/usr/bin/7z")
    monkeypatch.setattr("forensic_triage.container_inventory.run_command", fake_run)
    catalog = index_containers(
        tmp_path, [{"path": "Ablage.7z", "extension": "7z"}], "001", LIMITS,
    )

    assert calls[0][1:5] == ["l", "-slt", "-bd", "--"]
    assert catalog["containers"][0]["format"] == "7z"
    assert catalog["containers"][0]["entries"][0]["path"] == "Datei.txt"


def test_password_protected_headers_are_marked_without_password_attempt(tmp_path, monkeypatch) -> None:
    (tmp_path / "Geheim.rar").write_bytes(b"container")

    monkeypatch.setattr("forensic_triage.container_inventory._seven_zip_binary", lambda: "/usr/bin/7z")
    monkeypatch.setattr(
        "forensic_triage.container_inventory.run_command",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args, 2, "Enter password (will not be echoed):", "Break signaled",
        ),
    )
    catalog = index_containers(
        tmp_path, [{"path": "Geheim.rar", "extension": "rar"}], "001", LIMITS,
    )

    container = catalog["containers"][0]
    assert container["status"] == "encrypted_headers"
    assert container["encrypted"] is True
    assert container["entries"] == []


def test_missing_rar_volume_is_marked_incomplete(tmp_path, monkeypatch) -> None:
    (tmp_path / "Teil.rar").write_bytes(b"container")
    monkeypatch.setattr("forensic_triage.container_inventory._seven_zip_binary", lambda: "/usr/bin/7z")
    monkeypatch.setattr(
        "forensic_triage.container_inventory.run_command",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 2, "", "Missing volume"),
    )

    catalog = index_containers(
        tmp_path, [{"path": "Teil.rar", "extension": "rar"}], "001", LIMITS,
    )

    assert catalog["containers"][0]["status"] == "incomplete"


def test_7zip_warning_keeps_entries_but_never_marks_check_complete(tmp_path, monkeypatch) -> None:
    (tmp_path / "Warnung.7z").write_bytes(b"container")
    output = """----------
Path = teilweise.txt
Size = 8
Attributes = A
Encrypted = -
"""
    monkeypatch.setattr("forensic_triage.container_inventory._seven_zip_binary", lambda: "/usr/bin/7z")
    monkeypatch.setattr(
        "forensic_triage.container_inventory.run_command",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 1, output, "Warnings: 1"),
    )

    catalog = index_containers(
        tmp_path, [{"path": "Warnung.7z", "extension": "7z"}], "001", LIMITS,
    )

    assert catalog["containers"][0]["status"] == "incomplete"
    assert catalog["containers"][0]["entry_count"] == 1


def test_zip_encryption_flag_is_detected_without_reading_payload(tmp_path) -> None:
    archive_path = tmp_path / "encrypted.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("secret.txt", b"payload")
    raw = bytearray(archive_path.read_bytes())
    local_header = raw.index(b"PK\x03\x04")
    central_header = raw.index(b"PK\x01\x02")
    raw[local_header + 6] |= 0x01
    raw[central_header + 8] |= 0x01
    archive_path.write_bytes(raw)

    catalog = index_containers(
        tmp_path, [{"path": "encrypted.zip", "extension": "zip"}], "001", LIMITS,
    )

    assert catalog["containers"][0]["encrypted"] is True
    assert catalog["containers"][0]["entries"][0]["encrypted"] is True


def test_archive_encryption_summary_includes_zip_7z_and_rar() -> None:
    files = [
        {"partition_slot": "001", "path": "encrypted.zip", "category": "Archive"},
        {"partition_slot": "001", "path": "encrypted.7z", "category": "Archive"},
        {"partition_slot": "001", "path": "encrypted.rar", "category": "Archive"},
        {"partition_slot": "001", "path": "clear.rar", "category": "Archive"},
        {"partition_slot": "001", "path": "broken.7z", "category": "Archive"},
        {"partition_slot": "001", "path": "unknown.tar", "category": "Archive"},
    ]
    catalog = {
        "containers": [
            {"partition_slot": "001", "path": "encrypted.zip", "format": "zip", "status": "ok", "truncated": False, "encrypted": True},
            {"partition_slot": "001", "path": "encrypted.7z", "format": "7z", "status": "ok", "truncated": False, "encrypted": True},
            {"partition_slot": "001", "path": "encrypted.rar", "format": "rar", "status": "encrypted_headers", "truncated": False, "encrypted": True},
            {"partition_slot": "001", "path": "clear.rar", "format": "rar", "status": "ok", "truncated": False, "encrypted": False},
            {"partition_slot": "001", "path": "broken.7z", "format": "7z", "status": "incomplete", "truncated": False, "encrypted": False},
        ],
    }

    assert archive_encryption_summary(files, catalog) == {
        "total": 6, "encrypted": 3, "not_encrypted": 1, "unknown": 2,
    }


def test_archive_states_distinguish_partitions_and_keep_encryption_precedence() -> None:
    from forensic_triage.container_inventory import archive_encryption_state, archive_encryption_states

    files = [{"path": "same.zip", "category": "Archive", "partition_slot": str(slot)} for slot in range(3)]
    catalog = {"containers": [
        {"path": "same.zip", "format": "zip", "partition_slot": "0", "encrypted": True},
        {"path": "same.zip", "format": "zip", "partition_slot": "0", "status": "ok"},
        {"path": "same.zip", "format": "zip", "partition_slot": "1", "status": "ok"},
        {"path": "same.zip", "format": "zip", "partition_slot": "2", "status": "ok", "truncated": True},
    ]}
    states = archive_encryption_states(catalog)
    assert [archive_encryption_state(file, states) for file in files] == ["encrypted", "not_encrypted", "unknown"]
    assert archive_encryption_state({**files[0], "source": "container_index"}, states) is None
    assert archive_encryption_summary(files + files, catalog) == {"total": 3, "encrypted": 1, "not_encrypted": 1, "unknown": 1}
