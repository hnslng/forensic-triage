# Architecture

The CLI has one orchestration path. `device` enforces safety invariants; `partitions` parses dynamic offsets from `mmls`; `filesystem` parses `fsstat` and bodyfile-format `fls`; `classifier`, `keywords`, and `statistics` produce objective derived metadata; `reporting` serializes the result.

The raw tool outputs remain beside normalized results for auditability. A future dashboard must consume `summary.json`, `hits.json`, and `files.csv`; it must not introduce a parallel scanning or classification implementation.

Version 0.1 reads names, paths, extensions, sizes, and filesystem-provided timestamps only. It does not open or interpret file content. The default inventory uses `fls -u` and excludes deleted entries; recovery-oriented enumeration is outside the version 1 scope.
