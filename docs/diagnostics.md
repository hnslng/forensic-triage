# Diagnosekonsole (Alpha 70)

Die Diagnosekonsole ist ein lokales Werkzeug für den Testbetrieb. Sie zeigt in der Weboberfläche, was TRIAGE//BOX intern erkennt und tut — USB-Geräte, Android-/iPhone-Kandidaten, ADB- und Trust-Zustände, Scans, Updates und Fehler — damit spätere Hardwaretests (Pi, USB-Sticks, Android, iPhone) nachvollziehbar bleiben.

Sie ist **Diagnose-Infrastruktur, keine neue Logging-Plattform** und ändert keine Erkennungs-, Scanner- oder Forensiklogik.

## Aufbau

- **Ringbuffer im RAM**: thread-sicher, standardmäßig die letzten **500 Einträge** (älteste werden verworfen). Über die Umgebungsvariable `FORENSIC_TRIAGE_DIAG_BUFFER_MAX` konfigurierbar, Obergrenze 2000. Kein Schreiben auf Datenträger, keine Persistenz: Nach einem Service-Neustart ist die Konsole leer (Zustand „NOCH KEINE DIAGNOSEEREIGNISSE").
- **Handler statt Zweitsystem**: ein eigener `logging.Handler` übernimmt die bestehenden Python-LogRecords. Vorhandene `logging.info/warning/error`-Aufrufe funktionieren unverändert. HTTP-Zugriffszeilen (`web GET …`) und ungefiltertes journalctl fließen bewusst **nicht** in die Konsole; bestehende Speicherorte (`scan.log`, journal) bleiben unangetastet.
- **Struktur je Eintrag**: fortlaufende `seq` (monoton steigend, Cursor für Polling), ISO- Zeitstempel mit Millisekunden, `LEVEL`, `CATEGORY`, Meldung und optional kleine Details (maximal 12 Felder, je 200 Zeichen).

## Kategorien

`SYSTEM · USB · ANDROID · IPHONE · SCAN · UPDATE · WEB · CASE · ERROR`

## NORMAL- und DEBUG-Modus

- **NORMAL** (Vorgabe): wichtige Zustandsänderungen — Geräte verbunden/getrennt, Einbinden/Schreibschutz, Verbindungs-/Trust-Zustände, Scanstart/-ende mit Dauer, Update-Statuswechsel, Fehler (WARNING/ERROR).
- **DEBUG**: zusätzlich technische Details aus dem kontrollierten `forensic-triage`-Logger-Namespace — sysfs-Kandidaten mit `idVendor`, `idProduct`, Hersteller, Modell und Serien-**Vorhanden-Flag**, ADB-Binary vorhanden ja/nein, ADB-Zustand pro Gerät (`adb devices`), resultierender `connection_state`. Der Root-Logger wird nicht global auf DEBUG gesetzt; Debug-Aufzeichnung wird serverseitig per Umschalter aktiviert (`POST /api/logs/mode`).

## Logflut-Vermeidung

Zustandsänderungen (Gerät verbunden/getrennt, ADB-/Trust-Statusübergänge, Einhängen, Schreibschutz, Strom- und Update-Zustände) werden nur bei tatsächlicher Änderung geloggt. Identische Poll-Ergebnisse erzeugen keine Einträge. Wiederkehrende Fehler (z. B. blockierte Erkennung) erscheinen erneut frühestens nach 60 Sekunden (Dedup/Cooldown).

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
- Seriennummern von Telefonen erscheinen nicht als Klartext, sondern nur als Serienstatus (Vorhanden ja/nein); technische Kennungen (`idVendor`/`idProduct`) nur im DEBUG-Modus.
- RAM-only: die Konsole wird nicht auf Datenträger geschrieben, wodurch keine neue Aufbewahrungs-/Löschthematik entsteht.

## Manueller Hardware-Test (Pi)

1. DIAGNOSE öffnen, Modus DEBUG aktivieren.
2. USB-Stick anstecken → USB-Ereignisse beachten (verbunden, Details), danach abziehen → „getrennt".
3. Android ohne USB-Debugging anstecken → ablesen: Wird ein USB-Gerät erkannt? `idVendor`/`idProduct`/Hersteller/Produkt erscheinen? Seriennform vorhanden? Kandidat erkannt? ADB vorhanden? Welcher `connection_state` entsteht?
4. USB-Debugging aktivieren, Autorisierung am Telefon bestätigen → Zustandsübergänge verdeutlichen (`debugging_required → unauthorized → authorized`).

Wichtig: In Alpha 70 wird die frühe Android-Erkennung **nicht** repariert — der Test zeigt nur, was aktuell passiert, und liefert die Grundlage für Alpha 71.
