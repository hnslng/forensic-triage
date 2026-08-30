# Testplan / Test plan

## Automatisierte Tests

Der aktuelle Stand umfasst 30 automatisierte Tests. Lokal ausführen:

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

## Synthetischer Testdatenträger

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
- Online-/Offline-Zustand und offene Entscheidung nach Abziehen
- Entscheidungspflichten: Beweismittelnummer bei „Sichern“, Begründung bei „Nicht ausgewählt“
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

`v0.2.0-alpha.21` dokumentiert einen funktionsfähigen Prototyp. Eine spätere Einsatzversion benötigt bestandene Hardwaretests, ein Sicherheitsreview, verschlüsselten Fallspeicher, getestete Wiederherstellung, festgelegte Betriebsprozesse und dokumentierte Freigabe.

Für den ZIP-/ISO-/7Z-/RAR-Schnellindex müssen zusätzlich intakte, beschädigte, verschlüsselte, mehrteilige und sehr große Testcontainer geprüft werden. Nachzuweisen sind: keine Extraktion oder Dekompression, keine Passwortversuche, sichtbare Limitkennzeichnung, höchstens das konfigurierte Zusatzzeitbudget sowie unveränderte äußere Datei-/Ordnerzahlen.

## English summary

The project currently has 59 automated tests plus a synthetic 960-file physical-media fixture. Before any operational release, it still needs real parallel-device, powered-hub, failure, optical-media, Raspberry Pi, recovery, encrypted-storage, and hardware-write-blocker validation.
