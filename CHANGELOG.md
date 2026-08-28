# Änderungshistorie / Changelog

Das Format orientiert sich an „Keep a Changelog“. Das Projekt verwendet semantische Versionsnummern; Alpha-Versionen sind nicht für ungeprüften Einsatz bestimmt.

## [0.2.0-alpha.18] – 2026-08-28

### Hinzugefügt

- Raspberry-Pi-Bootstrap für den Ein-Befehl-Ablauf bei kurzzeitig öffentlichem Repository
- wiederholbare Installation beziehungsweise Aktualisierung unter `/opt/triagebox`
- Schutz vor Überschreiben lokaler Codeänderungen im Bootstrap

### Geändert

- Pi-Installation im Einstieg priorisiert und internen Mac-/VM-Aufbau aus den Bedienunterlagen herausgelöst
- Entwicklungsaufbau und frühere VM-Validierung als interne, weiterhin reproduzierbare Nachweise eingeordnet
- Installationsbesitz am tatsächlichen Eigentümer des Projektordners ausgerichtet

## [0.2.0-alpha.17] – 2026-08-28

### Hinzugefügt

- opt-in Raspberry-Pi-Installation über `install_debian.sh --pi`
- getrennte, root-geschützte Hotspot-Konfiguration unter `/etc/forensic-triage/pi-network.env`
- vorbereiteter WPA2-Hotspot `TRIAGEBOX`, Hostname `triagebox`, Avahi/mDNS und feste Adresse `10.42.0.1`
- eigener nftables-Weiterleitungsschutz gegen Internet-/Ethernet-Routing aus dem Hotspot
- Schutz vor dem Abbruch einer laufenden SSH-Sitzung über `wlan0`

### Dokumentiert

- Entwicklungskennwort `triagebox123` klar als öffentlich bekannten Alpha-Wert ausgewiesen
- Pi-Installation, Kennwortwechsel, Adresse und noch ausstehende Hardwarevalidierung beschrieben

## [0.2.0-alpha.16] – 2026-08-28

### Hinzugefügt

- eigener Scanner-Prozess je Datenträger mit privatem Linux-Mount-Namensraum
- konfigurierbares Gesamtzeitlimit von 180 Sekunden und Befehlszeitlimit von 15 Sekunden
- Gerätequarantäne nach Zeitüberschreitung bis zum erkannten physischen Trennen
- direkter, nur-lesender Inventarpfad für eingelegte Medien in externen USB-CD/DVD-Laufwerken
- roter Dashboard-Zustand `MEDIUM ANTWORTET NICHT` ohne automatische Endloswiederholung

### Geändert

- Geräte-, Mount-, TSK-, Auswerf- und Aktualisierungsbefehle zeitlich begrenzt
- systemd-Dienst verwendet private Mounts und beendet Worker als gemeinsame Kontrollgruppe
- Fehler-, Timeout-, Quarantäne- und optische Scanpfade durch zusätzliche Tests abgesichert

## [0.2.0-alpha.15] – 2026-08-28

### Dokumentiert

- einfaches Zugriffsschutzkonzept für den geplanten Raspberry-Pi-Feldbetrieb festgehalten
- passwortgeschützten WPA3-/WPA2-Hotspot, gemeinsames Gerätepasswort, kurze Sitzung und lokales HTTPS als Zielbild definiert
- verschlüsselten Fallspeicher, Firewall-, Wiederherstellungs- und Sicherheitstests als Pflicht vor echtem Einsatz ergänzt
- zentrale Benutzerverwaltung für den ersten Feldprototyp bewusst ausgeschlossen; Bearbeiterkürzel bleibt Audit-Angabe statt Anmeldung

## [0.2.0-alpha.14] – 2026-08-28

### Geändert

- linken Innenabstand der Dateitypliste reduziert
- Zahlenspalte schmaler gesetzt und dadurch gesamten Tabellenblock nach links verschoben
- mobile Ausrichtung entsprechend angeglichen

## [0.2.0-alpha.13] – 2026-08-28

### Geändert

- Dateitypliste bündig an den Innenrändern des Panels ausgerichtet
- Balkenspalte bis zum rechten Innenrand flexibel verbreitert
- übermäßige Fettschrift der Kategorien an die übrigen Ergebnislisten angeglichen
- Zahlenspalte kompakter gestaltet, ohne ihre tabellarische Ausrichtung aufzugeben

## [0.2.0-alpha.12] – 2026-08-28

### Geändert

- Dateitypen als ruhige unsichtbare Tabelle mit Zahl, Bezeichnung und Balken angeordnet
- Zahlen rechtsbündig mit tabellarischen Ziffern vor die Bezeichnung gesetzt
- alle Vergleichsbalken auf identische Start- und Endpositionen ausgerichtet
- aktive Filterzeile verändert die Spaltenpositionen nicht mehr

## [0.2.0-alpha.11] – 2026-08-28

### Bereinigt

- Mac-/VM-spezifische Startervorlage aus dem Repository entfernt
- persönliche lokale Startdatei bleibt weiterhin durch `.gitignore` ausgeschlossen
- Entwicklungs- und Veröffentlichungsdokumentation entsprechend berichtigt

## [0.2.0-alpha.10] – 2026-08-28

### Geändert

- Dateitypen wieder als platzsparende Ein-Zeilen-Liste dargestellt
- kurze Vergleichsbalken rechts neben der zusammengehörigen Bezeichnung und Trefferzahl platziert
- Fokusrahmen der Löschbestätigung von allgemeinem Grün auf Warnrot angepasst

## [0.2.0-alpha.9] – 2026-08-28

### Geändert

- Dateityp und Trefferzahl als kompakte Kopfzeile direkt zusammengeführt
- Balken jeweils unmittelbar darunter angeordnet
- dreigeteilte Ergebnisstruktur unverändert beibehalten

## [0.2.0-alpha.8] – 2026-08-28

### Geändert

- Dateityp-Balken wieder deutlicher sichtbar und kompakter angeordnet
- Trefferzahl direkt hinter dem verkürzten Balken platziert
- „Filter aufheben“ bei aktiver Filterung unmittelbar neben „Suchen“ eingeblendet

## [0.2.0-alpha.7] – 2026-08-28

### Geändert

- Fallarchiv-Einträge und Aktionsschaltflächen behutsam vergrößert
- Löschbestätigung als klar links ausgerichtete Checkbox-Zeile repariert
- Zweck von lokaler Mac-Startdatei und versionierter Beispielvorlage ausdrücklich dokumentiert

## [0.2.0-alpha.6] – 2026-08-28

### Geändert

- Dateitypen und Stichworttreffer öffnen die dazugehörige Metadaten-Dateiliste
- aktiver Ergebnisfilter wird kompakt und ohne zusätzliche Kastenoptik markiert
- doppeldeutige Rücksprungschaltflächen durch einen kontextbezogenen Befehl „Filter aufheben“ ersetzt
- freie Dateinamen-/Pfadsuche und Ergebnisfilter in Bedienung und Dokumentation klar getrennt
- Trefferquelle wird als Dateiname, Ordnerpfad oder Pfad ausgewiesen

## [0.2.0-alpha.5] – 2026-08-27

### Geändert

- Löschpasswort vollständig entfernt
- Löschdialog und Server verlangen eine ausdrückliche Bestätigung für den konkret genannten Fall
- endgültige Schaltfläche bleibt bis zur Bestätigung deaktiviert
- Entfernen bleibt eine wiederherstellbare Verschiebung in den internen Papierkorb

## [0.2.0-alpha.4] – 2026-08-27

### Sicherheit

- festes Entwicklungs-Löschpasswort aus Programmcode und Konfigurationsvorlage entfernt
- Installer erzeugt einen zufälligen lokalen Wert und migriert die alte Entwicklungsvorgabe automatisch
- Fallentfernung bleibt bei fehlender Passwortkonfiguration serverseitig gesperrt
- Sicherheitsrichtlinie und Prüfung des vollständigen Git-Verlaufs dokumentiert

### Veröffentlichung

- Repository-Dokumentation für öffentliche Lesbarkeit vorbereitet
- persönliche Starterkonfiguration durch eine neutrale, kopierbare Vorlage ersetzt
- konservative Nutzungsbedingungen ergänzt; eine spätere Open-Source-Lizenz bleibt eine gesonderte Entscheidung
- automatischer GitHub-Testlauf für Pushes und Pull Requests ergänzt

## [0.2.0-alpha.3] – 2026-08-27

### Hinzugefügt

- kompakter PDF-Grobsichtungsbericht im A4-Querformat mit einer Zeile je Datenträger
- separater PDF-Download im Dashboard; der vollständige ZIP-Export enthält den Bericht ebenfalls
- technische Grobinhaltsangabe aus Dateikategorien sowie Entscheidung und dokumentierte Begründung

### Validiert

- PDF-Erzeugung und Aufnahme in das SHA-256-Manifest werden automatisiert geprüft

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
