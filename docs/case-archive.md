# Lokale Fallakte / Local case archive

## Zweck und Speicherort

Die Fallunterlagen des Dashboards liegen unter dem konfigurierten `FORENSIC_TRIAGE_CASEFILES_ROOT`, standardmäßig `casefiles/` im ursprünglichen Projektordner. CLI-Ergebnisse können im getrennten Ergebnispfad liegen; Dienstdiagnosen liegen im Systemjournal. Dieses Verzeichnis ist von Git ausgeschlossen. Vor realem Einsatz muss es auf verschlüsseltem, zugriffsgeschütztem Speicher liegen und in ein genehmigtes Sicherungs- und Aufbewahrungskonzept eingebunden werden.

Jeder Scan erhält innerhalb des Falles automatisch eine neutrale Sichtungsnummer. Eine offizielle Beweismittel-/Asservatennummer wird erst ergänzt, wenn die Entscheidung „Sichern“ gespeichert wird.

```text
casefiles/
├── case-index.sqlite3
├── .trash/
└── FALL-2026-001/
    ├── case.json
    ├── case-report.pdf
    ├── case-report.txt
    ├── media-register.csv
    ├── audit.log
    ├── manifest.sha256
    └── media/
        └── SICHT-001/
            ├── records/
            │   └── <scan-id>.json
            └── scans/
                └── <scan-id>/
                    ├── device.json
                    ├── partitions.json
                    ├── files.csv
                    ├── summary.json
                    ├── hits.json
                    ├── container-index.json
                    ├── scan.log
                    └── raw/
```

## Inhalte

- `files.csv`: vollständiges Verzeichnis der beobachteten aktiven Dateien mit Pfad, Endung, Kategorie, Größe und Dateisystem-Zeitstempeln; keine Dateiinhalte
- `device.json`: beim Scan gespeicherte Geräteangaben einschließlich Modell, Seriennummer, Kapazität, Transport und verifiziertem Read-only-Zustand
- `container-index.json`: begrenztes Inhaltsverzeichnis erkannter ZIP-, ISO-, 7Z- und RAR-Dateien; keine extrahierten oder dekomprimierten Nutzdaten
- `media-register.csv`: Übersicht aller Sichtungen und Entscheidungen im Fall
- `case-report.pdf`: kompakter, druckbarer Querformat-Bericht mit einer Zeile je Datenträger
- `case-report.txt`: menschenlesbare Fallzusammenfassung
- `audit.log`: neu erzeugter lesbarer Export der chronologischen Ereignisse aus dem lokalen Index
- `manifest.sha256`: Prüfsummen der lesbaren Exporte und aufbewahrten Scanartefakte
- `case-index.sqlite3`: durchsuchbarer lokaler Index

JSON-, CSV-, Text- und Logdateien bleiben unabhängig lesbar, falls Dashboard oder Datenbank nicht verfügbar sind.

Die wesentlichen Geräteangaben stehen außerdem im lokalen Fallindex und in `media-register.csv`. Der Nachweisdialog liest für Details die gespeicherte `device.json`, damit die Identität eines bereits abgezogenen Mediums weiterhin kontrolliert werden kann.

## Entscheidungen und Audit

Eine Entscheidungsänderung erzeugt ein neues Ereignis, statt die frühere Historie still zu überschreiben. „Nicht sichern“ verlangt eine strukturierte Begründung. „Sichern“ verlangt eine offizielle Beweismittelnummer. Der frühere Zustand „Weitere Prüfung“ bleibt in historischen Datensätzen lesbar, kann aber nicht mehr neu gespeichert werden.

Fallstart, Sichtungsreservierung, Scanergebnis/-fehler und Entscheidungen haben Audit-Ereignisse. Fallende ist derzeit kein eigenes Ereignis; Navigation und Filter werden ebenfalls nicht im Fall-Audit gespeichert. Bearbeiterkürzel werden bei Fallstart, Sichtungsreservierung und Entscheidung mitgeführt. Das Kürzel ist eine Verantwortlichkeitsangabe, aber noch keine technische Benutzeranmeldung.

Das Manifest kann Änderungen gegenüber einem vertrauenswürdig aufbewahrten Stand erkennbar machen. Es wird mit den Exporten aktualisiert, ist keine digitale Signatur und schützt nicht vor einem Angreifer, der Dateien und Manifest gemeinsam ändern kann. Es beweist nicht allein Urheberschaft oder vollständige Chain of Custody.

## Export

Der PDF-Bericht kann separat geladen und einer Akte beigelegt werden. Er nennt Sichtungsnummer, Datenträger, Seriennummer, technischen Grobinhalt, Entscheidung und gegebenenfalls die dokumentierte Begründung. Der Grobinhalt wird ausschließlich aus Dateiendungskategorien gebildet; Begriffe wie „Urlaubsfotos“ werden nicht automatisch behauptet, weil keine Dateiinhalte ausgewertet werden.

Der ZIP-Export enthält den einzelnen Fallordner einschließlich PDF, Metadateninventaren und Nachweisen. Der zentrale `case-index.sqlite3` außerhalb dieses Ordners ist nicht enthalten. Daher ist ein Fall-ZIP keine vollständige Systemsicherung und noch kein getestetes Wiederimportformat. Er enthält keine Kopie der Nutzdateien des gesichteten Mediums. Ein Export aus einem realen Fall ist trotzdem eine schützenswerte Fallunterlage und darf nicht in Git gespeichert werden.

## Entfernen und Wiederherstellung

Ein Fall kann im Fallarchiv direkt über „Löschen“ entfernt werden, ohne ihn vorher zu öffnen. Das Dashboard sperrt das Löschen des aktiven Falls; er muss dort zuerst beendet werden. Der Warnungsdialog verlangt eine ausdrückliche Bestätigung für den konkret genannten Fall; ein Passwort ist nicht erforderlich.

**Bekannte Grenze:** Der DELETE-Endpunkt prüft bisher die Fallbestätigung, aber nicht zusätzlich aktive Fallsitzung oder laufende Scans. Die UI-Sperre ist deshalb kein vollständiger serverseitiger Schutz. Diese Prüfung muss vor Freigabe ergänzt und mit gleichzeitigen Anfragen getestet werden; siehe [Roadmap](roadmap.md).

Technisch wird der Fall aus dem aktiven SQLite-Index entfernt und sein Ordner nach `casefiles/.trash/` verschoben. Die Dateien bleiben erhalten. Es gibt aber noch keine fertige Wiederherstellungsfunktion für den aktiven SQLite-Index; das Zurückverschieben des Ordners allein macht den Fall nicht wieder im Dashboard sichtbar. Die Funktion ist daher ein Entfernen aus der aktiven Fallliste, keine sichere Datenvernichtung. Ein geprüfter Wiederherstellungs- und endgültiger Löschprozess ist vor Einsatzbetrieb noch festzulegen.

## Sicherung und Wiederherstellung

Eine vollständige Datensicherung muss den zentralen Index, sämtliche Fallordner einschließlich `.trash`, separat gespeicherte Scannergebnisse, eigene Profile und benötigte lokale Konfiguration konsistent umfassen. Während einer Dateikopie keine Scans oder Entscheidungen schreiben lassen; am einfachsten den Webdienst nach beendetem Fall kontrolliert stoppen. SQLite im WAL-Modus nicht als isolierte Datenbankdatei während laufender Schreibzugriffe kopieren. Den Restore auf einem getrennten Teststand prüfen; ein getestetes automatisches Backup-/Restore-Verfahren ist noch offen.

## Noch offen

- Verschlüsselung-at-rest verbindlich konfigurieren und testen
- Wiederherstellungsablauf aus `.trash` dokumentieren und validieren
- Aufbewahrungs- und Löschfristen definieren
- digitale Signaturen bewerten
- Layout und Formulierungen des PDF-Berichts fachlich abnehmen

## English summary

Case data is stored locally under the Git-ignored `casefiles/` directory. Each medium receives a neutral sighting number; an official evidence number is required only for “Secure”. A compact PDF report, open-format exports, and a SHA-256 manifest accompany the SQLite index. Removal preserves files in internal trash but removes their database entries; no supported re-import is implemented yet. Active-case deletion is blocked in the dashboard, not yet by the DELETE endpoint. Real deployment requires encrypted storage, access control, retention rules, and a tested recovery procedure.
