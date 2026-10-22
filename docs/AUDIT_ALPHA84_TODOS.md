# Gegenprüfung des Alpha-82-Berichts und Arbeitsliste für Alpha 84

Stand: **22. Oktober 2026**. Grundlage: der vom Projektinhaber übergebene Prüfbericht zu Alpha 82, gegengeprüft am lokalen Alpha-84-Code (`v0.2.0-alpha.84`, Commit `c171badef3dfc2ffd242313f9c9f11c1406ccf37`) samt nachfolgender Dokumentation. Keine Programm-, Installer- oder Systemänderung bei dieser Gegenprüfung. Keine Server-/GitHub-Zugriffe, keine Prüfung oder Änderung am FCA-Projekt.

## Umfang und Aussagegrenzen

Alle 14 Befunde K1–K5 und W1–W9 sowie die zusätzlichen TRIAGE-Beobachtungen wurden gegen relevante lokale Quellen abgeglichen. Das ist eine gezielte Code-/Dokumentationsprüfung, kein vollständiges Zeilen-, Secret-, Penetrations- oder Hardwareaudit. Fehlende Schutzprüfungen sind im Code sichtbar; konkrete Browserangriffe und Betriebssystemverhalten wurden nicht praktisch nachgestellt. Verweise auf Dateien sind der Nachweis für die Einordnung, nicht für eine bestandene Hardwareabnahme.

Status: **teilweise** = bereits wirksame Korrektur, aber Berichtsforderungen nicht vollständig erfüllt; **offen** = Umsetzung oder Nachweis fehlt; **Realtest offen** = automatisierte Prüfung ersetzt keine Geräteabnahme. Kein Befund wird nur aufgrund eines grünen Gesamttests geschlossen.

## Zusammenfassung aller Befunde

| ID | Alpha-84-Stand | Nachweis im Projekt | Nächster Schritt |
|---|---|---|---|
| K1 | Teilweise behoben | `fast_inventory.py: inventory_tree`, `scanner.py`, Tests für fehlende Datei und Verzeichnisfehler | Fehlerliste begrenzen, Gesamtzähler und Fehlerart ergänzen; EIO und Unmount-Ausfall gezielt prüfen |
| K2 | Teilweise behoben | `scan_quality.py`, `casefiles.py`, `pdf_report.py`, `web/app.js: renderResults` | Qualitätsstatus in Register/Medienliste/Audit; Bestätigung bei „Nicht sichern“ |
| K3 | Offen; konkrete Vorfallsursache korrigiert | `commands.py`, `scan_process.py`, `scanner.py`, `web.py`, nginx-Vorlage | Fortschritt/Teilspeicherung planen und testen; nicht pauschal Limits erhöhen |
| K4 | Offen, Hardwareauswirkung nicht nachgestellt | `device.py`, `scripts/install_debian.sh`, `deploy/` | Automount-Schutz für dedizierte Box entwerfen und auf Testgerät validieren |
| K5 | Offen; vorhandene Arbeitssperren berücksichtigen | `web.py`, nginx-/systemd-Vorlagen, `SECURITY.md` | Route-spezifischer Browserzugriffsschutz, serverseitige Bestätigungen und Härtung |
| W1 | Offen | `period.py: validate_period`, Datumsfelder und Vergleiche in `web/` | Robuste Datumseingabe und verständliche Plausibilitätswarnung |
| W2 | Offen; Snapshot-Erhalt bewusst vorhanden | `casefiles.py: start_case`, `period.py`, `docs/timestamps.md` | Zusätzliche versionierte Zeitraumauswertung aus gespeicherten Metadaten |
| W3 | Teilweise vorhanden, Realtest offen | `period.py: period_timezone_info`, `fast_inventory.py` | FAT/exFAT-Zeitzonen-/Sommerzeitvergleich; Zeitzone verständlich anzeigen |
| W4 | Offen für gezielten Wiederholungsworkflow | Scan-/Refresh-/Eject-Routen, Quarantäne und Medienzustände in `web.py`/`web/app.js` | Explizites „Neu einlesen“ mit eigenem Lauf und Vorgängerverweis |
| W5 | Teilweise verständliche Meldungen, keine einheitliche Schicht | `scan_worker.py`, `scan_process.py`, Fehlerantworten in `web.py` | Stabile Fehlercodes, Handlungsanweisung und getrennte technische Details |
| W6 | Offen | `.github/workflows/tests.yml` | Isolierten Browser-Testjob ergänzen |
| W7 | Offen | `pyproject.toml`, kein versioniertes Lock-/Constraints-Artefakt gefunden | Reproduzierbare Abhängigkeiten einschließlich Zielplattform planen |
| W8 | Teilweise aktualisiert, Restwidersprüche belegt | README, `docs/forensic-safety.md`, Roadmap | Alte Ist-Aussagen korrigieren, Historie kennzeichnen, Versionsprüfung ergänzen |
| W9 | Wartungsaufgabe bestätigt, niedrige Priorität | große UI-/Web-/Fallaktenmodule und Browsertestdatei | Nur schrittweise, mit Regressionstests aufteilen |

## Priorität 1: Fehlerergebnisse verlässlich machen

### K1 – Teilinventar und Lesefehler

Bereits vorhanden: `OSError` pro Dateieintrag wird im Mountpfad protokolliert, `os.walk` hat einen Fehlerhandler, nachfolgende lesbare Einträge werden weiter erfasst. Ohne Fehlerkanal wird ein Fehler weiterhin ausgelöst statt stillschweigend ein vollständiges Ergebnis zu behaupten. Tests prüfen fehlenden Eintrag (`ENOENT`), simulierten Verzeichniszugriffsfehler und Erhalt der lesbaren Nachbareinträge.

- [ ] Fehlerliste begrenzen, aber Gesamtzahl aller Fehler weiterzählen; getrennte Datei-/Verzeichniszähler und Fehlerart speichern. Aktuell unbeschränkte Liste mit Pfad, errno und Text.
- [ ] `EIO`, sehr viele Fehler, fehlgeschlagene Wurzelbegehung und ausschließlich nicht lesbare Einträge testen. Aktuell kann eine komplett fehlgeschlagene Begehung als `partial` statt `failed` gelten; nie als Leerbefund behandeln.
- [ ] Umgang mit Fehlern nach der Begehung festlegen: etwa beim Unmount kann die Rückgabe des Inventars weiterhin verloren gehen. Teildaten sichern, aber fehlenden sicheren Abschluss ausdrücklich dokumentieren.
- [ ] Fehler während Dateisystem-/Partitionsbeschreibung von wirklich leeren, erfolgreich gelesenen Beständen unterscheiden.

Abnahme: Datei vor/nach künstlichem `EIO` bleibt erhalten; Verzeichnisfehler ist gezählt; bei mehr Fehlern als Detail-Limit bleiben genaue Zähler erhalten. Komplettausfall und Cleanup-Fehler werden eindeutig angezeigt, ohne Schreibschutz oder Unmount-Prüfung zu lockern.

### K2 – Warnung bis zur Entscheidung und ins Register tragen

Bereits vorhanden: `complete`/`partial`/`failed` und Warnungen in der Zusammenfassung; Ergebnisansicht, Diagnose sowie Text-/PDF-Berichte kennzeichnen Fehler. Historische Partitionsfehler werden lesend berücksichtigt. Noch nicht durchgängig vorhanden: Status in den Medienlisten und CSV-Registern, genaue Fehlerzähler und entscheidungsbezogene Bestätigung. `scan_completed` im Fall-Audit enthält derzeit keinen Qualitätsstatus.

- [ ] Status und Fehlerzähler in Medienübersicht, Medienregister und Fall-Audit ergänzen; additive, getestete Migration beziehungsweise nachvollziehbare Ableitung wählen.
- [ ] Bei „Nicht sichern“ nach unvollständiger/fehlgeschlagener Sichtung zusätzliche ausdrückliche Bestätigung und Begründung verlangen, serverseitig prüfen und auditieren.
- [ ] Alte und fehlende Qualitätsangaben konservativ behandeln; keine pauschale Vollständigkeit für unbewertbare Unterlagen behaupten.
- [ ] Detailanzeige von technischen Rohfehlern trennen, Anzahl übersprungener Einträge verständlich nennen.

Abnahme: Ein Nullergebnis mit Fehlern trägt überall eine Warnung. Eine direkte API-Anfrage ohne zusätzliche Bestätigung kann die Schutzabfrage nicht umgehen; Bestätigung und Qualitätsstand stehen im Audit und Export.

### K3 – Zeitlimit und Fortschritt

Belegt: Standard 180 Sekunden gesamt und 15 Sekunden je externem Gerätebefehl; Werte konfigurierbar. Timeout bricht den Worker ab, fertige Dateiliste wird bislang erst zum Ende geschrieben. Keine allgemeine Kapazitätsgrenze belegt. Das tatsächlich gelieferte Vorfallsprotokoll zeigt einen Dateieintragsfehler nach 55,446 Sekunden, **keinen Timeout**. Eine generelle Nichtauswertbarkeit großer Sticks oder angebliche 285-GB-Grenze ist nicht nachgewiesen.

- [ ] Mit bekanntem großen Testbestand messen, welche Stufe Zeit verbraucht; Fortschritt ohne zusätzliche Nutzdatenanalyse erfassen.
- [ ] Dauerhaftes inkrementelles Teilinventar und konsistente Abschlussmarkierung entwerfen; unterbrochene/abgestürzte Läufe dürfen nicht `complete` erscheinen.
- [ ] Gesamtlimit, Befehlslimits und Fortschritts-Watchdog getrennt bewerten; nginx-Zeitlimit (aktuell 190 Sekunden) und Clientverhalten mit berücksichtigen.
- [ ] FAST-Abhängigkeit von `fsstat` prüfen: Typinformation nur dann anderweitig beziehen, wenn Sicherheits-/Partitionsprüfung und Nachweise erhalten bleiben.
- [ ] Neustartverhalten der flüchtigen Quarantäne festlegen; keine Entsperrung eines möglicherweise noch aktiven Kernelzugriffs per Knopfdruck.

Abnahme: Simulierter Befehls-/Gesamttimeout und Prozessabbruch erhalten eindeutig unvollständige Teildaten; andere Scans und Oberfläche bleiben bedienbar. Pi-Messung separat, keine Laufzeitgarantie aus Simulation.

### W4/W5 – Neu einlesen und verständliche Fehler

- [ ] Wiederholungsaktion je Medium mit eindeutig neuem Lauf, Vorgängerverweis und erhaltenem Fehlversuch. Festlegen, ob neue SICHT-Nummer oder Unterlauf; nicht bestehende Snapshots überschreiben.
- [ ] Quarantäne respektieren; nötiges Abziehen/Neuverbinden klar erläutern. Vor Wiederholung Verfügbarkeit und Schreibschutz erneut prüfen.
- [ ] Fehlercodes für Einbinden, Partitionserkennung, Zeitlimit, Teilinventar, Schreibschutz, bereits eingebundenes Medium, Verbindungsverlust und unbekannte Fehler einführen.
- [ ] Jede Meldung erklärt: Was ist passiert? Was bedeutet das Ergebnis? Was ist als Nächstes zu tun? Technische Details aufklappbar und im Protokoll erhalten.
- [ ] Keine unbewiesene Ursache behaupten: Mountfehler bedeutet nicht sicher Dateisystemschaden; Timeout bedeutet nicht sicher großen/defekten Stick; keine Partition bedeutet nicht sicher leer/verschlüsselt.

Abnahme: Python-/Browserprüfungen für alle Fehlerpfade, Wiederholung und Quarantäne; alte und neue Läufe bleiben auffindbar. CRT-Design beibehalten, Rohfehler nie einzige Benutzerinformation.

## Priorität 2: Zugriff und Datenträgerschutz

### K4 – Automount vor der Schutzfolge

Belegt: bereits eingebundene Geräte werden abgelehnt; Installer enthält keine erkennbare dedizierte Automount-Verhinderung. Verhalten des konkreten Pi ist dadurch nicht bewiesen. Read-only wird erst nach Geräteprüfung gesetzt.

- [ ] Zielplattform und mögliche Automount-Dienste auf dem Test-Pi erfassen; Desktop und Lite getrennt behandeln.
- [ ] Eng begrenzten Automount-Schutz für autorisierte Prüfmedien entwerfen; nicht blind systemweite Dienste auf beliebigen Installationen maskieren.
- [ ] Frühe Read-only-Regel nur mit exakter Geräteabgrenzung und Rennen-Test einsetzen; udev allein ist kein validierter Hardware-Schreibblocker.
- [ ] Hashvergleich vor/nach Scan auf entbehrlichem Testmedium und Kontrolle unmittelbar nach Anstecken; Referenz mit Hardware-Schreibblocker. Systemmedium niemals zum Testziel machen.
- [ ] Nicht sauber abgeschlossene Journale und verweigertes Mounten als Erfassungslücke behandeln; keine Reparatur auf Beweismitteln.

Abnahme: dokumentierter Lite-/Desktop-Test ohne ungewolltes Read-write-Mount; Vor-/Nachvergleich reproduzierbar. Hardware-Schreibblocker und Grenzen bleiben ausdrücklich dokumentiert.

### K5 – Webzugriffe, Bestätigungen und Root-Dienst

Belegt: keine Anmeldung oder zentrale Host-/Origin-/CSRF-Prüfung; nginx akzeptiert private Netzbereiche und arbeitet als Default-Server. `server_name` allein ist keine Host-Sperre. Webdienst läuft als root, besitzt `PrivateMounts=true`, aber keine weitergehende Härtung wie `ProtectSystem`. Konkrete CSRF-/DNS-Rebinding-Angriffe wurden hier nicht ausgeführt.

Vorhandene Schutzmaßnahmen nicht unterschlagen: Power prüft zulässige Aktion sowie aktive Fälle/Scans/Updates; Installationen besitzen Arbeitssperren und Offline-Pakete Signaturprüfung. Die zweite Power-/Update-Bestätigung ist aber ein UI-Schritt, kein separater serverseitiger Nachweis. DELETE verlangt die Fallnummer, prüft jedoch keine aktive Fall-/Scansperre.

- [ ] Host- und Origin-Vertrauensmodell für Hotspot, LAN, mDNS und zulässige IP-Aufrufe festlegen; auch Reverse-Proxy-Konfiguration berücksichtigen.
- [ ] Zentralen Schutz zustandsändernder Routen gegen fremde Browserursprünge und CSRF implementieren. Fehlende/`null`-Origins und direkte API-Aufrufe bewusst regeln.
- [ ] Content-Type routenspezifisch validieren: JSON für JSON-Routen, **`application/octet-stream` für signierte Offline-Pakete erhalten**. Keine pauschale JSON-Pflicht, die Updates zerstört.
- [ ] Serverseitige Bestätigungen für gefährliche Aktionen und atomare Arbeitssperren ergänzen; aktive/laufend gescannte Fälle auch im DELETE-Endpunkt schützen, Parallelzugriffe testen.
- [ ] Root-Webdienst verkleinern beziehungsweise privilegierte Geräteaktionen abtrennen; systemd-Härtung schrittweise gegen Mount-/Worker-/Update-Funktionen testen.
- [ ] Web-Entsperrung, HTTPS, gerätespezifisches WLAN-Kennwort und verschlüsselte Fallablage bleiben vor echtem Einsatz offen.

Abnahme: fremde Host-/Origin-/CSRF-Anfragen ohne Mutation zurückweisen; legitime lokale Bedienung und Offline-Upload funktionieren; direkte Power-/Lösch-/Installationsanfragen umgehen Bestätigungen oder Arbeitssperren nicht. Gefährliche Befehle im Test ausschließlich mocken, keinen echten Neustart auslösen.

## Priorität 3: Datum, Zeitraum und Zeitzone

### W1 – Datumseingabe

Belegt: native Datumsfelder ohne min/max; UI vergleicht Texte. Backend prüft echtes ISO-Datum und Reihenfolge, aber keine Jahresplausibilität. Browserproblem mit der Jahreszahl wurde hier nicht auf Safari reproduziert.

- [ ] Verlässliche Zwischenwert-/Jahresprüfung und Fehlermeldung direkt am Feld, einschließlich fünfstelliger Jahre; Datum/Reihenfolge in UI und Backend konsistent behandeln.
- [ ] Zulässige Jahresgrenzen fachlich entscheiden. Keine pauschale Sperre historischer/zukünftiger Zeiträume allein nach Vorschlag des Berichts; ggf. Warnung und bewusste Bestätigung statt Ausschluss.
- [ ] 0202, 2062, 20266, ungültigen Tag, Schaltjahr, leeren/halben Zeitraum und Beginn nach Ende prüfen; Safari-Jahreseingabe praktisch testen.

Abnahme: keine stillen Tippfehler oder unverständlichen Zwischenzustände; legitime vereinbarte Zeiträume bleiben nutzbar.

### W2 – Nachträgliche Zeitraumauswertung

Belegt: geänderter Fallzeitraum wird auditiert, bestehende Sichtungs-Snapshots und Zähler bleiben bewusst unverändert. Das ist kein Nachweis für eine bereits vorhandene Neuauswertung.

- [ ] Neue versionierte Auswertung aus gespeichertem `files.csv` erstellen, mit Zeitraum, Zeitzone, Quellenbezug und Audit; Originale unverändert lassen.
- [ ] Alte/fehlende Zeiträume in der UI erkennbar machen; neue Auswertung je Sichtung/Fall bewusst starten, aktive Ansicht und Berichtsversion kennzeichnen.
- [ ] Telefone weiter „nicht anwendbar“; fehlende/ungültige Zeitwerte gesondert zählen.

Abnahme: Scan ohne Zeitraum → Zeitraum setzen → Neuauswertung liefert erwartete Zahlen/Kategorien; Original-Hashes unverändert, Audit und Export nennen die neue Auswertung.

### W3 – FAT/exFAT und Zeitzonen

Bereits vorhanden: IANA-Zeitzonenquelle und Reproduzierbarkeitskennzeichen. Nicht belegt: korrekte FAT-/exFAT-Kernelkonvertierung auf jedem Pi; Mount enthält keine explizite Zeitzonenoption. FAT und exFAT nicht ohne Prüfung gleichsetzen.

- [ ] Gerätezeitzone im Setup prüfen/anzeigen; nicht ungefragt weltweit `Europe/Vienna` erzwingen.
- [ ] Bekannte FAT-/exFAT-Zeiten um 23:30/00:30 sowie Sommer-/Winterzeit gegen FAST und TSK vergleichen, Werkzeug-/Kernelstand dokumentieren.
- [ ] Unbekannte Quellzeitzone oder nicht reproduzierbare lokale Zone sichtbar kennzeichnen; keine unbewiesene automatische Korrektur.

Abnahme: Tageszuordnung mit bekanntem Sollbestand und Zeitzone reproduzierbar, verbleibende Unsicherheit sichtbar.

## Priorität 4: Testprozess und Dokumentation

### W6 – Browserprüfungen in CI

- [ ] Eigenen CI-Job für Node/Playwright mit Browserinstallation und passender Version ergänzen; Berechtigungen minimal und Actions wie bisher gepinnt.
- [ ] Sämtliche isolierten Browserprüfungen ausführen, neue Schutz-/Fehlerfälle aufnehmen. Python-Version 3.12 zusätzlich zur bisherigen 3.11 prüfen.
- [ ] Lauf und Artefakte erst nach bewusster Veröffentlichung als CI-Erfolg melden. Aktuell nur lokaler Nachweis, kein GitHub-Lauf.

Abnahme: absichtlich fehlschlagender UI-Test macht CI rot, unveränderter Stand grün; ohne Pi oder echte Falldaten.

### W7 – Reproduzierbare Abhängigkeiten

- [ ] Lock-/Constraints-Konzept für Python inklusive Transitiven, Build-/Testwerkzeugen und Hashes festlegen; Playwright/Node und Debian-Werkzeugstände mit erfassen.
- [ ] Pi-Architektur und verfügbare Wheels berücksichtigen; Offline-Kompatibilitätsprüfung bei Format-/Abhängigkeitswechsel mit testen.
- [ ] Neuinstallation aus kontrollierten Quellen auf getrenntem Testsystem wiederholen und Versionen dokumentieren.

Abnahme: reproduzierbarer Bestand auf Zielplattform; Abhängigkeitsänderungen werden nicht als gewöhnliches kompatibles `.tbu` ausgegeben.

### W8 – Restliche Dokumentationswidersprüche

Bereits aktualisiert: README-Projektstatus, Projektstand, Testplan, Offline-Ablauf und Alpha-84-Prüfnachweis. Restlich belegt: README-Grenzen nennen Alpha 60, englische Zusammenfassung stellt Alpha 75 heraus; `forensic-safety.md` nennt Alpha 64 und historisch missverständliche iPhone-Mount-Aussagen. Roadmap hatte Alpha-64-Stand und behauptete persistente Diagnose pauschal, obwohl die UI-Konsole RAM-only ist.

- [ ] Alte Ist-Versionsaussagen entfernen oder eindeutig als „seit“/historisch kennzeichnen; aktuelle Telefon-App-only-Grenzen in beiden Sprachen abgleichen.
- [ ] Versionen aus Paketquelle ableiten oder automatisiert gegen aktuelle Statusfelder prüfen; historische Release-/Testnachweise nicht pauschal umschreiben.
- [ ] Querverweise, UI-Bezeichnungen und widersprüchliche Implementiert-/Offen-Einträge systematisch abgleichen.

Abnahme: aktuelle Statusangaben stimmen mit Paketversion überein; historische Nachweise bleiben erkennbar historisch. Dieser Bericht schließt W8 nicht allein durch Erfassung der Restpunkte.

## Priorität 5: Wartbarkeit (W9)

Gemessener Umfang zum Prüfzeitpunkt, gerundet: `web/app.js` 189 kB, `web.py` 72 kB, `casefiles.py` 57 kB, Browsertests 159 kB und CSS 109 kB. Größe ist eine Wartungslast, allein kein Sicherheitsfehler.

- [ ] Bei ohnehin nötigen Änderungen fachlich kleine Module ausgliedern, öffentliche Schnittstellen stabil halten.
- [ ] Keine große Umstrukturierung gleichzeitig mit Änderungen an Schreibschutz, Fehlerabschluss oder Entscheidungsworkflow.

Abnahme: unverändertes Verhalten mit vollständigen Python-/Browserregressionen; kein eigenes Großprojekt vor den Sicherheitsaufgaben.

## Weitere Aussagen des übergebenen Berichts

- **Montieren/Zeitstempel:** FAST verwendet geprüften Software-Read-only-Mount, TSK ist mountfrei. Aussage über tatsächliche Unverändertheit des Mediums benötigt Vor-/Nachtest und Schutz vor Automount; nicht als universelle Hardwaregarantie auslegen.
- **Kapazität/Vorfall:** Bericht nennt 285 GB; die bereitgestellte Anzeige zeigte einen als 256-GB-Stick beschriebenen Datenträger mit 232,4 angezeigten GB. Keine 285-GB-Messung und keine größenbedingte Ursache belegt. Private Gerätekennungen/Pfade nicht in Git übernehmen.
- **Tests im alten Bericht:** 299/303 Python-Tests bei fehlendem `ssh-keygen` sind historische Fremdumgebungsergebnisse, kein aktueller Fehlschlag des lokalen Alpha-84-Stands.
- **Installation:** Doku lädt das Bootstrap-Skript zuerst in eine Datei und führt es danach als root aus; nicht wörtlich `curl | bash`. Vertrauen in Quelle/Ref bleibt relevant. [ ] Freigegebenen Ref/Integritätsnachweis für Neuinstallation und privaten Lesezugriff reproduzierbar prüfen.
- **Kennwort-Platzhalter:** README nennt einen Alpha-Platzhalter, kein belastbarer Nachweis eines echten Secret-Leaks. [ ] Deployment-Defaults und Ersetzung vor Einsatz separat prüfen; in dieser Gegenprüfung kein vollständiger Secret-Scan.
- **Backup/Zugriff:** Unverschlüsselte Ablage, fehlende Anmeldung/HTTPS, nicht vollständiger Restore und Stromausfall-Rollback bleiben offene Einsatzgrenzen, keine neuen erledigten Funktionen.
- **Nutzdaten:** Keine pauschale Behauptung „keine Bytes gelesen“: Dateimetadaten und Archivverzeichnisse werden gelesen, letztere ggf. intern dekodiert. Keine Extraktion/Ausführung von Nutzdateien; Telefonpfad App-/Gerätemetadaten.
- **FCA-Anhang:** anderes Projekt, nicht geprüft und nicht verändert. Keine dortige Behebung oder Aktualität behaupten.

## Arbeitsregeln und erneute Abnahme

1. Vor Scanner-/Mount-/Zeitänderungen zunächst reproduzierbaren Fehlertest schreiben; danach Änderung, vollständige Python- und Browserprüfungen, Changelog und betroffene Doku.
2. Read-only-Schutzfolge, Isolation, Update-Signatur und unveränderliche Original-Snapshots erhalten. Keine Reparatur oder Schreibzugriffe auf Prüfmedien.
3. Datenbank-/Registererweiterungen additiv und gegen alte Fallakten testen. UI-Meldungen im bestehenden Design halten.
4. Implementierung, automatisierte Prüfung, Installation und Hardwareabnahme getrennt abhaken. Keine Freigabe allein aus grünem Testlauf.
5. Diese Gegenprüfung verändert das bereits ausgegebene Alpha-84-Paket nicht. Künftige funktionale Änderungen erhalten einen neuen Release-Stand.

## Prüfläufe dieser Gegenprüfung

Vollständige lokale Python- und Browserläufe wurden bei dieser Gegenprüfung erneut ausgeführt; keine Server-/Hardwaretests und keine Ausführung von Power-/Installationsaktionen.

- Python: **319 bestanden**, keine Fehler (3,17 Sekunden).
- Browser: **107 bestanden**, keine Fehler oder übersprungenen Tests (ca. 99 Sekunden, Chromium).
- Dokumentationsprüfung: **73 relative Dateiverweise** in den bearbeiteten Dokumenten auf vorhandene Zieldateien geprüft; `git diff --check` erfolgreich. Ankerziele und externe Webseiten dabei nicht geprüft. Alpha-84-Paketprüfsumme erneut kontrolliert und unverändert.

Paketbezogener vorheriger Nachweis: [Alpha 84](validation-2026-10-22-alpha84.md). Gemeinsame Aufgabenübersicht: [Roadmap](roadmap.md).
