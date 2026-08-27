# Lokale Fallakte / Local case archive

## Zweck und Speicherort

Das Dashboard speichert betriebliche Unterlagen ausschließlich unter `casefiles/` auf dem Scanner. Dieses Verzeichnis ist von Git ausgeschlossen. Vor realem Einsatz muss es auf verschlüsseltem, zugriffsgeschütztem Speicher liegen und in ein genehmigtes Sicherungs- und Aufbewahrungskonzept eingebunden werden.

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
                    ├── scan.log
                    └── raw/
```

## Inhalte

- `files.csv`: vollständiges Verzeichnis der beobachteten aktiven Dateien mit Pfad, Endung, Kategorie, Größe und Dateisystem-Zeitstempeln; keine Dateiinhalte
- `media-register.csv`: Übersicht aller Sichtungen und Entscheidungen im Fall
- `case-report.pdf`: kompakter, druckbarer Querformat-Bericht mit einer Zeile je Datenträger
- `case-report.txt`: menschenlesbare Fallzusammenfassung
- `audit.log`: chronologische Ereignisse aus dem lokalen Index
- `manifest.sha256`: Prüfsummen der lesbaren Exporte und aufbewahrten Scanartefakte
- `case-index.sqlite3`: durchsuchbarer lokaler Index

JSON-, CSV-, Text- und Logdateien bleiben unabhängig lesbar, falls Dashboard oder Datenbank nicht verfügbar sind.

## Entscheidungen und Audit

Eine Entscheidungsänderung erzeugt ein neues Ereignis, statt die frühere Historie still zu überschreiben. „Nicht ausgewählt“ verlangt eine strukturierte Begründung. „Sichern“ verlangt eine offizielle Beweismittelnummer. „Weitere Prüfung“ hält den offenen Zustand fest.

Bearbeiterkürzel werden bei Fallstart, Sichtungsreservierung und Entscheidung mitgeführt. Das Kürzel ist eine Verantwortlichkeitsangabe, aber noch keine technische Benutzeranmeldung.

Das Manifest kann Änderungen erkennbar machen, ist aber keine digitale Signatur und beweist nicht allein Urheberschaft oder vollständige Chain of Custody.

## Export

Der PDF-Bericht kann separat geladen und einer Akte beigelegt werden. Er nennt Sichtungsnummer, Datenträger, Seriennummer, technischen Grobinhalt, Entscheidung und gegebenenfalls die dokumentierte Begründung. Der Grobinhalt wird ausschließlich aus Dateiendungskategorien gebildet; Begriffe wie „Urlaubsfotos“ werden nicht automatisch behauptet, weil keine Dateiinhalte ausgewertet werden.

Der ZIP-Export enthält zusätzlich die vollständige Fallakte einschließlich PDF, Metadateninventaren und Nachweisen. Er enthält keine Kopie der Nutzdateien des gesichteten Mediums. Ein Export aus einem realen Fall ist trotzdem eine schützenswerte Fallunterlage und darf nicht in Git gespeichert werden.

## Entfernen und Wiederherstellung

Ein Fall kann im Fallarchiv direkt über „Löschen“ entfernt werden, ohne ihn vorher zu öffnen. Der aktive Fall ist geschützt und muss zuerst beendet werden. Das lokale Löschpasswort ist erforderlich.

Technisch wird der Fall aus dem aktiven SQLite-Index entfernt und sein Ordner nach `casefiles/.trash/` verschoben. Die Dateien bleiben administrativ wiederherstellbar. Die Funktion ist daher ein Entfernen aus der aktiven Fallliste, keine sichere Datenvernichtung. Ein geprüfter Wiederherstellungs- und endgültiger Löschprozess ist vor Einsatzbetrieb noch festzulegen.

## Noch offen

- Verschlüsselung-at-rest verbindlich konfigurieren und testen
- Wiederherstellungsablauf aus `.trash` dokumentieren und validieren
- Aufbewahrungs- und Löschfristen definieren
- digitale Signaturen bewerten
- Layout und Formulierungen des PDF-Berichts fachlich abnehmen

## English summary

Case data is stored locally under the Git-ignored `casefiles/` directory. Each medium receives a neutral sighting number; an official evidence number is required only for “Secure”. A compact PDF report, open-format exports, and a SHA-256 manifest accompany the SQLite index. Removing a case moves its files to an internal recoverable trash directory and is not secure deletion. Real deployment requires encrypted storage, access control, retention rules, and a tested recovery procedure.
