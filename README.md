# Forensic Triage Box

Metadata-only inventory of removable media using The Sleuth Kit. Version 0.1 is a CLI prototype; it does not inspect file contents and does not make relevance or seizure decisions.

## Safety boundary

The scanner accepts only a whole block device reported by `lsblk` as USB. It refuses `/dev/sda`, refuses mounted targets or child partitions, sets the whole device read-only with `blockdev --setro`, and verifies `blockdev --getro == 1` before invoking `mmls`, `fsstat`, or `fls`.

Software read-only is suitable for this prototype but is not a substitute for a validated hardware write blocker in evidentiary use. Run only against media whose identity and authorization have been established independently.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
```

Create a synthetic fixture on an already mounted, empty test volume:

```bash
python scripts/create_test_media.py --target /path/to/TRIAGE_TEST-volume
```

The generator refuses to overwrite an existing `TRIAGE_TESTDATA` directory. Its expected manifest is written to `tests/fixtures/expected.json`, outside the test medium.

## Scan

The scan must run as root because Linux requires elevated privileges to change block-device read-only state:

```bash
sudo forensic-triage scan /dev/sdX \
  --profile profiles/default.yaml \
  --evidence BM-001 \
  --expected tests/fixtures/expected.json
```

Never assume a device name. Immediately before a scan, identify the target with:

```bash
lsblk -o NAME,TRAN,SIZE,MODEL,SERIAL,RO,MOUNTPOINTS
```

Each scan produces `device.json`, `partitions.json`, `files.csv`, `summary.json`, `hits.json`, `scan.log`, and raw `mmls`/`fsstat`/`fls` output under a timestamped result directory. When `--expected` is supplied, `validation.json` records every mismatch and the command fails until the scan matches the fixture.

## Current status

- Local package and CLI orchestration implemented and deployed to the Debian 13 VM.
- Extension classification, keyword matching, statistics, and TSK parsers covered by 11 unit tests on macOS and Linux.
- Synthetic 960-file fixture generator implemented.
- Physical SanDisk exFAT scan passed the expected manifest with no mismatches; see `docs/validation-2026-08-26.md`.
- Dashboard is now eligible as the next phase because the CLI scanner matches the fixture manifest.
