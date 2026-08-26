# Physical-media validation — 2026-08-26

## Environment

- Debian 13 VM, kernel `6.12.105+deb13-amd64`
- Python 3.13.5
- The Sleuth Kit 4.12.1
- SanDisk USB, 123,060,879,360 bytes
- GPT with one exFAT partition labeled `TRIAGE_TEST`

The authorized test medium was freshly partitioned and quick-formatted after repeated checks of USB transport, model, capacity, mountpoints, and separation from the `/dev/sda` system disk. The synthetic generator created 960 files. The medium was then unmounted and kernel read-only state was set and verified before analysis.

## Result

- validation: passed, zero mismatches
- files: 960
- directories: 18
- logical file bytes: 553,421,052
- keyword matches: 60
- scan duration: 1,921.431 seconds (32:01.431)
- read-only state after scan: `1`

The result bundle is retained locally under the Git-ignored `results/2026-08-26T093319Z_BM-001/` directory.

## Finding during validation

The first run included approximately 149,000 deleted entries recoverable from prior use of the quick-formatted exFAT medium. This was outside the version 1 definition of the currently present inventory. The scanner was changed to request undeleted entries with `fls -u` and to defensively exclude deleted, TSK-virtual, orphan, volume-label, and exFAT bookkeeping entries. Reprocessing the captured raw output and the final end-to-end scan both matched the expected manifest exactly.

On this 114.6 GiB exFAT medium, recursive `fls` inventory reads approximately the full volume regardless of the small live file count. Capacity and device throughput therefore dominate scan duration.

## Fast-mode validation

The same physical medium was subsequently scanned using the default fast mode. The whole block device was already read-only, the partition was temporarily mounted with `ro,nosuid,nodev,noexec`, mount options were programmatically verified, and cleanup unmounted it before returning.

- validation: passed, zero mismatches
- files: 960
- directories: 18
- logical file bytes: 553,421,052
- keyword matches: 60
- scanner-reported duration: 0.732 seconds
- read-only state after scan: `1`
- mountpoint after scan: none

The fast result bundle is retained locally under the Git-ignored `results/2026-08-26T122801Z_BM-FAST-001/` directory. TSK mode remains available with `--mode tsk` for a mount-free deep inventory.
