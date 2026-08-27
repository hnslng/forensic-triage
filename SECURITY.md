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

Die Fallentfernung besitzt kein Passwort und ist keine Benutzer- oder Rollenverwaltung. Gegen versehentliche Bedienung verlangt der Dialog eine fallbezogene Doppelbestätigung; entfernte Fallakten bleiben im internen Papierkorb wiederherstellbar. Der Webdienst muss deshalb auf einer kontrollierten lokalen Schnittstelle bleiben.

## English

TRIAGE//BOX is an alpha prototype with no version approved for unvalidated operational evidence handling. Do not publish vulnerability details, case data, credentials, or device identifiers in public issues. Use GitHub private vulnerability reporting when available. The service is unauthenticated and must remain on a controlled local interface. Case removal uses a case-specific double confirmation and recoverable trash, not user authentication.
