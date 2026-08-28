"""Single-scan subprocess entry point.

The web service starts one of these processes per medium. Keeping all media I/O
inside this process lets the web service time it out without becoming the stuck
reader itself.
"""

from __future__ import annotations

import json
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

from .scanner import scan


def execute(request: dict[str, Any]) -> Path:
    return scan(
        Path(request["device"]),
        Path(request["profile_path"]),
        str(request["evidence"]),
        Path(request["results_root"]),
        mode=str(request.get("mode", "fast")),
        keywords=list(request.get("keywords") or []),
        profile_sources=list(request.get("profile_sources") or []),
    )


def main() -> None:
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise ValueError("Ungültiger Scanauftrag.")
        result_dir = execute(request)
        print(json.dumps({"ok": True, "result_dir": str(result_dir)}), flush=True)
    except subprocess.TimeoutExpired as exc:
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({
            "ok": False,
            "timed_out": True,
            "error": f"Gerätebefehl überschritt sein Zeitlimit von {exc.timeout:g} Sekunden.",
        }), flush=True)
        raise SystemExit(2) from exc
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({"ok": False, "error": str(exc)}), flush=True)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
