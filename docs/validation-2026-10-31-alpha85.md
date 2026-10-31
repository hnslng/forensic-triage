# Alpha 85: Scanqualität und Fehlerbehandlung

Stand: 31.10.2026. Ausgangspunkt `bc5433ff83a4651b5ebf77b29541b4d334fcdeb3` auf `main`, Paket 0.2.0a84. Neuer Paketstand 0.2.0a85; der Release-Commit wird durch `v0.2.0-alpha.85` bezeichnet. Keine Änderungen fremder Arbeit lagen vor.

## Umsetzung

- Fehler werden nach Datei-, Verzeichnis- und sonstigem Zugriff vollständig gezählt. Beispiele sind pro Partition auf 50 begrenzt; ein Auslassungsmerkmal bleibt unabhängig vom Gesamtzähler.
- Erfolgreich leere Dateisysteme, Teilergebnisse, Totalausfälle und historisch nicht belegbare Qualität bleiben unterscheidbar. Root-Ausfall oder ausschließlich fehlgeschlagene Zugriffe werden nicht durch eine bloß erkannte Partition zu `partial`.
- Bei fehlerhaftem Unmount bleiben verfügbare Inventare erhalten; weitere Gerätezugriffe dieses Laufs enden, die bestehende Quarantäne wird gesetzt. Sichere Mountoptionen und Geräteprüfungen bleiben erhalten.
- Register, Dashboard-Kacheln, Ergebnis-/Nachweisansicht, CSV, Text/PDF und neue Abschluss-Audits zeigen Qualität und Fehlerzähler. Fehlversuche ohne Inventar werden aus Audit-Ereignissen rekonstruiert; die Dateizahlen sind unbekannt statt erfunden null.
- Nichtauswahl bei `partial`, `failed` oder `unknown` benötigt Notiz und aktive Bestätigung zum aktuellen Status. Direkte API-Anfragen ohne diese Angaben, mit Text statt boolescher Bestätigung oder mit abweichendem Status werden abgewiesen. Die Entscheidung einschließlich Qualitätsstand und Scan-ID wird auditiert.
- Keine neue Datenbankstruktur. Vorhandene Entscheidungen, Sichtungsnummern und Audit-Ereignisse bleiben erhalten. Alte Scan-Snapshots werden nicht neu geschrieben. Telefonentscheidungen bleiben von USB-spezifischen Bestätigungen getrennt.

## Lokale Prüfung

Die Abschlussprüfung umfasst die gesamte Python- und Browserregression sowie die Syntax-/Diffprüfung:

```text
.venv/bin/python -m pytest -q
node --check web/app.js
NODE_PATH=/opt/homebrew/lib/node_modules node --test tests/test_web_ui.cjs
git diff --check
```

Synthetische Fälle: gesund/leer, einzelner Dateifehler, 26 Verzeichnisfehler bei 47 erhaltenen Dateien und 38 Ordnern, 1.000 Fehler mit 50 gespeicherten Beispielen, Wurzel-/Partitionsausfälle, gemischte Partitionen, Unmount-Fehler samt Teildatenerhalt, Fehlversuch ohne Inventar und idempotenter Abschluss. Historische, künstlich erzeugte Datenbankschemas und eine getrennte Testdatenbankkopie prüfen erhaltene Entscheidungen/Auditzeilen. Hash-/Byteprüfungen bestätigen unveränderte Scan-Snapshots bei lesender Qualitätsableitung.

Browserprüfung: Status in Kacheln, Fallregister, Ergebnissen und Nachweisen; explizite Nichtauswahlbestätigung einschließlich Pflichtnotiz und unveränderter Telefonworkflow. Screenshot-Sichtprüfung bei 1512, 1280, 1000 und 800 Pixeln; keine horizontale Hauptseiten-Scrollbar. Ein synthetischer PDF-Bericht mit Teilinventar, Fehlversuch ohne Inventar und erfolgreich leerem Medium wurde gerendert und visuell geprüft; keine abgeschnittenen oder überlappenden Tabelleninhalte.

Lokales Ergebnis: **338 Python-Tests und 109 Browser-Tests bestanden**, keine fehlgeschlagenen oder übersprungenen Prüfungen. JavaScript-Syntax und `git diff --check` bestanden. Der CI-Nachweis wird im Abschlussbericht bzw. durch den Workflow des Release-Commits dokumentiert. Die vorhandene GitHub-CI prüft Python 3.11; Browserprüfungen laufen hier lokal mit Playwright. Es wurde kein neuer Browser-CI-Job behauptet.

## Grenzen und noch erforderliche Hardwareprüfung

- Keine neuen Pi-Hardwaremessungen. Reale EIO-/Unmount-Ausfälle, FAT/exFAT/NTFS-Verhalten und Kernel-Wartezustände müssen auf einem freigegebenen, entbehrlichen Testmedium geprüft werden. Keine universelle Performance- oder Schreibschutzgarantie aus Mock-Tests.
- Kein inkrementelles Wiederaufnahmeverfahren. Bei hart beendetem Worker können noch nicht gespeicherte In-Memory-Teildaten verloren gehen; die Sichtung bleibt als nicht erfolgreich abgeschlossener Versuch sichtbar.
- Die bestehende Quarantäne ist flüchtig. Ihr Neustartverhalten bleibt ein offener Hardware-/Betriebspunkt und wird nicht durch einen Webknopf umgangen.
- Historisch nicht protokollierte Fehler bleiben unbekannt. Ein Fehler beweist keine bestimmte technische Ursache oder inhaltliche Relevanz.
- Keine Änderung an B/M/C/A, Suchprofilen, Dateitypkatalogsystem oder Zeitraumauswertung; keine Dateivorschau und keine Nutzdatenanalyse.
- Keine neuen externen Abhängigkeiten. Keine vertraulichen Falldaten, Originalmedien oder Produktivdatenbank für Tests verwendet. Keine Installation oder Migration am produktiven Pi.

K1/K2 sind hinsichtlich der genannten Softwareanforderungen umgesetzt und geprüft; eine vollständige Hardwareabnahme bleibt offen. Siehe [Audit-Arbeitsliste](AUDIT_ALPHA84_TODOS.md) und [Scanqualität](scan-quality.md).
