import subprocess
import sys
import time

import pytest

from forensic_triage.commands import run_command


def test_command_timeout_returns_control_to_caller() -> None:
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        run_command([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.05)
    assert time.monotonic() - started < 2
