# Bedienung und Fallworkflow / Operation

## Grundsatz

TRIAGE//BOX unterstützt die Grobsichtung. Es entscheidet nicht, ob ein Medium rechtlich oder fachlich sicherzustellen ist. Alle relevanten Bedienhandlungen werden der lokalen Fallakte zugeordnet. Besonders Entscheidungen dürfen nur bewusst und mit dem richtigen Bearbeiterkürzel gespeichert werden.

## 1. System starten

1. Scanner-VM beziehungsweise später den Raspberry Pi starten.
2. Webdienststatus prüfen.
3. Vom Laptop über den SSH-Tunnel verbinden.
4. Dashboard öffnen.

Nach jedem Seiten- oder Dienstneustart ist **kein Fall aktiv**. Der Systemstatus zeigt „Gesperrt“ und es darf kein Scan beginnen.

## 2. Neuen Fall vorbereiten

1. „Auftrag öffnen“ wählen.
2. Neue Fallnummer eingeben.
3. Bearbeiter-/Kürzel eintragen.
4. Mindestens ein Suchprofil auswählen. Mehrere Profile werden zusammengeführt; doppelte Begriffe werden nur einmal gesucht.
5. Offene Voraussetzungen in der unteren Statuszeile prüfen.
6. „Fall starten“ wählen.

Das bloße Eingeben einer anderen Fallnummer wechselt den aktiven Fall nicht. Der Wechsel wird erst durch „Fall starten“ wirksam. Dadurch soll verhindert werden, dass neue Medien versehentlich einem alten Einsatz zugeordnet werden.

## 3. Vorhandenen Fall öffnen

1. „Auftrag öffnen“ und anschließend „Fallarchiv öffnen“ wählen.
2. Beim gewünschten Fall „Öffnen“ wählen.
3. Bearbeiterkürzel eintragen beziehungsweise prüfen.
4. Suchprofile prüfen.
5. „Fall starten“ ausdrücklich bestätigen.

## 4. Datenträger sichten

1. Berechtigung und physische Identität des Mediums außerhalb des Tools klären.
2. Medium anschließen.
3. Geräteangaben wie Typ, Größe, Modell und Seriennummer prüfen.
4. Bei aktivem Auto-Scan beginnt ein geeignetes, ungemountetes USB-Medium automatisch. Mehrere geeignete USB-Medien können parallel laufen.
5. Fortschritt und Abschlussstatus je Kachel beobachten.
6. Detailansicht öffnen und Kategorien, Stichworttreffer, Größen sowie Verzeichnisbaum prüfen.

„Online“ bedeutet, dass das Medium gegenwärtig erkannt wird. Nach Entfernen bleibt ein bereits protokolliertes Medium als „Offline“ in der Fallhistorie sichtbar. Ein offener Entscheidungsstatus muss weiterhin erkennbar bleiben.

## 5. Entscheidung dokumentieren

- **Sichern:** Medium soll in den nachfolgenden Sicherungs-/Laborprozess überführt werden. Erst jetzt ist eine offizielle Beweismittel-/Asservatennummer Pflicht.
- **Nicht ausgewählt:** Medium wird nach der Grobsichtung nicht ausgewählt. Eine strukturierte Begründung ist Pflicht, damit später nachvollziehbar bleibt, warum es nicht mitgenommen wurde.
- **Weitere Prüfung:** Entscheidung wird vertagt beziehungsweise zusätzliche Prüfung ist erforderlich.

Das Speichern einer Entscheidung erzeugt einen dauerhaften Protokolleintrag. Deshalb Auswahl, Fall, Medium und Bearbeiter vor dem Speichern kontrollieren.

## 6. Auswerfen und Aktualisieren

TRIAGE//BOX schreibt keine Nutzdaten auf das Medium. Der Software-Auswurf kann dennoch verwendet werden, damit das Betriebssystem das Gerät kontrolliert freigibt. Bei einem softwareseitig ausgeworfenen, weiterhin eingesteckten USB-Gerät versucht „Aktualisieren“, das Medium erneut zu erkennen. Ein physisches Ab- und Anstecken soll normalerweise nicht nötig sein.

## 7. Fall exportieren

„Falldaten laden“ erzeugt einen ZIP-Export der lokalen Fallakte. Der Export enthält Metadaten und Dokumentation, keine kopierten Dateiinhalte des gesichteten Mediums. Exporte aus echten Fällen müssen wie Fallunterlagen geschützt und dürfen nicht in Git gespeichert werden.

## 8. Fall entfernen

1. Aktiven Fall gegebenenfalls zuerst beenden.
2. Fallarchiv öffnen.
3. Beim gewünschten Fall „Löschen“ wählen.
4. Fallnummer in der Warnung prüfen.
5. Lokales Löschpasswort eingeben und bestätigen.

Der Fall muss dafür nicht zuerst geöffnet oder gestartet werden. Das Archiv bleibt während des Vorgangs geöffnet. Der aktive Fall kann nicht entfernt werden. Die lokale Fallakte wird in einen internen Papierkorb verschoben und bleibt administrativ wiederherstellbar; dies ist keine sichere Datenlöschung.

## 9. Fall beenden

„Fall beenden“ sperrt neue Scans und entfernt die aktive Zuordnung aus der Oberfläche. Vor Standort- oder Fallwechsel immer den alten Fall beenden. Ein Fall kann nicht beendet werden, solange ein Scan läuft.

## Störungen

- **Oberfläche nicht erreichbar:** VM/Pi, Netzwerk, SSH-Tunnel und Webdienst prüfen; den Mac-Starter erneut ausführen.
- **Medium nicht erkannt:** „Aktualisieren“ wählen, Kabel/Hub/Stromversorgung prüfen und Geräteinformationen kontrollieren.
- **Scan bleibt gesperrt:** Fallnummer, Bearbeiterkürzel und Suchprofil in der Statusmeldung prüfen.
- **Medium ist gemountet:** Nicht scannen; Mount außerhalb des Tools kontrolliert lösen und Gerät erneut identifizieren.
- **Fehlerstatus:** Medium nicht voreilig abziehen; Fehlermeldung und Protokoll sichern.

## English workflow summary

The system always starts without an active case. Enter or select a case, provide operator initials, select at least one search profile, and explicitly start the case. Eligible USB media may then scan automatically and in parallel. Review the metadata-only result and record one of three decisions. An evidence number is required only for “Secure”; a structured reason is required for “Not selected”. End the case before changing locations or deleting it. Cases can be opened or removed directly from the archive; the active case is protected.
