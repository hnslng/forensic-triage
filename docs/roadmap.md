# Roadmap und offene Aufgaben / Roadmap and TODOs

Stand: Version 0.2.0-alpha.2. Prioritäten richten sich nach forensischer Sicherheit und Nachvollziehbarkeit, nicht nach Funktionsmenge.

## Vor dem ersten realen Einsatz – zwingend

- [ ] Standard-Löschpasswort `123` durch ein langes lokales Passwort ersetzen.
- [ ] Fallarchiv auf verschlüsseltem, zugriffsgeschütztem Speicher betreiben und Sicherungskonzept festlegen.
- [ ] Hardware-Schreibblocker auswählen, beschaffen und mit dem Tool validieren.
- [ ] Organisatorischen Ablauf für Berechtigung, Beweismittelidentität, Zeitquelle und Chain of Custody festlegen.
- [ ] Mehrere physische USB-Medien gleichzeitig testen, einschließlich Fehler- und Abbruchszenarien.
- [ ] Wiederanlauf nach Strom-, Netzwerk- und Browserausfall prüfen.
- [ ] Audit-Log, Manifestprüfung, ZIP-Export und Wiederherstellung aus dem internen Papierkorb validieren.
- [ ] Freigabekriterien und dokumentierte Abnahme für eine Einsatzversion definieren.

## Raspberry Pi und Feldhardware

- [ ] Zielmodell, RAM, Speicher und Gehäuse festlegen.
- [ ] Raspberry Pi OS/Debian installieren und vollständige Installationsanleitung praktisch nachspielen.
- [ ] Aktiven, ausreichend versorgten USB-Hub für mehrere Datenträger validieren.
- [ ] Direkte Ethernet-Verbindung zum Laptop mit fester privater Adresse und Firewall einrichten.
- [ ] Touch-/Kleinbildschirm mit der echten Auflösung und Bedienung testen.
- [ ] Kontrolliertes Herunterfahren und Verhalten bei Stromverlust lösen.
- [ ] Status-LED-Konzept (`ready`, `scanning`, `complete`, `error`) entwickeln und GPIO getrennt vom Scanner anbinden.
- [ ] Temperatur und Laufzeit unter paralleler Last messen.

## Datenträger und Scanunterstützung

- [ ] CD/DVD-Laufwerk mit realen Medien validieren und erst danach freischalten.
- [ ] Weitere Dateisysteme und beschädigte Medien systematisch testen.
- [ ] Klären, ob eine sehr leichte Dateisignatur-/Magic-Byte-Prüfung ohne Vollinhaltsanalyse in den Grobsichtungsumfang aufgenommen wird.
- [ ] Falls umgesetzt: Abweichung zwischen Dateiendung und Signatur deutlich als Hinweis anzeigen.
- [ ] Verhalten bei verschlüsselten Volumes objektiv erkennen und dokumentieren, ohne Inhalte zu öffnen.
- [ ] Große Verzeichnisbäume und viele kleine Dateien auf Laufzeit und Speicherbedarf testen.

## Workflow und Dokumentation

- [ ] Administrativen Wiederherstellungsweg für entfernte Fälle dokumentieren und testen.
- [ ] Aufbewahrungs- und Löschfristen für Fallakten definieren.
- [ ] Rollen-/Berechtigungskonzept prüfen; das aktuelle Bearbeiterkürzel ist keine Anmeldung.
- [ ] Passwortverwaltung statt eines einzelnen lokalen Löschkennworts bewerten.
- [ ] PDF-Fallbericht nur bei klarer fachlicher Anforderung ergänzen.
- [ ] Prüfen, ob digitale Signaturen zusätzlich zum SHA-256-Manifest erforderlich sind.
- [ ] Deutsche UI-Texte abschließend redigieren und englische Vollübersetzung nur bei tatsächlichem Bedarf ergänzen.

## Qualität und Veröffentlichung

- [ ] Frontend-Tests für Fallstart, Archiv, Löschschutz und Entscheidungslogik ergänzen.
- [ ] Integrationsprüfung des parallelen Scanners auf Linux automatisieren.
- [ ] Abhängigkeiten und unterstützte Debian-/Python-Versionen fixieren und regelmäßig prüfen.
- [ ] Release-Checkliste erstellen.
- [ ] Vor `v1.0.0` Lizenz-/Nutzungsbedingungen und Verantwortlichkeiten festlegen.
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
