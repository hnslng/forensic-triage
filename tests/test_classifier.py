from forensic_triage.classifier import classify, original_extension_for


def test_known_extension_is_case_insensitive():
    assert classify("Belege/FOTO.JPEG") == ("jpeg", "Bilder")
    assert original_extension_for("Belege/FOTO.JPEG") == "JPEG"


def test_unknown_and_no_extension_are_explicit():
    assert classify("foo.weird") == ("weird", "Unbekannt")
    assert classify("README") == ("", "Unbekannt")
