#!/usr/bin/env python3
"""Create realistic, harmless USB and CD test media on macOS.

The fixture contains valid open and encrypted ZIP/7Z/RAR containers, damaged
and incomplete samples, a nested archive, an ISO containing a RAR archive,
normal metadata-only test files, and hidden entries. It never uses real case
data and refuses to overwrite an existing output directory.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import shutil
import sqlite3
import subprocess
import tempfile
import wave
import zipfile
from pathlib import Path


DEFAULT_PASSWORD = "triage-test"
CD_TARGET_BYTES = 620 * 1024 * 1024
USB_DEFAULT_TARGET_GIB = 12
USB_MINIMUM_TARGET_GIB = 12
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def run(args: list[str], cwd: Path | None = None) -> None:
    completed = subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "Unbekannter Werkzeugfehler").strip()
        raise RuntimeError(f"{Path(args[0]).name} fehlgeschlagen: {detail}")


def require_tools() -> dict[str, str]:
    names = {"zip": "zip", "rar": "rar", "7zz": "7zz", "hdiutil": "hdiutil"}
    resolved = {name: shutil.which(binary) for name, binary in names.items()}
    missing = [name for name, path in resolved.items() if path is None]
    if missing:
        raise SystemExit(f"Fehlende Werkzeuge: {', '.join(missing)}")
    return {name: str(path) for name, path in resolved.items()}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_pdf(path: Path, title: str) -> None:
    """Write a tiny valid one-page PDF without a third-party dependency."""
    safe_title = title.replace("(", "[").replace(")", "]").encode("latin-1", errors="replace")
    stream = b"BT /F1 16 Tf 54 760 Td (" + safe_title + b") Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    payload = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(payload))
        payload.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode())
    payload.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def write_sized_file(path: Path, size: int, prefix: bytes = b"") -> None:
    """Create a deterministic sparse file with a small recognizable header."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(prefix[:size])
        handle.truncate(size)


def write_normal_files(root: Path, label: str) -> None:
    write_text(root / "00_HINWEISE" / "README_TEST.txt", f"Synthetische TRIAGE//BOX-Testdaten: {label}")
    write_pdf(root / "01_ALLTAG" / "Dokumente" / "Rechnung_2025-014.pdf", "Synthetische Rechnung 2025-014")
    write_pdf(root / "01_ALLTAG" / "Dokumente" / "Vertrag_Muenchen.pdf", "Synthetischer Vertrag Muenchen")
    write_text(root / "01_ALLTAG" / "Tabellen" / "Kundenliste.csv", "kunde;ort;status\nTEST-001;Wien;aktiv\nTEST-002;Graz;inaktiv")
    write_text(
        root / "01_ALLTAG" / "E-Mail" / "Buchhaltung_Übergabe.eml",
        "From: test@example.invalid\nTo: test@example.invalid\nSubject: Synthetische Buchhaltung Übergabe\n\nKeine echten Daten.",
    )
    (root / "01_ALLTAG" / "Bilder").mkdir(parents=True, exist_ok=True)
    (root / "01_ALLTAG" / "Bilder" / "Urlaub_Alpen_001.png").write_bytes(PNG_1X1)
    (root / "01_ALLTAG" / "Bilder" / "Urlaub_Alpen_002.png").write_bytes(PNG_1X1)
    audio = root / "01_ALLTAG" / "Audio" / "Besprechung.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(audio), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8_000)
        handle.writeframes(b"\0\0" * 800)
    database = root / "02_FACHDATEN" / "Kunden_Buchhaltung.sqlite"
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE test_kunden (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute("INSERT INTO test_kunden(name) VALUES ('SYNTHETISCH-001')")
    write_text(root / "02_FACHDATEN" / "Bitcoin_wallet_Hinweis.txt", "Nur synthetischer Dateiname; keine Wallet-Daten.")
    write_text(root / "02_FACHDATEN" / "wallet.dat.TESTHINWEIS.txt", "Keine echte Wallet. Nur ein Stichworttest.")
    write_text(root / "02_VERSTECKT" / ".versteckter_Hinweis.txt", "Diese reguläre Dotfile soll im Inventar erscheinen.")
    write_text(root / "02_VERSTECKT" / ".intern" / "Steuerberater_notiz.txt", "Synthetischer versteckter Ordner.")


def create_source_payload(root: Path) -> None:
    write_pdf(root / "Dokumente" / "Rechnung_intern.pdf", "Rechnung im Archiv")
    write_text(root / "Tabellen" / "Kunden_intern.csv", "kunde;summe\nTEST-A;100\nTEST-B;200")
    write_text(root / "Wallets" / "Bitcoin_wallet.dat.HINWEIS.txt", "Keine echte Wallet; synthetischer Test.")
    write_text(root / "Umlaute" / "Prüfung_Übergabe_Österreich.txt", "UTF-8-Dateiname für die Metadatensuche.")


def zip_directory(source: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(source.rglob("*")):
            if item.is_file():
                archive.write(item, item.relative_to(source))


def create_archives(target: Path, work: Path, tools: dict[str, str], password: str) -> dict[str, Path]:
    target.mkdir(parents=True, exist_ok=True)
    source = work / "payload"
    create_source_payload(source)
    source_members = [item.name for item in sorted(source.iterdir())]

    open_zip = target / "01_Offen.zip"
    zip_directory(source, open_zip)
    run([tools["zip"], "-q", "-r", "-P", password, str(target / "02_Passwort_Dateien.zip"), "."], cwd=source)
    run([tools["7zz"], "a", "-bd", "-y", str(target / "03_Offen.7z"), "."], cwd=source)
    run([tools["7zz"], "a", "-bd", "-y", f"-p{password}", "-mhe=on", str(target / "04_Passwort_Kopf.7z"), "."], cwd=source)
    run([tools["rar"], "a", "-idq", "-ep1", str(target / "05_Offen.rar"), *source_members], cwd=source)
    run([tools["rar"], "a", "-idq", "-ep1", f"-p{password}", str(target / "06_Passwort_Dateien.rar"), *source_members], cwd=source)
    run([tools["rar"], "a", "-idq", "-ep1", f"-hp{password}", str(target / "07_Passwort_Kopf.rar"), *source_members], cwd=source)

    nested_source = work / "nested"
    nested_source.mkdir()
    shutil.copy2(target / "04_Passwort_Kopf.7z", nested_source / "Innen_Passwort_Kopf.7z")
    shutil.copy2(target / "05_Offen.rar", nested_source / "Innen_Offen.rar")
    write_text(nested_source / "README_Archiv_in_Archiv.txt", "TRIAGE//BOX zeigt die inneren Archive als Einträge, öffnet sie aber bewusst nicht rekursiv.")
    zip_directory(nested_source, target / "08_Archiv_in_Archiv.zip")

    damaged = target / "09_Beschaedigt.zip"
    data = open_zip.read_bytes()
    damaged.write_bytes(data[: max(64, len(data) // 2)])

    volume_source = work / "volume"
    volume_source.mkdir()
    (volume_source / "Synthetischer_Block.bin").write_bytes(bytes(range(256)) * 1_024)
    run([tools["rar"], "a", "-idq", "-ep1", "-m0", "-v64k", str(work / "Mehrteilig.rar"), "Synthetischer_Block.bin"], cwd=volume_source)
    first_volume = sorted(work.glob("Mehrteilig.part*.rar"))[0]
    missing_volume = target / "10_Mehrteilig_Teil2_fehlt.part1.rar"
    shutil.copy2(first_volume, missing_volume)

    iso_source = work / "iso-source"
    write_pdf(iso_source / "Dokumente" / "Rechnung_im_ISO.pdf", "Rechnung in ISO")
    write_text(iso_source / "Hinweise" / "Kunden_DATEV.txt", "Synthetischer Stichworttreffer im ISO-Verzeichnis.")
    (iso_source / "Archive").mkdir(parents=True, exist_ok=True)
    shutil.copy2(target / "05_Offen.rar", iso_source / "Archive" / "Innen_Offen.rar")
    iso = target.parent / "04_ISO" / "Datensicherung_2024_mit_RAR.iso"
    iso.parent.mkdir(parents=True, exist_ok=True)
    run([
        tools["hdiutil"], "makehybrid", "-quiet", "-o", str(iso), str(iso_source),
        "-iso", "-joliet", "-iso-volume-name", "TRIAGE_ISO", "-joliet-volume-name", "TRIAGE_ISO",
    ])
    return {
        "open_zip": open_zip,
        "encrypted_zip": target / "02_Passwort_Dateien.zip",
        "open_7z": target / "03_Offen.7z",
        "encrypted_7z": target / "04_Passwort_Kopf.7z",
        "open_rar": target / "05_Offen.rar",
        "encrypted_rar": target / "07_Passwort_Kopf.rar",
        "nested_zip": target / "08_Archiv_in_Archiv.zip",
        "damaged_zip": damaged,
        "missing_rar": missing_volume,
        "iso": iso,
    }


def write_expectations(
    root: Path,
    medium: str,
    password: str,
    usb_size_gib: int = USB_DEFAULT_TARGET_GIB,
) -> None:
    archive_expectation = (
        "10 Archive: 4 verschlüsselt, 4 nicht verschlüsselt, 2 ungeprüft"
        if medium == "USB"
        else "4 Archive: 2 verschlüsselt, 1 nicht verschlüsselt, 1 ungeprüft"
    )
    volume_expectation = (
        f"Volltest mit mindestens 3.800 Dateien und rund {usb_size_gib} GiB logischer Nutzgröße"
        if medium == "USB"
        else "Volltest mit mindestens 600 Dateien und rund 620 MiB Quelldaten"
    )
    write_text(
        root / "00_HINWEISE" / "ERWARTETE_BEOBACHTUNGEN.txt",
        f"""
TRIAGE//BOX – ERWARTETE BEOBACHTUNGEN ({medium})

- Normale Kategorien: Bilder, Audio, Dokumente, Tabellen, E-Mail, Datenbanken und Text/Logs.
- Stichwörter in Namen/Pfaden: Rechnung, Kunden, Buchhaltung, DATEV, Bitcoin, wallet.dat und Steuerberater.
- Versteckte Dateien und der Ordner .intern müssen im Inhaltsverzeichnis erscheinen.
- Offene ZIP-/7Z-/RAR-Archive müssen aufklappbare Verzeichnisnamen liefern.
- Passwortarchive müssen als verschlüsselt erkannt werden; es findet kein Passwortversuch statt.
- Erwartete Archivstatistik: {archive_expectation}.
- Umfang: {volume_expectation}.
- 08_Archiv_in_Archiv.zip zeigt innere Archive nur als Dateien. Sie werden nicht rekursiv geöffnet.
- Datensicherung_2024_mit_RAR.iso ist aufklappbar; Innen_Offen.rar darin bleibt ein nicht rekursiv geöffnetes Objekt.
- 09_Beschaedigt.zip und 10_Mehrteilig_Teil2_fehlt.part1.rar müssen als unvollständig, nicht lesbar oder ungeprüft erscheinen.

Nur zur manuellen Gegenprüfung lautet das Testpasswort: {password}
Alle Inhalte sind synthetisch und dürfen niemals mit einer echten Fallakte verwechselt werden.
""",
    )


def populate_usb_volume(usb_root: Path, target_bytes: int) -> None:
    """Create a realistic high-capacity USB fixture without wasting local disk space."""
    bulk = usb_root / "05_MENGENTEST"
    for index in range(1, 1_601):
        path = bulk / "Bilder" / f"Foto_Einsatz_{index:05d}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(PNG_1X1)
    for index in range(1, 701):
        prefix = "Rechnung" if index % 10 == 0 else "Dokument"
        write_pdf(
            bulk / "Dokumente" / f"{prefix}_{index:05d}.pdf",
            f"Synthetisches Dokument {index:05d}",
        )
    for index in range(1, 451):
        prefix = "Kunden" if index % 15 == 0 else "Export"
        write_text(
            bulk / "Tabellen" / f"{prefix}_{index:05d}.csv",
            f"id;wert\nTEST-{index:05d};{index * 10}",
        )
    for index in range(1, 251):
        prefix = "Buchhaltung" if index % 20 == 0 else "Korrespondenz"
        write_text(
            bulk / "E-Mail" / f"{prefix}_{index:05d}.eml",
            f"From: test@example.invalid\nSubject: Synthetische Nachricht {index:05d}\n\nKeine echten Daten.",
        )
    for index in range(1, 301):
        prefix = "Steuerberater" if index % 25 == 0 else "System"
        write_text(
            bulk / "Logs" / f"{prefix}_Protokoll_{index:05d}.log",
            "Synthetischer Metadaten-Testeintrag",
        )
    for index in range(1, 251):
        prefix = "wallet" if index % 25 == 0 else "web_export"
        write_text(
            bulk / "Web" / f"{prefix}_{index:05d}.json",
            f'{{"synthetic": true, "id": {index}}}',
        )
    for index in range(1, 101):
        prefix = "DATEV" if index % 20 == 0 else "Archiv"
        write_text(
            bulk / "Datenbanken" / f"{prefix}_{index:05d}.sqlite",
            "Synthetischer Dateityp-Test; keine echte Datenbank",
        )
        write_text(
            bulk / "Unbekannt" / f"fragment_{index:05d}.daten",
            "Synthetischer unbekannter Dateityp",
        )
    for index in range(1, 51):
        write_text(
            bulk / ".cache" / f".versteckt_{index:05d}.txt",
            "Regulär vorhandene versteckte Testdatei",
        )

    large = usb_root / "06_GROESSTE_DATEIEN"
    large_specs = [
        ("Video_Einsatzort_001.mp4", 4_608, b"\x00\x00\x00\x18ftypmp42"),
        ("Video_Einsatzort_002.mp4", 2_048, b"\x00\x00\x00\x18ftypmp42"),
        ("Kamera_Export.mov", 1_536, b"\x00\x00\x00\x14ftypqt  "),
        ("Systemabbild.img", 1_024, b"TRIAGE-SYNTHETIC\n"),
        ("Mailarchiv_Export.pst", 768, b"!BDN"),
        ("Audio_Besprechung.wav", 512, b"RIFF\x00\x00\x00\x00WAVE"),
        ("DATEV_Sicherung.bak", 384, b"TRIAGE-SYNTHETIC\n"),
        ("Kunden_Datenbank.sqlite", 256, b"SQLite format 3\x00"),
    ]
    for name, size_mib, prefix in large_specs:
        write_sized_file(large / name, size_mib * 1024 * 1024, prefix)

    current_size = sum(item.stat().st_size for item in usb_root.rglob("*") if item.is_file())
    remaining = target_bytes - current_size
    if remaining <= 0:
        raise RuntimeError("USB-Testdaten überschreiten bereits die Zielgröße")
    write_sized_file(
        large / "Video_Synthetisch_Restbestand.mp4",
        remaining,
        b"\x00\x00\x00\x18ftypmp42",
    )


def populate_cd_volume(cd_root: Path, target_bytes: int = CD_TARGET_BYTES) -> None:
    """Fill the CD source with many harmless metadata fixtures and large sparse files."""
    bulk = cd_root / "05_MENGENTEST"
    for index in range(1, 241):
        path = bulk / "Bilder" / f"Urlaub_Familie_{index:04d}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(PNG_1X1)
    for index in range(1, 121):
        write_pdf(
            bulk / "Dokumente" / f"Rechnung_Projekt_{index:04d}.pdf",
            f"Synthetische Rechnung {index:04d}",
        )
    for index in range(1, 81):
        write_text(
            bulk / "Tabellen" / f"Kunden_Export_{index:04d}.csv",
            f"kunde;wert\nTEST-{index:04d};{index * 10}",
        )
    for index in range(1, 41):
        write_text(
            bulk / "E-Mail" / f"Buchhaltung_Anfrage_{index:04d}.eml",
            f"From: test@example.invalid\nSubject: Synthetische Buchhaltung {index:04d}\n\nKeine echten Daten.",
        )
    for index in range(1, 31):
        write_text(
            bulk / "Web" / f"wallet_index_{index:04d}.json",
            f'{{"synthetic": true, "id": {index}}}',
        )
        write_text(
            bulk / "Logs" / f"Steuerberater_Protokoll_{index:04d}.log",
            "Synthetischer Metadaten-Testeintrag",
        )
    for index in range(1, 26):
        write_text(
            bulk / "Unbekannt" / f"artefakt_{index:04d}.daten",
            "Synthetischer unbekannter Dateityp",
        )
    for index in range(1, 11):
        write_text(
            bulk / ".cache" / f".versteckt_{index:04d}.txt",
            "Regulär vorhandene versteckte Testdatei",
        )

    large = cd_root / "06_GROESSTE_DATEIEN"
    large_specs = [
        ("Video_Einsatzort_001.mp4", 120, b"\x00\x00\x00\x18ftypmp42"),
        ("Video_Einsatzort_002.mp4", 96, b"\x00\x00\x00\x18ftypmp42"),
        ("Video_Einsatzort_003.mp4", 72, b"\x00\x00\x00\x18ftypmp42"),
        ("Kamera_Export.mov", 64, b"\x00\x00\x00\x14ftypqt  "),
        ("Audio_Besprechung_001.wav", 48, b"RIFF\x00\x00\x00\x00WAVE"),
        ("Audio_Besprechung_002.wav", 40, b"RIFF\x00\x00\x00\x00WAVE"),
        ("System_Backup_001.bak", 32, b"TRIAGE-SYNTHETIC\n"),
        ("System_Backup_002.bak", 24, b"TRIAGE-SYNTHETIC\n"),
        ("Datentraeger_Abbild.img", 16, b"TRIAGE-SYNTHETIC\n"),
        ("Kunden_Datenbank.db", 12, b"SQLite format 3\x00"),
        ("Mailarchiv_Export.pst", 8, b"!BDN"),
        ("Dokumentenstapel.pdf", 8, b"%PDF-1.4\n"),
        ("Praesentation_Einsatz.pptx", 8, b"PK\x03\x04"),
        ("Video_Kurzclip.mp4", 8, b"\x00\x00\x00\x18ftypmp42"),
    ]
    for name, size_mib, prefix in large_specs:
        write_sized_file(large / name, size_mib * 1024 * 1024, prefix)

    current_size = sum(item.stat().st_size for item in cd_root.rglob("*") if item.is_file())
    remaining = target_bytes - current_size
    if remaining <= 0:
        raise RuntimeError("CD-Testdaten überschreiten bereits die Zielgröße")
    write_sized_file(
        large / "Video_Synthetisch_Restbestand.mp4",
        remaining,
        b"\x00\x00\x00\x18ftypmp42",
    )


def copy_cd_subset(cd_root: Path, archives: dict[str, Path], password: str) -> None:
    write_normal_files(cd_root, "CD-R")
    cd_archives = cd_root / "03_ARCHIVE"
    cd_archives.mkdir(parents=True, exist_ok=True)
    for key in ("open_zip", "encrypted_7z", "encrypted_rar", "damaged_zip"):
        shutil.copy2(archives[key], cd_archives / archives[key].name)
    cd_iso = cd_root / "04_ISO"
    cd_iso.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archives["iso"], cd_iso / archives["iso"].name)
    populate_cd_volume(cd_root)
    write_expectations(cd_root, "CD-R", password)


def write_checksums(root: Path, output: Path) -> None:
    lines = []
    for item in sorted(root.rglob("*")):
        if item.is_file() and item != output:
            hasher = hashlib.sha256()
            with item.open("rb") as handle:
                for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                    hasher.update(chunk)
            digest = hasher.hexdigest()
            lines.append(f"{digest}  {item.relative_to(root).as_posix()}")
    write_text(output, "\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Erzeugt realistische synthetische USB- und CD-Testmedien.")
    parser.add_argument("--output", type=Path, required=True, help="neues Ausgabeverzeichnis")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="ausschließlich synthetisches Archiv-Testpasswort")
    parser.add_argument(
        "--usb-size-gib",
        type=int,
        default=USB_DEFAULT_TARGET_GIB,
        help="logische USB-Testgröße in GiB (mindestens 12; Standard: 12)",
    )
    args = parser.parse_args()
    if args.usb_size_gib < USB_MINIMUM_TARGET_GIB:
        parser.error(f"--usb-size-gib muss mindestens {USB_MINIMUM_TARGET_GIB} betragen")
    output = args.output.expanduser().resolve()
    if output.exists():
        parser.error(f"Ausgabe existiert bereits; wird nicht überschrieben: {output}")

    tools = require_tools()
    usb_root = output / "USB-STICK_KOPIEREN"
    cd_root = output / "CD-QUELLE"
    usb_root.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="triagebox-fixture-") as temporary:
        work = Path(temporary)
        write_normal_files(usb_root, "USB")
        archives = create_archives(usb_root / "03_ARCHIVE", work, tools, args.password)
        populate_usb_volume(usb_root, args.usb_size_gib * 1024 * 1024 * 1024)
        write_expectations(usb_root, "USB", args.password, args.usb_size_gib)
        copy_cd_subset(cd_root, archives, args.password)

    write_checksums(usb_root, usb_root / "00_HINWEISE" / "SHA256SUMS.txt")
    write_checksums(cd_root, cd_root / "00_HINWEISE" / "SHA256SUMS.txt")
    cd_iso = output / "TRIAGEBOX_CD_TEST.iso"
    run([
        tools["hdiutil"], "makehybrid", "-quiet", "-o", str(cd_iso), str(cd_root),
        "-iso", "-joliet", "-iso-volume-name", "TRIAGEBOX_CD", "-joliet-volume-name", "TRIAGEBOX_CD",
    ])
    if cd_iso.stat().st_size > 690_000_000:
        raise RuntimeError(
            f"CD-Abbild ist für einen 700-MB-Rohling zu groß: {cd_iso.stat().st_size} Bytes"
        )
    write_text(
        output / "BRENANLEITUNG_MAC.txt",
        f"""
CD-R TESTMEDIUM

Fertiges Abbild: {cd_iso}

1. Leeren CD-R-Rohling einlegen.
2. Im Finder das ISO auswählen und über „Ablage > Image … auf Medium brennen“ brennen.
   Alternativ im Terminal: hdiutil burn "{cd_iso}"
3. Nach erfolgreichem Brennen die CD auswerfen, in das externe USB-Laufwerk am Pi einlegen
   und erst dann in TRIAGE//BOX einen ausdrücklich neuen Testfall starten.

Nicht den Ordner CD-QUELLE zusätzlich brennen; das ISO enthält ihn bereits vollständig.
""",
    )
    write_text(
        output / "README.txt",
        f"""
TRIAGE//BOX REALISTISCHE TESTMEDIEN

- Den INHALT von USB-STICK_KOPIEREN auf einen leeren Test-USB-Stick kopieren.
- Der USB-Satz hat rund {args.usb_size_gib} GiB logische Größe. Große Dateien sind lokal platzsparend angelegt,
  belegen auf einem üblichen exFAT-Teststick beim Kopieren aber ihre vollständige Größe.
- TRIAGEBOX_CD_TEST.iso gemäß BRENANLEITUNG_MAC.txt auf einen CD-R-Rohling brennen.
- Testpasswort für die absichtlich verschlüsselten Archive: {args.password}
- Die Daten sind ausschließlich synthetisch. Nicht für echte Fälle verwenden.
""",
    )
    print(f"USB-Testdaten: {usb_root}")
    print(f"USB-Testgröße: {sum(item.stat().st_size for item in usb_root.rglob('*') if item.is_file()) / 1024 / 1024 / 1024:.1f} GiB")
    print(f"USB-Dateien: {sum(1 for item in usb_root.rglob('*') if item.is_file())}")
    print(f"CD-Abbild: {cd_iso}")
    print(f"CD-Abbildgröße: {cd_iso.stat().st_size / 1024 / 1024:.1f} MiB")
    print(f"Testpasswort: {args.password}")


if __name__ == "__main__":
    main()
