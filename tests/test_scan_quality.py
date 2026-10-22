import json

import pytest

from forensic_triage.scan_quality import apply_scan_quality
from forensic_triage.casefiles import _scan_summary


@pytest.mark.parametrize("partitions,status", [
    ([], "failed"),
    ([{"allocated": False}], "failed"),
    ([{"allocated": True, "scan_status": "ok"}], "complete"),
    ([{"allocated": True, "scan_status": "unsupported_or_error", "error": "unreadable"}], "failed"),
    ([{"allocated": True, "scan_status": "partial", "read_errors": [{"path": "broken.jpg"}]}], "partial"),
    ([{"allocated": True, "scan_status": "ok"}, {"allocated": True, "scan_status": "unsupported_or_error"}], "partial"),
])
def test_scan_coverage(partitions, status):
    summary = {"file_count": 0}
    apply_scan_quality(summary, partitions)
    assert summary["scan_status"] == status
    assert bool(summary["scan_warnings"]) == (status != "complete")


def test_legacy_scan_quality_does_not_rewrite_evidence(tmp_path):
    original = '{"file_count": 0}'
    (tmp_path / "summary.json").write_text(original)
    (tmp_path / "partitions.json").write_text(json.dumps([
        {"allocated": True, "scan_status": "unsupported_or_error", "error": "missing entry"}
    ]))
    assert _scan_summary(tmp_path)["scan_status"] == "failed"
    assert (tmp_path / "summary.json").read_text() == original
