import json

from forensic_triage.validation import compare_expected


def test_validation_compares_keywords_case_insensitively(tmp_path):
    summary = {
        "file_count": 1,
        "directory_count": 1,
        "total_file_bytes": 10,
        "extensions": {"pdf": 1},
        "categories_by_count": {"Dokumente": 1},
        "categories_by_bytes": {"Dokumente": 10},
        "largest_files": [{"path": "Rechnung.pdf", "size": 10}],
    }
    expected = {**summary, "keyword_hits": {"Rechnung": 1}}
    path = tmp_path / "expected.json"
    path.write_text(json.dumps(expected), encoding="utf-8")
    hits = {"by_keyword": {"rechnung": {"count": 1, "paths": ["Rechnung.pdf"]}}}
    assert compare_expected(summary, hits, path)["passed"] is True


def test_validation_exposes_mismatches(tmp_path):
    path = tmp_path / "expected.json"
    path.write_text(json.dumps({"file_count": 2, "keyword_hits": {}}), encoding="utf-8")
    result = compare_expected({"file_count": 1}, {"by_keyword": {}}, path)
    assert result["passed"] is False
    assert result["mismatches"][0]["field"] == "file_count"
