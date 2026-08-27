# So funktioniert TRIAGE//BOX / How it works

Diese Seite erklärt das System ohne Programmierkenntnisse. Die technische Modulübersicht steht ergänzend in [architecture.md](architecture.md).

## Der Ablauf in einem Satz

Die Bedienoberfläche erkennt angeschlossene Datenträger, übergibt jeden freigegebenen USB-Datenträger an einen abgesicherten Metadaten-Scanner und schreibt Ergebnis, Verlauf und Entscheidung in eine lokale Fallakte.

## Was passiert beim Anschließen?

1. Linux meldet die vorhandenen Laufwerke.
2. TRIAGE//BOX filtert daraus ganze USB-Datenträger heraus.
3. Gemountete, ungeeignete oder gefährliche Ziele werden abgelehnt.
4. Ohne ausdrücklich gestarteten Fall passiert kein Scan.
5. Der Scanner setzt das Blockgerät softwareseitig auf read-only und kontrolliert diesen Zustand.
6. Im schnellen Modus werden vorhandene Verzeichnis-Metadaten kurzzeitig über einen zusätzlichen Read-only-Mount gelesen.
7. Dateinamen, Pfade, Endungen, Größen und Zeitstempel werden in eine Tabelle geschrieben.
8. Aus diesen Daten entstehen Kategorien, Größenstatistik und Stichworttreffer.
9. Das Dashboard zeigt das Ergebnis. Es öffnet keine Nutzdatei vom Datenträger.
10. Die Entscheidung der bedienenden Person wird mit Zeit, Fall, Medium und Bearbeiter protokolliert.

In der Ergebnisansicht sind Dateikategorien und Stichworttreffer direkt mit dem gespeicherten Metadatenverzeichnis verknüpft. Ein Klick auf beispielsweise „Bilder“ filtert die Dateiliste nach dieser Kategorie. Ein Klick auf ein Stichwort zeigt die konkreten Trefferpfade und kennzeichnet, ob der Treffer im Dateinamen oder in einem übergeordneten Ordnerpfad vorkommt. Der aktive Filter steht in einer eigenen schmalen Statusleiste; „Filter aufheben“ stellt den vollständigen Verzeichnisbaum wieder her. Die freie Namens- und Pfadsuche bleibt eine davon getrennte Funktion. Große Treffermengen werden seitenweise nachgeladen.

Mehrere geeignete USB-Datenträger können gleichzeitig jeweils einen eigenen Scannerlauf erhalten. Ein Datenträger bekommt dabei automatisch eine neutrale Nummer wie `SICHT-001`.

## Welche Teile gibt es?

| Teil | Aufgabe |
|---|---|
| `web/index.html` | Aufbau der sichtbaren Seite |
| `web/styles.css` | Farben, Größen und Terminal-/CRT-Design |
| `web/app.js` | Klicks, Dialoge, Dashboardzustand und Kommunikation mit dem lokalen Dienst |
| `src/forensic_triage/web.py` | lokaler Webdienst, Gerätekoordination und API |
| `src/forensic_triage/device.py` | Zielprüfung und Read-only-Schutz |
| `src/forensic_triage/scanner.py` | zentraler Ablauf eines Scans |
| `src/forensic_triage/fast_inventory.py` | schneller Metadatenlauf über verifizierten Read-only-Mount |
| `src/forensic_triage/filesystem.py` | Verarbeitung des mountfreien TSK-Laufs |
| `classifier.py`, `keywords.py`, `statistics.py` | Kategorien, Treffer und Zahlen |
| `src/forensic_triage/casefiles.py` | Fallindex, Sichtungsnummern, Audit und Exporte |
| `src/forensic_triage/pdf_report.py` | kompakter druckbarer Fallbericht |
| `profiles/*.yaml` | mitgelieferte Stichwortprofile |

## Wo wird was gespeichert?

| Ort | Inhalt | In Git? |
|---|---|---|
| Projektordner | Programmcode, Profile, Tests und Dokumentation | ja |
| `/etc/forensic-triage/triage.env` | lokale Ports, Pfade und Profileinstellung | nein |
| `casefiles/` oder konfigurierter Fallpfad | Fallakten, SQLite-Index, Audit, Berichte und Manifeste | niemals |
| `results/` oder konfigurierter Ergebnispfad | technische Scannergebnisse | niemals |
| `casefiles/.trash/` | entfernte, wiederherstellbare Fallordner | niemals |
| systemd-Journal | Start-, Dienst- und Fehlermeldungen | nein |
| Browser/Laptop | nur Darstellung und gegebenenfalls SSH-Verbindung | keine dauerhafte Fallakte |

Der kompakte PDF-Bericht wird bei jeder Änderung der Fallakte aktualisiert und dort mitgeführt. PDF und ZIP werden beim Download zusätzlich im verwendeten Browser gespeichert; dieser Speicherort hängt vom Browser ab.

## Was ist die Konfiguration?

Eine Konfigurationsdatei trennt lokale Einstellungen vom Programmcode. Dadurch kann dasselbe Programm auf VM und Raspberry Pi laufen, ohne Quellcode oder Git-Dateien ändern zu müssen. Ein Portwechsel oder ein anderer verschlüsselter Fallspeicher wird in `/etc/forensic-triage/triage.env` eingetragen und der Dienst anschließend neu gestartet.

Das ist der übliche Ansatz für einen lokalen Linux-Dienst: Code bleibt versioniert, Passwörter und gerätespezifische Pfade bleiben lokal.

## Was passiert ausdrücklich nicht?

TRIAGE//BOX öffnet keine Dateien, erzeugt kein Image, sucht nicht in Dateiinhalten, führt kein Carving durch und entscheidet nicht automatisch über eine Sicherstellung. Eine umbenannte Datenbank mit Endung `.jpg` erscheint derzeit als Bild, weil noch keine Dateisignaturprüfung umgesetzt ist.

## English summary

The browser talks to a local Python service. After an explicit case start, each eligible USB disk is guarded, set read-only, inventoried, classified from metadata, and recorded in a local case archive. Configuration lives outside Git in `/etc/forensic-triage/triage.env`; real case data stays under the configured local case and result roots. The laptop is only a display/access client and stores no case database.
