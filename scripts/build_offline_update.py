#!/usr/bin/env python3
"""Create a signed .tbu file from a committed TRIAGE//BOX release tag."""

import argparse
import os
from pathlib import Path

from forensic_triage.offline_update import build_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Signiertes TRIAGE//BOX-Offline-Update erstellen")
    parser.add_argument("ref", help="freigegebener Git-Tag, z. B. v0.2.0-alpha.46")
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--key", type=Path, default=Path(os.environ.get(
        "TRIAGEBOX_UPDATE_SIGNING_KEY", "~/.config/triagebox/offline-update-signing",
    )).expanduser())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.repository / "dist" / f"triagebox-{args.ref}.tbu"
    manifest = build_bundle(args.repository, args.ref, output, args.key)
    print(f"Offline-Update: {output.resolve()}")
    print(f"Version: {manifest['version']}")
    print(f"Commit: {manifest['commit']}")


if __name__ == "__main__":
    main()
