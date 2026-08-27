"""Command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .scanner import scan


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="forensic-triage")
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    scan_parser = commands.add_parser("scan", help="inventory a whole removable block device")
    scan_parser.add_argument("device", type=Path)
    scan_parser.add_argument("--profile", type=Path, required=True)
    scan_parser.add_argument("--evidence", required=True)
    scan_parser.add_argument("--results", type=Path, default=Path("results"))
    scan_parser.add_argument("--expected", type=Path, help="fixture manifest to validate against")
    scan_parser.add_argument(
        "--mode", choices=("fast", "tsk"), default="fast",
        help="fast read-only mount inventory (default) or mount-free TSK directory walk",
    )
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "scan":
        result = scan(args.device, args.profile, args.evidence, args.results, args.expected, args.mode)
        print(result)


if __name__ == "__main__":
    main()
