# Änderungshistorie / Changelog

Das Format orientiert sich an „Keep a Changelog“. Das Projekt verwendet semantische Versionsnummern; Alpha-Versionen sind nicht für ungeprüften Einsatz bestimmt.

## [0.2.0-alpha.2] – 2026-08-27

### Hinzugefügt

- wiederholbar ausführbares Debian-/Pi-Installationsskript mit Prüfmodus
- lokale, von Git getrennte Konfiguration unter `/etc/forensic-triage/triage.env`
- konfigurierbare Webadresse, Port-, Ergebnis-, Fallakten- und Profilpfade
- verständliche Funktions- und Speicherortübersicht ohne erforderliche Programmierkenntnisse
- eigener Konfigurationsleitfaden

### Geändert

- Mac-/VM-Angaben aus der eigentlichen Produktinstallation entfernt und als temporäre Entwicklungsumgebung ausgelagert
- systemd-Dienst wird installationspfadabhängig aus einer Vorlage erzeugt
- Installation führt Paketinstallation, Python-Setup, Tests, Konfiguration und Dienstaktivierung in einem Ablauf aus
- vorhandene lokale Konfiguration und Fallakten bleiben bei erneuter Installation unangetastet

### Validiert

- 30 automatisierte Tests erfolgreich
- Konfigurationswerte aus der lokalen Umgebung werden korrekt als Dienstvorgaben übernommen

## [0.2.0-alpha] – 2026-08-27

### Hinzugefügt

- lokales Dashboard mit Fall-, Medien- und Ergebnisansicht
- expliziter Fallstart mit Fallnummer, Bearbeiter und Suchprofilen
- paralleler Auto-Scan mehrerer geeigneter USB-Datenträger
- neutrale Sichtungsnummern und spätere Beweismittelnummer bei „Sichern“
- dauerhafte lokale Fallakte mit SQLite-Index, Audit-Log, Medienregister, Bericht und SHA-256-Manifest
- ZIP-Export von Falldaten
- durchsuchbarer Datei-/Verzeichnisbaum
- kombinierbare, bearbeitbare und neu anlegbare Stichwortprofile
- Krypto-/Wallet-Profil für leichte Namens- und Pfadindikatoren
- Software-Auswurf und erneute Geräteerkennung
- Mac-Starter für den privaten SSH-Tunnel
- direkte Versionsabfrage über `forensic-triage --version` und `forensic-triage-web --version`
- deutsche Hauptdokumentation, Installationsanleitung, Bedienungsanleitung und Roadmap

### Geändert

- Dashboard für kleine Bildschirme gestrafft und visuell vereinheitlicht
- Auftragserfassung in ein eigenes Modal verschoben
- aktive Fallzuordnung deutlich hervorgehoben und nach Neustart grundsätzlich gesperrt
- Entscheidungsbuttons nach Risiko und Bedeutung unterschieden
- Voraussetzungen für „Fall starten“ werden gemeinsam angezeigt
- verschachtelte Modale verwenden nur noch den obersten abgedunkelten Hintergrund
- Fälle können direkt im Archiv geöffnet oder passwortgeschützt entfernt werden
- aktiver Fall ist gegen Entfernen geschützt
- Stichwortsuche normalisiert Groß-/Kleinschreibung, häufige Trenner und deutsche Umlautschreibweisen

### Validiert

- 29 automatisierte Tests erfolgreich
- physischer SanDisk-USB-Datenträger mit exFAT und 960 synthetischen Dateien
- schneller Scan in 0,732 Sekunden bei unverändertem Read-only-Status

### Bekannte Grenzen

- Alpha-/Prototypstatus, keine Freigabe für ungeprüften Feldeinsatz
- keine Inhaltsanalyse, Dateisignaturprüfung, Images, Wiederherstellung oder Carving
- CD/DVD-Erkennung vorhanden, Scan noch deaktiviert
- Raspberry Pi und mehrere reale Parallelmedien noch nicht validiert
- Software-Schreibschutz ersetzt keinen Hardware-Schreibblocker

## [0.1.0] – 2026-08-26

### Hinzugefügt

- Python-Paket und CLI-Orchestrierung
- strikte USB-Zielprüfung sowie Setzen und Verifizieren des Blockgeräte-Schreibschutzes
- schneller Read-only-Mount-Modus und mountfreier TSK-Modus
- Parser für Partitionen und Dateisystemausgaben
- Klassifizierung nach Dateiendungen, Stichwortsuche und Statistiken
- synthetischer 960-Dateien-Testdatenträger und Sollmanifest
- erste physische Validierung auf einer Debian-VM

## English summary

Version 0.2.0-alpha adds the operator dashboard, explicit case sessions, parallel USB scanning, durable case records, editable combined keyword profiles, safe eject/refresh, direct archive actions, and comprehensive German documentation. It remains an unvalidated alpha prototype with no content analysis, file-signature detection, imaging, recovery, carving, or optical-media scanning.
