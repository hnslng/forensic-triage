# Bedienung und Fallworkflow / Operation

## Grundsatz

TRIAGE//BOX unterstützt die Grobsichtung. Es entscheidet nicht, ob ein Medium rechtlich oder fachlich sicherzustellen ist. Alle relevanten Bedienhandlungen werden der lokalen Fallakte zugeordnet. Besonders Entscheidungen dürfen nur bewusst und mit dem richtigen Bearbeiterkürzel gespeichert werden.

## 1. System starten

1. Scanner-System starten.
2. Webdienststatus prüfen.
3. Lokalen Bildschirm oder freigegebene Netzwerkverbindung verwenden.
4. Dashboard öffnen.

Nach jedem Seiten- oder Dienstneustart ist **kein Fall aktiv**. Der Systemstatus zeigt „Gesperrt“ und es darf kein Scan beginnen.

## 2. Neuen Fall vorbereiten

1. Links „Fall anlegen / öffnen“ wählen.
2. Neue Fallnummer eingeben.
3. Bearbeiter-/Kürzel eintragen.
4. Mindestens ein Suchprofil auswählen. Mehrere Profile werden zusammengeführt; doppelte Begriffe werden nur einmal gesucht.
5. Offene Voraussetzungen in der unteren Statuszeile prüfen.
6. „Fall starten“ wählen.

Das bloße Eingeben einer anderen Fallnummer wechselt den aktiven Fall nicht. Der Wechsel wird erst durch „Fall starten“ wirksam. Dadurch soll verhindert werden, dass neue Medien versehentlich einem alten Einsatz zugeordnet werden.

## 3. Vorhandenen Fall öffnen

1. „Fall anlegen / öffnen“ und anschließend „Fallarchiv öffnen“ wählen.
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

„Nachweis anzeigen“ nennt die beim Scan gespeicherten Geräteangaben (Modell, Seriennummer, Kapazität, Medientyp und Gerätepfad) sowie den verifizierten Schreibschutz. Diese Angaben stammen aus der Sichtungsakte und bleiben deshalb auch nach dem Abziehen des Mediums verfügbar.

Dateikategorien und Stichwortzeilen sind anklickbar. Die passende Dateiliste öffnet sich darunter automatisch; der aktive Filter wird direkt über der Liste angezeigt. Bei Stichworttreffern zeigt „Treffer in“, ob der Begriff aus dem Dateinamen oder einem Ordnerpfad stammt. „Weitere Dateien laden“ ergänzt große Trefferlisten. Der nur bei aktiver Filterung direkt neben „Suchen“ eingeblendete Befehl „Filter aufheben“ führt eindeutig zum vollständigen Verzeichnisbaum zurück.

Die freie Suche ist davon getrennt: Suchbegriff in „Dateiname oder Pfad filtern“ eingeben und „Suchen“ wählen oder die Eingabetaste drücken. Ein leerer Suchbegriff verändert die aktuelle Ansicht nicht. Dateiinhalte werden dabei nicht durchsucht.

Regulär vorhandene versteckte Dateien und Ordner erscheinen im Metadateninventar ebenfalls. Gelöschte Dateien, bewusst ausgefilterte interne Dateisystemeinträge und wegen Beschädigung nicht lesbare Einträge gehören nicht zu dieser Grobsichtung.

„Online“ bedeutet, dass das Medium gegenwärtig erkannt wird. Nach Entfernen bleibt ein bereits protokolliertes Medium als „Offline“ in der Fallhistorie sichtbar. Ein offener Entscheidungsstatus muss weiterhin erkennbar bleiben.

## 5. Entscheidung dokumentieren

- **Sichern:** Medium soll in den nachfolgenden Sicherungs-/Laborprozess überführt werden. Erst jetzt ist eine offizielle Beweismittel-/Asservatennummer Pflicht.
- **Nicht sichern:** Medium wird nach der Grobsichtung nicht ausgewählt. Eine strukturierte Begründung ist Pflicht, damit später nachvollziehbar bleibt, warum es nicht mitgenommen wurde.

Einen eigenen Zustand „Weitere Prüfung“ gibt es nicht mehr. Bestehen nach der Grobsichtung noch Zweifel, wird das Medium zur Sicherung ausgewählt und erhält eine Beweismittel-/Asservatennummer. Historische Protokolle mit dem früheren Status bleiben unverändert nachvollziehbar, der Status kann aber nicht erneut vergeben werden.

Das Speichern einer Entscheidung erzeugt einen dauerhaften Protokolleintrag. Deshalb Auswahl, Fall, Medium und Bearbeiter vor dem Speichern kontrollieren.

## 6. Auswerfen und Aktualisieren

TRIAGE//BOX schreibt keine Nutzdaten auf das Medium. Der Software-Auswurf kann dennoch verwendet werden, damit das Betriebssystem das Gerät kontrolliert freigibt. Bei einem softwareseitig ausgeworfenen, weiterhin eingesteckten USB-Gerät versucht „Aktualisieren“, das Medium erneut zu erkennen. Ein physisches Ab- und Anstecken soll normalerweise nicht nötig sein.

Bei einem externen USB-CD/DVD-Laufwerk erscheint direkt in der Laufwerkskachel `CD/DVD AUSWERFEN`. Dieser Befehl ist auch ohne aktiven Fall und bei leerem Laufwerk verfügbar, damit sich eine Schublade ohne physischen Knopf öffnen lässt. Während eines Scans oder solange das Medium anderweitig gemountet ist, bleibt der Auswurf gesperrt. Nach einer protokollierten Sichtung steht derselbe Befehl zusätzlich an der Medienkachel.

## 7. Fall exportieren

„PDF-Bericht“ lädt eine kurze, druckbare Fallübersicht im A4-Querformat. Pro Datenträger enthält sie eine Zeile mit Seriennummer, technischen Dateikategorien, Entscheidung und gegebenenfalls der Begründung für „Nicht sichern“. „Falldaten ZIP“ erzeugt zusätzlich den vollständigen Export der lokalen Fallakte. Beide Exporte enthalten keine kopierten Dateiinhalte des gesichteten Mediums. Exporte aus echten Fällen müssen wie Fallunterlagen geschützt und dürfen nicht in Git gespeichert werden.

Im Datei-Explorer können erkannte ZIP-, ISO-, 7Z- und RAR-Dateien wie ein Ordner aufgeklappt werden – auch in der nach `ARCHIVE` gefilterten Tabelle. Das Format ergibt sich aus dem Dateinamen; eine zusätzliche Plakette wird bewusst nicht wiederholt. Angezeigt und durchsucht werden ausschließlich katalogisierte Namen und Verzeichniswege. `LIMIT` bedeutet, dass das kurze Zeit- oder Mengenbudget erreicht wurde und die virtuelle Liste bewusst unvollständig ist. `NAMEN VERSCHLÜSSELT`, `UNVOLLSTÄNDIG` und `NICHT LESBAR` sind keine Beweise für einen leeren Container; der Datenträger muss bei Relevanz einer professionellen Folgeprüfung zugeführt werden.

Unter der Dateitypenliste stehen zwei kompakte Filter, beispielsweise `4 verschlüsselt` und `2 ungeprüft`. Anklicken zeigt die passenden Archivdateien im unteren Verzeichnis; erneutes Anklicken oder `Filter aufheben` stellt den Explorer wieder her. Bei null Treffern ist der jeweilige Filter deaktiviert. Die Dateitypzeile `ARCHIVE` behält ihre äußere Dateianzahl und den ausgerichteten Balken.

Verschlüsselte Archive werden im Explorer und in Suchergebnissen mit einem kleinen Amber-Hinweis `VERSCHLÜSSELT` gekennzeichnet, ungeprüfte mit einem neutralen, gepunkteten `UNGEPRÜFT`. Der Verschlüsselungswert stammt aus eindeutig erkannten ZIP-, 7Z- oder RAR-Merkmalen. `Ungeprüft` umfasst insbesondere noch nicht unterstützte Formate sowie beschädigte, unvollständige oder nur teilweise katalogisierte Archive und ist ausdrücklich kein Entwarnungsstatus. Die Filter beziehen sich ausschließlich auf Archivdateien auf dem Medium, nicht auf verschachtelte Archivnamen. Sie nutzen gespeicherte Metadaten, ohne neu zu scannen oder Fallprotokolle zu ändern.

Bei `GRÖSSTE DATEIEN` steht die Größe fest links, daneben der Dateiname und darunter der Ordner. Lange Namen werden in der Kachel abgekürzt; der vollständige Pfad bleibt im Tooltip und nach Auswahl im Dateiverzeichnis verfügbar. Ein Klick zeigt exakt diesen gespeicherten Pfad im unteren Metadatenverzeichnis. Er öffnet keine Nutzdatei und liest den Datenträger nicht erneut. `Filter aufheben` führt zurück zum vollständigen Explorer.

## 8. Fall entfernen

1. Aktiven Fall gegebenenfalls zuerst beenden.
2. Fallarchiv öffnen.
3. Beim gewünschten Fall „Löschen“ wählen.
4. Fallnummer in der Warnung prüfen.
5. Die fallbezogene Bestätigung aktivieren.
6. „Diesen Fall aus dem Archiv entfernen“ bewusst auslösen.

Der Fall muss dafür nicht zuerst geöffnet oder gestartet werden. Das Archiv bleibt während des Vorgangs geöffnet. Der aktive Fall kann nicht entfernt werden. Die lokale Fallakte wird in einen internen Papierkorb verschoben und bleibt administrativ wiederherstellbar; dies ist keine sichere Datenlöschung.

## 9. Fall beenden

„Fall beenden“ sperrt neue Scans und entfernt die aktive Zuordnung aus der Oberfläche. Vor Standort- oder Fallwechsel immer den alten Fall beenden. Ein Fall kann nicht beendet werden, solange ein Scan läuft.

## Störungen

- **Oberfläche nicht erreichbar:** Scanner, Netzwerkverbindung, konfigurierte Adresse/Port und Webdienst prüfen.
- **Medium nicht erkannt:** „Aktualisieren“ wählen, Kabel/Hub/Stromversorgung prüfen und Geräteinformationen kontrollieren.
- **Scan bleibt gesperrt:** Fallnummer, Bearbeiterkürzel und Suchprofil in der Statusmeldung prüfen.
- **Medium ist gemountet:** Nicht scannen; Mount außerhalb des Tools kontrolliert lösen und Gerät erneut identifizieren.
- **Fehlerstatus:** Medium nicht voreilig abziehen; Fehlermeldung und Protokoll sichern.

## English workflow summary

The system always starts without an active case. Enter or select a case, provide operator initials, select at least one search profile, and explicitly start the case. Eligible USB media may then scan automatically and in parallel. Review the metadata-only result and record either “Secure” or reasoned “Do not secure”. An evidence number is required only for “Secure”. End the case before changing locations or deleting it. Cases can be opened or removed directly from the archive; the active case is protected.
