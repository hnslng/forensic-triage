# TRIAGE//BOX

**Version 0.2.0-alpha.17 · private Alpha-Entwicklungsfassung · Deutsch / English**

> [!CAUTION]
> **Nicht für ungeprüften Einsatz mit echten Beweismitteln freigegeben.** Das Projekt ist ein transparenter Entwicklungsprototyp. Es ersetzt weder validierte Forensikwerkzeuge noch Hardware-Schreibblocker, Verfahrensanweisungen oder eine fachliche Sicherstellungsentscheidung.

TRIAGE//BOX ist ein leichtgewichtiges Werkzeug zur forensischen Grobsichtung von Wechseldatenträgern vor Ort. Es inventarisiert mehrere geeignete USB-Datenträger parallel, ordnet Dateien anhand ihrer Metadaten ein, sucht in Namen und Pfaden nach konfigurierbaren Begriffen und dokumentiert Scan und Entscheidung nachvollziehbar in einer lokalen Fallakte.

Das Werkzeug ersetzt weder eine forensische Sicherung noch eine Laboranalyse. Es soll die Entscheidung unterstützen, welche Datenträger für eine spätere professionelle Untersuchung gesichert oder mitgenommen werden.

> **English summary:** TRIAGE//BOX is a private alpha prototype for fast, read-only field triage of removable media. It is not approved for operational evidence handling. It inventories active files and metadata, searches names and paths, and creates a local audit trail. It does not image, carve, recover deleted data, inspect file contents, or make seizure decisions. See [English summary](#english-summary).

## Aktueller Funktionsumfang

- lokales, klickbares Dashboard im Terminal-/CRT-Stil
- bewusster Fallstart mit Fallnummer und Bearbeiterkürzel
- kein aktiver Fall nach Neustart; Scans bleiben bis zur Freigabe gesperrt
- parallele Grobsichtung mehrerer ungemounteter USB-Datenträger
- schneller Standardmodus mit kurzzeitigem, verifiziert schreibgeschütztem Mount
- langsamer, mountfreier TSK-Modus für technische Vergleichstests
- vollständiges Metadaten-Inhaltsverzeichnis als `files.csv`
- Kategorien nach Dateiendung, Größenstatistik und größte Dateien
- kombinierbare und lokal bearbeitbare Stichwortprofile
- Stichwortsuche ohne Beachtung der Groß-/Kleinschreibung in Namen und Pfaden
- neutrale Sichtungsnummern `SICHT-###`; Beweismittelnummer erst bei „Sichern“
- Entscheidungen „Sichern“, „Nicht ausgewählt“ und „Weitere Prüfung“
- lokale Fallakte mit Audit-Log, Medienregister, Bericht und SHA-256-Manifest
- ZIP-Export der Falldaten
- direktes Öffnen und doppelt bestätigtes, wiederherstellbares Entfernen einzelner Fälle im Fallarchiv
- sicherer Software-Auswurf und erneute Geräteerkennung

## Wichtige Grenzen

Version 0.2.0-alpha.17 liest **keine Dateiinhalte**. Die Stichwortsuche arbeitet ausschließlich auf Datei- und Ordnernamen beziehungsweise Pfaden. Die Dateikategorie wird derzeit anhand der Dateiendung gebildet.

Das bedeutet insbesondere:

- Eine SQLite-Datenbank, die nur in `.jpg` umbenannt wurde, wird derzeit nicht als Datenbank erkannt.
- Es gibt noch keine Magic-Byte-/Dateisignaturprüfung.
- Es werden keine gelöschten Dateien wiederhergestellt und keine Daten geschnitzt („Carving“).
- Es wird kein forensisches Image erzeugt.
- Verschlüsselte Container werden nicht geöffnet oder inhaltlich bewertet.
- Geladene Medien in externen USB-CD/DVD-Laufwerken werden über einen eigenen, nur-lesenden Scanpfad erfasst; der reale Hardwaretest steht noch aus.
- Das System trifft keine rechtliche oder fachliche Sicherstellungsentscheidung.

Für echte Beweismittel ist ein validierter Hardware-Schreibblocker erforderlich. Der implementierte Software-Schreibschutz ist eine zusätzliche Schutzschicht, kein Ersatz dafür.

## Installation auf dem Scanner

Das private Repository benötigt auf dem Scanner einen eigenen, möglichst nur lesenden GitHub-Deploy-Key:

```bash
git clone git@github.com:hnslng/forensic-triage.git
cd forensic-triage
```

Falls das Repository später bewusst öffentlich gestellt wird, kann stattdessen ohne Anmeldung über HTTPS geklont werden.

Anschließend auf einem Debian-basierten Scanner:

```bash
sudo ./scripts/install_debian.sh
```

Auf Raspberry Pi OS Bookworm über Ethernet beziehungsweise an der lokalen Konsole:

```bash
sudo ./scripts/install_debian.sh --pi
```

Das wiederholbar ausführbare Skript installiert Systempakete, Python-Umgebung, Tests, Konfiguration und systemd-Dienst. Es überschreibt bei Aktualisierungen weder lokale Konfiguration noch Fallakten. Einzelheiten: [Installation und Aktualisierung](docs/installation.md).

Lokale Einstellungen wie Host, Port und Speicherpfade stehen außerhalb von Git in `/etc/forensic-triage/triage.env`. Der Pi-Modus trennt WLAN-SSID und Kennwort in `/etc/forensic-triage/pi-network.env`. Siehe [Konfiguration](docs/configuration.md).

## Bedienablauf

1. Dashboard öffnen. Nach jedem Neustart ist **kein Fall aktiv**.
2. „Auftrag öffnen“ wählen.
3. Neue Fallnummer eingeben oder einen vorhandenen Fall im Archiv öffnen.
4. Bearbeiterkürzel eintragen und Suchprofile auswählen.
5. „Fall starten“ ausdrücklich bestätigen.
6. Autorisierte, ungemountete USB-Datenträger anschließen. Bei aktivem Auto-Scan beginnen geeignete Medien selbstständig.
7. Ergebnis je Medium prüfen und eine Entscheidung dokumentieren.
8. Nur bei „Sichern“ eine offizielle Beweismittel-/Asservatennummer vergeben.
9. Datenträger sicher auswerfen beziehungsweise nach abgeschlossener Sichtung abziehen.
10. Fall beenden und bei Bedarf die Falldaten als ZIP exportieren.

Ein Fall wird direkt im Fallarchiv über „Löschen“ entfernt. Der aktive Fall ist geschützt und muss zuerst beendet werden. „Löschen“ verschiebt die lokale Fallakte in einen wiederherstellbaren internen Papierkorb; es ist keine sichere Datenvernichtung.

Die ausführliche Bedienung steht in [docs/operation.md](docs/operation.md).

## Zugriff auf die Oberfläche

Standardmäßig lauscht der Dienst ausschließlich auf `127.0.0.1:8787`. Zugriff erfolgt entweder auf einem lokalen Bildschirm oder über eine bewusst eingerichtete, geschützte Verbindung. Die spätere direkte Ethernet-Verbindung zwischen Pi und Laptop wird erst mit der realen Hardware konfiguriert.

Der gegenwärtige Mac-/VM-Aufbau dient nur zum Entwickeln und Ausprobieren. Er ist getrennt in [Temporäre Entwicklungsumgebung](docs/development-setup.md) beschrieben und kein Bestandteil des Produkts.

## CLI-Scan für technische Tests

Nicht anhand eines vermuteten Gerätenamens arbeiten. Ziel unmittelbar vorher prüfen:

```bash
lsblk -o NAME,TRAN,SIZE,MODEL,SERIAL,RO,MOUNTPOINTS
```

Beispiel:

```bash
sudo .venv/bin/forensic-triage scan /dev/sdX \
  --profile profiles/default.yaml \
  --evidence TEST-001
```

Der Standard ist `--mode fast`. Für den langsameren mountfreien Verzeichnislauf kann `--mode tsk` ergänzt werden. `--expected tests/fixtures/expected.json` vergleicht einen autorisierten Testdatenträger mit dem synthetischen Sollbestand.

## Dokumentation

- [Dokumentationsübersicht](docs/README.md)
- [So funktioniert TRIAGE//BOX](docs/how-it-works.md)
- [Installation und Aktualisierung](docs/installation.md)
- [Konfiguration](docs/configuration.md)
- [Bedienung und Fallworkflow](docs/operation.md)
- [Forensische Sicherheitsgrenzen](docs/forensic-safety.md)
- [Architektur](docs/architecture.md)
- [Lokale Fallakte und Protokollierung](docs/case-archive.md)
- [Testplan](docs/test-plan.md)
- [Validierung mit physischem Medium](docs/validation-2026-08-26.md)
- [Roadmap und offene Aufgaben](docs/roadmap.md)
- [Generische Entwicklungsumgebung](docs/development-setup.md)
- [Sicherheitsrichtlinie](SECURITY.md)
- [Nutzungsbedingungen](LICENSE.md)
- [Änderungshistorie](CHANGELOG.md)

## Datenschutz und Git

Das Repository enthält ausschließlich Quellcode, Profile, Tests und Dokumentation. Folgendes darf niemals eingecheckt werden:

- echte Fall- oder Beweismitteldaten
- Verzeichnisse `casefiles/` und `results/`
- Passwörter, Tokens, private SSH-Schlüssel oder `.env`-Dateien
- Exporte aus echten Einsätzen

Vor realem Betrieb muss das Fallarchiv auf verschlüsseltem, zugriffsgeschütztem Speicher liegen. Der Löschdialog verlangt zwei bewusste Bedienhandlungen für den konkret genannten Fall; entfernte Fälle bleiben im internen Papierkorb wiederherstellbar.

## Projektstatus

- Paketversion: `0.2.0a17` (Python/PEP 440)
- Git-/Releasebezeichnung: `v0.2.0-alpha.17`
- automatisierte Tests: 43
- validiert: SanDisk USB, exFAT, Debian-VM, schneller Read-only-Modus
- noch nicht validiert: Raspberry Pi, mehrere reale USB-Geräte gleichzeitig, CD/DVD, Hardware-LEDs, Einsatzbetrieb

Siehe [docs/roadmap.md](docs/roadmap.md) für die priorisierten nächsten Schritte.

## English summary

TRIAGE//BOX is a local field-triage aid for removable media. It starts locked, requires an explicit case and operator session, can scan eligible USB disks in parallel, and stores metadata inventories, keyword hits, decisions, and integrity manifests in a local case archive.

The default fast mode temporarily mounts partitions with `ro,nosuid,nodev,noexec` only after the whole block device has been set to and verified as read-only. A slower mount-free TSK directory walk remains available for testing. Software read-only controls do not replace a validated forensic hardware write blocker.

Version 0.2.0-alpha.17 searches file and directory names, not file contents. Each scan runs in a time-limited isolated process; loaded media in external USB optical drives use a dedicated read-only path, pending real-hardware validation. It creates a compact PDF case report, but does not detect renamed file types by signature, recover deleted files, carve data, or create forensic images. Installation details are in [docs/installation.md](docs/installation.md); configuration is documented in [docs/configuration.md](docs/configuration.md), and the current limitations are in [docs/roadmap.md](docs/roadmap.md). Any later public visibility would not constitute operational approval or an open-source licence; see [LICENSE.md](LICENSE.md).
