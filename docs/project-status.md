# Projektstand und Nachweise

Stand: **10. September 2026**, Anwendung **v0.2.0-alpha.45**. Einstellungen für Stichwortprofile und Dateitypen sowie signierte Offline-Updates über den eigenen Hotspot sind implementiert. Der Alpha-45-Update- und Praxistest auf dem Pi steht noch aus. Einzelheiten: [Einstellungen](settings.md) und [Offline-Updates](offline-updates.md).

## Was „funktioniert“ hier bedeutet

- **Implementiert:** im aktuellen Code vorhanden.
- **Automatisch geprüft:** mit den beschriebenen synthetischen Tests geprüft; keine Aussage über jede reale Hardware.
- **Praktisch beobachtet:** im bisherigen Testbetrieb verwendet; noch keine vollständige formale Abnahme.
- **Offen:** Umsetzung oder reproduzierbarer Nachweis fehlt.

| Bereich | Aktueller Stand | Noch nachzuweisen / zu verbessern |
|---|---|---|
| Raspberry Pi 3B+ | Installiert und im Testbetrieb; Alpha 43 wurde zuletzt praktisch auf dem Pi verwendet. | Alpha 45 zunächst online aktualisieren und prüfen; reproduzierbare Neuinstallation, finaler Speicher-/Stromaufbau und Dauerbetrieb. |
| Netzwerk | Hotspot und Router-LAN verwendet; `http://triagebox.local/` erfolgreich ohne Port aufgerufen. | Direkte Ethernet-Verbindung ohne Router, Offline-Betrieb, gerätespezifisches Passwort und Firewall-Abnahme. |
| USB-Grobsichtung | Reale Testmedien, darunter drei gleichzeitig angeschlossene Sticks, bereits gesichtet. | Vollständiger Soll-/Ist-Vergleich, systematische Parallel- und Störungstests. |
| Fallworkflow | Start/Ende, Sichtungsnummern, zwei Entscheidungen, Geräte-/Dateimetadaten, PDF und ZIP implementiert. | Vollständiger Probeeinsatz einschließlich Wiederöffnung, konsistentem Bericht und Pflichtangaben. |
| Explorer und Archivfilter | Medienwechsel, verspätete Antworten, Filter, Archiv-Unterordner und Pagination automatisch geprüft. | Wiederholung mit bekannten Beständen auf dem Pi; Grenzen bei großen und unvollständigen Katalogen. |
| Archivverschlüsselung | ZIP/7Z/RAR-Merkmale, ungeklärter Status und lesbare Verzeichnisse implementiert. | Keine allgemeine PDF-/Office-/Volume-Verschlüsselungserkennung; Gründe nur soweit der gespeicherte Index sie liefert. |
| Schreibschutz und Isolation | Software-Read-only, getrennte Prozesse, Zeitlimits und begrenzte Diagnoseprotokolle vorhanden. | Physische Schreibschutzprüfung; Hardware-/Kernelstillstand wird dadurch nicht ausgeschlossen. |
| Updates | Online-Prüfung und bewusste Installation praktisch verwendet. Alpha 45 ergänzt signierte Offline-Pakete, Uploadfortschritt, Abhängigkeitsgrenze und eine gemeinsame Installationssperre. | Alpha 45 einmal online einspielen; danach erstes echtes Offline-Update, Fehler-/Stromausfallprüfung und Wiederherstellung aller veränderten Komponenten. |
| Einstellungen | Gemeinsamer Bereich für Profile und Dateitypen, atomare lokale Speicherung, Konflikterkennung und unveränderlicher Scan-Snapshot implementiert. | Bedienung und Erstübernahme auf dem Pi mit vorhandenen Profilen praktisch prüfen. |
| Entfernte Fälle | Ordner bleiben im Papierkorb; Entfernen automatisch geprüft. | Kein fertiger Import zurück in den aktiven Fallindex; kein geprüfter Restore-Ablauf. |
| Zugriff und Ablage | Lokaler HTTP-Zugang, konfigurierte Fallablage, keine Web-Anmeldung. | Gemeinsame Entsperrung, HTTPS und verschlüsselte Fallablage gemäß Schutzkonzept. |
| CD/DVD | Scan-/Auswurfpfad implementiert; bisher instabiler Hardwareversuch. | Test mit separat versorgtem Laufwerk. Ein solches wurde als möglicherweise vorhanden gemeldet, noch nicht geprüft. |

## Vorhandene Prüfnachweise

- **123 Python-Tests:** für Alpha 45 erfolgreich; zusätzlich sind signierte/manipulierte Pakete, Versions- und Abhängigkeitsgrenzen sowie gestreamte Uploads abgedeckt.
- **27 isolierte Browsertests:** für Alpha 45 erfolgreich. Sie prüfen zusätzlich Auswahl, Sperrung, Upload und sichtbaren Abschluss eines Offline-Updates.
- **26. August 2026:** dokumentierter Sollvergleich mit 960 Dateien auf exFAT; schneller Lauf 0,732 Sekunden auf der beschriebenen VM. Dies ist ein historischer Einzeltest, kein Geschwindigkeitsversprechen für den Pi oder beliebige Medien: [Nachweis](validation-2026-08-26.md).
- **Bisheriger Pi-Testbetrieb:** Installation, Hotspot/LAN, mehrere USB-Sticks, Archivbeispiele und Updates im Entwicklungsverlauf beobachtet. Die Feldtestserie mit vollständigem Prüfprotokoll steht noch aus.

Für Alpha 45 wurden keine neuen realen Scans, Offline-Updates am Pi, Stromunterbrechungen oder Wiederherstellungen ausgeführt. Neue Messwerte gehören mit Version, Aufbau, Testbestand und Abweichungen in einen datierten Nachweis; echte Falldaten bleiben außerhalb von Git.

## Bekannte Abweichungen vom Zielablauf

1. **Browser-Neuladen beendet den Fall nicht.** Die aktive Sitzung liegt im Arbeitsspeicher des Webdienstes und wird vom Browser wieder übernommen. Nach Dienst-/Pi-Neustart ist sie leer. Vor Standortwechsel muss der Fall ausdrücklich beendet werden.
2. **Protokollierung ist ereignisbezogen.** Fallstart, Sichtungsreservierung, Scanfehler/-ergebnis und Entscheidungen werden erfasst. Fallende erzeugt derzeit kein eigenes Fall-Audit-Ereignis. Navigation ist ebenfalls kein Audit-Ereignis.
3. **Einstellungs-Migration ist noch nicht auf dem Pi abgenommen.** Profile und Dateityp-Katalog liegen nun außerhalb des Programmverzeichnisses; der erste Wechsel aus Alpha 43 und ein Rückwechsel müssen mit vorhandenen eigenen Profilen praktisch geprüft werden.
4. **Rollback ist begrenzt.** Der Updater bereitet Code getrennt vor und wechselt den Laufzeitlink. Dienst-/nginx-Vorlagen werden zuvor installiert; der vorhandene Fehlerpfad deckt nicht sämtliche Änderungen und Unterbrechungen ab.
5. **Papierkorb bedeutet Dateierhalt.** Das Zurückverschieben eines Fallordners allein rekonstruiert den entfernten SQLite-Eintrag nicht.
6. **Löschsperre noch nicht vollständig serverseitig.** Das Dashboard sperrt aktive Fälle; der DELETE-Endpunkt prüft nur die Bestätigung, nicht zusätzlich aktive Sitzung oder laufende Scans. Vor dem nächsten vollständigen Probeeinsatz priorisiert absichern.
7. **Gerätequarantäne ist flüchtig.** Gesperrte Geräte sind nach Dienst-/Pi-Neustart nicht mehr in der Quarantäneliste; ein sicherer Wiederanlauf ist noch zu testen.

Diese Punkte sind Arbeitsaufträge in der [Roadmap](roadmap.md), keine bereits behobenen Funktionen. Der [Testplan](test-plan.md) definiert den nächsten Probeeinsatz.
