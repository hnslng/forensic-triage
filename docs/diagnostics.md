# Diagnosekonsole (Alpha 71)

Die Diagnosekonsole ist ein lokales Werkzeug für den Testbetrieb. Sie zeigt in der Weboberfläche, was TRIAGE//BOX intern erkennt und tut — USB-Geräte, Android-/iPhone-Kandidaten, ADB- und Trust-Zustände, Scans, Updates und Fehler — damit spätere Hardwaretests (Pi, USB-Sticks, Android, iPhone) nachvollziehbar bleiben.

Sie ist **Diagnose-Infrastruktur, keine neue Logging-Plattform** und ändert keine Erkennungs-, Scanner- oder Forensiklogik.

## Aufbau

- **Ringbuffer im RAM**: thread-sicher, standardmäßig die letzten **500 Einträge** (älteste werden verworfen). Über die Umgebungsvariable `FORENSIC_TRIAGE_DIAG_BUFFER_MAX` konfigurierbar, Obergrenze 2000. Kein Schreiben auf Datenträger, keine Persistenz: Nach einem Service-Neustart ist die Konsole leer (Zustand „NOCH KEINE DIAGNOSEEREIGNISSE").
- **Handler statt Zweitsystem**: ein eigener `logging.Handler` übernimmt nur bewusst freigegebene Records aus dem `forensic-triage`-Namespace, Records mit expliziter Diagnosekategorie oder bekannten Modulen unter `forensic_triage/`. Der Root-Logger bleibt auf seinem vorhandenen Level; INFO-Daten fremder Bibliotheken werden nicht aufgenommen. Ein zusätzlicher WARNING-StreamHandler entsteht nur, wenn der Prozess noch keinen normalen Handler besitzt. Bestehende Speicherorte (`scan.log`, journal) bleiben unangetastet.
- **Struktur je Eintrag**: fortlaufende `seq` (monoton steigend, Cursor für Polling), ISO- Zeitstempel mit Millisekunden, `LEVEL`, `CATEGORY`, Meldung und optional kleine Details (maximal 12 Felder, je 200 Zeichen).

## Kategorien

`SYSTEM · USB · ANDROID · IPHONE · SCAN · UPDATE · WEB · CASE · ERROR`

## NORMAL- und DEBUG-Modus

- **NORMAL** (Vorgabe): wichtige Zustandsänderungen — Geräte verbunden/getrennt, Einbinden/Schreibschutz, Verbindungs-/Trust-Zustände, Scanstart/-ende mit Dauer, Update-Statuswechsel, Fehler (WARNING/ERROR).
- **DEBUG**: zusätzlich technische Details aus dem kontrollierten `forensic-triage`-Logger-Namespace — sysfs-Pfad, `idVendor`, `idProduct`, Hersteller, Modell, Geräteklasse, Interfaceklasse/-subklasse/-protokoll, Kandidaten- oder Ablehnungsgrund, Confidence, Serien-**Vorhanden-Flag**, ADB-Binary, ADB-Zustand, resultierender `connection_state` und Identitätsquelle. Technisch erforderliche Gerätekennungen wie die ADB-ID dürfen hier erscheinen. Der Root-Logger wird nicht global erweitert; Debug-Aufzeichnung wird serverseitig per Umschalter aktiviert.

## Logflut-Vermeidung

Zustandsänderungen werden nur bei tatsächlicher Änderung geloggt. Identische Poll-Ergebnisse erzeugen keine Einträge. Wiederkehrende Fehler erscheinen einmal und dann frühestens 60 Sekunden nach dem zuletzt **ausgegebenen** Ereignis; unterdrückte Poll-Treffer verlängern das Fenster nicht. Scan-Exceptions bleiben vollständig im Journal, während die Konsole genau ein kompaktes Fehlerereignis erhält.

## Bedienung (Tab DIAGNOSE in den Einstellungen)

- **NORMAL/DEBUG** – Modusumschalter (serverseitig wirksam, Client filtert zusätzlich die Anzeige).
- **Kategorie-Filter** – ALLE / USB / ANDROID / IPHONE / SCAN / UPDATE / SYSTEM.
- **PAUSE/FORTSETZEN** – hält nur die Anzeige an; das Backend läuft weiter. Nach dem Fortsetzen werden die noch im Ringbuffer vorhandenen Einträge nachgeladen; bei zu großer Lücke springt die Anzeige auf den neuesten verfügbaren Stand.
- **LEEREN** – leert ausschließlich die lokale Ansicht und setzt den Cursor; der Server-Ring läuft weiter (kein mutierender Clear-Endpoint).
- **KOPIEREN** – kopiert die sichtbaren (gefilterten) Zeilen als Text `JJJJ-MM-TT HH:MM:SS.mmm LEVEL KATEGORIE MELDUNG key=wert …` in die Zwischenablage; bei.blockierter Zwischenablage erscheint ein klarer Fehlerstatus.
- **Auto-Scroll** folgt neuen Zeilen nur, wenn die Ansicht am unteren Rand steht; sonst erscheint `↓ ZUM ENDE`. Die Konsole hält maximal 500 Zeilen im DOM.

Polling fragt ca. 1× pro Sekunde **nur ab** der zuletzt gesehenen `seq` (`GET /api/logs/recent?since=…&limit=200`) und läuft nur, wenn die Konsole sichtbar ist; bei verborgenem Tab/Fenster bzw. im Hintergrund pausiert es.

## API

- `GET /api/logs/recent` — read-only. Optional: `since` (Sequenz-Cursor, exklusiv), `limit` (1–500, Standard 200), `level` (`DEBUG/…/ERROR`, Minimum), `category` (feste Kategorien). Ungültige Werte → HTTP 400. Antwort: `{ "entries": [...], "mode": "normal", "count": n, "latest": <letzte seq> }`. Ohne Cursor wird der neueste Stand geliefert, mit Cursor die ältesten neuen Einträge zuerst (stabiler Poll-Zug).
- `POST /api/logs/mode` mit `{ "mode": "normal" | "debug" }` — einziger schreibender Endpoint; nur lokale Weboberfläche.

Diagnoseendpunkte geben ausschließlich bereits erfasste, strukturierte Einträge zurück — keine Pfadparameter, kein Shell-Zugriff, keine Systemdateien.

## Datenschutz

- Keine Passwörter, Tokens, Sitzungsdaten oder privaten Schlüssel; keine Dateiinhalte.
- NORMAL zeigt keine Telefonseriennummern oder UDIDs im Klartext. DEBUG darf technische Kennungen anzeigen, wenn sie zur lokalen Fehleranalyse erforderlich sind. Passwörter, Tokens, Sitzungsdaten, Dateiinhalte und andere Secrets bleiben in beiden Modi ausgeschlossen.
- RAM-only: die Konsole wird nicht auf Datenträger geschrieben, wodurch keine neue Aufbewahrungs-/Löschthematik entsteht.

## Manueller Hardware-Test (Pi)

1. DIAGNOSE öffnen, Modus DEBUG aktivieren.
2. USB-Stick anstecken → USB-Ereignisse beachten (verbunden, Details), danach abziehen → „getrennt".
3. Samsung ohne USB-Debugging anstecken und normale Datenfreigabe bestätigen: Telefonkachel, `debugging_required`, Anleitung sowie erkannte USB-Merkmale/Kandidatenbegründung prüfen.
4. USB-Debugging aktivieren, Autorisierung zunächst offen lassen: `authorization_required` prüfen.
5. Dialog bestätigen: `authorized` und Scanbereitschaft prüfen; anschließend abziehen und genau einen Disconnect prüfen.

Diese Alpha-71-Funktion ist automatisiert/mock-basiert geprüft, aber noch nicht mit einem echten Telefon am Raspberry Pi abgenommen.
