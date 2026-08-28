"""Process isolation and a hard wall-clock deadline for one media scan."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any


class ScanProcessError(RuntimeError):
    """A scanner worker failed without taking down the web service."""


class ScanTimeoutError(ScanProcessError):
    """A scanner worker exceeded the configured overall deadline."""


def worker_command() -> list[str]:
    """Use a private mount namespace on Linux so worker mounts cannot leak."""
    base = [sys.executable, "-m", "forensic_triage.scan_worker"]
    unshare = shutil.which("unshare")
    if sys.platform.startswith("linux") and unshare:
        return [unshare, "--mount", "--propagation", "private", "--", *base]
    return base


def _stop_process_group(process: subprocess.Popen[str], grace_seconds: float = 1.0) -> bool:
    """Best-effort stop; a kernel D-state may only end after hardware returns."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    try:
        process.communicate(timeout=grace_seconds)
        return True
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return True
    try:
        process.communicate(timeout=grace_seconds)
        return True
    except subprocess.TimeoutExpired:
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        return False


def run_isolated_scan(
    request: dict[str, Any],
    *,
    timeout_seconds: float,
    command_timeout_seconds: float,
) -> Path:
    """Run one complete scan outside the web process and enforce its deadline."""
    environment = os.environ.copy()
    environment["FORENSIC_TRIAGE_COMMAND_TIMEOUT_SECONDS"] = str(command_timeout_seconds)
    process = subprocess.Popen(
        worker_command(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env=environment,
    )
    try:
        stdout, stderr = process.communicate(
            json.dumps(request, ensure_ascii=False),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stopped = _stop_process_group(process)
        suffix = "" if stopped else " Der Kernel wartet weiterhin auf das Medium."
        raise ScanTimeoutError(
            f"Zeitlimit von {timeout_seconds:g} Sekunden überschritten.{suffix} "
            "Medium abziehen, neu verbinden und erst dann erneut versuchen."
        ) from exc

    response: dict[str, Any] = {}
    for line in reversed(stdout.splitlines()):
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            response = candidate
            break
    if response.get("timed_out"):
        raise ScanTimeoutError(
            f"{response.get('error')} Medium abziehen, neu verbinden und erst dann erneut versuchen."
        )
    if process.returncode != 0 or not response.get("ok"):
        detail = str(response.get("error") or stderr.strip() or "Scanner-Worker fehlgeschlagen.")
        raise ScanProcessError(detail)
    result_dir = Path(str(response.get("result_dir", "")))
    if not result_dir.is_dir():
        raise ScanProcessError("Scanner-Worker meldete kein vollständiges Ergebnisverzeichnis.")
    return result_dir
