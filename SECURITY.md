# Sicherheitsrichtlinie / Security policy

## Status

TRIAGE//BOX ist ein Alpha-Prototyp und derzeit für keine Version zum ungeprüften Einsatz mit echten Beweismitteln freigegeben. Insbesondere sind Zugriffsschutz, verschlüsselte Speicherung, Hardware-Schreibblocker, Wiederherstellung und Raspberry-Pi-Hardware noch nicht formal validiert.

Der Webdienst bindet standardmäßig nur an `127.0.0.1`. Er besitzt derzeit keine Benutzeranmeldung. Der Installer richtet zusätzlich nginx auf Port 80 für private IPv4-Netze ein, auch ohne Pi-Modus. Damit ist die Oberfläche im privaten LAN/Hotspot ohne Web-Anmeldung erreichbar. Loopback am Python-Dienst allein ist keine Zugriffssperre für diese Oberfläche. Netzwerkzugriff darf nur über die kontrollierte lokale Verbindung erfolgen; HTTPS, gemeinsame Entsperrung und verschlüsselte Fallablage bleiben offen.

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

Die Fallentfernung besitzt kein Passwort und ist keine Benutzer- oder Rollenverwaltung. Gegen versehentliche Bedienung verlangt der Dialog eine fallbezogene Doppelbestätigung. Entfernte Fallordner bleiben im Papierkorb erhalten, aber ein Rückimport in den Fallindex fehlt noch. Das Dashboard sperrt das Löschen aktiver Fälle; die zusätzliche Fall-/Scanprüfung im DELETE-Endpunkt ist noch offen. Die Oberfläche darf deshalb nur im kontrollierten Testnetz betrieben werden; siehe [Projektstand](docs/project-status.md).

## English

TRIAGE//BOX is an alpha prototype with no version approved for unvalidated operational evidence handling. Do not publish vulnerability details, case data, credentials, or device identifiers in public issues. Use GitHub private vulnerability reporting when available. The service is unauthenticated and must remain on a controlled test network. Case removal uses case-specific double confirmation and preserves files in trash, but has no supported index re-import. Active-case deletion is blocked in the dashboard, not yet by the DELETE endpoint.
