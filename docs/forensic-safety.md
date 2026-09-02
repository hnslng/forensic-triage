# Forensische Sicherheitsgrenzen / Forensic safety

## Vor jeder Analyse

Die bedienende Person muss Berechtigung und physische Identität des Datenträgers anhand von Transport, Kapazität, Modell und Seriennummer feststellen. Gerätenamen wie `/dev/sdb` sind flüchtig und dürfen niemals ungeprüft angenommen werden.

## Implementierte Schutzfolge

1. Übergebenen `/dev`-Pfad auflösen.
2. Ganzes USB-Blockgerät oder externes optisches USB-Laufwerk verlangen.
3. Den expliziten Systemdatenträger-Sentinel `/dev/sda` ablehnen.
4. Mountpoints auf Gerät und Partitionen rekursiv ablehnen.
5. Gesamtes Blockgerät mit `blockdev --setro` schreibschützen.
6. Read-only-Zustand mit `blockdev --getro == 1` verifizieren.
7. USB-Partitionen mit `mmls` und `fsstat` erfassen; das Dateisystem einer CD/DVD direkt am optischen Gerät prüfen.
8. Im schnellen Modus nur mit `ro,nosuid,nodev,noexec` mounten, `ro` verifizieren, Metadaten lesen und im garantierten Cleanup wieder unmounten.
9. ZIP-/ISO-/7Z-/RAR-Verzeichnisstrukturen nur begrenzt, ohne Extraktion und ohne Rekursion katalogisieren.
10. Im TSK-Modus stattdessen `fls -u` ohne Mount verwenden; dort ist der Containerindex nicht verfügbar.

## Bedeutung des Software-Schreibschutzes

Linux weist darauf hin, dass ein nur mit `ro` gemountetes Dateisystem je nach Implementierung dennoch Sonderverhalten zeigen kann. Deshalb setzt TRIAGE//BOX zusätzlich das gesamte Blockgerät schreibgeschützt und überprüft diesen Zustand.

Trotzdem ist der aktuelle Schutz nur „defense in depth“. Für echte Beweismittel sind ein validierter Hardware-Schreibblocker, dokumentierte Handhabung, synchronisierte Zeit, organisatorische Chain of Custody und eine formale Werkzeugvalidierung erforderlich.

## Was der Scanner nicht tut

- keine Nutzdatei-Payload öffnen, dekomprimieren oder darstellen; nur ZIP-/ISO-/7Z-/RAR-Verzeichnisstrukturen lesen
- keine Makros, Programme oder Skripte vom Medium ausführen
- kein Imaging, Recovery oder Carving
- keine Passwörter brechen oder Verschlüsselung umgehen
- keine automatische Relevanz- oder Sicherstellungsentscheidung treffen
- CD/DVD-Unterstützung bis zum bestandenen Test mit dem vorgesehenen realen Laufwerk nur als Alpha-Funktion behandeln

## Beschädigte Medien

Der Webdienst führt jede Sichtung in einem getrennten Worker-Prozess mit eigenem Linux-Mount-Namensraum aus. Einzelne Gerätebefehle und der gesamte Scan besitzen feste Zeitlimits. Nach einer Überschreitung wird das Medium protokolliert und bis zum erkannten Abziehen gesperrt; andere Medien und die Bedienoberfläche sollen weiterarbeiten.

Ein Prozess-Zeitlimit kann einen Linux-Prozess im nicht unterbrechbaren Hardware-Wartezustand nicht augenblicklich aus dem Kernel entfernen. Deshalb bleibt das physische Trennen des betroffenen Mediums beziehungsweise das Abschalten seines einzelnen Hub-Ports der letzte Rückfallweg. TRIAGE//BOX unternimmt keine langwierige Datenrettung und wiederholt fehlgeschlagene Leseversuche nicht automatisch.

Auf einem Raspberry Pi 3B+ teilen sich externe USB-Medien den USB-Pfad mit einer von USB gestarteten System-SSD. Ein fehlerhaftes oder stromhungriges Prüfmedium kann dadurch nicht nur seinen isolierten Scanworker, sondern den Systemdatenträger und damit den ganzen Pi blockieren. Für diesen Aufbau ist das System auf einer hochwertigen MicroSD und ein eigenständig versorgter USB-Hub für Prüfmedien die robustere Trennung. Persistente, begrenzte Systemprotokolle sichern die bis zum Ausfall geschriebenen Diagnosemeldungen über einen Neustart hinweg; sie können einen Hardwarestillstand nicht verhindern.

## Metadaten und Fehlinterpretationen

Dateiendungen können falsch oder absichtlich irreführend sein. Version 0.2.0-alpha.38 prüft noch keine Magic Bytes. Kategorien sind daher Hinweise aus Dateinamen, keine bestätigten Dateitypen. Regulär vorhandene versteckte Dateien werden inventarisiert; gelöschte Dateien, interne Dateisystem-Hilfseinträge und nicht lesbare Einträge werden nicht wiederhergestellt. Stichworttreffer stammen nur aus äußeren oder in ZIP-/ISO-/7Z-/RAR-Verzeichnissen gespeicherten Namen und Pfaden und beweisen keinen Dateiinhalt. Nur eindeutig erkannte Verschlüsselungsmerkmale werden als verschlüsselt gezählt; nicht unterstützte, beschädigte, unvollständige oder wegen eines Limits nicht fertig geprüfte Archive bleiben `UNGEPRÜFT`. Bei verschlüsselten Kopfbereichen werden keine Passwörter versucht.

## Schutz der Fallunterlagen

Keine Zugangsdaten, privaten Schlüssel, echten Falldaten oder Ergebnisverzeichnisse gehören in Git. `casefiles/`, `results/`, Exporte und interne Papierkörbe müssen lokal geschützt werden. Die fallbezogene Löschbestätigung ist nur eine Fehlbedienungssperre und keine Benutzeranmeldung.

## English summary

The scanner validates a whole unmounted USB disk or external USB optical drive, sets and verifies it as read-only, and then uses either a defensively read-only mount or a mount-free TSK walk. Time-limited isolated scanner processes prevent one slow medium from owning the web service. These software controls do not replace a validated hardware write blocker. File extensions and path keywords are indicators only; version 0.2.0-alpha.38 reads bounded ZIP/ISO/7Z/RAR directory metadata but does not inspect signatures or file payloads.
