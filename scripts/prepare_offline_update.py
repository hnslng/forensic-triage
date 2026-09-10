#!/usr/bin/env python3
"""Verify and stage an uploaded TRIAGE//BOX offline update."""

import argparse
from pathlib import Path

from forensic_triage.offline_update import prepare_bundle


parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
parser.add_argument("releases_root", type=Path)
parser.add_argument("allowed_signers", type=Path)
parser.add_argument("current_version")
parser.add_argument("current_root", type=Path)
args = parser.parse_args()
print(prepare_bundle(args.package, args.releases_root, args.allowed_signers, args.current_version, args.current_root))
