# Projektstand und Nachweise

Stand: **6. September 2026**, Anwendung **v0.2.0-alpha.43**, Quellcode-Stand `f9e588e`. Diese Bestandsaufnahme ändert nur Dokumentation und vergibt keine neue Programmversion.

## Was „funktioniert“ hier bedeutet

- **Implementiert:** im aktuellen Code vorhanden.
- **Automatisch geprüft:** mit den beschriebenen synthetischen Tests geprüft; keine Aussage über jede reale Hardware.
- **Praktisch beobachtet:** im bisherigen Testbetrieb verwendet; noch keine vollständige formale Abnahme.
- **Offen:** Umsetzung oder reproduzierbarer Nachweis fehlt.

| Bereich | Aktueller Stand | Noch nachzuweisen / zu verbessern |
|---|---|---|
| Raspberry Pi 3B+ | Installiert und im Testbetrieb; Alpha 43 wurde vom Update-Endpunkt als aktuelle installierte Version gemeldet. | Reproduzierbare Neuinstallation, finaler Speicher-/Stromaufbau und Dauerbetrieb. |
| Netzwerk | Hotspot und Router-LAN verwendet; `http://triagebox.local/` erfolgreich ohne Port aufgerufen. | Direkte Ethernet-Verbindung ohne Router, Offline-Betrieb, gerätespezifisches Passwort und Firewall-Abnahme. |
| USB-Grobsichtung | Reale Testmedien, darunter drei gleichzeitig angeschlossene Sticks, bereits gesichtet. | Vollständiger Soll-/Ist-Vergleich, systematische Parallel- und Störungstests. |
| Fallworkflow | Start/Ende, Sichtungsnummern, zwei Entscheidungen, Geräte-/Dateimetadaten, PDF und ZIP implementiert. | Vollständiger Probeeinsatz einschließlich Wiederöffnung, konsistentem Bericht und Pflichtangaben. |
| Explorer und Archivfilter | Medienwechsel, verspätete Antworten, Filter, Archiv-Unterordner und Pagination automatisch geprüft. | Wiederholung mit bekannten Beständen auf dem Pi; Grenzen bei großen und unvollständigen Katalogen. |
| Archivverschlüsselung | ZIP/7Z/RAR-Merkmale, ungeklärter Status und lesbare Verzeichnisse implementiert. | Keine allgemeine PDF-/Office-/Volume-Verschlüsselungserkennung; Gründe nur soweit der gespeicherte Index sie liefert. |
| Schreibschutz und Isolation | Software-Read-only, getrennte Prozesse, Zeitlimits und begrenzte Diagnoseprotokolle vorhanden. | Physische Schreibschutzprüfung; Hardware-/Kernelstillstand wird dadurch nicht ausgeschlossen. |
| Updates | Prüfung und bewusste Installation praktisch verwendet; Fallende im Updatefenster seit Alpha 43. | Vollständige Fehler-/Stromausfallprüfung, Erhalt eigener Profile und Wiederherstellung aller veränderten Komponenten. |
| Entfernte Fälle | Ordner bleiben im Papierkorb; Entfernen automatisch geprüft. | Kein fertiger Import zurück in den aktiven Fallindex; kein geprüfter Restore-Ablauf. |
| Zugriff und Ablage | Lokaler HTTP-Zugang, konfigurierte Fallablage, keine Web-Anmeldung. | Gemeinsame Entsperrung, HTTPS und verschlüsselte Fallablage gemäß Schutzkonzept. |
| CD/DVD | Scan-/Auswurfpfad implementiert; bisher instabiler Hardwareversuch. | Test mit separat versorgtem Laufwerk. Ein solches wurde als möglicherweise vorhanden gemeldet, noch nicht geprüft. |

## Vorhandene Prüfnachweise

- **98 Python-Tests:** zuletzt im Zuge Alpha 41 erfolgreich; decken unter anderem Scannerbausteine, Fallablage, Zählung und Archivstatus ab. Alpha 42/43 änderten die Oberfläche, nicht die Scannerlogik.
- **23 isolierte Browsertests:** zuletzt für Alpha 43 erfolgreich. Sie nutzen synthetische API-Antworten und prüfen unter anderem die neuen Update-/Fallende-Abläufe.
- **26. August 2026:** dokumentierter Sollvergleich mit 960 Dateien auf exFAT; schneller Lauf 0,732 Sekunden auf der beschriebenen VM. Dies ist ein historischer Einzeltest, kein Geschwindigkeitsversprechen für den Pi oder beliebige Medien: [Nachweis](validation-2026-08-26.md).
- **Bisheriger Pi-Testbetrieb:** Installation, Hotspot/LAN, mehrere USB-Sticks, Archivbeispiele und Updates im Entwicklungsverlauf beobachtet. Die Feldtestserie mit vollständigem Prüfprotokoll steht noch aus.

Bei diesem Dokumentationsabgleich wurden keine neuen Scans, Stromunterbrechungen oder Wiederherstellungen ausgeführt. Neue Messwerte gehören mit Version, Aufbau, Testbestand und Abweichungen in einen datierten Nachweis; echte Falldaten bleiben außerhalb von Git.

## Bekannte Abweichungen vom Zielablauf

1. **Browser-Neuladen beendet den Fall nicht.** Die aktive Sitzung liegt im Arbeitsspeicher des Webdienstes und wird vom Browser wieder übernommen. Nach Dienst-/Pi-Neustart ist sie leer. Vor Standortwechsel muss der Fall ausdrücklich beendet werden.
2. **Protokollierung ist ereignisbezogen.** Fallstart, Sichtungsreservierung, Scanfehler/-ergebnis und Entscheidungen werden erfasst. Fallende erzeugt derzeit kein eigenes Fall-Audit-Ereignis. Navigation ist ebenfalls kein Audit-Ereignis.
3. **Eigene Profile sind noch nicht zuverlässig vom Programmverzeichnis getrennt.** Profiländerungen können ein Update wegen lokaler Codeänderungen sperren; eigene Dateien werden nicht automatisch in neue Release-Verzeichnisse übernommen.
4. **Rollback ist begrenzt.** Der Updater bereitet Code getrennt vor und wechselt den Laufzeitlink. Dienst-/nginx-Vorlagen werden zuvor installiert; der vorhandene Fehlerpfad deckt nicht sämtliche Änderungen und Unterbrechungen ab.
5. **Papierkorb bedeutet Dateierhalt.** Das Zurückverschieben eines Fallordners allein rekonstruiert den entfernten SQLite-Eintrag nicht.
6. **Löschsperre noch nicht vollständig serverseitig.** Das Dashboard sperrt aktive Fälle; der DELETE-Endpunkt prüft nur die Bestätigung, nicht zusätzlich aktive Sitzung oder laufende Scans. Vor dem nächsten vollständigen Probeeinsatz priorisiert absichern.
7. **Gerätequarantäne ist flüchtig.** Gesperrte Geräte sind nach Dienst-/Pi-Neustart nicht mehr in der Quarantäneliste; ein sicherer Wiederanlauf ist noch zu testen.

Diese Punkte sind Arbeitsaufträge in der [Roadmap](roadmap.md), keine bereits behobenen Funktionen. Der [Testplan](test-plan.md) definiert den nächsten Probeeinsatz.
