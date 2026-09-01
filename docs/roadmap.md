# Roadmap und offene Aufgaben / Roadmap and TODOs

Stand: Version 0.2.0-alpha.24. Prioritäten richten sich nach forensischer Sicherheit und Nachvollziehbarkeit, nicht nach Funktionsmenge.

## Vor dem ersten realen Einsatz – zwingend

- [x] Fallbezogene Doppelbestätigung und wiederherstellbaren Papierkorb ohne Passwort umsetzen.
- [ ] Das in [security-concept.md](security-concept.md) festgehaltene einfache Zugriffsschutzkonzept vollständig implementieren und abnehmen.
- [ ] Fallarchiv auf verschlüsseltem, zugriffsgeschütztem Speicher betreiben und Sicherungskonzept festlegen.
- [ ] Hardware-Schreibblocker auswählen, beschaffen und mit dem Tool validieren.
- [ ] Organisatorischen Ablauf für Berechtigung, Beweismittelidentität, Zeitquelle und Chain of Custody festlegen.
- [ ] Mehrere physische USB-Medien gleichzeitig testen, einschließlich der implementierten Prozessisolation, Zeitlimits und Fehlerquarantäne.
- [ ] Wiederanlauf nach Strom-, Netzwerk- und Browserausfall prüfen.
- [ ] Audit-Log, Manifestprüfung, ZIP-Export und Wiederherstellung aus dem internen Papierkorb validieren.
- [ ] Freigabekriterien und dokumentierte Abnahme für eine Einsatzversion definieren.

## Raspberry Pi und Feldhardware

- [x] Opt-in-Installationsmodus `--pi` für NetworkManager-Hotspot, Hostname, Avahi und Weiterleitungsschutz vorbereiten.
- [x] Ein-Befehl-Bootstrap für eine kontrolliert öffentliche GitHub-Phase vorbereiten.
- [x] Portfreie lokale HTTP-Adresse `http://triagebox.local/` über einen auf das Hotspot-Netz begrenzten Reverse-Proxy vorbereiten.
- [x] Tägliche reine Release-Prüfung und bewusst auslösbare, rollback-fähige Aktualisierung vorbereiten.
- [ ] Zielmodell, RAM, Speicher und Gehäuse festlegen.
- [ ] Raspberry Pi OS/Debian installieren und vollständige Installationsanleitung praktisch nachspielen.
- [ ] Aktiven, ausreichend versorgten USB-Hub für mehrere Datenträger validieren.
- [ ] Raspberry Pi 3B+ als privaten, passwortgeschützten WPA3-/WPA2-WLAN-Hotspot `TRIAGEBOX` mit gerätespezifischem Passwort einrichten; keine USB-Netzwerkverbindung vorsehen.
- [ ] Pi-Hostname `triagebox` festlegen und mDNS/Avahi einrichten, damit die Oberfläche im privaten Hotspot über `triagebox.local` erreichbar ist.
- [ ] Portlose HTTPS-Adresse `https://triagebox.local/` über Port 443 samt lokalem Zertifikatsverfahren umsetzen und auf die vorgesehenen privaten Schnittstellen begrenzen.
- [ ] Direkte Ethernet-Verbindung mit fester privater Adresse als robuste Rückfallebene einrichten.
- [ ] Feste private Pi-IP für WLAN und Ethernet dokumentieren, falls mDNS auf einem Laptop nicht funktioniert.
- [ ] Hotspot-Verschlüsselung, starkes WLAN-Passwort, Firewall und Verhalten ohne Internetverbindung prüfen.
- [ ] Gemeinsames Gerätepasswort, kurze Browsersitzung, Inaktivitätssperre und Abmeldung implementieren; keine zentrale Benutzerverwaltung für den ersten Feldprototyp.
- [ ] Touch-/Kleinbildschirm mit der echten Auflösung und Bedienung testen.
- [ ] Kontrolliertes Herunterfahren und Verhalten bei Stromverlust lösen.
- [ ] Status-LED-Konzept (`ready`, `scanning`, `complete`, `error`) entwickeln und GPIO getrennt vom Scanner anbinden.
- [ ] Temperatur und Laufzeit unter paralleler Last messen.

## Datenträger und Scanunterstützung

- [ ] Implementierten CD/DVD-Scanpfad mit realen intakten und beschädigten Medien im vorgesehenen Laufwerk validieren.
- [ ] Weitere Dateisysteme und beschädigte Medien systematisch testen.
- [ ] Klären, ob eine sehr leichte Dateisignatur-/Magic-Byte-Prüfung ohne Vollinhaltsanalyse in den Grobsichtungsumfang aufgenommen wird.
- [ ] Falls umgesetzt: Abweichung zwischen Dateiendung und Signatur deutlich als Hinweis anzeigen.
- [ ] Verhalten bei verschlüsselten Volumes objektiv erkennen und dokumentieren, ohne Inhalte zu öffnen.
- [ ] Große Verzeichnisbäume und viele kleine Dateien auf Laufzeit und Speicherbedarf testen.
- [x] ZIP- und ISO-Verzeichnisstrukturen ohne Extraktion, Rekursion oder Änderung der äußeren Dateizahlen katalogisieren.
- [x] 7Z- und RAR-Verzeichnisstrukturen über Debians `7zip` nur im Listenmodus katalogisieren und Verschlüsselung konservativ kennzeichnen.
- [ ] ZIP-/ISO-/7Z-/RAR-Schnellindex und Drei-Sekunden-Budget auf dem Raspberry Pi mit großen, beschädigten, verschlüsselten, mehrteiligen und ungewöhnlichen Containern validieren.
- [ ] TAR-Unterstützung nach der Hardwaremessung bewerten.

## Workflow und Dokumentation

- [ ] Administrativen Wiederherstellungsweg für entfernte Fälle dokumentieren und testen.
- [ ] Aufbewahrungs- und Löschfristen für Fallakten definieren.
- [ ] Rollen-/Berechtigungskonzept prüfen; das aktuelle Bearbeiterkürzel ist keine Anmeldung.
- [ ] Rollen-/Rechteverwaltung nur bei späterem Mehrbenutzerbedarf bewerten.
- [x] Kompakten PDF-Fallbericht im Querformat mit einer Zeile je Datenträger ergänzen.
- [ ] PDF-Berichtsaufbau und Formulierungen fachlich abnehmen.
- [ ] Prüfen, ob digitale Signaturen zusätzlich zum SHA-256-Manifest erforderlich sind.
- [ ] Deutsche UI-Texte abschließend redigieren und englische Vollübersetzung nur bei tatsächlichem Bedarf ergänzen.

## Qualität und Veröffentlichung

- [ ] Frontend-Tests für Fallstart, Archiv, Löschschutz und Entscheidungslogik ergänzen.
- [ ] Integrationsprüfung des parallelen Scanners auf Linux automatisieren.
- [ ] Abhängigkeiten und unterstützte Debian-/Python-Versionen fixieren und regelmäßig prüfen.
- [ ] Release-Checkliste erstellen.
- [x] Vorläufige restriktive Nutzungsbedingungen und Verantwortlichkeiten dokumentieren.
- [ ] Vor `v1.0.0` entscheiden, ob und unter welcher Open-Source-Lizenz das Projekt freigegeben wird.
- [ ] Sicherheitsreview und formale Werkzeugvalidierung durchführen.

## Bewusst nicht im aktuellen Umfang

- forensische Images erstellen
- gelöschte Dateien wiederherstellen oder Carving durchführen
- Dateiinhalte vollständig indexieren
- Malware ausführen oder Dateien in Vorschauen öffnen
- Passwörter brechen oder verschlüsselte Inhalte entschlüsseln
- automatische rechtliche beziehungsweise fachliche Sicherstellungsentscheidungen

Diese Aufgaben gehören in nachgelagerte, professionell validierte Werkzeuge und nicht in die schnelle Grobsichtung vor Ort.

## English summary

The highest priorities are hardware validation, encrypted case storage, a real hardware write blocker, multi-device testing, recovery testing, and formal operating procedures. Raspberry Pi, optical media, GPIO LEDs, and optional lightweight file-signature checks remain future work. Imaging, carving, content indexing, decryption, and automated seizure decisions are intentionally out of scope.
