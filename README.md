# TRIAGE//BOX

**Version 0.2.0-alpha.81 · private Alpha-Entwicklungsfassung · Deutsch / English**

> [!CAUTION]
> **Nicht für ungeprüften Einsatz mit echten Beweismitteln freigegeben.** Das Projekt ist ein transparenter Entwicklungsprototyp. Es ersetzt weder validierte Forensikwerkzeuge noch Hardware-Schreibblocker, Verfahrensanweisungen oder eine fachliche Sicherstellungsentscheidung.

TRIAGE//BOX ist ein leichtgewichtiges Werkzeug zur forensischen Grobsichtung von Wechseldatenträgern und Mobilgeräten vor Ort. USB-/CD-Medien werden anhand zugänglicher Metadaten inventarisiert. Bei iPhones, iPads und Android-Geräten beantwortet ein eigener Krypto-Schnellscan dagegen bewusst nur die Frage, ob in der erfassten Benutzer-App-Liste relevante Wallet-, Börsen- Krypto-Apps oder Banking-/Finanz-Apps vorkommen. Zusätzlich erkennt TRIAGE//BOX auf Datenträgern charakteristische Strukturen lokaler Geräte-Backups (z. B. iTunes/Finder, Samsung Smart Switch, Android ADB, Xiaomi, Huawei), öffnet diese aber niemals. Scan und Entscheidung werden nachvollziehbar in einer lokalen Fallakte dokumentiert.

Das Werkzeug ersetzt weder eine forensische Sicherung noch eine Laboranalyse. Es soll die Entscheidung unterstützen, welche Datenträger für eine spätere professionelle Untersuchung gesichert oder mitgenommen werden.

> **English summary:** TRIAGE//BOX is a private alpha prototype for fast, read-only field triage of removable media. It is not approved for operational evidence handling. It inventories active files and metadata, searches names and paths, and creates a local audit trail. It reads only bounded ZIP, ISO, 7Z and RAR directory metadata, never file payloads; it does not image, carve, recover deleted data, or make seizure decisions. See [English summary](#english-summary).

## Aktueller Funktionsumfang

- lokales, klickbares Dashboard im Terminal-/CRT-Stil
- bewusster Fallstart mit Fallnummer und Bearbeiterkürzel
- kein aktiver Fall nach Pi-/Webdienst-Neustart; Browser-Neuladen übernimmt dagegen die noch aktive Gerätesitzung
- parallele Grobsichtung mehrerer ungemounteter USB-Datenträger
- schneller Standardmodus mit kurzzeitigem, verifiziert schreibgeschütztem Mount
- langsamer, mountfreier TSK-Modus für technische Vergleichstests
- Metadaten-Inhaltsverzeichnis der erfassten aktiven Dateien als `files.csv`
- sichtbare Datenträger-Metadaten mit Modell, Seriennummer, Kapazität, Gerätepfad und verifiziertem Schreibschutz im Nachweisdialog
- begrenzter ZIP-/ISO-/7Z-/RAR-Schnellindex: interne Verzeichnisnamen ohne Extraktion im Explorer aufklappbar und durchsuchbar
- bearbeitbarer Dateityp-Katalog mit erweitertem Standard und je Scan gespeichertem Katalogstand
- gemeinsame Einstellungen für Stichwortprofile, Dateitypen, Erkennungsregeln und Systemupdates außerhalb des Fallfensters
- Kategorien nach Dateiendung, Größenstatistik und größte Dateien
- kombinierbare und lokal bearbeitbare Stichwortprofile
- Stichwortsuche ohne Beachtung der Groß-/Kleinschreibung in Namen und Pfaden
- neutrale Sichtungsnummern `SICHT-###`; Beweismittelnummer erst bei „Sichern“
- zwei eindeutige Entscheidungen: „Sichern“ oder begründet „Nicht sichern“
- gemeinsame Entscheidungszentrale für abgezogene Medien mit noch offenem Status; keine gestapelten Einzelmeldungen
- lokale Fallakte mit Audit-Log, Medienregister, Bericht und SHA-256-Manifest
- ZIP-Export der Falldaten
- direktes Öffnen und doppelt bestätigtes Entfernen einzelner Fälle mit Dateierhalt im Papierkorb; Rückimport noch offen
- sicherer Software-Auswurf und erneute Geräteerkennung
- softwareseitiges Öffnen externer USB-CD/DVD-Laufwerke auch ohne physischen Auswurfknopf
- automatische Telefonerkennung: iPhone über reguläre Apple-USB-Dienste; Android konservativ bereits vor USB-Debugging über Hersteller-, Produkt-, Geräteklassen- und USB-Interface-Evidenz und nach Freigabe über ADB
- schneller iPhone-/Android-App-Scan mit Geräteinformationen, zugänglichen Benutzerprofilen, Benutzer-App-Liste und Krypto-Klassifikation – ohne Foto-, Medien- oder Dateisichtung
- verständliche Samsung-, Pixel-, Xiaomi-, Motorola-, OnePlus- und allgemeine Android-Anleitung, solange die Verbindung am Telefon noch nicht vorbereitet oder bestätigt ist
- gemeinsame, lokal bearbeitbare Erkennungsregeln mit getrennten iOS-Bundle-IDs und Android-Package-IDs; Wallets, Hardware-Wallet-Begleiter, Börsen, Portfolio-/Steuer-, Zahlungsdienste, Banking/Finanzen und Geräte-Backups bleiben nachvollziehbar getrennt
- Master-Detail-Editor für Erkennungsregeln mit Suche, Filter, Sortierung, Duplizieren, Löschen, JSON-Import/Export und Tooltips
- Banking-/Finanz-Apps erzeugen bewusst neutrale Hinweise; sie allein lösen keinen Krypto-Hinweis aus
- Geräte-Backup-Erkennung auf Datenträgern anhand struktureller Merkmale ohne Öffnung der Backup-Inhalte

## Wichtige Grenzen

Version 0.2.0-alpha.60 liest bei Wechseldatenträgern keine Nutzdatei-Payload. Als eng begrenzte Ausnahme werden die Verzeichnisstrukturen von ZIP-Dateien, ISO-Images sowie 7Z- und RAR-Archiven gelesen. Der normale Telefon-Schnellscan liest ausschließlich Geräte- und App-Metadaten: keine AFC-/Medienbereiche, Fotos, Dateien, Ordner, Wallet-Inhalte, Schlüssel oder Seeds. Komprimierte Archivverzeichnisse auf Datenträgern können intern dekodiert werden; Nutzdateien werden weder extrahiert noch ausgeführt. Die Stichwortsuche für Datenträger arbeitet ausschließlich auf Datei- und Ordnernamen beziehungsweise Pfaden.

Das bedeutet insbesondere:

- Eine SQLite-Datenbank, die nur in `.jpg` umbenannt wurde, wird derzeit nicht als Datenbank erkannt.
- Es gibt noch keine Magic-Byte-/Dateisignaturprüfung.
- Es werden keine gelöschten Dateien wiederhergestellt und keine Daten geschnitzt („Carving“).
- Regulär vorhandene versteckte Dateien und Ordner werden inventarisiert; nicht lesbare Einträge und interne Dateisystem-Hilfsstrukturen können beziehungsweise sollen dagegen fehlen.
- Es wird kein forensisches Image erzeugt.
- Eindeutig erkannte verschlüsselte ZIP-, 7Z- und RAR-Archive werden gekennzeichnet; Inhalte werden nicht entschlüsselt.
- Bei verschlüsselten Archivköpfen werden keine Passwörter angefordert oder ausprobiert; interne Namen bleiben verborgen.
- Die Archivstatistik nennt sicher erkannte Verschlüsselung; bei nicht unterstützten, beschädigten oder nicht vollständig geprüften Archiven steht bewusst `UNGEPRÜFT`.
- Verschachtelte Archive werden nur als Eintrag angezeigt und nicht rekursiv geöffnet. TAR und weitere Formate werden derzeit nicht katalogisiert.
- Geladene Medien in externen USB-CD/DVD-Laufwerken werden über einen eigenen, nur-lesenden Scanpfad erfasst; der reale Hardwaretest steht noch aus.
- Das System trifft keine rechtliche oder fachliche Sicherstellungsentscheidung.
- Ein App-Treffer belegt weder Wallet-Inhalte noch Vermögenswerte. „Kein Treffer“ bedeutet nur: keine passende App in der tatsächlich erfassten App-Liste. Ein technisch nicht zugängliches Profil wird ausdrücklich als ungeprüft ausgewiesen.
- Banking-/Finanz-App-Treffer sind neutral und keine Krypto-Indikatoren.
- Backup-Erkennungen belegen nur charakteristische Strukturen (Pfad, Dateiname, Endung), nie den Inhalt oder die erfolgreiche Wiederherstellung eines Backups.
- Android wird nach ausreichend sicherer USB-Evidenz schon vor aktiviertem USB-Debugging samt Anleitung angezeigt. Der App-Schnellscan erfordert weiterhin USB-Debugging und die Bestätigung am entsperrten Telefon. MTP/PTP allein gilt nicht als Android-Beleg. Arbeitsprofile werden abgefragt, soweit das System sie meldet; unzugängliche Bereiche werden nicht negativ bewertet.

Für echte Beweismittel ist ein validierter Hardware-Schreibblocker erforderlich. Der implementierte Software-Schreibschutz ist eine zusätzliche Schutzschicht, kein Ersatz dafür.

## Installation auf dem Scanner

Wenn das Repository für die Dauer der Installation bewusst öffentlich geschaltet wird, genügt auf einem per Ethernet verbundenen Raspberry Pi:

```bash
curl -fsSLo /tmp/triagebox-install.sh https://raw.githubusercontent.com/hnslng/forensic-triage/main/scripts/bootstrap_pi.sh && sudo bash /tmp/triagebox-install.sh
```

Das Skript prüft das System, installiert Git, lädt TRIAGE//BOX nach `/opt/triagebox` und führt den Pi-Installer aus. Nach dem vollständigen Abschluss kann das Repository wieder privat gestellt werden.

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

Auf Raspberry Pi OS/Debian über Ethernet beziehungsweise an der lokalen Konsole (der Installer prüft die Debian-Familie, keine bestimmte Releaseversion):

```bash
sudo ./scripts/install_debian.sh --pi
```

Das wiederholbar ausführbare Skript installiert Systempakete, Python-Umgebung, Tests, Konfiguration und systemd-Dienst. Fallakten bleiben erhalten. Bestehende Einstellungen werden grundsätzlich beibehalten; der Installer ergänzt Updateparameter, migriert passende Codepfade und setzt im Pi-Modus die Backend-Bindung auf Loopback. Einzelheiten: [Installation und Aktualisierung](docs/installation.md).

Lokale Einstellungen wie Host, Port und Speicherpfade stehen außerhalb von Git in `/etc/forensic-triage/triage.env`. Der Pi-Modus trennt WLAN-SSID und Kennwort in `/etc/forensic-triage/pi-network.env`. Siehe [Konfiguration](docs/configuration.md).

## Bedienablauf

1. Dashboard öffnen. Nach einem Pi-/Webdienst-Neustart ist **kein Fall aktiv**; nach bloßem Browser-Neuladen kann der zuletzt am Gerät gestartete Fall weiter aktiv sein.
2. Links „Fall verwalten“ wählen.
3. Neue Fallnummer eingeben oder einen vorhandenen Fall im Archiv öffnen.
4. Bearbeiterkürzel eintragen und Suchprofile auswählen.
5. „Fall starten“ ausdrücklich bestätigen.
6. Autorisierte, ungemountete USB-Datenträger oder ein Telefon anschließen. Beim iPhone Entsperren/Vertrauen bestätigen; bei Android gegebenenfalls die angezeigten Schritte und danach die Verbindungsabfrage am Telefon bestätigen. Bei aktivem Auto-Scan beginnt die passende Sichtung selbstständig.
7. Ergebnis je Medium prüfen und eine Entscheidung dokumentieren.
8. Nur bei „Sichern“ eine offizielle Beweismittel-/Asservatennummer vergeben.
9. Datenträger sicher auswerfen beziehungsweise nach abgeschlossener Sichtung abziehen.
10. PDF und bei Bedarf Falldaten als ZIP exportieren, dann Fall beenden.

Ein Fall wird direkt im Fallarchiv über „Löschen“ entfernt. Das Dashboard sperrt diese Aktion beim aktiven Fall; die zusätzliche serverseitige Fall-/Scanprüfung fehlt noch. „Löschen“ erhält die Dateien in einem internen Papierkorb; ein fertiger Rückimport in die Fallliste ist noch nicht vorhanden. Es ist keine sichere Datenvernichtung; Einzelheiten unter [Fallakte](docs/case-archive.md#entfernen-und-wiederherstellung).

Die ausführliche Bedienung steht in [docs/operation.md](docs/operation.md).

## Telefon- und Krypto-Schnellscan

TRIAGE//BOX erkennt den Gerätetyp automatisch. Beim iPhone werden nach regulärer Kopplung die gemeldeten Benutzer-Apps gelesen. Bei Android erkennt die Box verbreitete Hersteller bereits auf USB-Ebene; für die zuverlässige App-Liste führt die Oberfläche durch die einmalige Gerätefreigabe. Danach werden alle über die Android-Schnittstelle sichtbaren Benutzer-/Arbeitsprofile nacheinander abgefragt. Ein nicht zugänglicher geschützter Bereich bleibt als **nicht vollständig prüfbar** markiert.

Die lokale Regelbasis ordnet verifizierte iOS-Bundle-IDs beziehungsweise Android-Package-IDs Kategorien und Relevanzstufen zu. **HOCH** kennzeichnet etwa Self-Custody-Wallets, Hardware-Wallet-Begleiter und Börsen/Broker; **MITTEL** klar kryptobezogene Steuer-/Portfolio- und Zahlungsdienste; **NIEDRIG** vage Hinweise auf nicht katalogisierte Kandidaten; **NEUTRAL** Banking-/Finanz-, Messenger- und Cloud-Apps. App-Namen und Aliase dienen ergänzend der Erkennung, Paketkennungen werden nicht geraten. Unverifizierte Kennungen bleiben leer und werden als „ID fehlt“ gekennzeichnet. Regeln lassen sich unter **Einstellungen → Erkennungsregeln** lokal erweitern.

Der Schnellscan liest keine Wallet-Inhalte, Schlüssel, Seeds, Nachrichten, Fotos oder sonstigen Dateien. Er ist ein Triage-Hinweis: Eine erkannte Krypto-App begründet eine weitere fachliche Prüfung; Banking-/Finanz-Apps dokumentiert das System separat als neutralen Finanzhinweis. Kein Treffer ist nur für die erfolgreich erfasste App-Liste aussagekräftig. Details stehen in [iPhone-Triage](docs/iphone-triage.md) und [Android-/Mobilgerät-Triage](docs/android-triage.md).

## Live-Kit: aktueller Stand

Im aktuellen Repository gibt es **kein eigenständiges „Live-Kit“**, kein bootfähiges Live-Abbild und keinen separaten Live-Kit-Startpfad. Vorhanden sind die normale Debian/Raspberry-Pi-Installation (`scripts/bootstrap_pi.sh`, `scripts/install_debian.sh`) und signierte `.tbu`-Pakete für Anwendungsupdates. Ein `.tbu` ist kein Live-Kit: Es aktualisiert eine bereits installierte TRIAGE//BOX und kann fehlende Debian-Systempakete nicht offline nachinstallieren.

Falls künftig ein transportables Live-Kit hinzukommt, braucht es ein eigenes, geprüftes Build-Artefakt, einen dokumentierten Boot-/Vertrauenspfad, Hardwarekompatibilität und eine Abgrenzung zur installierten Pi-Box. Bis dahin bezeichnet die Dokumentation nichts Bestehendes als Live-Kit; der Punkt steht ausdrücklich in der [Roadmap](docs/roadmap.md).

## Zugriff auf die Oberfläche

Der Scanner selbst lauscht ausschließlich auf `127.0.0.1:8787`. Auf dem Pi liefert der lokale Reverse-Proxy die Oberfläche portfrei unter `http://triagebox.local/`. Er akzeptiert den privaten TRIAGEBOX-Hotspot sowie private LAN-Adressen, damit ein per Ethernet am gemeinsamen Router-LAN angeschlossener Pi ohne WLAN-Wechsel bedient werden kann. Die direkte Kabelverbindung Pi–Laptop ohne Router benötigt noch die geplante Ethernet-Konfiguration. HTTPS und die spätere Web-Entsperrung bleiben vor einem realen Einsatz offen.

Der Pi prüft beim Start mit Verzögerung und anschließend täglich nur auf neue Git-Tags. Er installiert niemals selbstständig. Unter **Einstellungen → System & Updates** kann ein freigegebenes Online-Update bewusst installiert oder ein signiertes `.tbu`-Paket vollständig offline über den TRIAGEBOX-Hotspot hochgeladen werden. Beides ist bei aktivem Fall oder laufendem Scan serverseitig gesperrt. Die neue Version wird getrennt vorbereitet und mit Python-Tests geprüft; der Code wird über einen atomaren Symlinkwechsel aktiviert. Nach dem notwendigen Neuladen bleibt die Updateansicht ohne Dashboard-Zwischenbild erhalten und bestätigt den erfolgreichen Abschluss sichtbar. Offline-Pakete werden zusätzlich anhand ihrer Signatur, vollständigen Dateiliste und SHA-256-Prüfsummen geprüft. Die Systemleiste zeigt auf Raspberry-Pi-Hardware nur bei einem aktuellen oder seit dem Boot registrierten Stromproblem einen farbigen Blitz; Neustart und Herunterfahren liegen getrennt im Power-Menü, benötigen eine zweite Bestätigung und sind während Fall, Scan oder Update gesperrt. Einzelheiten und Grenzen: [Offline-Updates](docs/offline-updates.md) und [Installation](docs/installation.md#5-aktualisieren).

Entwicklungs- und Validierungsaufbauten sind interne technische Nachweise und kein Bestandteil der Pi-Bedienung.

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
- [Aktueller Projektstand und Nachweise](docs/project-status.md)
- [So funktioniert TRIAGE//BOX](docs/how-it-works.md)
- [Installation und Aktualisierung](docs/installation.md)
- [Signierte Offline-Updates](docs/offline-updates.md)
- [Konfiguration](docs/configuration.md)
- [Einstellungen: Stichwortprofile, Dateitypen und Erkennungsregeln](docs/settings.md)
- [Erkennungsregeln: Krypto, Banking, Backups, Dateihinweise](docs/detection-rules.md)
- [Gerätebackup-Erkennung](docs/device-backups.md)
- [Bedienung und Fallworkflow](docs/operation.md)
- [Forensische Sicherheitsgrenzen](docs/forensic-safety.md)
- [Architektur](docs/architecture.md)
- [Lokale Fallakte und Protokollierung](docs/case-archive.md)
- [Testplan](docs/test-plan.md)
- [Realistische USB-/CD-Testmedien](docs/test-media.md)
- [iPhone-Krypto-Schnellscan, Grenzen und Realtest](docs/iphone-triage.md)
- [Android-/Telefon-Triage und Gerätefreigabe](docs/android-triage.md)
- [Validierung mit physischem Medium](docs/validation-2026-08-26.md)
- [Roadmap und offene Aufgaben](docs/roadmap.md)
- [Sicherheitsrichtlinie](SECURITY.md)
- [Nutzungsbedingungen](LICENSE.md)
- [Änderungshistorie](CHANGELOG.md)

## Datenschutz und Git

Das Repository enthält ausschließlich Quellcode, Profile, Tests und Dokumentation. Folgendes darf niemals eingecheckt werden:

- echte Fall- oder Beweismitteldaten
- Verzeichnisse `casefiles/` und `results/`
- echte Kennwörter, Tokens, private SSH-Schlüssel oder `.env`-Dateien; der dokumentierte Alpha-Platzhalter ist kein Betriebsgeheimnis
- Exporte aus echten Einsätzen

Vor realem Betrieb muss das Fallarchiv auf verschlüsseltem, zugriffsgeschütztem Speicher liegen. Der Löschdialog verlangt zwei bewusste Bedienhandlungen für den konkret genannten Fall; entfernte Fallordner bleiben im internen Papierkorb erhalten. Für vollständige Wiederherstellung müssen auch Fallindex, Profile und Konfiguration konsistent gesichert werden.

## Projektstatus

- Paketversion: `0.2.0a81` (Python/PEP 440)
- Git-/Releasebezeichnung: `v0.2.0-alpha.81`
- automatisierte Tests: 303 Python-Prüfungen und 102 isolierte Browserprüfungen; darin Fallzeitraum-Validierung, B/M/C/A-Coverage und Klassifikation, FAST/statx-Sicherheitsverhalten, persistente Snapshots und Exporte sowie responsive Zeitraum-UI
- dokumentierter Sollvergleich: SanDisk/exFAT im beschriebenen VM-Test vom 26. August 2026
- praktisch in Betrieb: Raspberry Pi 3B+, Hotspot/LAN, portfreie Adresse, USB-Sichtungen und bewusste Updates; drei reale USB-Sticks wurden bereits ausprobiert
- offen: reale Android-/Samsung-Abnahme, erneuter iPhone-Zeitvergleich der neuen App-only-Version, vollständiger Probeeinsatz, systematische Parallel-/Störungstests, Datenwiederherstellung, Schutzkonzept und formale Freigabe
- Dokumentationsstand: 5. Oktober 2026; der [Projektstand](docs/project-status.md) unterscheidet vorhandene Funktionen von abgeschlossenen Nachweisen

Siehe [docs/roadmap.md](docs/roadmap.md) für die priorisierten nächsten Schritte.

## English summary

TRIAGE//BOX is a local field-triage aid for removable media. It starts locked after a service/device restart (a browser reload resumes the active device session), requires an explicit case and operator session, can scan eligible USB disks in parallel, and stores metadata inventories, keyword hits, decisions, and integrity manifests in a local case archive.

The default fast mode temporarily mounts partitions with `ro,nosuid,nodev,noexec` only after the whole block device has been set to and verified as read-only. A slower mount-free TSK directory walk remains available for testing. Software read-only controls do not replace a validated forensic hardware write blocker.

Version 0.2.0-alpha.75 adds optional case-period timestamp evaluation for removable-media metadata, immutable period snapshots per scan, and corresponding case/register/TXT/PDF reporting. FAST uses a direct Linux `statx` metadata call when available, with an `os.stat` fallback and no per-file subprocess; birth time is reported only when the platform provides it. Android and iPhone scans remain app-only, with period evaluation marked not applicable. Android recognition and ADB behavior were not changed. No new real hardware acceptance was performed for Alpha 75. TRIAGE//BOX searches removable-media names and paths, not file payloads; phone quick scans read device and user-app metadata only, never phone files, photos, wallet contents, keys or seeds. Installation details are in [docs/installation.md](docs/installation.md); phone scope is in [docs/iphone-triage.md](docs/iphone-triage.md) and [docs/android-triage.md](docs/android-triage.md).
