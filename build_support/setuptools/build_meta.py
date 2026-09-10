"""Minimal PEP 517/660 backend used when an offline venv has no setuptools.

The module deliberately uses setuptools' established backend import name so an
Alpha-45 device sees an unchanged dependency fingerprint.  ``backend-path``
limits this shim to this repository.  It builds only the small, pure-Python
TRIAGE//BOX project and is not a general setuptools replacement.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
import tomllib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _project() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def _distribution_name() -> str:
    return str(_project()["name"]).replace("-", "_")


def _dist_info() -> str:
    return f"{_distribution_name()}-{_project()['version']}.dist-info"


def _metadata() -> bytes:
    project = _project()
    lines = [
        "Metadata-Version: 2.3",
        f"Name: {project['name']}",
        f"Version: {project['version']}",
        f"Summary: {project.get('description', '')}",
        f"Requires-Python: {project.get('requires-python', '>=3.11')}",
    ]
    lines.extend(f"Requires-Dist: {item}" for item in project.get("dependencies", []))
    for extra, requirements in project.get("optional-dependencies", {}).items():
        lines.append(f"Provides-Extra: {extra}")
        lines.extend(f'Requires-Dist: {item}; extra == "{extra}"' for item in requirements)
    return ("\n".join(lines) + "\n\n").encode()


def _wheel_metadata() -> bytes:
    return b"Wheel-Version: 1.0\nGenerator: triagebox-offline-bootstrap\nRoot-Is-Purelib: true\nTag: py3-none-any\n\n"


def _entry_points() -> bytes:
    scripts = _project().get("scripts", {})
    body = "[console_scripts]\n" + "".join(f"{name} = {target}\n" for name, target in scripts.items())
    return body.encode()


def _record(files: dict[str, bytes]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    for name, raw in sorted(files.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
        writer.writerow((name, f"sha256={digest}", len(raw)))
    writer.writerow((f"{_dist_info()}/RECORD", "", ""))
    return stream.getvalue().encode()


def _base_files() -> dict[str, bytes]:
    prefix = _dist_info()
    return {
        f"{prefix}/METADATA": _metadata(),
        f"{prefix}/WHEEL": _wheel_metadata(),
        f"{prefix}/entry_points.txt": _entry_points(),
        f"{prefix}/top_level.txt": b"forensic_triage\n",
    }


def _write_wheel(wheel_directory: str, files: dict[str, bytes]) -> str:
    files[f"{_dist_info()}/RECORD"] = _record(files)
    filename = f"{_distribution_name()}-{_project()['version']}-py3-none-any.whl"
    destination = Path(wheel_directory) / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as wheel:
        for name, raw in sorted(files.items()):
            wheel.writestr(name, raw)
    return filename


def _prepare_metadata(metadata_directory: str) -> str:
    destination = Path(metadata_directory) / _dist_info()
    destination.mkdir(parents=True, exist_ok=True)
    for name, raw in _base_files().items():
        (destination / Path(name).name).write_bytes(raw)
    return destination.name


def _supported_features() -> list[str]:
    return ["build_editable"]


def get_requires_for_build_wheel(config_settings=None) -> list[str]:
    return []


def get_requires_for_build_editable(config_settings=None) -> list[str]:
    return []


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None) -> str:
    return _prepare_metadata(metadata_directory)


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None) -> str:
    return _prepare_metadata(metadata_directory)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None) -> str:
    files = _base_files()
    files[f"__editable__.{_distribution_name()}-{_project()['version']}.pth"] = \
        f"{(ROOT / 'src').resolve()}{os.linesep}".encode()
    return _write_wheel(wheel_directory, files)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None) -> str:
    files = _base_files()
    for source in sorted((ROOT / "src" / "forensic_triage").rglob("*.py")):
        relative = source.relative_to(ROOT / "src").as_posix()
        files[relative] = source.read_bytes()
    return _write_wheel(wheel_directory, files)
