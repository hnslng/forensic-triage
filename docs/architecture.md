# Architektur / Architecture

## Überblick

TRIAGE//BOX trennt Scanner, Fallarchiv und Bedienoberfläche. Die Weboberfläche führt keine eigene Klassifizierung durch, sondern ruft denselben abgesicherten Scanner auf wie die CLI.

```text
Browser
  └─ lokale Weboberfläche (HTML/CSS/JS)
       └─ Python-Webdienst und paralleler Koordinator
            ├─ Geräteerkennung und Sicherheitsprüfungen
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

Der Webdienst erkennt Geräte mit `lsblk`, führt geeignete USB- und optische Medien getrennt und reserviert pro physischem Gerätepfad höchstens einen laufenden Worker-Prozess. Jeder Worker ruft den abgesicherten Scanner in einem privaten Linux-Mount-Namensraum auf. Einzelbefehle und Gesamtscan besitzen eigene Zeitlimits. Nach einer Überschreitung wird der betroffene Gerätepfad bis zum erkannten Abziehen gesperrt. Die Prozessisolation soll andere Scans und den Webdienst verfügbar halten; ein blockierter Kernel, USB-Bus oder Systemdatenträger kann diese Trennung dennoch überwinden.

Bei USB-Speichern dient die gemeldete Datenträgerseriennummer als Wiedererkennungsmerkmal. Bei CD/DVD darf die Seriennummer des Laufwerks nicht als Identität der eingelegten Scheibe gelten. Dort bildet der Webdienst deshalb eine Medienkennung aus vorhandener Volume-UUID, Volume-Label und Kapazität. Diese Kennung ist eine praktische Grobsichtungsidentität und keine kryptografische Prüfsumme des optischen Mediums.

Sichtungsnummern werden in einer unmittelbaren SQLite-Transaktion reserviert. Lesbare Fallexporte werden serialisiert. Dadurch dürfen parallele Scans weder dieselbe `SICHT-###`-Nummer erhalten noch gleichzeitig denselben Bericht überschreiben.

Der aktive Fall liegt als gemeinsame Sitzung im Arbeitsspeicher des Webdienstes (`ACTIVE_CASE_SESSION`). Nach einem Dienst-/Pi-Neustart ist sie leer. Beim Browser-Neuladen übernimmt `syncCaseSessionFromServer()` eine noch laufende Gerätesitzung einschließlich Fallnummer und Bearbeiter. Das ist keine Benutzeranmeldung. Ein gewünschter erneuter Freigabeschritt nach Browser-/Netzwerkverlust bleibt ein offener Workflow-Punkt.

## Geräteerkennung bei Störungen

Dashboard-Status und manuelles Aktualisieren verwenden eine gemeinsame, nicht blockierend belegte Erkennungssperre. `lsblk` hat ein eigenes kurzes Zeitlimit. Fehler führen zu einer zehnsekündigen Pause und einem ausdrücklich veralteten Gerätebestand (`device_error`). Gleichzeitige Statusanfragen erhalten den letzten Stand, ohne weitere Gerätebefehle zu starten. Im laufenden Dienst werden Quarantänen nur nach erfolgreicher Erkennung eines fehlenden Geräts bereinigt; nach Dienstneustart ist die bisher rein speicherbasierte Quarantäneliste leer. Der Browser sperrt neue Medienaktionen während eines unbekannten Verbindungszustands; gespeicherte Fallakten bleiben lesbar. Diese Maßnahmen ersetzen keine funktionierende Stromversorgung und können einen blockierten Systemdatenträger nicht isolieren.

## Stichwortprofile und Dateityp-Katalog

Seit Alpha 44 liegen bearbeitete Profile als YAML-Dateien unter `FORENSIC_TRIAGE_SETTINGS_ROOT/profiles`. `settings.py` übernimmt vorhandene Profile ohne Überschreiben lokaler Kopien und verwaltet den versionierten Dateityp-Katalog. Katalogspeicherung verwendet einen atomaren Dateiaustausch und eine Prüfung des zuletzt gelesenen Hashes gegen konkurrierende Änderungen. Mehrere ausgewählte Profile werden vor dem Scan zusammengeführt und Begriffe dedupliziert. Die tatsächlich ausgewählte Liste sowie Profilversion und SHA-256-Profilhash werden mit dem Scan gespeichert.

Der Webdienst übergibt einen Katalog-Snapshot an den isolierten Worker. Vor Statistik und Export ordnet `apply_catalog()` sowohl äußere Dateien als auch virtuelle Archivdateien anhand desselben Snapshots ein. `filetype-catalog.json` und die Referenz in `summary.json` dokumentieren diesen Stand; Leseansichten greifen weiterhin auf gespeicherte Kategorien zu. Die technische Auswahl unterstützter Archivleser bleibt davon getrennt. Migrationsdetails stehen in [settings.md](settings.md).

Die Suche arbeitet ausschließlich auf Namen und Pfaden, einschließlich katalogisierter ZIP-/ISO-/7Z-/RAR-Pfade. Sie ist nicht gleichbedeutend mit Inhaltsanalyse oder struktureller Erkennung eines Wallets.

## Frontend

`web/index.html`, `web/styles.css` und `web/app.js` bilden eine lokale Oberfläche ohne externes Frontend-Framework. IDs sind feste Bindungen für die Ereignislogik. Dialoge werden nativ mit `<dialog>` umgesetzt; bei verschachtelten Dialogen wird der Hintergrund nur auf der obersten Ebene abgedunkelt.

## Updatepfade

Der Online-Updater bereitet einen Git-Tag in einem eigenen Release-Verzeichnis vor. Der Offline-Pfad streamt ein signiertes `.tbu`-Paket zunächst in eine atomar ersetzte Übergabedatei. `offline_update.py` prüft die SSH-Signatur und anschließend jeden manifestierten regulären Dateieintrag, bevor es in ein temporäres Verzeichnis unter dem Release-Root schreibt und dieses atomar benennt. Abweichende Abhängigkeiten werden offline abgelehnt. Beide Wege führen danach denselben Test-, Vorlagen-, Laufzeitlink- und Dienststartpfad aus. Eine flüchtige Installationssperre verhindert parallel neue Fall- und Scanstarts.

## Sicherheitsgrenze

Version 0.2.0-alpha.46 liest Dateinamen, Pfade, Endungen, Größen und vom Dateisystem bereitgestellte Zeitstempel. Regulär vorhandene versteckte Einträge werden mit erfasst; gelöschte und ausgewählte interne Dateisystemeinträge werden bewusst nicht wiederhergestellt. Zusätzlich werden Verzeichnisstrukturen von ZIP-Dateien, ISO-Images sowie 7Z- und RAR-Archiven zeitlich und mengenmäßig begrenzt gelesen; Nutzdaten werden nicht extrahiert, dekomprimiert oder interpretiert. Eindeutige Verschlüsselungsmerkmale werden gezählt, alle nicht zuverlässig prüfbaren Archive bleiben unbekannt. Klassifizierung erfolgt anhand der Endung; Signaturabweichungen werden noch nicht erkannt. Recovery, Carving und Imaging liegen außerhalb des Umfangs.

## English summary

The browser calls a local Python service, which coordinates one guarded scanner process per eligible physical device. Each process has per-command and whole-scan deadlines and uses a private Linux mount namespace. A timed-out path is quarantined in memory until detected disconnect; restarting the service also clears that quarantine. Hardware/kernel stalls can still affect the whole device. Both CLI and dashboard use the same scanner. Atomic SQLite sighting reservations and serialized exports protect parallel case records. The fast path uses a verified read-only mount; TSK provides a slower mount-free walk. The dashboard uses bounded device discovery, stale-response protection, consistent archive navigation and numeric sighting order. Version 0.2.0-alpha.46 keeps persistent profile and file-type settings, accepts signed dependency-compatible offline application bundles through the private hotspot, and exposes cached Raspberry Pi power-health flags. Reboot and poweroff accept only fixed actions, use a delayed transient systemd unit, and are blocked during cases, scans or updates. Archive-status filters and explorer annotations use the stored classification; nested archive names are excluded from those status filters. Persistent diagnostics remain bounded; the scanner does not inspect file signatures or payloads.
