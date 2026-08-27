from forensic_triage.keywords import build_hits, list_profiles, load_profile, match_keywords, save_profile


def test_keyword_matching_uses_full_path_and_casefold():
    assert match_keywords("Buchhaltung/RECHNUNG_01.pdf", ["rechnung", "fibu"]) == ["rechnung"]


def test_hits_count_each_file_once_per_keyword():
    files = [{"path": "FIBU/fibu_export.csv"}, {"path": "neutral/FIBU.txt"}]
    hits = build_hits(files, ["fibu"])
    assert hits["total_matches"] == 2
    assert hits["by_keyword"]["fibu"]["count"] == 2


def test_profiles_can_be_created_and_updated_safely(tmp_path):
    created = save_profile(tmp_path, None, "Krypto Test", ["wallet.dat", "electrum"])
    assert created["id"] == "krypto-test"
    assert created["version"] == "1.0"
    assert list_profiles(tmp_path)[0]["keyword_count"] == 2

    updated = save_profile(tmp_path, created["id"], "Krypto Test", ["wallet.dat", "trezor"])
    assert updated["version"] == "1.1"
    assert load_profile(tmp_path / "krypto-test.yaml")["keywords"] == ["wallet.dat", "trezor"]
