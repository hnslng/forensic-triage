"""Keyword profile loading and path matching."""

from __future__ import annotations

from pathlib import Path

from forensic_triage.keywords import build_hits, list_profiles, load_profile, match_keywords, save_profile


def test_keyword_matching_uses_full_path_and_casefold():
    assert match_keywords("Buchhaltung/RECHNUNG_01.pdf", ["rechnung", "fibu"]) == ["rechnung"]


def test_keyword_matching_accepts_embedded_terms_umlaut_variants_and_separators():
    path = "Archiv/alte_UEBERWEISUNG_2026/seed_phrase.txt"
    assert match_keywords(path, ["Überweisung", "seed phrase", "wallet.dat"]) == ["Überweisung", "seed phrase"]


def test_hits_count_each_file_once_per_keyword():
    files = [{"path": "FIBU/fibu_export.csv"}, {"path": "neutral/FIBU.txt"}]
    hits = build_hits(files, ["fibu"])
    assert hits["total_matches"] == 2
    assert hits["by_keyword"]["fibu"]["count"] == 2


def test_standard_profiles_are_extended_for_alpha68():
    root = Path(__file__).resolve().parents[1] / "profiles"
    profiles = list_profiles(root)
    by_id = {profile["id"]: profile for profile in profiles}
    assert by_id["default"]["keyword_count"] >= 35
    assert by_id["krypto"]["keyword_count"] >= 30
    default = load_profile(root / "default.yaml")
    assert {"eingangsrechnung", "gutschrift", "kontoauszug", "ustva", "opos"} <= set(default["keywords"])
    assert "fibu" in default["keywords"]
    krypto = load_profile(root / "krypto.yaml")
    assert {"bip39", "xpub", "xprv", "wallet.json"} <= set(krypto["keywords"])


def test_extended_profiles_produce_no_matches_on_neutral_paths():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "profiles"
    for filename in ("default.yaml", "krypto.yaml"):
        profile = load_profile(root / filename)
        for path in (
            "Beispiel/lebenslauf_2026.pdf",
            "IMG_20260102_104503.jpg",
            "Musik/sommerplaylist01.mp3",
            "Notizen/spielle_oft.aufgaben",
            "Schule/aufgabe_luise_susanne.docx",
        ):
            assert match_keywords(path, profile["keywords"]) == [], (filename, path)


def test_profiles_can_be_created_and_updated_safely(tmp_path):
    created = save_profile(tmp_path, None, "Krypto Test", ["wallet.dat", "electrum"])
    assert created["id"] == "krypto-test"
    assert created["version"] == "1.0"
    assert list_profiles(tmp_path)[0]["keyword_count"] == 2

    updated = save_profile(tmp_path, created["id"], "Krypto Test", ["wallet.dat", "trezor"])
    assert updated["version"] == "1.1"
    assert load_profile(tmp_path / "krypto-test.yaml")["keywords"] == ["wallet.dat", "trezor"]
