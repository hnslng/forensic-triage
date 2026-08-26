# Forensic Triage Box

Fast metadata-only inventory of removable media with a read-only mount path and an optional mount-free The Sleuth Kit path. Version 0.1 does not inspect file contents and does not make relevance or seizure decisions.

## Safety boundary

The scanner accepts only a whole block device reported by `lsblk` as USB. It refuses `/dev/sda`, refuses mounted targets or child partitions, sets the whole device read-only with `blockdev --setro`, and verifies `blockdev --getro == 1` before analysis.

The default `fast` mode uses `mmls` and `fsstat`, then temporarily mounts each supported partition with `ro,nosuid,nodev,noexec` while the block device itself remains kernel read-only. It reads directory metadata only and immediately unmounts. `--mode tsk` performs the slower mount-free `fls` walk.

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

The default mode is `fast`. For the mount-free TSK inventory, add `--mode tsk`.

Never assume a device name. Immediately before a scan, identify the target with:

```bash
lsblk -o NAME,TRAN,SIZE,MODEL,SERIAL,RO,MOUNTPOINTS
```

Each scan produces `device.json`, `partitions.json`, `files.csv`, `summary.json`, `hits.json`, `scan.log`, and raw tool output under a timestamped result directory. When `--expected` is supplied, `validation.json` records every mismatch and the command fails until the scan matches the fixture.

## Current status

- Local package and CLI orchestration implemented and deployed to the Debian 13 VM.
- Extension classification, keyword matching, statistics, fast inventory, and TSK parsers covered by 13 unit tests on macOS and Linux.
- Synthetic 960-file fixture generator implemented.
- Physical SanDisk exFAT scans passed the expected manifest with no mismatches. The final fast scan took 0.732 seconds; see `docs/validation-2026-08-26.md`.
- A local operator dashboard is available. It detects one unmounted USB disk, starts the guarded fast scan, and renders categories, keyword hits, largest files, and scan metadata.

## Operator dashboard

Run the interface inside the VM from the repository checkout:

```bash
sudo forensic-triage-web
```

It binds to `127.0.0.1:8787` by default. Keep it private and reach it from the Mac through an SSH tunnel:

```bash
ssh -L 8787:127.0.0.1:8787 triage@10.0.1.105
```

Then open `http://127.0.0.1:8787` on the Mac. The server refuses to start a scan unless exactly one unmounted whole USB disk is available. The existing scanner performs the final identity, mount-state, transport, and read-only checks.

The supplied `deploy/forensic-triage-web.service` keeps the private VM service running after boot. It intentionally listens only on VM localhost; do not expose it directly to the LAN or internet.

Every dashboard scan receives an automatic neutral sighting number and is stored in a durable local case archive with a searchable SQLite index, complete `files.csv` inventory, device and partition metadata, keyword hits, scan log, media register, human-readable case report, append-only decision events, and a SHA-256 manifest. An official evidence number is required only when the operator selects the medium for securing. See `docs/case-archive.md`. `casefiles/` is excluded from Git and must never be pushed to the source repository.
