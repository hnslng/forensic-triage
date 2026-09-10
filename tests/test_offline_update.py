import subprocess
import zipfile
from pathlib import Path

import pytest

from forensic_triage.offline_update import REQUIRED_FILES, build_bundle, prepare_bundle, tag_to_pep440


def make_signing_key(tmp_path: Path) -> tuple[Path, Path]:
    key = tmp_path / "signing"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    public = key.with_suffix(".pub").read_text().split()
    allowed = tmp_path / "allowed-signers"
    allowed.write_text(f"triagebox-updates {public[0]} {public[1]}\n")
    return key, allowed


def make_release(tmp_path: Path, allowed_signers: Path, version: str = "0.2.0a45") -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    for name in REQUIRED_FILES:
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n")
    (repository / "pyproject.toml").write_text(
        '[build-system]\nrequires=["setuptools>=75"]\nbuild-backend="setuptools.build_meta"\n'
        f'[project]\nname="forensic-triage"\nversion="{version}"\ndependencies=["PyYAML>=6.0"]\n'
        '[project.optional-dependencies]\ntest=["pytest>=8.0"]\n'
    )
    (repository / "scripts/update_triagebox.sh").chmod(0o755)
    (repository / "deploy/offline-update-allowed-signers").write_bytes(allowed_signers.read_bytes())
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-qm", "release"], check=True)
    subprocess.run(["git", "-C", str(repository), "tag", "v0.2.0-alpha.45"], check=True)
    return repository


def test_signed_bundle_is_verified_and_staged_atomically(tmp_path):
    key, allowed = make_signing_key(tmp_path)
    repository = make_release(tmp_path, allowed)
    package = tmp_path / "release.tbu"
    manifest = build_bundle(repository, "v0.2.0-alpha.45", package, key)

    version = prepare_bundle(package, tmp_path / "releases", allowed, "0.2.0a44", repository)

    release = tmp_path / "releases" / version
    assert version == "v0.2.0-alpha.45"
    assert manifest["python_version"] == "0.2.0a45"
    assert (release / ".triagebox-release").read_text().strip() == version
    assert (release / "scripts/update_triagebox.sh").stat().st_mode & 0o111
    assert not list((tmp_path / "releases").glob(".v0.2.0-alpha.45-*"))


def test_previously_staged_bundle_is_rechecked_before_retry(tmp_path):
    key, allowed = make_signing_key(tmp_path)
    repository = make_release(tmp_path, allowed)
    package = tmp_path / "release.tbu"
    build_bundle(repository, "v0.2.0-alpha.45", package, key)
    releases = tmp_path / "releases"
    version = prepare_bundle(package, releases, allowed, "0.2.0a44", repository)
    (releases / version / "web/index.html").write_text("manipuliert\n")

    with pytest.raises(ValueError, match="anderem oder unvollständigem Inhalt"):
        prepare_bundle(package, releases, allowed, "0.2.0a44", repository)


def test_tampered_bundle_is_rejected_before_extraction(tmp_path):
    key, allowed = make_signing_key(tmp_path)
    repository = make_release(tmp_path, allowed)
    package = tmp_path / "release.tbu"
    build_bundle(repository, "v0.2.0-alpha.45", package, key)
    tampered = tmp_path / "tampered.tbu"
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            raw = source.read(info)
            if info.filename == "manifest.json":
                raw = raw.replace(b'"commit":"', b'"commit":"0')
            target.writestr(info, raw)

    with pytest.raises(ValueError, match="SIGNATUR"):
        prepare_bundle(tampered, tmp_path / "releases", allowed, "0.2.0a44", repository)
    assert not (tmp_path / "releases").exists()


def test_offline_bundle_rejects_same_version_and_dependency_changes(tmp_path):
    key, allowed = make_signing_key(tmp_path)
    repository = make_release(tmp_path, allowed)
    package = tmp_path / "release.tbu"
    build_bundle(repository, "v0.2.0-alpha.45", package, key)
    with pytest.raises(ValueError, match="nicht neuer"):
        prepare_bundle(package, tmp_path / "same", allowed, "0.2.0a45", repository)

    current = tmp_path / "current"
    current.mkdir()
    (current / "pyproject.toml").write_text(
        '[build-system]\nrequires=["setuptools>=75"]\nbuild-backend="setuptools.build_meta"\n'
        '[project]\nname="forensic-triage"\nversion="0.2.0a44"\ndependencies=["NEW>=1"]\n'
        '[project.optional-dependencies]\ntest=["pytest>=8.0"]\n'
    )
    with pytest.raises(ValueError, match="Abhängigkeiten"):
        prepare_bundle(package, tmp_path / "changed", allowed, "0.2.0a44", current)


@pytest.mark.parametrize("tag, expected", [
    ("v1.2.3-alpha.4", "1.2.3a4"), ("v1.2.3-beta.4", "1.2.3b4"),
    ("v1.2.3-rc.4", "1.2.3rc4"), ("v1.2.3", "1.2.3"),
])
def test_release_tag_conversion(tag, expected):
    assert tag_to_pep440(tag) == expected
