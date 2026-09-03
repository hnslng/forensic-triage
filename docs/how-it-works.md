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
8. ZIP-Dateien, ISO-Images sowie 7Z- und RAR-Archive erhalten innerhalb eines gemeinsamen Zeitbudgets einen reinen Verzeichnisindex; es wird nichts extrahiert oder dekomprimiert.
9. Aus den äußeren Metadaten und den zusätzlichen virtuellen Containerpfaden entstehen Kategorien, Größenstatistik und Stichworttreffer. Die normalen Datei-/Ordnerzahlen zählen Containerinhalte bewusst nicht doppelt.
10. Das Dashboard zeigt das Ergebnis. Es öffnet oder zeigt keine Nutzdatei-Payload vom Datenträger.
11. Die Entscheidung der bedienenden Person wird mit Zeit, Fall, Medium und Bearbeiter protokolliert.

Normale versteckte Dateien und Ordner werden dabei wie andere aktive Dateisystemeinträge erfasst: Dazu gehören Unix-Namen mit führendem Punkt und reguläre aktive Einträge mit einem Hidden-Attribut. Bewusst nicht gesucht werden gelöschte Dateien; interne Dateisystem-Hilfsstrukturen werden ausgefiltert. Beschädigte oder nicht lesbare Einträge können ohne Recovery ebenfalls fehlen.

In der Ergebnisansicht sind Dateikategorien und Stichworttreffer direkt mit dem gespeicherten Metadatenverzeichnis verknüpft. Ein Klick auf beispielsweise „Bilder“ filtert die Dateiliste nach dieser Kategorie. Archive bleiben auch in dieser gefilterten Tabelle über einen Pfeil aufklappbar. Ein Klick auf ein Stichwort zeigt die konkreten Trefferpfade und kennzeichnet, ob der Treffer im Dateinamen oder in einem übergeordneten Ordnerpfad vorkommt. Der aktive Filter steht in einer eigenen schmalen Statusleiste; zugleich erscheint „Filter aufheben“ direkt neben der Suche und stellt den vollständigen Verzeichnisbaum wieder her. Die freie Namens- und Pfadsuche bleibt eine davon getrennte Funktion. Große Treffermengen werden seitenweise nachgeladen.

ZIP-, ISO-, 7Z- und RAR-Dateien erscheinen dort wie aufklappbare Ordner mit einem Formatkennzeichen. Der virtuelle Baum stammt aus `container-index.json`. ZIP wird direkt über das Zentralverzeichnis gelesen, ISO über ISO9660 beziehungsweise vorhandene Rock-Ridge-, Joliet- oder UDF-Verzeichnisstrukturen. Für 7Z und RAR ruft der Scanner das vom Debian-Installer bereitgestellte Werkzeug `7z` ausschließlich im Listenmodus `l -slt` auf. Die Standardeingabe ist dabei geschlossen: TRIAGE//BOX gibt kein Passwort ein und startet keinen interaktiven Passwortversuch. Interne Dateinamen fließen in die Pfadsuche und Stichwortsuche ein; sie verändern aber weder die Anzahl noch das Datenvolumen der tatsächlich auf dem Medium erfassten äußeren Dateien. Beschädigte, unvollständige, kopfverschlüsselte Container und erreichte Limits werden sichtbar unterschieden.

Unter der Dateitypenliste stehen kompakte, anklickbare Statuszähler für sicher erkannte verschlüsselte ZIP-, 7Z- und RAR-Archive und für `Ungeprüft`. Die Auswahl zeigt die zugehörigen äußeren Archivdateien; verschachtelte Archivnamen werden nicht mitgezählt. Zähler, Filter und Explorerkennzeichnung verwenden dieselbe Einstufung aus dem gespeicherten Archivindex, zugeordnet nach Partition und Pfad. Es wird dafür nicht erneut auf den Datenträger zugegriffen.

Archive, deren Verschlüsselungszustand wegen Format, Beschädigung, fehlendem Teilvolume oder Limit nicht zuverlässig feststeht, bleiben `Ungeprüft`. TRIAGE//BOX versucht keine Passwörter und deutet `Ungeprüft` niemals als unverschlüsselt. Eine positiv erkannte Verschlüsselung bleibt auch bei einem unvollständigen Inhaltsverzeichnis als solche markiert. Innere Archivdateien erhalten keine ungeprüfte oder verschlüsselte Einstufung aus dem Zustand ihres äußeren Archivs.

Die Liste der größten Dateien zeigt Größen in einer festen linken Spalte sowie Dateiname und Ordner daneben. Ein Klick fragt über `exact_path` exakt den gespeicherten Metadatenpfad des ausgewählten Mediums ab; ähnlich benannte Dateien werden nicht mit ausgewählt. Dabei werden weder Nutzdateien geöffnet noch zusätzliche Daten vom Medium gelesen.

Die gefilterte Liste zählt **Fundstellen**, nicht zusätzliche physische Dateien: Bei zehn Archivdateien auf dem Stick und drei weiteren Archivdateien innerhalb von ZIP-/ISO-Verzeichnissen zeigt sie beispielsweise 13 Fundstellen. Die Spalte **Fundort** unterscheidet `AUF DEM MEDIUM` und etwa `IM ZIP` oder `IM ISO`. Verschachtelte Archive bleiben sichtbare Einträge mit dem Hinweis `NICHT WEITER GEÖFFNET`; sie werden nicht rekursiv entpackt. Sowohl die Ordner im normalen Explorer als auch jene in der gefilterten Archivansicht lassen sich aufklappen.

Beim Wechsel von Sichtung oder Filter verwirft die Oberfläche verspätete Antworten der vorherigen Ansicht. Die Sichtungen im Dashboard und im tabellarischen Fallprotokoll werden numerisch aufsteigend angezeigt; Online- und Offline-Gruppen bleiben getrennt. Navigation und Sortierung ändern weder die gespeicherten Sichtungsnummern noch die Entscheidungen.

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
| `src/forensic_triage/container_inventory.py` | begrenzter ZIP-/ISO-/7Z-/RAR-Verzeichnisindex ohne Extraktion |
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

Die beim Scan gelesenen Gerätedaten liegen pro Sichtung in `device.json`; die zentralen Angaben stehen zusätzlich im lokalen Fallindex und in `media-register.csv`. Der Nachweisdialog zeigt Modell, Seriennummer, Kapazität, Medientyp, technischen Gerätepfad und den dokumentierten Schreibschutz direkt an. Dadurch bleiben die Identitätsangaben auch sichtbar, wenn der Datenträger später offline ist.

## Was ist die Konfiguration?

Eine Konfigurationsdatei trennt lokale Einstellungen vom Programmcode. Dadurch kann dasselbe Programm auf unterschiedlichen Debian-Zielsystemen laufen, ohne Quellcode oder Git-Dateien ändern zu müssen. Ein Portwechsel oder ein anderer verschlüsselter Fallspeicher wird in `/etc/forensic-triage/triage.env` eingetragen und der Dienst anschließend neu gestartet.

Das ist der übliche Ansatz für einen lokalen Linux-Dienst: Code bleibt versioniert, Passwörter und gerätespezifische Pfade bleiben lokal.

## Was passiert ausdrücklich nicht?

TRIAGE//BOX liest keine Nutzdatei-Payload, erzeugt kein Image, sucht nicht in Dateiinhalten, führt kein Carving durch und entscheidet nicht automatisch über eine Sicherstellung. Die einzige eng begrenzte Ausnahme ist das Lesen von ZIP-/ISO-/7Z-/RAR-Verzeichnisstrukturen; Einträge werden nicht extrahiert, dekomprimiert oder rekursiv geöffnet. Eine umbenannte Datenbank mit Endung `.jpg` erscheint weiterhin als Bild, weil noch keine Dateisignaturprüfung umgesetzt ist.

## English summary

The browser talks to a local Python service. After an explicit case start, each eligible USB disk is guarded, set read-only, inventoried, classified from metadata, and recorded in a local case archive. Configuration lives outside Git in `/etc/forensic-triage/triage.env`; real case data stays under the configured local case and result roots. The laptop is only a display/access client and stores no case database.
