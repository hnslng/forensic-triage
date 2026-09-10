"""Called by the updater before switching away from the previous release."""
import sys
from pathlib import Path

from forensic_triage.settings import prepare_profiles

source = Path(sys.argv[1])
root = Path(sys.argv[2])
prepare_profiles(root, source)
