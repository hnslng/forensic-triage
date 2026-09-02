# Realistische Testmedien / Realistic test media

Das Skript `scripts/create_field_test_media.py` erzeugt auf macOS zwei harmlose, synthetische Testmedien:

- einen Ordner zum Kopieren auf einen leeren USB-Teststick;
- ein fertiges ISO-Abbild zum Brennen auf eine CD-R.

Enthalten sind normale Dokument-, Tabellen-, Bild-, Audio-, E-Mail- und Datenbankdateien, versteckte Dateien und Ordner, Stichwörter mit Umlauten und eingebetteten Zeichenfolgen sowie echte ZIP-, 7Z- und RAR-Archive. Die Container umfassen offene Archive, Archive mit verschlüsselten Dateien, Archive mit verschlüsselten Kopfzeilen, ein Archiv im Archiv, ein beschädigtes ZIP und ein unvollständiges mehrteiliges RAR. Zusätzlich enthält ein ISO-Image ein RAR-Archiv, damit die bewusst nicht rekursive Behandlung verschachtelter Container sichtbar wird.

## Erzeugen

Voraussetzungen auf dem Entwicklungs-Mac:

- macOS-Werkzeuge `zip` und `hdiutil`;
- `rar`;
- `7zz`, beispielsweise mit `brew install sevenzip`.

```bash
python scripts/create_field_test_media.py \
  --output "$HOME/Desktop/TRIAGEBOX-Testmedien-alpha34"
```

Das Skript verweigert das Überschreiben eines vorhandenen Zielordners. Das feste Testpasswort lautet `triage-test` und schützt ausschließlich die synthetischen Archive; es darf niemals als Betriebskennwort verwendet werden.

## USB-Test

Den **Inhalt** von `USB-STICK_KOPIEREN/` auf einen leeren, eindeutig als Testmedium markierten USB-Stick kopieren. Danach sauber auswerfen, am Pi anschließen, einen eigenen Testfall starten und die Datei `00_HINWEISE/ERWARTETE_BEOBACHTUNGEN.txt` mit der Anzeige vergleichen.

## CD-R-Test

`TRIAGEBOX_CD_TEST.iso` als Abbild auf den Rohling brennen, nicht als gewöhnliche Datei auf eine Daten-CD kopieren. Im Finder kann das ISO über die Brennfunktion für Images geschrieben werden. Alternativ:

```bash
hdiutil burn "$HOME/Desktop/TRIAGEBOX-Testmedien-alpha34/TRIAGEBOX_CD_TEST.iso"
```

Nach erfolgreichem Brennen die CD neu einlegen und anschließend im externen USB-Laufwerk am Pi prüfen. Das beigefügte `BRENANLEITUNG_MAC.txt` enthält denselben Ablauf.

## Erwartete Grenzen

- Offene Archive liefern aufklappbare Namen und Pfade.
- Passwortgeschützte Archive werden als verschlüsselt markiert; TRIAGE//BOX versucht kein Passwort.
- Container innerhalb eines ZIP oder ISO erscheinen als Eintrag, werden aber nicht rekursiv geöffnet.
- Beschädigte oder unvollständige Archive bleiben ausdrücklich `UNGEPRÜFT`, `UNVOLLSTÄNDIG` oder `NICHT LESBAR`.
- Die Testdateien prüfen Metadaten, Kategorien und Namen/Pfade. Sie stellen keine inhaltliche forensische Validierung dar.

## English summary

The generator creates harmless synthetic USB and CD-R fixtures with valid open and encrypted ZIP/7Z/RAR files, nesting, an ISO containing a RAR file, damaged/incomplete samples, hidden entries, and keyword-bearing names. It refuses to overwrite an existing output directory. The password `triage-test` is for synthetic archive testing only.
