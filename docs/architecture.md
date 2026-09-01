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
- `container_inventory` katalogisiert ZIP-, ISO-, 7Z- und RAR-Verzeichnisstrukturen innerhalb harter Mengen- und Zeitgrenzen, ohne Einträge zu extrahieren. 7Z und RAR werden über Debians `7z` ausschließlich im Listenmodus verarbeitet.
- `reporting` schreibt normalisierte Ergebnisse und behält rohe Werkzeugausgaben.

Der Standardmodus `fast` liest aktive Verzeichniseinträge über einen Mount mit `ro,nosuid,nodev,noexec`, nachdem das gesamte Blockgerät schreibgeschützt wurde. `tsk` verwendet `fls -u` ohne Mount und ist auf großen Datenträgern erheblich langsamer.

## Webdienst und Parallelität

Der Webdienst erkennt Geräte mit `lsblk`, führt geeignete USB- und optische Medien getrennt und reserviert pro physischem Gerätepfad höchstens einen laufenden Worker-Prozess. Jeder Worker ruft den abgesicherten Scanner in einem privaten Linux-Mount-Namensraum auf. Einzelbefehle und Gesamtscan besitzen eigene Zeitlimits. Nach einer Überschreitung wird nur der betroffene Gerätepfad bis zum erkannten Abziehen gesperrt; Weboberfläche und parallele Scans bleiben unabhängig.

Bei USB-Speichern dient die gemeldete Datenträgerseriennummer als Wiedererkennungsmerkmal. Bei CD/DVD darf die Seriennummer des Laufwerks nicht als Identität der eingelegten Scheibe gelten. Dort bildet der Webdienst deshalb eine Medienkennung aus vorhandener Volume-UUID, Volume-Label und Kapazität. Diese Kennung ist eine praktische Grobsichtungsidentität und keine kryptografische Prüfsumme des optischen Mediums.

Sichtungsnummern werden in einer unmittelbaren SQLite-Transaktion reserviert. Lesbare Fallexporte werden serialisiert. Dadurch dürfen parallele Scans weder dieselbe `SICHT-###`-Nummer erhalten noch gleichzeitig denselben Bericht überschreiben.

Der aktive Fall ist eine bewusste Sitzung im Browser. Nach einem Seiten- oder Dienstneustart wird er nicht automatisch wiederhergestellt. Die dauerhaften Daten bleiben im Fallarchiv erhalten; neue Scans bleiben gesperrt, bis Fall, Bearbeiter und Suchprofile erneut bestätigt wurden.

## Stichwortprofile

Profile liegen als YAML-Dateien unter `profiles/`. Mehrere ausgewählte Profile werden vor dem Scan zusammengeführt und Begriffe dedupliziert. Die tatsächlich ausgewählte Liste sowie Profilversion und SHA-256-Profilhash werden mit dem Scan gespeichert.

Die Suche arbeitet ausschließlich auf Namen und Pfaden, einschließlich katalogisierter ZIP-/ISO-/7Z-/RAR-Pfade. Sie ist nicht gleichbedeutend mit Inhaltsanalyse oder struktureller Erkennung eines Wallets.

## Frontend

`web/index.html`, `web/styles.css` und `web/app.js` bilden eine lokale Oberfläche ohne externes Frontend-Framework. IDs sind feste Bindungen für die Ereignislogik. Dialoge werden nativ mit `<dialog>` umgesetzt; bei verschachtelten Dialogen wird der Hintergrund nur auf der obersten Ebene abgedunkelt.

## Sicherheitsgrenze

Version 0.2.0-alpha.28 liest Dateinamen, Pfade, Endungen, Größen und vom Dateisystem bereitgestellte Zeitstempel. Zusätzlich werden Verzeichnisstrukturen von ZIP-Dateien, ISO-Images sowie 7Z- und RAR-Archiven zeitlich und mengenmäßig begrenzt gelesen; Nutzdaten werden nicht extrahiert, dekomprimiert oder interpretiert. Eindeutige Verschlüsselungsmerkmale werden gezählt, alle nicht zuverlässig prüfbaren Archive bleiben unbekannt. Klassifizierung erfolgt anhand der Endung; Signaturabweichungen werden noch nicht erkannt. Recovery, Carving und Imaging liegen außerhalb des Umfangs.

## English summary

The browser calls a local Python service, which coordinates one guarded scanner process per eligible physical device. Each process has per-command and whole-scan deadlines and uses a private Linux mount namespace. A timed-out path is quarantined until physical disconnect so the dashboard and other scans remain available without an automatic retry loop. Both CLI and dashboard use the same scanner. Atomic SQLite sighting reservations and serialized exports protect parallel case records. The fast path uses a verified read-only mount; TSK provides a slower mount-free walk. Version 0.2.0-alpha.28 adds a bounded ZIP/ISO/7Z/RAR directory index and conservative archive encryption counts but does not inspect file signatures or payloads.
