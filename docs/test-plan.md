# Testplan / Test plan

Stand: 4. Oktober 2026 · Anwendung: `v0.2.0-alpha.68`. Dies ist ein Prüfplan, kein Beleg, dass alle folgenden Prüfungen bereits bestanden wurden. Vorhandene Nachweise und praktische Pi-Beobachtungen stehen in [project-status.md](project-status.md). Die Telefon-Praxistests stehen in [iphone-triage.md](iphone-triage.md#erster-test-mit-einem-echten-iphone) und [android-triage.md](android-triage.md#praktischer-samsung-test).

Für den Alpha-68-Pi-Nachtest zuerst in Safari/macOS die Hauptseite laden, ohne Einstellungen zu öffnen: wenn kein Fall aktiv ist, liegt der gesamte TRIAGE//BOX-Bildschirm im Hintergrund, ist abgedunkelt und deutlicher (ca. 7,5 px) geblurrt und nicht bedienbar. Der zentrale Startbereich zeigt `TRIAGE//BOX` (die beiden Slashes separat in Acid-Grün), `BEREIT` und den Button „Fall anlegen / öffnen" — ohne zusätzlichen Erklärungssatz darunter. Oben rechts im Overlay befinden sich kompakte Utility-Controls für Einstellungen und Power, die dieselben lokalen Inline-SVGs wie die Systemleiste verwenden. Beide öffnen ihre Dialoge über dem Overlay; nach dem Schließen ist der Startzustand wieder sichtbar. Beim Reload mit serverseitig aktivem Fall darf das Overlay nicht kurz aufblitzen. Im aktiven Fall ohne Medium zeigt das Medien-Dashboard statt mehrzeiliger Hilfe nur `KEIN MEDIUM VERBUNDEN`.

Danach Einstellungen öffnen, Stichwortprofile wählen: Profilliste links als Tabellenansicht mit den Spalten **PROFIL**, **STICHWÖRTER** und **VERSION** rechtsbündig, gleiche Master-Breite und Zeilenhöhe wie bei den Dateitypen. Editor rechts: Profilname bearbeiten, duplizieren, neues Profil anlegen, **ALLE**/**KEINE**, Zähler `n / m AKTIV`, Suchleiste „Begriff suchen …" (filtert nur die Anzeige), Begriffe hinzufügen/entfernen, speichern und „Auswahl für nächste Scans" getrennt prüfen. Die Stichwortliste ist eine einzeilige Tabelle (AKTIV · STICHWORT/DATEINAME · ENTFERNEN) mit eigener Scrollfläche; Header, Suche und Footer bleiben dabei sichtbar. Mit einem langen Profil (100–250 Begriffe) Scrollen, Filter und Entfernen prüfen. Eine leere Auswahl muss nach dem Speichern leer bleiben. Die erweiterten Standardprofile umfassen 38 Begriffe (Allgemein / Wirtschaft) und 32 Begriffe (Krypto / Wallets).

Dann Dateitypen wählen: Kategorien links als Tabellenansicht mit den Spalten **KATEGORIE** und **ENDUNGEN** (Anzahl rechtsbündig als Zahl), kopf- und zeilengleich mit der Profilliste. Klick öffnet rechts den Editor für Kategoriename und Endungen. Neue Kategorie anlegen, Endungen bearbeiten, Änderungen übernehmen, Kategorie löschen, Standard laden und Änderungen speichern prüfen.

Dann Erkennungsregeln wählen: Suche, Filter, Sortierung und Regelanzahl stehen auf Desktop in einer Zeile mit gemeinsamer Label-Baseline. Der Tabellenkopf bleibt beim Scrollen sticky und deckt die Zeilen vollständig ab — Regressionsprüfung der Alpha-67-Korrektur einzeln durchführen (Symbol `✓`, `?`, `—` und Statuszeilen dürfen nicht durchscheinen). Der rechte Editor nutzt die volle Höhe mit scrollbarer Feldbereich und festem Footer; die Footer-Buttons **Übernehmen** und **Abbrechen** sind kompakt. Bei einer Regel mit nur Android-ID muss Android `✓` und iOS `?` zeigen; eine Regel ohne verifizierte IDs muss `? / ?` zeigen. `?` darf niemals als Aussage verstanden werden, dass keine App existiert. Tooltips per Maus, Tabulator und Touch prüfen und die migrierten lokalen Regeln, eigenen Regeln und gelöschten Standardregeln mit dem Alpha-62-Bestand vergleichen. Wichtige Bedienicons (Einstellungen, Power, Aktualisieren, Fall starten/beenden, Auswerfen, Stromwarnung, Overlay-Utility-Controls) müssen als Inline-SVGs gerendert werden, nicht als abhängige Unicode-Zeichen.

Dann Updates wählen: Der Statusblock zeigt Version, Status und letzte Prüfung gemeinsam mit dem Knopf „Jetzt prüfen". Normalzustand nach abgeschlossenem Update ist ausschließlich `✓ AKTUELL` — keine dauerhafte Erfolgsmeldung mehr. Falls eine ältere Alpha dem Dienst noch den Zustand `installed` schreibt, zeigt die Oberfläche weiterhin nur `✓ AKTUELL` mit der neuen Version. „Update verfügbar" zeigt `UPDATE VERFÜGBAR · <Zielversion>` mit Primärknopf; Prüfung/Installation zeigen den laufenden Zustand; Fehlerzustände zeigen `UPDATE FEHLGESCHLAGEN` und eine kurze konkrete Ursache. Offline-Update bleibt als eigener Abschnitt mit Durchsuchen und PAKET INSTALLIEREN vorhanden und bleibt durch aktive Fälle/Scans gesperrt.

Responsive-Verhalten bei 1440 px, 1280 px, 1000 px und 620 px prüfen: Profil-Master-Detail, Dateitypen-Master-Detail und Erkennungsregeln-Toolbar sollen sinnvoll umgebrochen werden, Settings-Footer und wichtige Buttons müssen erreichbar bleiben. Zusätzlich auf Safari/macOS, Firefox und Brave/Chromium unter Windows prüfen, ob Settings, Stichwortprofile, Dateitypen, Erkennungsregeln, Updates, Medienkarten, Fallfenster, Tooltips, Statuszeilen, Tabellen und Ergebnis-/Scanansicht weiterhin technisch aussehen, aber kleine Labels/Hilfetexte nicht pixelig oder zu dünn wirken. Es dürfen keine externen Fonts geladen werden; `Courier New` darf nicht mehr als primärer Stack-Fallback auftauchen.

Für Alpha 61 zusätzlich prüfen: Erkennungsregeln im neuen Master-Detail-Editor bearbeiten, suchen, filtern, duplizieren, löschen und per JSON exportieren/importieren. Regeländerungen speichern, anschließend neuen Scan und Regelstand/Treffergrund in `crypto-rules.json`, `crypto-hints.json`, `backup-hints.json`, `summary.json` und Fall-ZIP vergleichen. Bestehende Sichtungen müssen unverändert bleiben. Banking-/Finanz-Apps dürfen nicht als Krypto-Hinweis zählen. Geräte-Backup-Strukturen müssen in `backup-hints.json` und der Oberfläche sichtbar sein, ohne dass Backup-Inhalte analysiert werden. Telefonläufe müssen ein leeres `files.csv` erzeugen und dürfen keine AFC-/MTP-/Dateiinventarisierung starten. Bei iPhones/iPads Seriennummer und UDID getrennt prüfen. Bei Android müssen unvollständige Profile und nicht sichtbare geschützte Bereiche einen unbekannten Status statt eines Negativbefunds erhalten.

## Automatisierte Tests

Die Python-Tests lokal ausführen:

```bash
.venv/bin/python -m pytest
```

Abgedeckt sind insbesondere:

- Normalisierung von Dateiendungen und Kategorien
- Stichwortsuche in vollständigen Pfaden, Groß-/Kleinschreibung, Trenner und Umlaute
- kombinierte und gespeicherte Profile
- deterministische Dateizahlen, Byte-Summen und größte Dateien
- Parsing dynamischer `mmls`-Offsets
- Parsing von `fls`-Bodyfile-Datensätzen
- schneller Read-only-Inventarpfad
- Scanner-Protokollierung und Validierung
- Fallakte, parallele Sichtungsnummern, Entscheidungen, Manifest und Wiederherstellungsablage
- Geräteerkennung, Software-Auswurf und Reaktivierung
- signierte Offline-Pakete, Manipulations-/Versions-/Abhängigkeitsablehnung und gestreamte Uploads
- iPhone-App-only-Lauf ohne Datei-Mount und mit getrennten Phasenzeiten
- Android-USB-Vorerkennung ohne ADB, fehlendes `adb`, Autorisierungszustände, mehrere sichtbare Profile und gemeinsamer Erkennungsregelstand
- skalierbare Regellisten, Migration alter Regeln, Banking-Neutralität, iOS-/Android-/Alias-Matching, Legacy-Regeln, unbekannte Krypto-Kandidaten
- Alpha-62-Plattformstatus-Migration: vorhandene verifizierte IDs, fehlende IDs als `unverified`, explizites `not_applicable`, eigene Regeln, Tombstones und Snapshot-Kompatibilität
- Geräte-Backup-Signaturen, falsche/incomplete Backup-Strukturen, mehrere Backups auf einem Datenträger

### Browser-Regressionsprüfungen

Zusätzlich prüft `tests/test_web_ui.cjs` die echte Oberfläche in Chromium mit ausschließlich synthetischen API-Antworten. Es wird weder ein Pi kontaktiert noch ein Scan gestartet oder eine echte Fallakte verändert. Voraussetzung ist Node.js mit installiertem `playwright` und einem Chromium-Browser:

```bash
node --test tests/test_web_ui.cjs
```

Bei vorhandenem Google Chrome kann `TRIAGE_BROWSER_CHANNEL=chrome` gesetzt werden. Ist Playwright außerhalb des Projekts installiert, muss Node es über `NODE_PATH` finden. Diese Werkzeuge gehören nur zur Entwicklung, nicht zur Pi-Installation.

Geprüft werden Medien- und Filterwechsel mit absichtlich verspäteten Antworten, Rückkehr zum Dashboard, A–B–A-Wechsel, Archiv-Unterordner und Pagination in beiden Ansichten, Wiederholung fehlgeschlagener Archivabrufe sowie numerische Sichtungssortierung. Dazu kommen Archivstatusfilter, exakte Dateiauswahl, Fallende im Updatefenster, der signierte Offline-Upload, die flackerfreie Wiederherstellung des Updatefensters und die Strom-/Systemansicht einschließlich Sperr- und Bestätigungszustand. Die Entscheidungszentrale wird mit drei gleichzeitig entfernten synthetischen Medien, verhindertem Dialogstapeln, eindeutiger Zuordnung und Rückkehr aus der Sichtung geprüft. Eine reine Navigation darf keine schreibenden API-Aufrufe auslösen. Alpha 66 prüft außerdem den nativen Monospace-Font-Stack mit `ui-monospace`, das Entfernen von `Courier New`, das Fehlen externer Font-URLs oder `@import`, die reduzierte Scanline-Opacity und die Sichtbarkeit zentraler Oberflächenbereiche nach den Typografieänderungen.

Für die Erkennungsregeln werden zusätzlich geprüft: geschlossener/ geöffneter/ wieder geschlossener Einstellungsdialog ohne Layoutfläche, Regel-Suche, beschriftete Filter und Sortierung, alle drei Plattform-ID-Status, Android-only- und ID-lose Regeln, kein allgemeines Häkchen hinter App-Namen, Regel-Auswahl, Editor, Speichern, Abbrechen, Tooltips per Hover/Fokus/Klick, JSON-Import/Export, große Regellisten und Backup-Ergebnisdarstellung.

Für den aktuellen Alpha-67-Arbeitsstand sind 178 Python-Tests und 69 isolierte Browserprüfungen mit Chromium erfolgreich. Installer und Updater führen Python-Tests aus, nicht Browser- oder Hardwareprüfungen. Diese automatisierten Ergebnisse ersetzen den Alpha-67-Pi-/Safari-/Windows-Nachtest nicht.

## Telefon-Schnellscan

### iPhone

- Entsperrt/vertrauenswürdig: Geräteinformationen und Benutzer-App-Liste vollständig, Krypto-Treffer reproduzierbar, `files.csv` leer.
- Gesperrt, Vertrauen verweigert oder App-Limit erreicht: verständlicher Teilfehler; niemals pauschal „keine Krypto-Apps“.
- Mit demselben Gerät den alten beobachteten Lauf (ca. 16,35 Sekunden mit Dateizusatz) und Alpha 61 vergleichen. Geräte-, App-Inventar- und Klassifikationszeit getrennt aus `summary.json.timings` dokumentieren.

### Android

- Gerät mit deaktiviertem USB-Debugging: Herstellererkennung und passende Anleitung ohne Sichtungsreservierung.
- Debugging aktiv, Autorisierung offen: Status wartet; kein Scan.
- Autorisierung bestätigt: Auto-Scan startet, Geräte-/Builddaten und Drittanbieterpakete werden erfasst.
- Hauptprofil, Arbeitsprofil und weitere sichtbare Benutzer: App-Zahl und Status je Profil nachvollziehbar.
- Secure Folder/Knox nicht als Profil sichtbar: Status unbekannt/nicht prüfbar; kein Negativbefund.
- Autorisierung entzogen, Gerät gesperrt, Kabelabbruch und mehrere Android-Geräte: eindeutige Kacheln, nachvollziehbarer Fehler, Weboberfläche bleibt bedienbar.
- Fehlendes Debian-Paket `adb`: konkrete Installationsmeldung statt endloser Freigabeanleitung.
- Treffer und Nichttreffer mit verifizierten Testpaketen prüfen; Package-ID, Profil, Regel-ID, Kategorie und Relevanz müssen im Snapshot nachvollziehbar sein.

## Vollständiger Probeeinsatz

Dies ist der nächste gemeinsame Meilenstein, zunächst ohne CD-Laufwerk. Nur ausdrücklich vorgesehene Testmedien und synthetische Fälle verwenden; keine echten Falldaten in Git ablegen.

### Vorbereitung

- Programmversion, Betriebssystem, Pi-Modell, Systemmedium, Netzteil, Kabel und Netzwerkweg notieren.
- Drei Teststicks als A, B und C physisch kennzeichnen. Modell, Kapazität, Seriennummer, Partitionen und erwartete Inhalte unabhängig festhalten; bei fehlender/gleicher Seriennummer nicht allein darauf vertrauen.
- Den Sollbestand aus der passenden Fixture-/Manifestdatei verwenden. Historische Zahlen verschiedener Testdatensätze nicht vermischen. Nachträglich hinzugefügte Dateien oder Finder-Metadaten verändern die Erwartung und müssen erklärt werden.
- Bestehende Testakten konsistent sichern. Für den Durchlauf einen eindeutig bezeichneten neuen Testfall verwenden, ohne alte Fälle zu löschen.
- Die priorisierte serverseitige Löschsperre aus der Roadmap vorab ergänzen und mit isolierten Tests nachweisen; UI-Sperren allein nicht als Abnahme behandeln.
- Vor Beginn kein aktiver Fall und keine laufenden Scans; Auto-Scan zunächst aus. Kontrollierter Neustart nur nach Beenden aller laufenden Arbeiten.

### Ablauf und Erfolgskriterien

| Schritt | Durchführung | Bestanden, wenn … |
|---|---|---|
| 1 · Freigabe | Nach Dienst-/Pi-Neustart Oberfläche öffnen, Testfall vorbereiten, Kürzel und Profile auswählen und ausdrücklich starten. | Vor Freigabe kein Scan beginnt; Fallnummer und Kürzel eindeutig angezeigt werden. |
| 2 · Erfassung | A anschließen, dann B und C; Auto-Scan einschalten. Auf einem weiteren Durchlauf alle drei bereits angeschlossen starten. | Geeignete Medien erfasst werden, Scans unabhängig fortschreiten und das Systemmedium nicht angeboten wird. |
| 3 · Zuordnung | Gerätedaten und Verzeichnisse jeder Sichtung mit A/B/C vergleichen. | Keine Sichtung das Verzeichnis eines anderen Mediums zeigt; Reihenfolge innerhalb der Online-/Offline-Gruppen numerisch ist. |
| 4 · Bestand | Datei-/Ordnerzahlen, Bytes, Kategorien, Stichworttreffer und größte Dateien gegen den Sollbestand prüfen. | Jede Abweichung erklärt ist; Archiv-Inneneinträge nicht die äußere Dateizahl erhöhen. |
| 5 · Archive | Offene, dateiverschlüsselte, namensverschlüsselte, beschädigte und verschachtelte Beispiele auswählen; Statusfilter und Unterordner öffnen. | Filter zu den gezählten äußeren Archiven passen; lesbare Namen keine entschlüsselten Inhalte suggerieren; unbekannt nicht als unverschlüsselt gilt; verschachtelte Archive nicht weiter extrahiert werden. |
| 6 · Navigation | Schnell A–B–A wechseln, Suche, Dateityp, Archivstatus und „Filter aufheben“ verwenden; größte Datei anklicken. | Auch verspätete Antworten keine fremden Ergebnisse anzeigen und keine Entscheidung oder sonstige Falländerung auslösen. |
| 7 · Entscheidung | A „Sichern“ mit Beweismittelnummer, B „Nicht sichern“ mit sachlicher Begründung, C zunächst offen lassen. Pflichtfelder probeweise leer lassen. | Ungültige Eingaben keinen Entscheidungseintrag erzeugen; gültige Einträge genau zum gewählten Medium gehören; C sichtbar offen bleibt. |
| 8 · Offline | Nach Scanabschluss B auswerfen/abziehen; C mit offener Entscheidung ebenfalls nach Scanabschluss abziehen. Erneut anschließen. | Online-/Offline-Status nachvollziehbar wechselt; offene Entscheidungen und historische Metadaten erhalten bleiben und Medien korrekt zugeordnet werden. |
| 9 · Unterlagen | PDF und Fall-ZIP exportieren, Medienregister und Audit vergleichen. | Fall, Kürzel, Geräte-/Sichtungsnummern, Entscheidungen und Begründungen konsistent sind; Bericht lesbar bleibt; Manifest zum Export passt. ZIP allein gilt nicht als vollständiges Systembackup. |
| 10 · Wiederanlauf | Aktiven Fall im Browser neu laden; danach ausdrücklich beenden, erneut öffnen und schließlich nach beendetem Fall den Dienst/Pi neu starten. | Neuladen den aktuell serverseitigen Fall übernimmt; ausdrückliches Ende und Neustart die Scanfreigabe entfernen; gespeicherte Unterlagen erhalten bleiben. |

Browser-Neuladen ohne erneute Fallfreigabe und das fehlende Fallende-Audit sind bekannte Istzustände, nicht stillschweigend erfüllte Sicherheitsziele. Die Entscheidung über eine zusätzliche Wiederfreigabe und die Protokollergänzung stehen in der Roadmap.

### Prüfprotokoll

Pro Durchlauf mindestens festhalten:

```text
Datum / Prüfer:
Version / Commit / Betriebssystem:
Pi / Systemmedium / Stromversorgung / Netzwerk:
Testfall und Medien A, B, C (Modell, Seriennummer, Kapazität, Partitionen):
Sollbestand / Fixture-Version:
Schritt / Erwartung / Beobachtung / Dauer / bestanden oder abweichend:
Abweichung und reproduzierbare Schritte:
Ablage von Bericht, Export, Logs und Screenshots:
Gesamturteil / offene Punkte / nächster Test:
```

Keinen Schritt wegen „sieht ungefähr richtig aus“ als bestanden markieren. Ungeklärte Zuordnungs-, Zähl- oder Protokollfehler verhindern die Abnahme des Probeeinsatzes. Ergebnisse in einem neuen datierten Nachweis festhalten, nicht in den historischen VM-Nachweis von August eintragen.

## Synthetischer Testdatenträger

Für realistische offene, verschlüsselte, verschachtelte und beschädigte Archive sowie ein brennbares CD-R-Abbild siehe [test-media.md](test-media.md). Der folgende große deterministische Datensatz bleibt der Laufzeit- und Zählwertvergleich.

1. Autorisierten SanDisk anhand von Transport, Modell, Seriennummer und Kapazität identifizieren.
2. Sicherstellen, dass kein Systemdatenträger das Ziel sein kann.
3. Nur nach erneuter `lsblk`-Kontrolle partitionieren oder formatieren.
4. Leeres Testvolume beschreibbar mounten und Fixture erzeugen:

   ```bash
   python scripts/create_test_media.py --target /pfad/zum/TRIAGE_TEST-volume
   ```

5. Alle Partitionen unmounten.
6. Read-only-Zustand setzen und prüfen.
7. Standardscan `fast` ausführen und sicherstellen, dass der temporäre Mount read-only war und nach Abschluss nicht mehr existiert.
8. `--mode tsk` separat als mountfreien Vergleichspfad prüfen.
9. Dateizahl, Ordnerzahl, Endungen, Kategorien, Bytes, Stichwortzahlen und größte Dateien mit `tests/fixtures/expected.json` vergleichen.
10. Laufzeit, Werkzeugversionen, Hardwareidentität und rohe Ausgaben dokumentieren.

Jede Abweichung ist bis zu einer nachvollziehbaren Erklärung ein fehlgeschlagener Test. Dateisystembedingte Metadaten dürfen nicht still ignoriert werden.

## Manuelle UI-Prüfung

- Dienst-/Pi-Neustart ohne aktiven Fall; Scan gesperrt; Browser-Neuladen übernimmt dagegen die bestehende Serversitzung
- gemeinsame Anzeige aller fehlenden Startvoraussetzungen
- expliziter Fallwechsel mit neuem Bearbeiter
- mehrere Suchprofile gleichzeitig
- parallele Medienkacheln und unabhängige Statuswerte
- Sichtungsreihenfolge 1, 2, 3, 8, 10 statt lexikographischer oder Scanabschluss-Reihenfolge
- keine fremden oder unsichtbaren Verzeichnisse nach schnellem Medien-/Filterwechsel
- Archiv-Unterordner und weitere Einträge in Explorer und gefilterter Liste
- äußere Dateien und zusätzliche Archiv-Fundstellen klar getrennt beschriftet
- Größen der größten Dateien bei langen Pfaden ohne horizontales Scrollen sichtbar; Klick wählt exakt den Metadateneintrag, auch bei Sonderzeichen
- Archivstatus kompakt und anklickbar; Zahlen und Balken der Dateitypliste bleiben ausgerichtet
- Statusfilter liefern genau die gezählten äußeren Archive, einschließlich Pagination; verschachtelte Archivnamen nicht mitgezählt
- Explorer und Suchliste kennzeichnen Verschlüsselung/ungeklärten Status dezent mit Text; Nullzähler deaktiviert, Filterreset und Medienwechsel korrekt
- Online-/Offline-Zustand und offene Entscheidung nach Abziehen
- Entscheidungspflichten: Beweismittelnummer bei „Sichern“, Begründung bei „Nicht sichern“
- kein versehentliches Protokollieren durch reine Navigation
- Fallarchiv: sichtbare Aktionen „Öffnen“ und „Löschen“
- Dashboard sperrt Löschen aktiver Fälle; zusätzlich noch zu implementierende serverseitige Fall-/Scanprüfung isoliert und mit gleichzeitigen Anfragen testen
- fehlende oder abweichende Fallbestätigung verändert keine Fallakte
- korrektes Entfernen lässt Archiv geöffnet und verschiebt Unterlagen nach `.trash`
- PDF-Bericht, ZIP-Export und Manifestprüfung
- Tastaturfokus und kleiner Bildschirm

## Noch erforderliche Hardwaretests

- zwei oder mehr reale USB-Datenträger parallel mit dokumentiertem Sollvergleich; drei angeschlossene Sticks wurden bereits praktisch erprobt
- endgültigen Strom-/USB-Aufbau unter Last prüfen; eigener Hub nach Bedarf, separat versorgtes Laufwerk braucht für sich allein keinen zusätzlich versorgten Hub
- Abziehen während Scan und während offener Entscheidung
- defektes, nicht lesbares und unbekanntes Dateisystem
- CD und DVD im vorgesehenen separat versorgten Laufwerk: zunächst leer mit Auto-Scan aus, dann intaktes Testmedium manuell, anschließend Auto-Scan und Fehlerfälle
- künstlich blockierter Scanner-Worker: Zeitlimit, Gerätequarantäne und weiterhin reagierende Weboberfläche
- physisch blockierender Datenträger: Auswirkungen auf weitere Ports, Systemmedium und Oberfläche messen; Kernel-/Busstillstand ist durch Softwarezeitlimits nicht ausgeschlossen
- Raspberry Pi: Router-LAN/Hotspot wiederholbar prüfen; direkte Ethernet-Verbindung ohne Router erst konfigurieren und abnehmen; kleines Display nur bei tatsächlichem Einsatz
- Stromverlust und kontrollierter Wiederanlauf
- Hardware-Schreibblocker

## Releasekriterium

`v0.2.0-alpha.60` dokumentiert einen funktionsfähigen Prototyp mit iPhone-Praxisbeobachtungen vor dem App-only-Umbau und simuliertem Android-Collector, aber noch ohne vollständige praktische Abnahme der neuen Telefonfunktion. Eine spätere Einsatzversion benötigt bestandene iPhone-/Android- und Hardwaretests, ein Sicherheitsreview, verschlüsselten Fallspeicher, getestete Wiederherstellung, festgelegte Betriebsprozesse und dokumentierte Freigabe.

Für den ZIP-/ISO-/7Z-/RAR-Schnellindex müssen zusätzlich intakte, beschädigte, verschlüsselte, mehrteilige und sehr große Testcontainer geprüft werden. Nachzuweisen sind: keine Nutzdatei-Extraktion oder Inhaltsanalyse, keine Passwortversuche, sichtbare Limitkennzeichnung und unveränderte äußere Datei-/Ordnerzahlen. Komprimierte Archivverzeichnisse können intern dekodiert werden. Das Zusatzzeitbudget ist zu messen; es ist keine harte Garantie gegen blockierte Bibliotheks-/Kernelzugriffe. Überschreitungen und nicht beendete Prozesse müssen als Abweichung protokolliert werden.

## English summary

The project has Python tests, isolated browser regressions and synthetic USB/CD fixtures. A Pi with hotspot/LAN and several USB sticks has already been used, but a documented end-to-end trial is still required. The checklist above covers media identity, counts, archives, navigation, decisions, exports and restart. Further failure, recovery, access/storage protection, optical-media and write-protection validation is pending. A separately powered optical drive can be tested without requiring a powered hub solely for that drive.
