# Scanqualität und sichere Entscheidungen

Seit Alpha 85 tragen Dateisystem-Sichtungen einen Qualitätsstatus. Der Status bewertet den vorgesehenen Inventarisierungsumfang, nicht die inhaltliche Relevanz oder die forensische Vollständigkeit einer Sicherung.

| Status | Anzeige | Bedeutung |
|---|---|---|
| `complete` | SCAN VOLLSTÄNDIG | Alle vorgesehenen Partitionen ohne dokumentierten Inventarisierungsfehler erfasst. Auch ein erfolgreich gelesenes leeres Dateisystem kann vollständig sein. |
| `partial` | SICHTUNG UNVOLLSTÄNDIG | Lesbare Teildaten vorhanden, weitere Bereiche oder der sichere Abschluss nicht erfolgreich. Der tatsächliche Gesamtbestand ist unbekannt. |
| `failed` | SICHTUNG FEHLGESCHLAGEN | Keine verlässliche Inventarisierung möglich; beispielsweise Wurzelverzeichnis nicht lesbar, alle Dateizugriffe gescheitert oder keine Partition auswertbar. |
| `unknown` | SCANQUALITÄT NICHT BEWERTBAR | Historische Belege fehlen oder erlauben keine sichere Bewertung. Eine nicht dokumentierte Vollständigkeit wird nicht angenommen. |

## Leer ist etwas anderes als fehlgeschlagen

Null Dateien plus erfolgreicher Dateisystemzugriff ohne Fehler kann ein leerer Bestand sein. Null Dateien nach einem technischen Fehler belegen keinen leeren Datenträger. Zahlen und Treffer eines Teilinventars beziehen sich ausschließlich auf den erfassten Teil. Nicht erfasste Dateien und Inhalte können nicht ausgeschlossen werden.

Fehlt das Inventar ganz, lautet die Anzeige „Kein auswertbares Dateiinventar erstellt.“ Die CSV-Zellen für Dateien, Ordner und Treffer bleiben leer; es werden keine künstlichen Nullwerte in die Medien-Tabelle geschrieben. Eine verlorene oder unlesbare historische Inventardatei wird ebenfalls nicht als Leerbefund angezeigt.

## Zähler und Erhalt der Teildaten

Jede neu erfasste Partition speichert `read_error_counts` mit `file`, `directory`, `other` und `total`, außerdem `read_error_count`. `read_errors` enthält höchstens 50 Beispiele mit Zugriffsart, relativem Pfad, Fehlernummer und Fehlertext. `read_errors_truncated` zeigt ausgelassene Details an. Bei 1.000 Fehlern bleibt der Gesamtzähler 1.000, auch wenn nur 50 Beispiele gespeichert sind. Die Wurzelbegehung und erfolgreiche Metadatenzugriffe werden getrennt erfasst; eine gefundene Partition allein ist kein erfolgreicher Teilbestand.

Die Zusammenfassung enthält `scan_status`, `scan_quality_version`, `scan_error_count`, `scan_error_counts`, `scan_affected_partitions` und `scan_inventory_present`. Der Gesamtfehlerzähler berücksichtigt zusätzlich dokumentierte Partitions-/Abschlussfehler. Historische Fehlerlisten ohne getrennte Zähler erlauben nur die Auswertung der tatsächlich gespeicherten Meldungen; nicht protokollierte Fehler sind nicht rekonstruierbar.

Lesbare Nachbardateien und andere sichere Bereiche werden weiter erfasst. Schlägt das Unmount oder das Entfernen des temporären Mountpunkts fehl, bleiben bereits erfasste Metadaten verfügbar. Weitere Medienzugriffe dieses Laufs enden; die Oberfläche hält das Gerät in der vorhandenen Quarantäne. Ein Gerätebefehls-Timeout beendet ebenfalls die weitere Partitionsbearbeitung und erhält bereits verfügbare Ergebnisse. Das Betriebssystem-/Worker-Gesamtzeitlimit bleibt unverändert: Bei einem hart beendeten Prozess kann noch nicht gespeicherter Arbeitsspeicherbestand nicht wiederhergestellt werden. Die reservierte Sichtung bleibt als nicht erfolgreich abgeschlossener Versuch sichtbar. Ein inkrementelles Wiederaufnahmesystem ist nicht implementiert.

## Fallregister und Audit

Reservierungen und Fehlereignisse des bestehenden Audits bilden fehlgeschlagene oder nicht sicher abgeschlossene Versuche in Kacheln, Fallprotokoll, CSV, Text und PDF ab. Es ist keine neue Datenbanktabelle nötig. Bestehende Sichtungsnummern, Entscheidungen und Audit-Ereignisse werden nicht umgeschrieben. Mehrere Fehlermeldungen derselben reservierten Sichtung erzeugen einen Registereintrag; ein bereits registriertes Ergebnis bekommt keinen zusätzlichen Fehlversuchseintrag.

`scan_completed` bleibt aus Kompatibilitätsgründen der Name für die Registrierung eines verfügbaren Ergebnisses. Neue Ereignisse enthalten zusätzlich `scan_status`, `inventory_complete`, Fehlerzahl und betroffene Partitionen. Ein gespeichertes Ergebnis mit `failed` ist ausdrücklich keine vollständig erfolgreiche Sichtung. Technische Fehler ohne registrierbares Inventar erhalten genau ein `scan_failed`-Ereignis. Scheitert nach einer erfolgreichen Registrierung nur noch die Antwort-/Exportverarbeitung, wird kein widersprüchlicher zweiter Scanabschluss erzeugt.

## Nicht sichern

Bei `partial`, `failed` oder `unknown` muss die Person neben einem Begründungscode eine sachliche Notiz angeben und die zusätzliche Warnung bewusst bestätigen. Das Kästchen ist bei jeder neu angezeigten Sichtung und beim Wechsel der Entscheidung zunächst leer. Die API überprüft einen echten booleschen Wert `quality_acknowledged=true`, den dazu passenden aktuellen `quality_status` und die Notiz. Fehlende, als Text übertragene oder zu einem anderen Status gehörende Bestätigungen werden abgewiesen. Die Entscheidung und der bestätigte Status einschließlich Scan-ID/Fehlerzahl stehen im Audit. Dieser Schutz ersetzt keine Benutzeranmeldung oder allgemeine CSRF-Abwehr.

Vollständige USB-Sichtungen behalten den bisherigen Ablauf. Telefon-Schnellsichtungen verwenden weiterhin ihre Fachpersonen-Dokumentation; USB-spezifische Nichtauswahlbestätigungen werden dort nicht verlangt. Die Qualität von Telefon-APIs bezieht sich auf deren begrenzten Umfang und bestätigt keine vollständige Dateisystemerfassung.

## Historie und Sicherheitsgrenzen

Alte Qualitätswerte werden im Speicher anhand vorhandener Zusammenfassungen und Partitionsdaten abgeleitet. `summary.json`, `partitions.json`, B/M/C/A und Scanzeiträume werden dabei nicht verändert. Aktuelle Exporte können diese abgeleiteten Hinweise enthalten. Es findet keine rückwirkende Reparatur von Falldaten statt.

Schreibschutz, Medienidentität, sichere Mountoptionen, Arbeitssperren und Quarantäne bleiben erhalten. Ein Lesefehler beweist keinen Hardwaredefekt, ein Mountfehler keinen Dateisystemschaden und ein Timeout keine bestimmte Datenmenge. Verbindungen prüfen und eine erneute autorisierte Sichtung in Betracht ziehen; keine Reparatur auf dem Originalmedium durchführen.

## Prüfstand

Synthetische Python- und Browserregressionen prüfen vollständige/leere Bestände, einzelne Fehler, 26 Verzeichnisfehler bei 47 Dateien/38 Ordnern, 1.000 gezählte Fehler mit 50 Beispielen, Root-Ausfall, Partitionsausfall, Teildatenerhalt bei Unmount-Fehler, Fehlversuche ohne Inventar, alte Datenbankkopien und direkte API-Umgehungsversuche. Die Oberfläche wird bei 1512, 1280, 1000 und 800 Pixeln geprüft; Test-PDFs werden gerendert und visuell kontrolliert.

Noch erforderlich: kontrollierte FAT/exFAT/NTFS-Prüfungen auf einem freigegebenen Pi-Testgerät, reale EIO-/Unmount-/Kernel-Wartezustände, Neustartverhalten der bestehenden flüchtigen Quarantäne und Vor-/Nachvergleich eines entbehrlichen Testmediums. Grüne lokale Tests sind keine Hardwareabnahme. Es erfolgt keine automatische Installation auf dem produktiven Pi.
