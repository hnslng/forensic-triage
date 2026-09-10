# Einstellungen: Stichwortprofile, Dateitypen und Updates

Seit `v0.2.0-alpha.44` öffnet **Einstellungen** in der oberen Systemleiste einen eigenen Bereich außerhalb des Fallfensters. Er funktioniert auch ohne aktiven Fall.

## Stichwortprofile

- **Bearbeiten:** Profilname und Suchbegriffe ändern, Begriffe hinzufügen oder entfernen.
- **Duplizieren:** vorhandene Begriffe in ein neues, unabhängig gespeichertes Profil übernehmen.
- **Neues Profil:** eigenes Profil anlegen.
- **Profil speichern:** Namen und vollständige Begriffsliste dauerhaft speichern.
- **Auswahl für nächste Scans:** nur die angehakten vorhandenen Begriffe für kommende Scans auswählen; die gespeicherte Begriffsliste bleibt unverändert.

Im Fallfenster werden weiterhin die Profile für den Einsatz ausgewählt. Dort gibt es keine Profilverwaltung mehr. Neu angelegte oder duplizierte Profile werden bei bereits vorhandener Auswahl nicht automatisch aktiviert. Profile werden über Namen und Pfade gesucht; die Einstellung löst keine Inhaltsanalyse aus.

## Dateitypen

Die Suche findet Kategorien oder Endungen. Jede Zeile enthält einen Kategorienamen und die dazugehörigen Endungen. Endungen mit Komma, Leerzeichen oder Zeilenumbruch trennen; ein führender Punkt und Großbuchstaben werden normalisiert. Beispielsweise werden `.JPG` und `jpg` gleich behandelt.

Endungen können ergänzt, entfernt oder zwischen Kategorien verschoben werden. **Neue Kategorie** ergänzt eine Zeile; das × entfernt eine Kategorie aus dem Entwurf. Eine Endung darf nur einer Kategorie zugeordnet sein. Doppelte oder ungültige Einträge verhindern das Speichern des gesamten Entwurfs. Nicht zugeordnete oder fehlende Endungen ergeben automatisch **Unbekannt**.

**Standard laden** lädt den mit dieser Programmversion gelieferten Katalog in den Entwurf. Erst **Änderungen speichern** übernimmt ihn. Schließen mit ungespeicherten Änderungen verlangt eine Verwerfbestätigung. Hat ein anderer Browser den Katalog zwischenzeitlich gespeichert, wird ein veralteter Schreibversuch abgelehnt; Einstellungen erneut öffnen und Änderungen neu eintragen.

Der erweiterte Standard enthält unter anderem Kameraformate, makrofähige Office-Dateien, Audio/Video, Archivendungen, forensische Images, Systemartefakte und Kontakte/Kalender. `.raw` und `.key` stehen wegen ihrer unterschiedlichen Verwendungen unter **Mehrdeutig**, `.bak` unter **Sicherungskopien**. **Schutz-/Schlüsseldateien** ist ausschließlich eine Endungskategorie: Sie bestätigt weder Verschlüsselung noch Relevanz. Eine Datei kann durch Umbenennen weiterhin falsch eingeordnet werden.

Es wird die letzte Endung ausgewertet: `backup.tar.gz` wird über `gz` eingeordnet. Mehrteilige Sondernamen werden nicht als eigener Dateitypnachweis interpretiert. Zusätzliche Archivendungen erweitern nur die Kategoriezuordnung; der Verzeichnisleser unterstützt weiterhin ZIP, ISO, 7Z und RAR. Die Verschlüsselungszähler beziehen sich auf die der Kategorie **Archive** zugeordneten äußeren Dateien. Beim Verschieben einer Endung in eine andere Kategorie verändert sich deshalb auch der Umfang dieser Zähler.

## System & Updates

Der dritte Einstellungsbereich zeigt die installierte Programmversion und den zuletzt bekannten Updatestatus. **System & Updates öffnen** führt in das ausführliche Updatefenster für Online-Prüfung und signierte `.tbu`-Pakete. Updates werden nie automatisch installiert. Während Prüfung, Upload, Installation und anschließendem Dienstneustart bleibt das Fenster geöffnet beziehungsweise wird nach dem Neuladen automatisch wiederhergestellt. Ein laufender Balken zeigt die aktuelle Phase; ein Prozentwert wird nur für die tatsächlich messbare Paketübertragung angegeben.

## Nachvollziehbarkeit

Neue Scans übernehmen zu Beginn einen unveränderlichen Katalogstand. Derselbe Stand gilt für äußere Dateien und katalogisierte Archiv-Inneneinträge. Gespeichert werden der vollständige Katalog als `filetype-catalog.json` sowie Version und SHA-256 in `summary.json`. Der Katalog gehört damit zur Fallakte, zum Manifest und zum ZIP-Export. Im Nachweisdialog steht er unter **Technische Ablagepfade anzeigen**.

Änderungen beeinflussen ausschließlich neue Scans. Laufende Scans behalten ihren übernommenen Stand; alte Sichtungen, Entscheidungen und Berichte werden durch das Bearbeiten der Einstellungen nicht umklassifiziert. Ältere Sichtungen ohne Katalogdatei werden im Nachweis entsprechend bezeichnet.

## Lokale Ablage und Updates

`FORENSIC_TRIAGE_SETTINGS_ROOT` bestimmt den Ordner. Der Installer verwendet `<ursprünglicher Projektordner>/settings`; ohne ausdrücklichen Eintrag nimmt der Webdienst `settings` neben dem konfigurierten Fallordner. Beim Bootstrap ist das üblicherweise `/opt/triagebox/settings`.

```text
settings/
├── filetypes.json
└── profiles/
    ├── default.yaml
    └── weitere-profile.yaml
```

Beim ersten Start werden vorhandene Profile kopiert, ohne bereits gespeicherte lokale Profile zu überschreiben. Der Alpha-44-Webdienst sucht dabei zuerst im neuesten bisherigen Release, dann im ursprünglichen Installationsordner und zuletzt in seinen mitgelieferten Profilen. Damit wird auch der Erstwechsel durch einen älteren Updater abgefangen, der den neuen Migrationsschritt selbst noch nicht ausführen kann. Ab dem neuen Updater werden Profile zusätzlich bereits vor dem Umschalten übernommen. Eine separate Sicherung vor Updates bleibt trotzdem sinnvoll; lokale Änderungen an versionierten Dateien können bereits die Updateprüfung blockieren.

Nach der Übernahme schreibt der Profileditor nur in den Einstellungen-Ordner. Der Dateityp-Katalog wird atomar gespeichert. Bestehende lokale Einstellungen bleiben bei späteren Updates erhalten; neue Standardzuordnungen werden bewusst über **Standard laden** übernommen. Diesen Ordner gemeinsam mit Fallindex und Fallunterlagen sichern. Direkte Änderungen an `filetypes.json` werden bei ungültiger Prüfsumme abgelehnt.

Die CLI verwendet den gespeicherten Katalog, wenn `FORENSIC_TRIAGE_SETTINGS_ROOT` in ihrer Umgebung gesetzt ist; andernfalls verwendet sie den mitgelieferten Standard. Auch CLI-Scans speichern ihren Katalogstand.

## English summary

Settings has separate keyword-profile, file-type, and system-update sections outside the case dialog. Operators can edit or duplicate profiles, maintain an extension catalog, and deliberately open online or signed offline updates. Duplicate extensions and stale concurrent saves are rejected. Each new scan stores its immutable catalog and hash; historical results are unchanged. Operator settings are kept outside release checkouts and should be included in backups. Extension categories do not confirm file contents or encryption.
