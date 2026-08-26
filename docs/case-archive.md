# Local case archive

The operator dashboard stores operational records only under `casefiles/` on the scanning system. This directory is excluded from Git and must be placed on encrypted, access-controlled storage before real case use.

Each scan is retained beneath its case and evidence number:

```text
casefiles/
├── case-index.sqlite3
└── FALL-2026-001/
    ├── case.json
    ├── case-report.txt
    ├── media-register.csv
    ├── audit.log
    ├── manifest.sha256
    └── media/
        └── BM-001/
            ├── records/
            │   └── <scan-id>.json
            └── scans/
                └── <scan-id>/
                    ├── device.json
                    ├── partitions.json
                    ├── files.csv
                    ├── summary.json
                    ├── hits.json
                    ├── scan.log
                    └── raw/
```

`files.csv` is the full active-file directory observed during the metadata scan. It includes paths, extensions, categories, sizes, and filesystem-provided timestamps. It does not contain file contents.

`audit.log` is regenerated from append-only database events. A decision update adds a new event rather than deleting the earlier history. A non-selection requires a structured reason. `manifest.sha256` covers the human-readable exports and every retained scan artifact so later changes are detectable with `sha256sum -c manifest.sha256`.

The SQLite database is the searchable local index. JSON, CSV, text, and log exports remain independently readable if the dashboard or database is unavailable. PDF export, encryption-at-rest configuration, digital signatures, optical-media support, and parallel media workers remain later deployment phases.
