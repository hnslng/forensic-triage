# Nachträgliche Metadatenauswertung (Alpha 86)

## Bedienung und Bedeutung

Eine gespeicherte USB-Sichtung im Fallregister öffnen. Die neue **Zeitraumauswertung** zeigt zuerst **Originalscan**: den damals gespeicherten Zeitraum und die damaligen Dateizuordnungen. **Neu auswerten** verlangt Beginn, Ende, eine ausdrücklich gewählte IANA-Zeitzone und Bearbeiter. Ein angeschlossenes Medium ist dafür weder erforderlich noch vorgesehen. Keine Vorschau, Inhaltsanalyse, neue Stichwortsuche oder Geräteaktion findet statt.

Jede neue Version bleibt in der Auswahl erhalten. Beim Wechsel wechseln Zeitraumstatistik, Kategorien und Dateifilter gemeinsam. Offene oder verspätete Antworten einer vorherigen Auswertung oder Medienansicht werden verworfen. Die vier oberen Kennzahlen des Scans bleiben historische Scanwerte. Der historische Zeitraumzähler wird, soweit vorhanden, zusätzlich im Kontext genannt.

In **Warum im Zeitraum?** öffnen Zähler die zugehörigen Originaldateien im Explorer. B/M/C/A-Beiträge überschneiden sich; nur die drei Gruppen **im Zeitraum + außerhalb + nicht bestimmbar** summieren sich zur Zahl erfasster Originaldateieinträge. Ausschließlich B/M/C/A und Mehrfachbeiträge werden getrennt gezählt. Der Explorer kombiniert Zeitraum, Kategorie, gespeichertes Stichwort/alle Treffer, Trefferquelle, Originalbestand und Zeitstempelgruppe. **Filter aufheben** setzt die Dateifilter zurück und erhält die gewählte Auswertung. Die vorhandene Ordner-/Containeransicht bleibt erhalten. Filterlisten werden serverseitig paginiert, höchstens 500 Einträge je Antwort; die Oberfläche fordert 250 an.

Einzelne Zeilen zeigen Partition, gespeicherte Stichwörter, Trefferquelle und aufklappbare B/M/C/A-Werte. Identische Pfade auf verschiedenen Partitionen bleiben getrennte Dateieinträge. Fehlt die Partitionskennung, wird dies angezeigt. Sortierung nach Pfad, Größe, Kategorie oder jüngstem **passenden** Zeitstempel; stabile zusätzliche Schlüssel verhindern wechselnde Seiten bei Gleichständen. Die vorhandene ungefilterte Baumansicht behält ihre historische Reihenfolge.

## Zeitraum und Zeitqualität

Es gilt unverändert `evaluate_file_period()` aus `period.py`: mindestens ein gültiger B/M/C/A-Wert innerhalb beider inklusiver lokaler Kalendertage genügt. Sommer-/Winterzeit und Tagesgrenzen folgen `ZoneInfo`. C bedeutet Metadatenänderung, keine Erstellung; A beweist keine bewusste Benutzerhandlung. FAT/exFAT/NTFS können unterschiedliche Werte und Genauigkeiten liefern. Es werden keine Werte korrigiert oder ersetzt.

Die Zusatzanalyse unterscheidet fehlende, technisch ungültige, parsebare Null-Epochen und Werte nach dem dokumentierten Scanbeginn. Der Nach-Scan-Hinweis ist eine Auffälligkeit, kein Manipulationsnachweis. Ohne dokumentierten Scanzeitpunkt ist diese Prüfung nicht möglich. Dateien ohne gültige Zeitstempel sind **nicht bestimmbar**, selbst wenn eine ältere Scanlogik einen negativen Treffer gespeichert hatte. Dieser abgeleitete Hinweis ändert die historische CSV nicht. Ohne ursprünglichen Zeitraum sind Originalzuordnungen ebenfalls nicht bestimmbar.

Bei historischen nicht reproduzierbaren Zeitzonen bleiben gespeicherte positive/negative Zuordnungen maßgeblich; es wird weder Wien noch die heutige Systemzeitzone zur Neuberechnung unterstellt. Die Unsicherheit wird angezeigt. Einzelwerte erscheinen dann ausdrücklich in UTC. Eine neue Auswertung verlangt immer eine gültige IANA-Zone. Fehlen historische Zuordnungsfelder, werden sie nicht erfunden; eine neue explizite Auswertung kann die vorhandenen Rohzeitwerte bewerten.

Virtuelle Archivdateien erhalten keine Zeitzuordnung des Containers und keine aus einem Archivnamen behauptete unabhängige Dateizeit. Sie bleiben getrennte virtuelle Einträge mit **Zeitraum nicht eigenständig bestimmbar**. Ihre Zahl erhöht keinen Originaldateizähler.

Datumsfelder prüfen echte Kalendertage, Schaltjahre, Vollständigkeit, Reihenfolge und genau vierstellige Jahre 0001–9999. Vor 1900 oder nach aktuellem Jahr + 1 ist eine ausdrückliche Bestätigung erforderlich; das Backend akzeptiert hierfür nur den JSON-Wert `true`. Legitime ungewöhnliche Zeiträume bleiben möglich. Native Datumseingaben unterliegen zusätzlich min/max; der Server bleibt maßgeblich.

## Historische Stichwörter

Grundlage ist ausschließlich `hits.json`, einschließlich damaliger Profilversion, Hash, Quellen und tatsächlich gewählter Begriffe. Heutige Profile werden nicht geladen. Nulltreffer erscheinen nur für nachweislich aktive damalige Begriffe. Ohne gespeicherte Auswahl werden nur tatsächlich dokumentierte Begriffe gezeigt; unbekannte erfolglose Suchen werden nicht behauptet.

Getrennt ausgewiesen werden gespeicherte Gesamtzuordnungen, dokumentierte Trefferpfade, eindeutig zugeordnete Originaldateien, virtuelle Einträge und Begriffe mit Treffern. Mehrere Begriffe können dieselbe Datei treffen. Die Einordnung Dateiname/Ordnerpfad/beides nutzt die bestehende Normalisierung für **bereits gespeicherte** Zuordnungen; neue Treffer werden dadurch nicht erzeugt. Pfadübergreifende Treffer werden gesondert gekennzeichnet.

Historische reine Pfadzeichenfolgen können dieselbe Datei auf mehreren Partitionen meinen. Der Filter zeigt in diesem Fall mögliche Kandidaten mit Mehrdeutigkeitshinweis. Es wird keine künstliche Eindeutigkeit behauptet; sichere eindeutige Zahlen sind dann Untergrenzen. Nicht auflösbare Trefferpfade bleiben als Problem sichtbar. Eine Abweichung zwischen gespeichertem Gesamtzähler und dokumentierten Pfaden wird nicht durch neue Suchläufe „repariert“.

## Speicherung, Audit und Export

Unveränderliche neue Versionen liegen unter `period-evaluations/<Medien-ID>/<32-Hex-ID>.sqlite3` innerhalb der Fallakte. Die Datei enthält Metadaten, Zusammenfassung, abgeleitete Dateizuordnungen und Stichwortverknüpfungen. Dazu gehören Auswertungsversion, Zeitpunkt/Bearbeiter, Zeitraum/Zone, Quell-Scan-ID und SHA-256 sämtlicher ursprünglicher Scanartefakte, einschließlich `files.csv`. Pro Version wird außerdem ihre eigene SHA-256 im bestehenden append-only Audit registriert.

Die Berechnung erfolgt in einer privaten Staging-Datei. Nach vollständiger Quellenkontrolle wird sie synchronisiert und mit einer atomaren Hardlink-Veröffentlichung ohne Ersetzen publiziert. Ein UUID-Konflikt bricht ab. Audit und Veröffentlichung werden zusammen abgeschlossen; unbestätigte Staging-Dateien und mögliche Crash-Waisen werden weder gelistet noch exportiert. Verzeichnis-Symlinks und fremde Speicherpfade sind unzulässig. Jeder Abruf überprüft Quell- und Versionsprüfsummen. Manipulierte oder anders zugeordnete Quellen führen zum Abbruch, keiner stillen Neuberechnung.

Originale `summary.json`, `files.csv`, `hits.json`, Partitionen, Rohartefakte sowie Geräte-/Scan-Snapshots werden nicht überschrieben. Eine Neuauswertung aktualisiert nur Audit und abgeleitete Fallberichte/Manifest. Bestehende historische Scanrecords werden dabei auch bei abweichendem alten Format erhalten. Eine ausdrücklich protokollierte Medienentscheidung darf wie bisher ihren abgeleiteten Entscheidungsrecord aktualisieren; das gehört nicht zur Neuauswertung.

Text und PDF hängen einen klar getrennten Abschnitt für spätere Auswertungen an; ursprüngliche Scanwerte bleiben im Originalteil. Das ZIP enthält nur registrierte vollständige Versionen. Manifest, ZIP und Versionsveröffentlichung sind gegen gegenseitiges Überholen geschützt. Die Auswertungsdatei lässt sich mit gewöhnlichen SQLite-Werkzeugen lesen; keine neue Laufzeitabhängigkeit.

Das ist logische Unveränderlichkeit mit Prüfsummen, kein WORM-Speicher und keine Signatur gegen einen Angreifer mit Schreibrechten auf Fallablage **und** Auditdatenbank. Dateisystemschutz, private Backups und kontrollierter Betrieb bleiben erforderlich. Schlägt nur die Berichterstellung nach erfolgtem Commit fehl, bleibt die Auswertung erhalten; die API meldet eine Exportwarnung, Berichte können erneut erzeugt werden.

## Ressourcen und Fehler

CSV wird fortlaufend in einen SQLite-Diskindex eingelesen. Grenzen: 512 MiB Quellartefakte insgesamt, 4.096 Quelldateien, 32 MiB je strukturierter JSON-Datei, 2 Mio. Original-/virtuelle Einträge und Stichwortverknüpfungen, 10.000 aktive Begriffe, 2 GiB veröffentlichter Index. Hashprüfung und Berechnung haben jeweils eine eigene 120-Sekunden-Grenze; SQL-Abfragen werden ebenfalls zeitlich begrenzt. Ein gesamter Auftrag einschließlich mehrerer Prüf- und Berichtsschritte kann länger dauern. SQLite verwendet 8 MiB Seitencache und temporäre Dateien. Es läuft höchstens eine Metadatenberechnung je Fallablage; Originalansichten werden außerhalb der Fälle in höchstens acht temporären Indizes zwischengespeichert.

Grenzen, beschädigte Strukturen, fehlendes Inventar, geänderte Quellen oder Speicherfehler führen zu einem sichtbaren Fehler und keiner veröffentlichten Teilversion. Größere Bestände oberhalb der Grenzen benötigen eine spätere Erweiterung; sie werden nicht still gekürzt. Ein API-Aufruf wartet auf die Berechnung; es gibt noch keine Hintergrundauftragswarteschlange oder Fortschrittsanzeige pro Datei. Gleichzeitige große Abrufe können warten und Quell-/Indexhashes verursachen bewusst zusätzliche Lesezeit.

Die maßgebliche Qualität `partial`/`failed`/`unknown` bleibt sichtbar. Eine Auswertung macht fehlende Dateien nicht wieder verfügbar. Ein Fehlversuch ohne Inventar ist kein normaler leerer Bestand.

## Neue API-Grenze

- `GET /api/evaluation-context`: Boot-CSRF-Token, Datumsrichtlinie und Zonenliste.
- `GET /api/media/<id>/analysis?evaluation_id=...`: Originalansicht oder registrierte Version.
- `GET/POST /api/cases/<fall>/media/<id>/period-evaluations`: Versionsliste beziehungsweise neue Version.
- `GET /api/media/<id>/files?analysis_view=1&...`: kombinierte Filter/Pagination.

Neue Routen und erweiterte Dateiabfragen verlangen freigegebene Hosts und same-origin Browserzugriffe. Zustandsänderungen verlangen JSON und ein pro Dienststart zufälliges Token in `X-Triage-CSRF`; keine CORS-Freigabe. Erlaubt sind IP-Literale, localhost, der tatsächliche Systemhostname und dessen `.local`-Name. Zusätzliche eigene Namen müssen ausdrücklich über `FORENSIC_TRIAGE_ALLOWED_HOSTS` konfiguriert werden. nginx soll den ursprünglichen Host weitergeben.

Dies ist keine Anmeldung und schließt die **übrigen Legacy-Routen** nicht nachträglich in eine zentrale Zugriffssperre ein. Der Dienst bleibt nur im kontrollierten Testnetz vertretbar. Offene Web-Entsperrung/HTTPS, Lösch-/Power-/Updatehärtung und der allgemeine Host-/Origin-/CSRF-Auditpunkt bleiben bestehen; siehe [Sicherheit](../SECURITY.md) und [Auditliste](AUDIT_ALPHA84_TODOS.md).
