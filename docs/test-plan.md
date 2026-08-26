# Test plan

## Local unit tests

- extension normalization and category mapping
- case-insensitive full-path keyword matching
- deterministic counts, byte totals, and top-five files
- parsing dynamic `mmls` offsets
- parsing `fls` bodyfile records

## Synthetic medium

1. Identify the authorized SanDisk by transport, model, serial, and capacity.
2. Confirm no system disk can match the selected target.
3. Partition and format only after a fresh `lsblk` review.
4. Mount the writable fixture volume temporarily and run `create_test_media.py`.
5. Unmount all partitions.
6. Set and verify read-only state.
7. Run the CLI scanner without a filesystem mount.
8. Compare file count, directory count, extensions, category counts/bytes, keyword counts, and top-five files with `tests/fixtures/expected.json`.
9. Record runtime and retain raw command output.

Any mismatch is a failed validation until explained and documented. Differences caused by filesystem-generated metadata must be explicitly filtered or added to the expected model, not silently ignored.
