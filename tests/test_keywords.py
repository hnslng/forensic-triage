from forensic_triage.keywords import build_hits, match_keywords


def test_keyword_matching_uses_full_path_and_casefold():
    assert match_keywords("Buchhaltung/RECHNUNG_01.pdf", ["rechnung", "fibu"]) == ["rechnung"]


def test_hits_count_each_file_once_per_keyword():
    files = [{"path": "FIBU/fibu_export.csv"}, {"path": "neutral/FIBU.txt"}]
    hits = build_hits(files, ["fibu"])
    assert hits["total_matches"] == 2
    assert hits["by_keyword"]["fibu"]["count"] == 2
