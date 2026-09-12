"""Build and verify signed, bounded TRIAGE//BOX offline update bundles."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import tomllib
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


FORMAT = "triagebox-offline-update-v1"
SIGNER_IDENTITY = "triagebox-updates"
SIGNATURE_NAMESPACE = "triagebox-update"
TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?$")
PEP_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?$")
REQUIRED_FILES = {
    "build_support/setuptools/__init__.py",
    "build_support/setuptools/build_meta.py",
    "pyproject.toml",
    "src/forensic_triage/__init__.py",
    "scripts/update_triagebox.sh",
    "deploy/forensic-triage-web.service.in",
    "deploy/forensic-triage-update@.service.in",
    "deploy/forensic-triage-update-check.timer",
    "deploy/forensic-triage-nginx.conf.in",
    "deploy/forensic-triage-journald.conf",
    "deploy/offline-update-allowed-signers",
    "web/index.html",
}
MAX_FILES = 5000
MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_MANIFEST_BYTES = 2 * 1024 * 1024


def _safe_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"Unsicherer Paketpfad: {value[:100]}")
    if path.parts[0] in {".git", ".venv", "casefiles", "results", "settings", "dist"}:
        raise ValueError(f"Nicht erlaubter Releasepfad: {value[:100]}")
    return path


def tag_to_pep440(tag: str) -> str:
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise ValueError("Ungültige Release-Version im Offline-Paket.")
    major, minor, patch, stage, number = match.groups()
    suffix = {"alpha": "a", "beta": "b", "rc": "rc"}.get(stage or "", "")
    return f"{major}.{minor}.{patch}{suffix}{number or ''}"


def _version_order(value: str) -> tuple[int, int, int, int, int]:
    match = PEP_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"Installierte Version ist nicht vergleichbar: {value}")
    major, minor, patch, stage, number = match.groups()
    stage_order = {"a": 0, "b": 1, "rc": 2, None: 3}[stage]
    return int(major), int(minor), int(patch), stage_order, int(number or 0)


def compare_release_to_installed(tag: str, installed_version: str) -> int:
    """Return -1, 0 or 1 when *tag* is older, equal or newer than installed."""
    candidate = _version_order(tag_to_pep440(tag))
    installed = _version_order(installed_version)
    return (candidate > installed) - (candidate < installed)


def dependency_fingerprint(raw_pyproject: bytes) -> str:
    data = tomllib.loads(raw_pyproject.decode("utf-8"))
    relevant = {
        "build": {
            "requires": data.get("build-system", {}).get("requires", []),
            "backend": data.get("build-system", {}).get("build-backend", ""),
        },
        "runtime": data.get("project", {}).get("dependencies", []),
        "test": data.get("project", {}).get("optional-dependencies", {}).get("test", []),
    }
    canonical = json.dumps(relevant, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def _canonical_manifest(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _stored_payload_matches(destination: Path, expected: dict[str, dict[str, Any]]) -> bool:
    """Confirm a previously staged signed payload before reusing it after a retry."""
    for path, record in expected.items():
        target = destination.joinpath(*PurePosixPath(path).parts)
        if not target.is_file() or target.is_symlink() or target.stat().st_size != record["size"]:
            return False
        hasher = hashlib.sha256()
        with target.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                hasher.update(chunk)
        if hasher.hexdigest() != record["sha256"]:
            return False
    return True


def _sign(raw: bytes, private_key: Path) -> bytes:
    with tempfile.TemporaryDirectory(prefix="triagebox-sign-") as temporary:
        source = Path(temporary) / "manifest.json"
        source.write_bytes(raw)
        completed = subprocess.run(
            ["ssh-keygen", "-Y", "sign", "-f", str(private_key), "-n", SIGNATURE_NAMESPACE, str(source)],
            check=False, capture_output=True, text=True, timeout=15,
        )
        if completed.returncode != 0:
            raise ValueError(f"Updatepaket konnte nicht signiert werden: {completed.stderr.strip()}")
        return source.with_suffix(".json.sig").read_bytes()


def _verify_signature(raw: bytes, signature: bytes, allowed_signers: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="triagebox-verify-") as temporary:
        signature_path = Path(temporary) / "manifest.sig"
        signature_path.write_bytes(signature)
        completed = subprocess.run(
            [
                "ssh-keygen", "-Y", "verify", "-f", str(allowed_signers),
                "-I", SIGNER_IDENTITY, "-n", SIGNATURE_NAMESPACE, "-s", str(signature_path),
            ],
            input=raw, check=False, capture_output=True, timeout=15,
        )
        if completed.returncode != 0:
            raise ValueError("SIGNATUR DES OFFLINE-UPDATES IST UNGÜLTIG")


def build_bundle(repository: Path, ref: str, output: Path, private_key: Path) -> dict[str, Any]:
    """Create a signed bundle exclusively from the committed Git tree at *ref*."""
    commit = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", f"{ref}^{{commit}}"],
        check=True, capture_output=True, text=True, timeout=15,
    ).stdout.strip()
    archive = subprocess.run(
        ["git", "-C", str(repository), "archive", "--format=tar", ref],
        check=True, capture_output=True, timeout=60,
    ).stdout
    files: dict[str, tuple[bytes, int]] = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source:
        for member in source.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"Nicht regulärer Git-Eintrag im Paket: {member.name}")
            path = str(_safe_path(member.name))
            stream = source.extractfile(member)
            if stream is None:
                raise ValueError(f"Git-Eintrag nicht lesbar: {path}")
            files[path] = (stream.read(), member.mode & 0o777)
    if not REQUIRED_FILES.issubset(files):
        missing = ", ".join(sorted(REQUIRED_FILES - files.keys()))
        raise ValueError(f"Release ist unvollständig: {missing}")
    if len(files) > MAX_FILES or sum(len(raw) for raw, _ in files.values()) > MAX_UNCOMPRESSED_BYTES:
        raise ValueError("Release überschreitet die Paketgrenzen.")
    raw_pyproject = files["pyproject.toml"][0]
    project_version = str(tomllib.loads(raw_pyproject.decode("utf-8")).get("project", {}).get("version", ""))
    if project_version != tag_to_pep440(ref):
        raise ValueError(f"Git-Tag {ref} und Paketversion {project_version or '—'} stimmen nicht überein.")
    manifest = {
        "format": FORMAT,
        "version": ref,
        "python_version": project_version,
        "commit": commit,
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "dependency_sha256": dependency_fingerprint(raw_pyproject),
        "files": [
            {"path": path, "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "mode": mode}
            for path, (raw, mode) in sorted(files.items())
        ],
    }
    manifest_raw = _canonical_manifest(manifest)
    signature = _sign(manifest_raw, private_key)
    with tempfile.TemporaryDirectory(prefix="triagebox-build-verify-") as temporary:
        allowed_signers = Path(temporary) / "allowed-signers"
        allowed_signers.write_bytes(files["deploy/offline-update-allowed-signers"][0])
        _verify_signature(manifest_raw, signature, allowed_signers)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
            target.writestr("manifest.json", manifest_raw)
            target.writestr("manifest.sig", signature)
            for path, (raw, mode) in sorted(files.items()):
                info = zipfile.ZipInfo(f"payload/{path}")
                info.date_time = (2026, 1, 1, 0, 0, 0)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | mode) << 16
                target.writestr(info, raw, compresslevel=9)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


def prepare_bundle(
    package: Path,
    releases_root: Path,
    allowed_signers: Path,
    current_version: str,
    current_root: Path,
) -> str:
    """Verify and atomically stage one newer, dependency-compatible release."""
    if not package.is_file() or not allowed_signers.is_file():
        raise ValueError("Offline-Paket oder öffentlicher Prüfschlüssel fehlt.")
    with zipfile.ZipFile(package, "r") as source:
        infos = source.infolist()
        if len(infos) > MAX_FILES + 2:
            raise ValueError("Offline-Paket enthält zu viele Einträge.")
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or "manifest.json" not in names or "manifest.sig" not in names:
            raise ValueError("Offline-Paket hat eine ungültige Struktur.")
        if source.getinfo("manifest.json").file_size > MAX_MANIFEST_BYTES or \
           source.getinfo("manifest.sig").file_size > 64 * 1024:
            raise ValueError("Offline-Paket enthält übergroße Prüfdaten.")
        manifest_raw = source.read("manifest.json")
        signature = source.read("manifest.sig")
        _verify_signature(manifest_raw, signature, allowed_signers)
        manifest = json.loads(manifest_raw)
        if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
            raise ValueError("Offline-Paketformat wird nicht unterstützt.")
        version = str(manifest.get("version", ""))
        python_version = str(manifest.get("python_version", ""))
        if tag_to_pep440(version) != python_version:
            raise ValueError("Versionsangaben im Offline-Paket stimmen nicht überein.")
        if _version_order(python_version) <= _version_order(current_version):
            raise ValueError("Offline-Update ist nicht neuer als die installierte Version.")
        if manifest.get("dependency_sha256") != dependency_fingerprint((current_root / "pyproject.toml").read_bytes()):
            raise ValueError("Dieses Update ändert Abhängigkeiten und benötigt deshalb den Online-Updater.")
        records = manifest.get("files")
        if not isinstance(records, list) or not 1 <= len(records) <= MAX_FILES:
            raise ValueError("Ungültige Dateiliste im Offline-Paket.")
        expected: dict[str, dict[str, Any]] = {}
        total = 0
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Ungültiger Dateieintrag im Offline-Paket.")
            path = str(_safe_path(str(record.get("path", ""))))
            size = record.get("size")
            mode = record.get("mode")
            digest = record.get("sha256")
            if path in expected or type(size) is not int or size < 0 or type(mode) is not int or mode & ~0o777:
                raise ValueError("Ungültige Dateimetadaten im Offline-Paket.")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("Ungültige Datei-Prüfsumme im Offline-Paket.")
            total += size
            expected[path] = record
        if total > MAX_UNCOMPRESSED_BYTES or not REQUIRED_FILES.issubset(expected):
            raise ValueError("Offline-Paket ist zu groß oder unvollständig.")
        payload_names = {f"payload/{path}" for path in expected}
        if set(names) != {"manifest.json", "manifest.sig", *payload_names}:
            raise ValueError("Offline-Paket enthält nicht freigegebene Dateien.")

        releases_root.mkdir(parents=True, exist_ok=True, mode=0o755)
        destination = releases_root / version
        manifest_digest = hashlib.sha256(manifest_raw).hexdigest()
        marker_name = ".triagebox-offline-manifest.json"
        if destination.exists():
            marker = destination / marker_name
            if marker.is_file() and \
               hashlib.sha256(marker.read_bytes()).hexdigest() == manifest_digest and \
               _stored_payload_matches(destination, expected):
                return version
            raise ValueError("Release-Ziel existiert bereits mit anderem oder unvollständigem Inhalt.")
        staging = Path(tempfile.mkdtemp(prefix=f".{version}-", dir=releases_root))
        try:
            for path, record in expected.items():
                info = source.getinfo(f"payload/{path}")
                stored_mode = (info.external_attr >> 16) & 0o170000
                if stored_mode not in {0, stat.S_IFREG} or info.file_size != record["size"]:
                    raise ValueError("Paketdatei ist kein regulärer freigegebener Eintrag.")
                target = staging.joinpath(*PurePosixPath(path).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                hasher = hashlib.sha256()
                written = 0
                with source.open(info, "r") as incoming, target.open("xb") as outgoing:
                    while chunk := incoming.read(1024 * 1024):
                        written += len(chunk)
                        if written > record["size"]:
                            raise ValueError("Paketdatei überschreitet ihre freigegebene Größe.")
                        hasher.update(chunk)
                        outgoing.write(chunk)
                    outgoing.flush()
                    os.fsync(outgoing.fileno())
                if written != record["size"] or hasher.hexdigest() != record["sha256"]:
                    raise ValueError("Prüfsumme einer Paketdatei stimmt nicht.")
                target.chmod(record["mode"])
            (staging / marker_name).write_bytes(manifest_raw)
            (staging / ".triagebox-release").write_text(f"{version}\n", encoding="ascii")
            os.replace(staging, destination)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    return version
