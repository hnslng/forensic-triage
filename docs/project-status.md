# Projektstand und Nachweise

Stand: **3. Oktober 2026**, Anwendung **v0.2.0-alpha.64**. Alpha 62 wurde auf dem realen Raspberry-Pi-Testgerät installiert und praktisch geprüft. Alpha 63 behebt die dabei beobachtete sichtbare geschlossene Einstellungsfläche und macht den Status technischer iOS-/Android-IDs eindeutig. Alpha 64 ist ein UI-/UX-Aufräumrelease: neuer Startzustand ohne aktiven Fall, SVG-Systemicons, integrierte Stichwortprofile in den Settings, vereinfachter Plattformstatus und ruhigere Scrollbars. Der normale Mobilgerät-Lauf bleibt ein App-only-Krypto-Schnellscan: Geräteinformationen, gemeldete Benutzer-Apps, gemeinsame Erkennungsregeln und Erfassungsgrenzen – keine Foto-, Medien- oder Dateisichtung.

Alpha 61 baut die Erkennungsregeln zu einer skalierbaren Plattform aus: gemeinsame Regeln für Krypto-Apps, Banking/Finanzen, Geräte-Backups und Dateihinweise; Master-Detail-Editor; Tooltips; erweiterter Krypto-Masterkatalog; breiter europäischer Banking-/Finanz-App-Katalog; und Erkennung lokaler Geräte-Backup-Strukturen auf Datenträgern ohne Öffnung der Inhalte. Die Implementierung ist automatisiert getestet, auf echten Mobilgeräten aber noch nicht abgenommen. Einzelheiten: [Bedienung](operation.md), [iPhone-Triage](iphone-triage.md), [Android-Triage](android-triage.md), [Einstellungen](settings.md), [Erkennungsregeln](detection-rules.md), [Gerätebackup-Erkennung](device-backups.md) und [Offline-Updates](offline-updates.md).

## Was „funktioniert“ hier bedeutet

- **Implementiert:** im aktuellen Code vorhanden.
- **Automatisch geprüft:** mit den beschriebenen synthetischen Tests geprüft; keine Aussage über jede reale Hardware.
- **Praktisch beobachtet:** im bisherigen Testbetrieb verwendet; noch keine vollständige formale Abnahme.
- **Offen:** Umsetzung oder reproduzierbarer Nachweis fehlt.

| Bereich | Aktueller Stand | Noch nachzuweisen / zu verbessern |
|---|---|---|
| Raspberry Pi 3B+ | Installiert und im Testbetrieb; signierte Offline-Updates wurden am 10. September erfolgreich verwendet. | Alpha 60 installieren und praktisch prüfen; für Android muss das neue Debian-Paket `adb` einmal online installiert beziehungsweise der Installer erneut ausgeführt werden. Reproduzierbare Neuinstallation, finaler Speicher-/Stromaufbau und Dauerbetrieb bleiben offen. |
| Netzwerk | Hotspot und Router-LAN verwendet; `http://triagebox.local/` erfolgreich ohne Port aufgerufen. Direkte Pi–Mac-Ethernet-Verbindung mit macOS-Internetfreigabe funktionierte über `192.168.2.2`. | Reiner Direktbetrieb ohne Internetfreigabe, gerätespezifisches Passwort, Firewall-Abnahme und optionaler temporärer WLAN-Wartungsmodus mit automatischem Hotspot-Fallback. |
| USB-Grobsichtung | Reale Testmedien, darunter drei gleichzeitig angeschlossene Sticks, bereits gesichtet. | Vollständiger Soll-/Ist-Vergleich, systematische Parallel- und Störungstests. |
| iPhone-Schnellscan | Reguläre USB-Erkennung, Trust-/Sperrhinweise, Geräte- und Benutzer-App-Metadaten, gemeinsame Krypto-Klassifikation und einheitliche Telefonansicht implementiert. AFC, File Sharing, Fotos und Dateien werden im normalen Lauf nicht mehr abgefragt. | Alpha 60 mit demselben echten iPhone messen; App-Listen-Vollständigkeit bei mehreren iOS-Versionen, gesperrtem Gerät und verweigertem Vertrauen systematisch prüfen. |
| Android-Schnellscan | USB-Vorerkennung für verbreitete Hersteller, ADB-Status, novice-taugliche Herstelleranleitungen, Autorisierung, App-Liste aller sichtbaren Profile und Krypto-Klassifikation implementiert und simuliert getestet. | Echten Samsung-/Pixel-/Xiaomi-Test durchführen; USB-Regeln, Auto-Start, Profile, Herstellerpfade und Verhalten ohne sichtbaren Secure Folder praktisch verifizieren. [Android-Triage](android-triage.md). |
| Fallworkflow | Start/Ende, Sichtungsnummern, zwei Entscheidungen, Entscheidungszentrale für abgezogene Medien, Geräte-/Dateimetadaten, PDF und ZIP implementiert. | Vollständiger Probeeinsatz einschließlich Mehrfachabzug, Wiederöffnung, konsistentem Bericht und Pflichtangaben. |
| Explorer und Archivfilter | Medienwechsel, verspätete Antworten, Filter, Archiv-Unterordner und Pagination automatisch geprüft. | Wiederholung mit bekannten Beständen auf dem Pi; Grenzen bei großen und unvollständigen Katalogen. |
| Archivverschlüsselung | ZIP/7Z/RAR-Merkmale, ungeklärter Status und lesbare Verzeichnisse implementiert. | Keine allgemeine PDF-/Office-/Volume-Verschlüsselungserkennung; Gründe nur soweit der gespeicherte Index sie liefert. |
| Schreibschutz und Isolation | Software-Read-only, getrennte Prozesse, Zeitlimits und begrenzte Diagnoseprotokolle vorhanden. | Physische Schreibschutzprüfung; Hardware-/Kernelstillstand wird dadurch nicht ausgeschlossen. |
| Updates | Online-Prüfung und bewusste Installation praktisch verwendet. Alpha 45 wurde von Alpha 43 online installiert; Alpha 48 wurde nach ausgewerteten Fehlversuchen erfolgreich offline von Alpha 45 installiert. Alpha 53 vergleicht den neuesten Tag mit der Paketversion statt nur mit dem Git-Stand. | Alpha 53 auf dem Pi einspielen und den behobenen Neuinstallationsfall praktisch bestätigen; weitere reguläre `.tbu`-Sprünge, Fehler-/Stromausfallprüfung und Wiederherstellung aller veränderten Komponenten. |
| Strom und System | Pi-Firmwarestatus, vier sichtbare Zustände sowie doppelt bestätigter Neustart/Shutdown mit serverseitigen Arbeitssperren implementiert und synthetisch geprüft. | Echten Pi-Wert auslesen; Neustart und Herunterfahren praktisch ohne angeschlossene Prüfmedien testen; Stromausfall bleibt getrennt offen. |
| Einstellungen | Gemeinsamer Bereich für Profile, Dateitypen, Erkennungsregeln und Systemupdates. Stichwortprofile seit Alpha 64 als Master-Detail innerhalb der Settings. Der geschlossene Dialog belegt keine Layoutfläche. Filter/Sortierung sind beschriftet; iOS-/Android-ID-Status zeigen nur noch `✓` / `?` / `—` ohne sichtbaren Badge. Atomare lokale Speicherung, Konflikterkennung und unveränderlicher Scan-Snapshot sind implementiert. | Alpha-64-Dialog, SVG-Icons, Overlay-Verhalten und Migration des realen Alpha-62-Regelbestands auf Safari/Pi prüfen; weitere App-IDs nur nach verifizierbarer Quelle ergänzen. |
| Entfernte Fälle | Ordner bleiben im Papierkorb; Entfernen automatisch geprüft. | Kein fertiger Import zurück in den aktiven Fallindex; kein geprüfter Restore-Ablauf. |
| Zugriff und Ablage | Lokaler HTTP-Zugang, konfigurierte Fallablage, keine Web-Anmeldung. | Gemeinsame Entsperrung, HTTPS und verschlüsselte Fallablage gemäß Schutzkonzept. |
| CD/DVD | Scan-/Auswurfpfad implementiert; bisher instabiler Hardwareversuch. | Test mit separat versorgtem Laufwerk. Ein solches wurde als möglicherweise vorhanden gemeldet, noch nicht geprüft. |

## Vorhandene Prüfnachweise

- **178 Python-Tests:** im Alpha-64-Arbeitsstand einschließlich Plattformstatus-Migration, eigener Regeln, Tombstones und unveränderlicher historischer Snapshots erfolgreich.
- **44 isolierte Browsertests:** im Alpha-64-Arbeitsstand mit Chromium erfolgreich. Sie prüfen unter anderem den Start-Overlay-Zustand, SVG-Systemicons, die integrierte Profilverwaltung, den vereinfachten Plattformstatus, ruhigere Scrollbars, den vollständig unsichtbaren geschlossenen Dialog, Filter-/Sortierlabels, globale Tooltips und den Regel-Editor mit synthetischen Antworten.
- **26. August 2026:** dokumentierter Sollvergleich mit 960 Dateien auf exFAT; schneller Lauf 0,732 Sekunden auf der beschriebenen VM. Dies ist ein historischer Einzeltest, kein Geschwindigkeitsversprechen für den Pi oder beliebige Medien: [Nachweis](validation-2026-08-26.md).
- **Bisheriger Pi-Testbetrieb:** Installation, Hotspot/LAN, mehrere USB-Sticks, Archivbeispiele und Updates im Entwicklungsverlauf beobachtet. Die Feldtestserie mit vollständigem Prüfprotokoll steht noch aus.

Für Alpha 61 wurden noch keine neuen realen Android-Scans, Mehrfachabzüge, Stromunterbrechungen oder Wiederherstellungen ausgeführt. Der letzte beobachtete iPhone-Lauf vor dem App-only-Umbau dauerte rund 16,35 Sekunden und enthielt noch einen Dateinamen-Zusatz; er ist kein Alpha-61-Leistungsnachweis. Neue Messwerte gehören mit Version, Aufbau, Testbestand und Abweichungen in einen datierten Nachweis; echte Falldaten bleiben außerhalb von Git.

## Bekannte Abweichungen vom Zielablauf

1. **Browser-Neuladen beendet den Fall nicht.** Die aktive Sitzung liegt im Arbeitsspeicher des Webdienstes und wird vom Browser wieder übernommen. Nach Dienst-/Pi-Neustart ist sie leer. Vor Standortwechsel muss der Fall ausdrücklich beendet werden.
2. **Protokollierung ist ereignisbezogen.** Fallstart, Sichtungsreservierung, Scanfehler/-ergebnis und Entscheidungen werden erfasst. Fallende erzeugt derzeit kein eigenes Fall-Audit-Ereignis. Navigation ist ebenfalls kein Audit-Ereignis.
3. **Einstellungs-Migration ist noch nicht auf dem Pi abgenommen.** Profile und Dateityp-Katalog liegen nun außerhalb des Programmverzeichnisses; der erste Wechsel aus Alpha 43 und ein Rückwechsel müssen mit vorhandenen eigenen Profilen praktisch geprüft werden.
4. **Rollback ist begrenzt.** Der Updater bereitet Code getrennt vor und wechselt den Laufzeitlink. Dienst-/nginx-Vorlagen werden zuvor installiert; der vorhandene Fehlerpfad deckt nicht sämtliche Änderungen und Unterbrechungen ab.
5. **Papierkorb bedeutet Dateierhalt.** Das Zurückverschieben eines Fallordners allein rekonstruiert den entfernten SQLite-Eintrag nicht.
6. **Löschsperre noch nicht vollständig serverseitig.** Das Dashboard sperrt aktive Fälle; der DELETE-Endpunkt prüft nur die Bestätigung, nicht zusätzlich aktive Sitzung oder laufende Scans. Vor dem nächsten vollständigen Probeeinsatz priorisiert absichern.
7. **Gerätequarantäne ist flüchtig.** Gesperrte Geräte sind nach Dienst-/Pi-Neustart nicht mehr in der Quarantäneliste; ein sicherer Wiederanlauf ist noch zu testen.

Diese Punkte sind Arbeitsaufträge in der [Roadmap](roadmap.md), keine bereits behobenen Funktionen. Der [Testplan](test-plan.md) definiert den nächsten Probeeinsatz.
