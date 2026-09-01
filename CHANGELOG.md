# Änderungshistorie / Changelog

Das Format orientiert sich an „Keep a Changelog“. Das Projekt verwendet semantische Versionsnummern; Alpha-Versionen sind nicht für ungeprüften Einsatz bestimmt.

## [0.2.0-alpha.31] – 2026-09-02

### Geändert

- Entscheidungsworkflow auf die eindeutigen Zustände `SICHERN` und `NICHT SICHERN` reduziert; Nicht-Sicherung verlangt weiterhin eine strukturierte Begründung.
- historischer Status „Weitere Prüfung“ bleibt in bestehenden Akten lesbar, kann aber nicht mehr neu gespeichert werden.
- doppelte Fallnummer und Bearbeiterangabe aus der Fallsteuerungsleiste entfernt; die große Kopfanzeige ist nun die einzige primäre Fallanzeige.
- zentrale Bedien-, Geräte-, Status- und Modalbeschriftungen für Laptop- und Kleinbildschirme vergrößert.
- Systemschaltfläche zeigt die installierte Version direkt und blendet nur relevante Updatezustände zusätzlich ein.
- sichtbare Uhr von UTC auf die lokale Browserzeit umgestellt; Audit- und Nachweiszeitstempel bleiben unverändert in UTC.

### Tests

- 73 automatisierte Tests erfolgreich, einschließlich serverseitiger Ablehnung des historischen Entscheidungsstatus und Prüfung auf genau zwei Entscheidungsbuttons.

## [0.2.0-alpha.30] – 2026-09-02

### Behoben

- die installierte Version bleibt im Systemdialog sichtbar, auch wenn eine fehlgeschlagene Update-Aktion keinen Versionswert in ihre Statusdatei geschrieben hat.
- ein Fehler der Update-Prüfung wird im Kopf ausdrücklich als `UPDATE-FEHLER` bezeichnet und nicht mehr als allgemeiner Systemfehler.

### Tests

- 71 automatisierte Tests erfolgreich, einschließlich Versions-Fallback bei unvollständigen Fehlerstatusdaten.

## [0.2.0-alpha.29] – 2026-09-02

### Behoben

- der sichere Updater akzeptiert nun sowohl normale Git-Checkouts als auch die von ihm selbst erzeugten verknüpften Git-Worktrees.
- ein installierter Release wird nicht mehr fälschlich mit `AKTUELLE INSTALLATION IST KEIN GIT-CHECKOUT` abgewiesen.

### Tests

- 70 automatisierte Tests erfolgreich, einschließlich Prüfung auf Unterstützung verknüpfter Git-Worktrees.

## [0.2.0-alpha.28] – 2026-09-02

### Behoben

- erneutes manuelles Ausführen des Installers schaltet den Laufzeit-Symlink nun auf den tatsächlich geprüften Checkout; ein alter atomarer Release bleibt nicht irrtümlich aktiv.
- `triagebox.local` fällt im privaten LAN nicht mehr auf einen von nginx abgewiesenen globalen IPv6-Zugang, sondern verwendet den vorgesehenen IPv4-Zugang.

### Tests

- 69 automatisierte Tests erfolgreich, einschließlich Laufzeit-Symlink und IPv4-only-Reverse-Proxy.

## [0.2.0-alpha.27] – 2026-09-02

### Behoben

- Update-Prüfung zeigt während des asynchronen Systemdienststarts nicht mehr kurz den veralteten vorherigen Status.
- Update-Installation bleibt sichtbar in Bearbeitung, wartet einen vorübergehenden Neustart des Webdienstes ab und lädt die Oberfläche nach Erfolg neu.
- Blockierende Fälle oder Scans werden direkt und konkret im Systemdialog angezeigt, statt nur im allgemeinen Bestätigungstext erwähnt zu werden.

### Geändert

- Oberfläche fragt den tatsächlichen systemd-Arbeitsstatus bis zum Ergebnis ab; die Prüfung hat 30 Sekunden, die getestete Installation höchstens 15 Minuten Zeit.
- Installationsbestätigung beschreibt nur noch den tatsächlichen Dienstneustart; Voraussetzungen werden vor dem Dialog geprüft.

### Tests

- 68 automatisierte Tests erfolgreich, einschließlich Statusermittlung der getrennten Update-Dienste.

## [0.2.0-alpha.26] – 2026-09-02

### Behoben

- zweite veraltete `/dev/sda`-Sperre im eigentlichen Scanner entfernt; ein ungemounteter Sichtungsstick auf `/dev/sda` kann nun gescannt werden.
- eingehängte Systemdatenträger bleiben unabhängig vom Linux-Gerätenamen weiterhin zwingend gesperrt.
- konkreter Scanfehler bleibt direkt in der Medienkachel sichtbar, statt nur als allgemeiner Kopfstatus zu erscheinen.

### Geändert

- System- und Update-Funktionen aus der engen weißen Statusleiste in einen eigenen kompakten Dialog verschoben.
- aktueller Stand wird eindeutig als `KEIN UPDATE VERFÜGBAR` dargestellt.
- portfreie Oberfläche ist zusätzlich über private Ethernet-/WLAN-Netze erreichbar; der Python-Dienst bleibt ausschließlich an `127.0.0.1` gebunden.
- der Release-Updater übernimmt künftig geprüfte nginx- und systemd-Vorlagen einer neuen Version.

## [0.2.0-alpha.25] – 2026-09-02

### Behoben

- Systemdatenträger wird anhand des tatsächlich eingehängten Root-Dateisystems ausgeschlossen, nicht mehr anhand des instabilen Gerätenamens `/dev/sda`.
- USB-Datenträger bleiben dadurch auch nach einer beim Neustart geänderten Linux-Gerätereihenfolge sichtbar.
- Update-Skript wird ausführbar ausgeliefert, damit Prüfung und Statusanzeige tatsächlich starten.

### Tests

- vertauschte Gerätenamen von System-SSD und Sichtungsstick reproduziert und abgesichert.
- ausführbares Update-Skript als Installationsvoraussetzung abgesichert.

## [0.2.0-alpha.24] – 2026-09-01

### Hinzugefügt

- portfreie Pi-Adresse `http://triagebox.local/` über einen lokalen nginx-Reverse-Proxy; der Python-Dienst bleibt auf `127.0.0.1:8787`.
- tägliche reine Prüfung auf freigegebene Git-Release-Tags, zusätzlich fünf Minuten nach dem Start.
- Dashboard-Aktionen „Update prüfen“ und „Update installieren“.
- getrennte Update-Vorbereitung mit Testlauf, atomarem Versionswechsel und automatischer Rückkehr zur Vorversion, falls der neue Webdienst nicht startet.

### Sicherheit

- der Reverse-Proxy akzeptiert ausschließlich lokale Zugriffe sowie Geräte aus dem privaten `10.42.0.0/24`-Hotspot.
- die Update-Installation wird serverseitig abgewiesen, solange ein Fall aktiv ist oder ein Scan läuft.
- die zeitgesteuerte Prüfung installiert niemals selbstständig eine neue Version.

## [0.2.0-alpha.23] – 2026-08-30

### Geändert

- sichtbaren Begriff „Auftrag“ durch den fachlich eindeutigen Begriff „Fall“ ersetzt.
- Einstieg als „Fall anlegen / öffnen“ links vor Fallstatus und Suchprofilen angeordnet.
- Button wechselt bei aktiver Sitzung zu „Fall verwalten“ und wird optisch zurückgenommen.
- Falldialog als „Fall anlegen oder öffnen“ eindeutig beschriftet.

## [0.2.0-alpha.22] – 2026-08-30

### Geändert

- Archive lassen sich nun auch direkt in der nach Dateityp gefilterten Tabelle aufklappen.
- redundante ZIP-/7Z-/RAR-Formatplakette neben dem bereits eindeutigen Dateinamen entfernt.

### Tests

- API-Metadaten für aufklappbare Container in gefilterten Ergebnissen abgesichert.

## [0.2.0-alpha.21] – 2026-08-30

### Hinzugefügt

- begrenzte Verzeichnisauflistung für 7Z- und RAR-Archive über Debians `7zip`
- eigene sichtbare Zustände für verschlüsselte Archivköpfe, fehlende Teilvolumes und fehlendes Werkzeug
- konservative Verschlüsselungsstatistik über ZIP, 7Z und RAR
- automatische Installation des benötigten `7zip`-Systempakets

### Sicherheit

- ausschließlich Listenmodus ohne Extraktion, Dekompression oder rekursive Öffnung
- geschlossene Standardeingabe und damit keine interaktiven Passwortversuche
- bestehendes gemeinsames Zeit- und Mengenbudget gilt unverändert auch für 7Z und RAR

## [0.2.0-alpha.20] – 2026-08-30

### Hinzugefügt

- kompakte Verschlüsselungsangabe direkt unter der Kategorie `ARCHIVE`
- konservative Aufteilung in `VERSCHLÜSSELT`, nachweislich nicht verschlüsselt und `UNGEPRÜFT`
- sichtbare Verschlüsselungskennzeichnung am aufklappbaren ZIP-Container

### Sicherheit

- nicht unterstützte, beschädigte oder wegen eines Limits nur teilweise gelesene Archive werden niemals als unverschlüsselt angenommen
- keine Passwortversuche, Entschlüsselung oder zusätzliche Rekursion

## [0.2.0-alpha.19] – 2026-08-30

### Hinzugefügt

- begrenzter, nicht extrahierender Verzeichnisindex für ZIP-Dateien und ISO-Images
- aufklappbare ZIP-/ISO-Container im vorhandenen Datei-Explorer
- freie Pfad- und Stichwortsuche über katalogisierte interne Dateinamen
- sichtbare Zustände für beschädigte beziehungsweise wegen Limits unvollständige Container

### Sicherheit

- gemeinsames Standard-Zeitbudget von drei Sekunden und Mengenlimits je Medium
- keine Dekompression, keine Extraktion und keine rekursive Öffnung verschachtelter Archive
- äußere Datei-/Ordnerzahlen und Datenvolumen bleiben von virtuellen Containerpfaden unberührt

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
