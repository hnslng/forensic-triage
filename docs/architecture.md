# Architektur / Architecture

## Überblick

TRIAGE//BOX trennt Scanner, Fallarchiv und Bedienoberfläche. Die Weboberfläche führt keine eigene Klassifizierung durch, sondern ruft denselben abgesicherten Scanner auf wie die CLI.

```text
Browser
  └─ lokale Weboberfläche (HTML/CSS/JS)
       └─ Python-Webdienst und paralleler Koordinator
            ├─ Geräteerkennung und Sicherheitsprüfungen
            ├─ Telefon-Schnellscan
            │    ├─ iPhone: Apple-Geräte- und Benutzer-App-Metadaten
            │    └─ Android: USB-Vorerkennung, ADB, Benutzerprofile und Apps
            ├─ Scanner: fast oder tsk
            │    ├─ Partitionserkennung
            │    ├─ Metadaten-Inventar
            │    ├─ begrenzter ZIP-/ISO-/7Z-/RAR-Verzeichnisindex
            │    ├─ Klassifizierung und Stichwortsuche
            │    └─ JSON/CSV/Log-Ergebnisse
            └─ Fallarchiv
                 ├─ SQLite-Index
                 ├─ lesbare Exporte
                 └─ SHA-256-Manifest
```

## Scanner

Der Scanner besitzt einen gemeinsamen Orchestrierungspfad und zwei Inventarmodi:

- `device` erzwingt Identitäts-, Mount- und Read-only-Bedingungen.
- `partitions` liest dynamische Partitionsgrenzen aus `mmls`.
- `fast_inventory` ordnet Partitionen Linux-Geräten zu und führt einen kurzzeitigen verifizierten Read-only-Mount aus.
- `filesystem` verarbeitet `fsstat` sowie das Bodyfile-Format von `fls` im TSK-Modus.
- `classifier`, `keywords` und `statistics` erzeugen objektive Ableitungen aus Metadaten.
- `container_inventory` katalogisiert ZIP-, ISO-, 7Z- und RAR-Verzeichnisstrukturen mit Mengenlimits und Zeitbudget, ohne Nutzdateien zu extrahieren. Das Budget ist keine harte Grenze für jeden Bibliotheks-/Kernelzugriff. 7Z und RAR werden über Debians `7z` ausschließlich im Listenmodus verarbeitet. Eine gemeinsame Einstufung nach Partition und Pfad liefert Verschlüsselungszähler, Statusfilter und Explorerkennzeichnung; die Leseansichten verwenden ausschließlich den gespeicherten Index.
- `reporting` schreibt normalisierte Ergebnisse und behält rohe Werkzeugausgaben.

Der Standardmodus `fast` liest aktive Verzeichniseinträge über einen Mount mit `ro,nosuid,nodev,noexec`, nachdem das gesamte Blockgerät schreibgeschützt wurde. `tsk` verwendet `fls -u` ohne Mount und ist auf großen Datenträgern erheblich langsamer.

## Webdienst und Parallelität

Der Webdienst erkennt Blockgeräte mit `lsblk`, iPhones getrennt über `idevice_id` und Android-Kandidaten über USB-Herstellerkennungen plus `adb devices -l`. Fehler eines Telefonadapters dürfen USB-/CD-Erkennung oder den jeweils anderen Telefonadapter nicht blockieren. Pro physischem Gerätepfad, `iphone:<UDID>` oder `android:<ADB-Serienkennung>` ist höchstens ein Worker aktiv. Einzelbefehle und Gesamtscan besitzen eigene Zeitlimits. Nach einer Überschreitung wird der betroffene Gerätepfad bis zum erkannten Abziehen gesperrt. Die Prozessisolation soll andere Scans und den Webdienst verfügbar halten; ein blockierter Kernel, USB-Bus oder Systemdatenträger kann diese Trennung dennoch überwinden.

Telefon-Worker verwenden dieselbe Prozess- und Fallarchitektur, aber keine Blockgeräteoperationen. `iphone.py` liest nach regulärer Kopplung Basis- und Benutzer-App-Metadaten. `android.py` erkennt Geräte schon ohne ADB auf USB-Ebene, verfolgt Autorisierungszustände und liest nach Freigabe die Drittanbieterpakete aller gemeldeten Benutzerprofile. Nur bei tatsächlich klassifizierten Android-Paketen wird zusätzlich die Paketversion abgefragt. Weder Pfad bindet Telefondateisysteme ein. `phone.json`, plattformspezifisches `iphone.json`/`android.json` und `apps.json` ergänzen die gemeinsame Ergebnisstruktur; `files.csv` bleibt beim Schnellscan absichtlich leer.

Bei USB-Speichern dient die gemeldete Datenträgerseriennummer als Wiedererkennungsmerkmal. Bei CD/DVD darf die Seriennummer des Laufwerks nicht als Identität der eingelegten Scheibe gelten. Dort bildet der Webdienst deshalb eine Medienkennung aus vorhandener Volume-UUID, Volume-Label und Kapazität. Diese Kennung ist eine praktische Grobsichtungsidentität und keine kryptografische Prüfsumme des optischen Mediums.

Sichtungsnummern werden in einer unmittelbaren SQLite-Transaktion reserviert. Lesbare Fallexporte werden serialisiert. Dadurch dürfen parallele Scans weder dieselbe `SICHT-###`-Nummer erhalten noch gleichzeitig denselben Bericht überschreiben.

Der aktive Fall liegt als gemeinsame Sitzung im Arbeitsspeicher des Webdienstes (`ACTIVE_CASE_SESSION`). Nach einem Dienst-/Pi-Neustart ist sie leer. Beim Browser-Neuladen übernimmt `syncCaseSessionFromServer()` eine noch laufende Gerätesitzung einschließlich Fallnummer und Bearbeiter. Das ist keine Benutzeranmeldung. Ein gewünschter erneuter Freigabeschritt nach Browser-/Netzwerkverlust bleibt ein offener Workflow-Punkt.

## Geräteerkennung bei Störungen

Dashboard-Status und manuelles Aktualisieren verwenden eine gemeinsame, nicht blockierend belegte Erkennungssperre. `lsblk` hat ein eigenes kurzes Zeitlimit. Fehler führen zu einer zehnsekündigen Pause und einem ausdrücklich veralteten Gerätebestand (`device_error`). Gleichzeitige Statusanfragen erhalten den letzten Stand, ohne weitere Gerätebefehle zu starten. Im laufenden Dienst werden Quarantänen nur nach erfolgreicher Erkennung eines fehlenden Geräts bereinigt; nach Dienstneustart ist die bisher rein speicherbasierte Quarantäneliste leer. Der Browser sperrt neue Medienaktionen während eines unbekannten Verbindungszustands; gespeicherte Fallakten bleiben lesbar. Diese Maßnahmen ersetzen keine funktionierende Stromversorgung und können einen blockierten Systemdatenträger nicht isolieren.

## Stichwortprofile und Dateityp-Katalog

Seit Alpha 44 liegen bearbeitete Profile als YAML-Dateien unter `FORENSIC_TRIAGE_SETTINGS_ROOT/profiles`. `settings.py` übernimmt vorhandene Profile ohne Überschreiben lokaler Kopien und verwaltet den versionierten Dateityp-Katalog. Katalogspeicherung verwendet einen atomaren Dateiaustausch und eine Prüfung des zuletzt gelesenen Hashes gegen konkurrierende Änderungen. Mehrere ausgewählte Profile werden vor dem Scan zusammengeführt und Begriffe dedupliziert. Die tatsächlich ausgewählte Liste sowie Profilversion und SHA-256-Profilhash werden mit dem Scan gespeichert.

Der Webdienst übergibt einen Katalog-Snapshot an den isolierten Worker. Vor Statistik und Export ordnet `apply_catalog()` sowohl äußere Dateien als auch virtuelle Archivdateien anhand desselben Snapshots ein. `filetype-catalog.json` und die Referenz in `summary.json` dokumentieren diesen Stand; Leseansichten greifen weiterhin auf gespeicherte Kategorien zu. Die technische Auswahl unterstützter Archivleser bleibt davon getrennt. Migrationsdetails stehen in [settings.md](settings.md).

`crypto_rules.py` verwaltet zusätzlich eine gemeinsame, versionierte Regelsammlung. App-Regeln führen getrennte `ios_bundle_ids` und `android_package_ids`, dazu Namen, Aliase, Kategorie und Relevanz. Der Webdienst übergibt denselben unveränderlichen Stand an iPhone-, Android- und Medien-Worker. Telefon-Worker prüfen ausschließlich App-Metadaten; der Medien-Worker kann weiterhin Dateinamen-/Pfadregeln einschließlich katalogisierter virtueller Containerpfade prüfen. `crypto-rules.json` und `crypto-hints.json` speichern Regelstand und konkrete Gründe pro Sichtung. Laufende und historische Scans werden durch Einstellungsänderungen nicht umklassifiziert.

Die Suche arbeitet ausschließlich auf Namen und Pfaden, einschließlich katalogisierter ZIP-/ISO-/7Z-/RAR-Pfade. Sie ist nicht gleichbedeutend mit Inhaltsanalyse oder struktureller Erkennung eines Wallets.

## Frontend

`web/index.html`, `web/styles.css` und `web/app.js` bilden eine lokale Oberfläche ohne externes Frontend-Framework. IDs sind feste Bindungen für die Ereignislogik. Dialoge werden nativ mit `<dialog>` umgesetzt; bei verschachtelten Dialogen wird der Hintergrund nur auf der obersten Ebene abgedunkelt.

## Updatepfade

Der Online-Updater bereitet einen Git-Tag in einem eigenen Release-Verzeichnis vor. Der Offline-Pfad streamt ein signiertes `.tbu`-Paket zunächst in eine atomar ersetzte Übergabedatei. `offline_update.py` prüft die SSH-Signatur und anschließend jeden manifestierten regulären Dateieintrag, bevor es in ein temporäres Verzeichnis unter dem Release-Root schreibt und dieses atomar benennt. Abweichende Abhängigkeiten werden offline abgelehnt. Beide Wege führen danach denselben Test-, Vorlagen-, Laufzeitlink- und Dienststartpfad aus. Eine flüchtige Installationssperre verhindert parallel neue Fall- und Scanstarts.

## Sicherheitsgrenze

Version 0.2.0-alpha.60 liest bei Dateimedien Namen, Pfade, Endungen, Größen und Dateisystemmetadaten. Bei Telefonen liest sie ausschließlich vom Betriebssystem gemeldete Geräte- und App-Metadaten; keine Telefondateien oder Medien. Regulär vorhandene versteckte Einträge auf Dateimedien werden mit erfasst; gelöschte und ausgewählte interne Dateisystemeinträge werden bewusst nicht wiederhergestellt. Zusätzlich werden Verzeichnisstrukturen von ZIP-Dateien, ISO-Images sowie 7Z- und RAR-Archiven zeitlich und mengenmäßig begrenzt gelesen; Nutzdaten werden nicht extrahiert, dekomprimiert oder interpretiert. Recovery, Carving und Imaging liegen außerhalb des Umfangs.

## English summary

The browser calls a local Python service, which coordinates one guarded worker per eligible physical device. Storage workers use read-only metadata inventory; iPhone and Android workers collect device and user-app metadata only and share one versioned crypto-rule snapshot. Android USB detection, ADB authorization and visible profiles are explicit states. Atomic SQLite sighting reservations and serialized exports protect parallel case records. Signed dependency-compatible offline bundles update application code, but cannot add a missing Debian `adb` package. Persistent diagnostics remain bounded; the scanner does not inspect file signatures, phone files or payloads.
