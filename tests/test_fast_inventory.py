import ctypes
import json
import os
import stat
import subprocess

import pytest

from forensic_triage import fast_inventory
from forensic_triage.fast_inventory import find_partition_path, inventory_tree


def test_find_partition_path_uses_dynamic_start_sector():
    data = {
        "blockdevices": [{
            "path": "/dev/sdz",
            "type": "disk",
            "children": [{"path": "/dev/sdz1", "type": "part", "start": 4096}],
        }]
    }
    assert str(find_partition_path(data, 4096)) == "/dev/sdz1"


def test_inventory_tree_collects_metadata_without_contents(tmp_path):
    folder = tmp_path / "Dokumente"
    folder.mkdir()
    sample = folder / "Bericht.PDF"
    sample.write_bytes(b"1234")
    files, directories = inventory_tree(tmp_path, "004")
    assert [item["path"] for item in directories] == ["Dokumente"]
    assert files[0]["path"] == "Dokumente/Bericht.PDF"
    assert files[0]["size"] == 4
    assert files[0]["original_extension"] == "PDF"
    assert files[0]["category"] == "Dokumente"


def test_inventory_tree_includes_hidden_files_and_directories(tmp_path):
    hidden_folder = tmp_path / ".intern"
    hidden_folder.mkdir()
    (tmp_path / ".hinweis.txt").write_text("sichtbar im Inventar", encoding="utf-8")
    (hidden_folder / ".daten.csv").write_text("a,b\n", encoding="utf-8")

    files, directories = inventory_tree(tmp_path, "001")

    assert [item["path"] for item in directories] == [".intern"]
    assert {item["path"] for item in files} == {".hinweis.txt", ".intern/.daten.csv"}


def test_statx_metadata_reads_birth_time_without_subprocess(tmp_path, monkeypatch):
    target = tmp_path / "item"
    target.write_text("x")
    calls = []

    class StatxCall:
        def __call__(self, dirfd, path, flags, mask, output):
            calls.append((dirfd, path, flags, mask))
            value = ctypes.cast(output, ctypes.POINTER(fast_inventory._Statx)).contents
            value.mask = fast_inventory.STATX_BASIC_STATS | fast_inventory.STATX_BTIME
            value.size, value.uid, value.gid = 9, 10, 11
            value.atime.tv_sec, value.mtime.tv_sec = 12, 13
            value.ctime.tv_sec, value.btime.tv_sec = 14, 15
            return 0

    class Library:
        statx = StatxCall()

    monkeypatch.setattr(fast_inventory.ctypes, "CDLL", lambda *_args, **_kwargs: Library())
    monkeypatch.setattr(fast_inventory, "run_command", lambda *_args, **_kwargs: pytest.fail("subprocess per file"))
    data = fast_inventory._stat_metadata(target)
    assert data == {"size": 9, "uid": 10, "gid": 11, "atime": 12, "mtime": 13,
                    "ctime": 14, "crtime": 15, "stat_method": "statx"}
    assert calls[0][2] & fast_inventory.AT_SYMLINK_NOFOLLOW


def test_statx_birth_time_mask_absent_keeps_crtime_none(tmp_path, monkeypatch):
    target = tmp_path / "item"
    target.write_text("x")

    class Call:
        def __call__(self, _dirfd, _path, _flags, _mask, output):
            value = ctypes.cast(output, ctypes.POINTER(fast_inventory._Statx)).contents
            value.mask = fast_inventory.STATX_BASIC_STATS
            value.size, value.uid, value.gid = 1, 2, 3
            value.atime.tv_sec = value.mtime.tv_sec = value.ctime.tv_sec = 4
            value.btime.tv_sec = 999999
            return 0

    class Library:
        statx = Call()

    monkeypatch.setattr(fast_inventory.ctypes, "CDLL", lambda *_args, **_kwargs: Library())
    assert fast_inventory._stat_metadata(target)["crtime"] is None


def test_statx_unavailable_falls_back_to_nofollow_os_stat(tmp_path, monkeypatch):
    target = tmp_path / "link"
    real = tmp_path / "real"
    real.write_text("target")
    target.symlink_to(real)

    class Library:
        pass

    monkeypatch.setattr(fast_inventory.ctypes, "CDLL", lambda *_args, **_kwargs: Library())
    data = fast_inventory._stat_metadata(target)
    assert data["crtime"] is None
    assert data["size"] == os.stat(target, follow_symlinks=False).st_size
    assert stat.S_ISLNK(os.stat(target, follow_symlinks=False).st_mode)


def test_readonly_inventory_verifies_child_and_mount_options(tmp_path, monkeypatch):
    target = tmp_path / "partition"
    mounted = tmp_path / "mounted"
    mounted.mkdir()
    calls = []
    monkeypatch.setattr(fast_inventory.os, "geteuid", lambda: 0)
    monkeypatch.setattr(fast_inventory.tempfile, "mkdtemp", lambda **_kwargs: str(mounted))
    monkeypatch.setattr(fast_inventory, "enforce_read_only", lambda device: calls.append(("ro", device)))

    def command(args, **_kwargs):
        calls.append(tuple(args))
        if args[0] == "findmnt":
            return subprocess.CompletedProcess(args, 0, json.dumps({"filesystems": [{"options": "ro,nosuid,nodev,noexec"}]}), "")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(fast_inventory, "run_command", command)
    monkeypatch.setattr(fast_inventory, "index_containers", lambda *_args: {})
    fast_inventory.readonly_mount_inventory(target, "001")
    assert calls[0] == ("ro", target)
    mount = next(call for call in calls if isinstance(call, tuple) and call[0] == "mount")
    assert mount[2] == "ro,nosuid,nodev,noexec"
    assert any(isinstance(call, tuple) and call[0] == "umount" for call in calls)


def test_failed_child_ro_verification_prevents_mount(tmp_path, monkeypatch):
    target = tmp_path / "partition"
    mounted = tmp_path / "mounted"
    mounted.mkdir()
    calls = []
    monkeypatch.setattr(fast_inventory.os, "geteuid", lambda: 0)
    monkeypatch.setattr(fast_inventory.tempfile, "mkdtemp", lambda **_kwargs: str(mounted))
    def reject(_device):
        raise fast_inventory.SafetyError("RO verification failed")
    monkeypatch.setattr(fast_inventory, "enforce_read_only", reject)
    monkeypatch.setattr(fast_inventory, "run_command", lambda args, **_kwargs: calls.append(args))
    with pytest.raises(fast_inventory.SafetyError):
        fast_inventory.readonly_mount_inventory(target, "001")
    assert not any(args and args[0] == "mount" for args in calls)
