# Forensische Sicherheitsgrenzen / Forensic safety

## Vor jeder Analyse

Die bedienende Person muss Berechtigung und physische Identität des Datenträgers anhand von Transport, Kapazität, Modell und Seriennummer feststellen. Gerätenamen wie `/dev/sdb` sind flüchtig und dürfen niemals ungeprüft angenommen werden.

## Implementierte Schutzfolge

1. Übergebenen `/dev`-Pfad auflösen.
2. Ganzes Blockgerät mit USB-Transport verlangen.
3. Den expliziten Systemdatenträger-Sentinel `/dev/sda` ablehnen.
4. Mountpoints auf Gerät und Partitionen rekursiv ablehnen.
5. Gesamtes Blockgerät mit `blockdev --setro` schreibschützen.
6. Read-only-Zustand mit `blockdev --getro == 1` verifizieren.
7. Partitionen und Dateisysteme mit `mmls` und `fsstat` erfassen.
8. Im schnellen Modus nur mit `ro,nosuid,nodev,noexec` mounten, `ro` verifizieren, Metadaten lesen und im garantierten Cleanup wieder unmounten.
9. Im TSK-Modus stattdessen `fls -u` ohne Mount verwenden.

## Bedeutung des Software-Schreibschutzes

Linux weist darauf hin, dass ein nur mit `ro` gemountetes Dateisystem je nach Implementierung dennoch Sonderverhalten zeigen kann. Deshalb setzt TRIAGE//BOX zusätzlich das gesamte Blockgerät schreibgeschützt und überprüft diesen Zustand.

Trotzdem ist der aktuelle Schutz nur „defense in depth“. Für echte Beweismittel sind ein validierter Hardware-Schreibblocker, dokumentierte Handhabung, synchronisierte Zeit, organisatorische Chain of Custody und eine formale Werkzeugvalidierung erforderlich.

## Was der Scanner nicht tut

- keine Dateiinhalte öffnen oder darstellen
- keine Makros, Programme oder Skripte vom Medium ausführen
- kein Imaging, Recovery oder Carving
- keine Passwörter brechen oder Verschlüsselung umgehen
- keine automatische Relevanz- oder Sicherstellungsentscheidung treffen
- keine CD/DVD scannen, solange der reale Laufwerkspfad nicht validiert ist

## Metadaten und Fehlinterpretationen

Dateiendungen können falsch oder absichtlich irreführend sein. Version 0.2.0-alpha.13 prüft noch keine Magic Bytes. Kategorien sind daher Hinweise aus Dateinamen, keine bestätigten Dateitypen. Stichworttreffer stammen nur aus Namen und Pfaden und beweisen keinen Dateiinhalt.

## Schutz der Fallunterlagen

Keine Zugangsdaten, privaten Schlüssel, echten Falldaten oder Ergebnisverzeichnisse gehören in Git. `casefiles/`, `results/`, Exporte und interne Papierkörbe müssen lokal geschützt werden. Die fallbezogene Löschbestätigung ist nur eine Fehlbedienungssperre und keine Benutzeranmeldung.

## English summary

The scanner validates a whole unmounted USB disk, sets and verifies the block device as read-only, and then uses either a defensively read-only mount or a mount-free TSK walk. These software controls do not replace a validated hardware write blocker. File extensions and path keywords are indicators only; version 0.2.0-alpha.13 does not inspect signatures or contents.
