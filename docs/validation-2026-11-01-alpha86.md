# Prüfnachweis Alpha 86 – Zeitraum, Stichwörter und Explorer

Stand: 1. November 2026. Ausgangspunkt: sauberes `main` auf `9de726ee03622c4e243b1de252d2959a126cf837`, identisch mit `origin/main` und `v0.2.0-alpha.85`; remote Tags vor Beginn aktualisiert, Alpha 86 frei. Ziel: `0.2.0a86` / `v0.2.0-alpha.86`. Den tatsächlichen Release-Commit liefert `git rev-parse v0.2.0-alpha.86^{commit}`; lokale Abschlussdokumentation und GitHub-Workflow belegen die Veröffentlichung.

Ausschließlich lokale synthetische Fallablagen und Metadaten. Kein Pi-Zugriff, kein angeschlossenes Medium, keine Geräteaktionen, keine Originaldateiinhalte und keine produktiven Falldaten. `scanner.py`, `container_inventory.py`, Telefonmodule und Suchprofile unverändert gegenüber Alpha 85. Keine neue Laufzeitabhängigkeit. Zusätzlich wurden alle neun bereits vorhandenen Funktionen in `period.py` per AST mit Alpha 85 verglichen: unverändert, einschließlich `evaluate_file_period()`, `parse_timestamp()`, `timestamp_coverage()` und `validate_period()`. Die neue Datumsplausibilität liegt ausschließlich an der Eingabegrenze.

## Referenz und fachlicher Nachweis

`tests/test_metadata_analysis.py` enthält neun Originaldateieinträge aus 2023/2024/2025 sowie Null-Epoche, ungültige Werte und einen nach dem Scan liegenden Wert; dazu ein virtueller Archiveintrag. Zwei Originale haben denselben relativen Pfad auf unterschiedlichen Partitionen. Die Referenz ist ausdrücklich keine SanDisk-Fallkopie.

| Erwartung für 01.01.–31.12.2024, UTC | Ergebnis |
|---|---:|
| Originaldateieinträge | 9 |
| im Zeitraum | 5 |
| außerhalb | 3 |
| nicht bestimmbar | 1 |
| Beiträge B / M / C / A | 1 / 4 / 0 / 1 |
| ausschließlich B / M / C / A | 0 / 3 / 0 / 1 |
| mehrere passende Typen | 1 |
| ohne gültige Zeitstempel | 1 |
| virtuelle Einträge, separat | 1 |

Zusätzliche Prüfung 2025: 1 im Zeitraum, 7 außerhalb, 1 nicht bestimmbar. Zwei Versionen derselben Sichtung bleiben separat erhalten. Sämtliche ursprünglichen Dateien, einschließlich Geräte-/Partitions-/Container- und Suchprofil-Snapshots, werden vor/nach beiden Auswertungen per SHA-256 verglichen. Zusätzlich bleibt ein bewusst abweichend formatiertes historisches Scanrecord unverändert.

Stichwortreferenz: 6 gespeicherte Zuordnungen und 6 dokumentierte Pfade; 3 sicher eindeutig zugeordnete Originaldateien, 1 virtueller Eintrag, 2 Begriffe mit Treffern. Quellen: je 1 nur Ordnerpfad, nur Dateiname, beides und virtueller Pfad sowie 2 mehrdeutige historische Pfadzuordnungen. Eindeutige Zahlen sind hier Untergrenzen. Ein aktiver Begriff ohne Treffer bleibt sichtbar. Eine daneben vorhandene neue Profilversion 1.1 wird nicht geladen; die gespeicherte Version 1.0 bleibt maßgeblich.

A–L sind durch diese Referenz und zusätzliche Grenz-/Zeitzonentests abgedeckt. Bekannte DST-Grenzen für Wien, New York und Tokio werden geprüft, ebenso unsichere historische lokale Zeitzonen ohne Neuberechnung unter der heutigen Systemzone. Fehlende/ungültige Datumsgrenzen, Schaltjahre, fünfstellige Jahre und bewusste Bestätigung von 0202/2062/9999 sind serverseitig geprüft. Null-Epoche bleibt technisch verfügbar und auffällig.

M–P sind über kombinierte Filter, stabile Partitionspagination, Sortierung, Qualität `partial`/`failed`/`unknown`, fehlendes Inventar, echte lokale HTTP-Anfragen und Browserregressionen abgedeckt. Browserreferenzen werden während der Tests aus dem realen Python-Backend in temporären synthetischen Fällen erzeugt. UI-Zähler und Kategorie-/B/M/C/A-Werte werden mit diesen Antworten abgeglichen. Auswertungs- und Medienwechsel einschließlich A→B→A, veraltete Dateilisten und verspätete Erstellungsantworten sind geprüft. Die bisherigen 109 Browserfälle bleiben Bestandteil der vollständigen Suite.

## Sicherheits- und Erhaltungsprüfungen

- Fremde Hosts/Origins einschließlich `null`, cross-site Fetches, fehlende/falsche CSRF-Token und falscher Content-Type werden vor neuer Mutation abgewiesen.
- Fall-/Medienzuordnung, extrem große IDs, Auswertungs-ID-Pfadversuche, zusätzliche lokale Pfadfelder, ungültige Zeitzonen und ungewöhnliche Jahre ohne echtes Boolean-Einverständnis werden abgewiesen.
- Sämtliche Quellartefakte und die registrierte Auswertungsdatei werden auf Änderung geprüft. UUID-Kollision ersetzt keine Version und erzeugt keinen zweiten Audit-Commit.
- Symlinks, beschädigte Metadatenstrukturen und Ressourcenüberschreitungen führen zu Fehlern ohne veröffentlichte Teilversion. Temporäre Dateien werden aufgeräumt.
- Manifest/Export enthalten registrierte Versionen und keine Staging-Dateien, Symlinks oder unregistrierten Crash-Waisen. Audit sowie Text/PDF unterscheiden Originalscan und Nachauswertung.
- Diese neue API-Grenze ist keine globale Behebung der Legacy-Sicherheitslücken; [SECURITY.md](../SECURITY.md) und [Datenmodell/Grenzen](metadata-evaluations.md) bleiben verbindlich.

## Lokale Durchführung

```sh
.venv/bin/python -m pytest
node --check web/app.js
TRIAGE_TEST_PYTHON=.venv/bin/python NODE_PATH=/opt/homebrew/lib/node_modules node --test tests/test_web_ui.cjs
git diff --check
```

`TRIAGE_TEST_PYTHON` ist nur für eine separat liegende lokale virtuelle Python-Umgebung erforderlich. In GitHub-CI sind Paket und Testabhängigkeiten im Python-Pfad installiert; dort genügt `node --test tests/test_web_ui.cjs`. Playwright wird isoliert mit Version 1.63.0 verwendet, keine Frontend- oder Produktabhängigkeit. Der Workflow ergänzt zum bisherigen Python-3.11-Job Node 22, JavaScript-Syntax und die komplette synthetische Chromium-Suite. Tatsächlicher CI-Erfolg wird erst nach dem Release-Push beurteilt und im lokalen Abschlussbericht mit Lauf-URL festgehalten.

**Lokale Ergebnisse: 370 Python-Tests, 117 Chromium-Browserprüfungen und zusätzlich 9 gezielte WebKit-Prüfungen bestanden.** Keine Fehler oder übersprungenen Fälle in diesen Läufen. WebKit 26.6 / Playwright 1.63.0 prüft neben den acht neuen Metadatenszenarien auch die bestehende Fallzeitraum-Bedienung. Native Safari bleibt eine separate praktische Eingabeprüfung. JavaScript-Syntax und `git diff --check` bestanden.

Sichtprüfung in der lokalen synthetischen Anwendung bei 1512, 1280, 1000 und 800 Pixeln: Zeitraumübersicht, Zähler, B/M/C/A-Tabelle, Explorerfilter und Erstellungsdialog ohne horizontales Überlaufen der Hauptseite oder abgeschnittenen Dialog. Zahlen bleiben sichtbar. Die Browserprüfung misst zusätzlich Elementgrenzen und Dialoghöhe für alle vier Breiten. Der synthetische PDF-Bericht mit zwei Auswertungen wurde nach PNG-Rendering visuell kontrolliert: klare Original-/Nachauswertungstrennung, lesbare Tabellen, keine abgeschnittenen Inhalte.

## Lokale Ressourcenmessung

Ein gesonderter synthetischer Lauf mit 100.000 CSV-Dateieinträgen auf dem Entwicklungs-Mac ergab:

- 100.000 innerhalb, 0 außerhalb, 0 unbekannt für das gewählte Referenzjahr.
- Diskindex-Berechnung: 2,507 s; gesamte Erstellung einschließlich Quellprüfsummen, Audit und Berichten: 2,661 s.
- Letzte Seite bei Offset 99.750: 250 von 100.000 Einträgen in 0,670 s einschließlich erneuter Quell-/Indexhashprüfung.
- Prozess-Spitzen-RSS stieg von 46.727.168 auf 67.551.232 Byte. Kein Laden des gesamten CSV-Inventars in eine Python-Dateiliste.

Das sind einmalige lokale Messungen, keine Pi-Laufzeitversprechen oder allgemeinen Grenzwerte. Die dokumentierten Mengen-/Zeitlimits und fehlende Hintergrundwarteschlange bleiben praktische Einschränkungen.

## Offene Abnahmen

Keine Installation von Alpha 86 auf dem Pi, kein neuer FAST-/TSK-Hardwarelauf und keine Performance-, Temperatur-, Last- oder Schreibschutzfreigabe. Reale FAT/FAT32/exFAT/NTFS-Zeiten, Medienwechsel, Stromversorgung und Integrität bleiben getrennte Hardwareprüfungen. Native Safari-Jahreseingabe ist durch eine WebKit-Automation nicht vollständig ersetzt. Historisch fehlende Fehler, aktive Suchbegriffe, Partitionskennungen oder Zeitstempel werden nicht nachträglich erfunden. Daten oberhalb der dokumentierten Ressourcenlimits werden ausdrücklich abgewiesen. Für echten Einsatz bleiben allgemeiner Zugriffsschutz und validierte Hardware erforderlich.
