# Architecture

The CLI has one orchestration path and two inventory modes. `device` enforces safety invariants; `partitions` parses dynamic offsets from `mmls`; `fast_inventory` maps offsets to partition devices and performs a temporary verified read-only mount; `filesystem` parses `fsstat` and bodyfile-format `fls` for TSK mode; `classifier`, `keywords`, and `statistics` produce objective derived metadata; `reporting` serializes the result.

The raw tool outputs remain beside normalized results for auditability. A future dashboard must consume `summary.json`, `hits.json`, and `files.csv`; it must not introduce a parallel scanning or classification implementation.

Version 0.1 reads names, paths, extensions, sizes, and filesystem-provided timestamps only. It does not open or interpret file content. The default `fast` inventory traverses active directory entries on a short-lived read-only mount while the underlying device remains read-only. `--mode tsk` uses `fls -u`, excludes TSK virtual entries, and remains available when a mount-free analysis is required. Recovery-oriented enumeration is outside the version 1 scope.
