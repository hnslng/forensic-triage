from forensic_triage.statistics import summarize


def test_summary_counts_and_orders_largest_files():
    files = [
        {"path": "b.mp4", "size": 20, "extension": "mp4", "category": "Video"},
        {"path": "a.jpg", "size": 10, "extension": "jpg", "category": "Bilder"},
    ]
    result = summarize(files, [{"path": "folder"}])
    assert result["file_count"] == 2
    assert result["directory_count"] == 1
    assert result["total_file_bytes"] == 30
    assert result["largest_files"][0] == {"path": "b.mp4", "size": 20}
