# Testplan / Test plan

## Automatisierte Tests

Die Python-Tests lokal ausführen:

```bash
.venv/bin/python -m pytest
```

Abgedeckt sind insbesondere:

- Normalisierung von Dateiendungen und Kategorien
- Stichwortsuche in vollständigen Pfaden, Groß-/Kleinschreibung, Trenner und Umlaute
- kombinierte und gespeicherte Profile
- deterministische Dateizahlen, Byte-Summen und größte Dateien
- Parsing dynamischer `mmls`-Offsets
- Parsing von `fls`-Bodyfile-Datensätzen
- schneller Read-only-Inventarpfad
- Scanner-Protokollierung und Validierung
- Fallakte, parallele Sichtungsnummern, Entscheidungen, Manifest und Wiederherstellungsablage
- Geräteerkennung, Software-Auswurf und Reaktivierung

### Browser-Regressionsprüfungen

Zusätzlich prüft `tests/test_web_ui.cjs` die echte Oberfläche in Chromium mit ausschließlich synthetischen API-Antworten. Es wird weder ein Pi kontaktiert noch ein Scan gestartet oder eine echte Fallakte verändert. Voraussetzung ist Node.js mit installiertem `playwright` und einem Chromium-Browser:

```bash
node --test tests/test_web_ui.cjs
```

Bei vorhandenem Google Chrome kann `TRIAGE_BROWSER_CHANNEL=chrome` gesetzt werden. Ist Playwright außerhalb des Projekts installiert, muss Node es über `NODE_PATH` finden. Diese Werkzeuge gehören nur zur Entwicklung, nicht zur Pi-Installation.

Geprüft werden Medien- und Filterwechsel mit absichtlich verspäteten Antworten, Rückkehr zum Dashboard, A–B–A-Wechsel, Archiv-Unterordner und Pagination in beiden Ansichten, Wiederholung fehlgeschlagener Archivabrufe sowie numerische Sichtungssortierung. Eine reine Navigation darf keine schreibenden API-Aufrufe auslösen.

## Synthetischer Testdatenträger

Für realistische offene, verschlüsselte, verschachtelte und beschädigte Archive sowie ein brennbares CD-R-Abbild siehe [test-media.md](test-media.md). Der folgende große deterministische Datensatz bleibt der Laufzeit- und Zählwertvergleich.

1. Autorisierten SanDisk anhand von Transport, Modell, Seriennummer und Kapazität identifizieren.
2. Sicherstellen, dass kein Systemdatenträger das Ziel sein kann.
3. Nur nach erneuter `lsblk`-Kontrolle partitionieren oder formatieren.
4. Leeres Testvolume beschreibbar mounten und Fixture erzeugen:

   ```bash
   python scripts/create_test_media.py --target /pfad/zum/TRIAGE_TEST-volume
   ```

5. Alle Partitionen unmounten.
6. Read-only-Zustand setzen und prüfen.
7. Standardscan `fast` ausführen und sicherstellen, dass der temporäre Mount read-only war und nach Abschluss nicht mehr existiert.
8. `--mode tsk` separat als mountfreien Vergleichspfad prüfen.
9. Dateizahl, Ordnerzahl, Endungen, Kategorien, Bytes, Stichwortzahlen und größte Dateien mit `tests/fixtures/expected.json` vergleichen.
10. Laufzeit, Werkzeugversionen, Hardwareidentität und rohe Ausgaben dokumentieren.

Jede Abweichung ist bis zu einer nachvollziehbaren Erklärung ein fehlgeschlagener Test. Dateisystembedingte Metadaten dürfen nicht still ignoriert werden.

## Manuelle UI-Prüfung

- Start ohne aktiven Fall; Scan gesperrt
- gemeinsame Anzeige aller fehlenden Startvoraussetzungen
- expliziter Fallwechsel mit neuem Bearbeiter
- mehrere Suchprofile gleichzeitig
- parallele Medienkacheln und unabhängige Statuswerte
- Sichtungsreihenfolge 1, 2, 3, 8, 10 statt lexikographischer oder Scanabschluss-Reihenfolge
- keine fremden oder unsichtbaren Verzeichnisse nach schnellem Medien-/Filterwechsel
- Archiv-Unterordner und weitere Einträge in Explorer und gefilterter Liste
- äußere Dateien und zusätzliche Archiv-Fundstellen klar getrennt beschriftet
- Größen der größten Dateien bei langen Pfaden ohne horizontales Scrollen sichtbar; Klick wählt exakt den Metadateneintrag, auch bei Sonderzeichen
- Archivstatus kompakt und anklickbar; Zahlen und Balken der Dateitypliste bleiben ausgerichtet
- Statusfilter liefern genau die gezählten äußeren Archive, einschließlich Pagination; verschachtelte Archivnamen nicht mitgezählt
- Explorer und Suchliste kennzeichnen Verschlüsselung/ungeklärten Status dezent mit Text; Nullzähler deaktiviert, Filterreset und Medienwechsel korrekt
- Online-/Offline-Zustand und offene Entscheidung nach Abziehen
- Entscheidungspflichten: Beweismittelnummer bei „Sichern“, Begründung bei „Nicht sichern“
- kein versehentliches Protokollieren durch reine Navigation
- Fallarchiv: sichtbare Aktionen „Öffnen“ und „Löschen“
- aktiver Fall kann nicht gelöscht werden
- fehlende oder abweichende Fallbestätigung verändert keine Fallakte
- korrektes Entfernen lässt Archiv geöffnet und verschiebt Unterlagen nach `.trash`
- PDF-Bericht, ZIP-Export und Manifestprüfung
- Tastaturfokus und kleiner Bildschirm

## Noch erforderliche Hardwaretests

- zwei oder mehr reale USB-Datenträger parallel
- USB-Hub mit eigener Stromversorgung
- Abziehen während Scan und während offener Entscheidung
- defektes, nicht lesbares und unbekanntes Dateisystem
- CD und DVD im vorgesehenen Laufwerk
- künstlich blockierter Scanner-Worker: Zeitlimit, Gerätequarantäne und weiterhin reagierende Weboberfläche
- physisch blockierender Datenträger: anderer USB-Port und paralleler Scan bleiben bedienbar
- Raspberry Pi einschließlich direkter Ethernet-Verbindung und kleinem Display
- Stromverlust und kontrollierter Wiederanlauf
- Hardware-Schreibblocker

## Releasekriterium

`v0.2.0-alpha.41` dokumentiert einen funktionsfähigen Prototyp. Eine spätere Einsatzversion benötigt bestandene Hardwaretests, ein Sicherheitsreview, verschlüsselten Fallspeicher, getestete Wiederherstellung, festgelegte Betriebsprozesse und dokumentierte Freigabe.

Für den ZIP-/ISO-/7Z-/RAR-Schnellindex müssen zusätzlich intakte, beschädigte, verschlüsselte, mehrteilige und sehr große Testcontainer geprüft werden. Nachzuweisen sind: keine Extraktion oder Dekompression, keine Passwortversuche, sichtbare Limitkennzeichnung, höchstens das konfigurierte Zusatzzeitbudget sowie unveränderte äußere Datei-/Ordnerzahlen.

## English summary

The project has Python tests and isolated browser regressions plus a synthetic 3,835-file, 12-GiB USB fixture and a 610-file CD-R fixture. Before any operational release, it still needs real parallel-device, powered-hub, failure, optical-media, Raspberry Pi, recovery, encrypted-storage, and hardware-write-blocker validation.
