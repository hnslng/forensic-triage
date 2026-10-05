# B/M/C/A-Zeitstempel und Fallzeiträume

TRIAGE//BOX vergleicht Dateisystem-Metadaten mit dem optionalen lokalen Zeitraum einer Fallakte. Die Auswertung liefert Hinweise für die Grobsichtung; ein Zeitstempel beweist keine Benutzerhandlung.

## Bedeutung

- **B – Birth / Created:** `crtime`, sofern Kernel und Dateisystem eine Birth-Time bereitstellen.
- **M – Modified:** `mtime`, Änderungszeit des Dateiinhalts.
- **C – Metadata Changed:** `ctime`, Änderungszeit der Dateisystem-Metadaten. C ist keine Erstellungszeit.
- **A – Accessed:** `atime`, Zugriffszeit. Dateisysteme oder Betriebssysteme können A auslassen oder nur eingeschränkt aktualisieren.

Die Werte bleiben getrennt und werden nicht gegenseitig ersetzt. Fehlende Werte bleiben leer. B ist nicht auf jedem Dateisystem verfügbar.

Eine Datei zählt einmal als „im Zeitraum“, wenn mindestens einer ihrer verfügbaren B/M/C/A-Zeitstempel auf einen lokalen Kalendertag von ZEITRAUM VON bis ZEITRAUM BIS fällt. Beide Grenzen sind inklusive. `period_matches` nennt die passenden Typen in der Reihenfolge B+M+C+A. Der jüngste passende Wert berücksichtigt ausschließlich Werte, die selbst innerhalb des Zeitraums liegen; Gleichstände behalten alle passenden Typen.

## FAST und TSK

FAST setzt das Blockgerät softwareseitig read-only, prüft diesen Zustand und verifiziert den read-only-Zustand des konkreten Partitionsgeräts vor dem Mount. Der Mount verwendet `ro,nosuid,nodev,noexec`; anschließend erfasst der Kernel-Dateisystemzugriff die Metadaten und das Medium wird ausgehängt. Auf Linux versucht TRIAGE//BOX `statx` in einem Metadatenaufruf. `STATX_BTIME` wird nur bei gesetzter Birth-Time-Maske übernommen. Fehlt sie oder ist `statx` nicht verfügbar, bleibt B leer und die vorhandenen `os.stat(..., follow_symlinks=False)`-Metadaten werden verwendet. FAST startet keinen TSK-Fallback für Birth-Time und keinen externen Prozess pro Datei.

Der explizite TSK-Modus bleibt mountfrei und liest B/M/C/A über den bestehenden `fls`-Pfad. Ein Raw-Dateisystemlauf mit TSK kann deutlich langsamer sein.

Ein Hardware-Schreibblocker ist für einen späteren realen forensischen Einsatz eine empfohlene zusätzliche Schutzschicht. Die Software setzt keinen vorhandenen Hardware-Schreibblocker voraus.

## Lokale Tage und Zeitzone

Der Zeitraum besteht aus zwei ISO-Daten (`YYYY-MM-DD`) und bezeichnet lokale Kalendertage. Die Fallakte speichert nach Möglichkeit die ermittelte IANA-Zeitzone. Die Auflösung prüft `TZ`, `/etc/localtime` und `/etc/timezone`. Wenn keine gültige IANA-Zone erkennbar ist, wird `timezone: "local"` mit `timezone_reproducible: false` gespeichert; die Auswertung nutzt dann die lokale Systemzeit. Diese Fallback-Auswertung lässt sich nach einem Wechsel der Systemzeitzone möglicherweise nicht identisch wiederholen.

Sommer- und Winterzeit werden durch `ZoneInfo` berücksichtigt. `UTC` ist eine gültige Zeitzone.

## Historie und Grenzen

Der Scan speichert seinen Fallzeitraum, seine Zeitzone und seine Auswertung in `summary.json`, `files.csv` und dem Medien-Snapshot. Spätere Änderungen der Fallakte schreiben diese Scan-Artefakte nicht neu. `case.json` bildet dagegen den aktuellen Fallzustand ab.

Coverage zählt einen Timestamp als verfügbar, wenn er technisch als Epoch-Wert interpretierbar ist. Fehlende und ungültige Werte werden getrennt behandelt. Es gibt keine künstlichen Jahresgrenzen. Containerinhalte werden nicht mit dem Zeitstempel des Containerdateieintrags als eigene Dateien bewertet. Android- und iPhone-Schnellscans inventarisieren keine Dateien; sie speichern den Zeitraum nur als historischen Kontext und kennzeichnen die Auswertung als `not_applicable`.
