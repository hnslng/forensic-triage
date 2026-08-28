"""Bounded external commands used around potentially unreliable media."""

from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Sequence
from typing import Any


DEFAULT_COMMAND_TIMEOUT_SECONDS = 15.0


def command_timeout_seconds() -> float:
    """Return the configured per-command deadline with a safe fallback."""
    raw = os.environ.get("FORENSIC_TRIAGE_COMMAND_TIMEOUT_SECONDS", "")
    try:
        value = float(raw) if raw else DEFAULT_COMMAND_TIMEOUT_SECONDS
    except ValueError:
        return DEFAULT_COMMAND_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_COMMAND_TIMEOUT_SECONDS


def run_command(
    args: Sequence[str],
    *,
    check: bool = True,
    text: bool = True,
    capture_output: bool = False,
    timeout: float | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Run a command without allowing a device operation to wait forever."""
    deadline = timeout if timeout is not None else command_timeout_seconds()
    process = subprocess.Popen(
        args,
        text=text,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE if capture_output else None,
        start_new_session=True,
        **kwargs,
    )
    try:
        stdout, stderr = process.communicate(timeout=deadline)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            stdout = exc.output
            stderr = exc.stderr
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        raise subprocess.TimeoutExpired(args, deadline, output=stdout, stderr=stderr) from exc
    completed = subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
    if check and process.returncode:
        raise subprocess.CalledProcessError(process.returncode, args, output=stdout, stderr=stderr)
    return completed
