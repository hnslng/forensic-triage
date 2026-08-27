# Sicherheitsrichtlinie / Security policy

## Status

TRIAGE//BOX ist ein Alpha-Prototyp und derzeit für keine Version zum ungeprüften Einsatz mit echten Beweismitteln freigegeben. Insbesondere sind Zugriffsschutz, verschlüsselte Speicherung, Hardware-Schreibblocker, Wiederherstellung und Raspberry-Pi-Hardware noch nicht formal validiert.

Der Webdienst bindet standardmäßig nur an `127.0.0.1`. Er besitzt derzeit keine Benutzeranmeldung. Eine Freigabe über `0.0.0.0`, ein fremdes WLAN oder das Internet ist nicht vorgesehen. Netzwerkzugriff darf nur über eine kontrollierte lokale Verbindung erfolgen.

## Sicherheitsprobleme melden

- Keine Schwachstellendetails, echten Falldaten, Zugangsdaten oder Gerätekennungen in öffentliche Issues schreiben.
- Wenn GitHub für dieses Repository die private Schwachstellenmeldung anbietet, bitte diese verwenden.
- Nicht sicherheitskritische Fehler können als normales GitHub-Issue ohne sensible Daten beschrieben werden.

## Geheimnisse und Falldaten

Folgendes darf nie in das Repository gelangen:

- echte Fallakten, Scanergebnisse oder Exporte
- Passwörter, Tokens oder private Schlüssel
- lokale `.env`- beziehungsweise `triage.env`-Dateien
- persönliche SSH-Starter mit realen Hosts und Schlüsselpfaden

Das Installationsskript erzeugt ein zufälliges lokales Löschpasswort in `/etc/forensic-triage/triage.env`. Fehlt dieser Wert, sperrt der Webdienst die Fallentfernung. Das Passwort ist kein Ersatz für eine echte Benutzer- und Rollenverwaltung.

## English

TRIAGE//BOX is an alpha prototype with no version approved for unvalidated operational evidence handling. Do not publish vulnerability details, case data, credentials, or device identifiers in public issues. Use GitHub private vulnerability reporting when available. The service is unauthenticated and must remain on a controlled local interface. The installer creates a random local deletion password; this is not a user authentication system.
