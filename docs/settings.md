# Einstellungen: Stichwortprofile, Dateitypen, Erkennungsregeln und Updates

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

## Erkennungsregeln

Der Bereich **Erkennungsregeln** ersetzt die bisherigen „Krypto-Regeln“ durch eine skalierbare, master-detail-basierte Verwaltung. Er ist in vier Unterbereiche gegliedert:

- **Krypto-Apps** – Self-Custody-Wallets, Hardware-Wallet-Begleiter, Börsen/Broker, Portfolio-/Steuer- und Zahlungsdienste
- **Banking & Finanzen** – Banken, Neobanken, Broker und Finanzdienste (immer neutral, niemals Krypto-Hinweis)
- **Geräte-Backups** – Strukturmerkmale lokaler Backups (Apple Finder/iTunes, Samsung Smart Switch, Android ADB, Xiaomi, Huawei, OnePlus/Oppo/realme, Windows-Image, iCloud Drive)
- **Dateihinweise** – Dateinamen- und Pfadmuster für Krypto-Hinweise auf Datenträgern

### Arbeitsfläche

Auf Desktop nutzt der Dialog fast die gesamte Browserfläche. Kopfzeile, Haupttabs, Untertabs und der Footer bleiben während des Scrollens sichtbar; nur die Listen- und Editor-Inhalte scrollen in ihren eigenen Bereichen. Links erscheint die Regelliste (ca. 55 %), rechts der Editor (ca. 45 %). Wenn keine Regel ausgewählt ist, zeigt der Editor einen Hilfstext statt einer leeren Fläche.

### Master-Detail-Ansicht

Links erscheint eine übersichtliche Tabelle aller Regeln des gewählten Bereichs. Eine Zeile zeigt Name, Kategorie, Vorhandensein einer iOS- bzw. Android-ID und den Status (aktiv/inaktiv/legacy). Rechts öffnet sich der Editor genau der ausgewählten Regel. Damit bleibt die Übersicht auch bei vielen hundert Regeln schnell.

### Filter und Suche

- Freie Suche über Name, Kategorie, Alias, iOS-Bundle-ID und Android-Package-ID
- Filter: aktiv, inaktiv, legacy, verifiziert, nicht verifiziert, iOS-ID fehlt, Android-ID fehlt
- Sortierung nach Name, Kategorie oder Status
- Die sichtbare Regelanzahl wird über der Liste angezeigt; der Footer zeigt Gesamt-, Standard- und Eigenregeln.

### Aktionen

- **Neue Regel** – erstellt eine leere Regel im aktuellen Bereich
- **Duplizieren** – kopiert die ausgewählte Regel mit neuer ID
- **Löschen** – entfernt die Regel nach Rückfrage; Standardregeln werden dauerhaft in `deleted_default_rule_ids` vermerkt
- **Aktivieren/Deaktivieren** – über den Editor-Status
- **JSON exportieren / importieren** – vollständige Regelsammlung inklusive Tombstones als JSON; Import muss vor dem Speichern geprüft werden

### Regelinhalt

App-Regeln führen getrennte, verifizierte `ios_bundle_ids` und `android_package_ids`; ergänzend sind exakte Namen, Aliase, frühere Namen oder ausdrücklich angelegte Suchbegriffe möglich. Datei-Regeln kombinieren exakte Namen, Begriffe, zusätzliche Kontextbegriffe und Endungen. Backup-Regeln definieren Plattform, Erkennungssicherheit sowie erforderliche Pfade, Dateien und Endungen.

Jede Regel kann folgende Metadaten tragen:

- `status`: `active` oder `legacy`
- `verified`: `true`/`false`
- `source`: Herkunft der Kennung oder Strukturinformation
- `last_verified`: Prüfdatum im Format `YYYY-MM-DD`
- `regions`: optionale Länderkürzel (z. B. `["AT","DE"]`)

### Speicherlogik

Der Editor arbeitet mit einem zweistufigen Entwurf:

- **Übernehmen** – schreibt die aktuellen Editorfelder in den lokalen Entwurf (noch nicht dauerhaft).
- **Abbrechen** – verwirft die Editoränderungen und schließt den Editor.
- **Alle Änderungen speichern** – speichert den gesamten Entwurf dauerhaft in `crypto-rules.json` und erhöht den Regelstand.

Der Footer zeigt den aktuellen Regelstand und warnt bei ungespeicherten Änderungen. Schließen mit ungespeicherten Änderungen verlangt eine Verwerfbestätigung.

Das Speichern validiert IDs, Kategorien, Hinweisstärken, Listen und konkurrierende Änderungen; ungültige Daten werden insgesamt zurückgewiesen. Android-Package-IDs und iOS-Bundle-IDs dürfen nicht geraten werden. Neue Regeln gelten ausschließlich für zukünftige Sichtungen.

### Hilfe und Tooltips

**? Begriffe erklären** öffnet einen eigenen Hilfe-Dialog über der Einstellungsoberfläche. Das Master-Detail-Layout wird nicht verschoben. Kleine **?**-Tooltips neben den Editorfeldern werden in einer globalen Tooltip-Schicht außerhalb der scrollbaren Bereiche gerendert, sodass sie nicht durch `overflow:hidden` abgeschnitten werden.

## System & Updates

Der vierte Einstellungsbereich enthält unmittelbar die vollständige Updateverwaltung für Online-Prüfung und signierte `.tbu`-Pakete; ein zweites Fenster oder ein weiterer Öffnungsschritt ist nicht erforderlich. Updates werden nie automatisch installiert. Während Prüfung, Upload, Installation und anschließendem Dienstneustart bleibt das Einstellungsfenster geöffnet beziehungsweise wird beim Neuladen bereits vor dem ersten Statusabruf direkt in dieser Registerkarte wiederhergestellt. Dadurch erscheint nicht kurz das Dashboard zwischen zwei Updatephasen. Ein laufender Balken zeigt die aktuelle Phase; ein Prozentwert wird nur für die tatsächlich messbare Paketübertragung angegeben. Nach erfolgreichem Abschluss erscheint im Fenster zusätzlich eine klar erkennbare Erfolgsmeldung mit der installierten Version.

## Nachvollziehbarkeit

Neue Scans übernehmen zu Beginn einen unveränderlichen Katalogstand. Derselbe Stand gilt für äußere Dateien und katalogisierte Archiv-Inneneinträge. Gespeichert werden der vollständige Katalog als `filetype-catalog.json` sowie Version und SHA-256 in `summary.json`. Der Katalog gehört damit zur Fallakte, zum Manifest und zum ZIP-Export. Im Nachweisdialog steht er unter **Technische Ablagepfade anzeigen**.

Änderungen beeinflussen ausschließlich neue Scans. Laufende Scans behalten ihren übernommenen Stand; alte Sichtungen, Entscheidungen und Berichte werden durch das Bearbeiten der Einstellungen nicht umklassifiziert. Ältere Sichtungen ohne Katalogdatei werden im Nachweis entsprechend bezeichnet. Neue Sichtungen speichern `crypto-rules.json`, `crypto-hints.json` und zusätzlich `backup-hints.json` in den Ergebnissen und im Fall-ZIP.

## Lokale Ablage und Updates

`FORENSIC_TRIAGE_SETTINGS_ROOT` bestimmt den Ordner. Der Installer verwendet `<ursprünglicher Projektordner>/settings`; ohne ausdrücklichen Eintrag nimmt der Webdienst `settings` neben dem konfigurierten Fallordner. Beim Bootstrap ist das üblicherweise `/opt/triagebox/settings`.

```text
settings/
├── crypto-rules.json
├── filetypes.json
└── profiles/
    ├── default.yaml
    └── weitere-profile.yaml
```

Beim ersten Start werden vorhandene Profile kopiert, ohne bereits gespeicherte lokale Profile zu überschreiben. Der Alpha-44-Webdienst sucht dabei zuerst im neuesten bisherigen Release, dann im ursprünglichen Installationsordner und zuletzt in seinen mitgelieferten Profilen. Damit wird auch der Erstwechsel durch einen älteren Updater abgefangen, der den neuen Migrationsschritt selbst noch nicht ausführen kann. Ab dem neuen Updater werden Profile zusätzlich bereits vor dem Umschalten übernommen. Eine separate Sicherung vor Updates bleibt trotzdem sinnvoll; lokale Änderungen an versionierten Dateien können bereits die Updateprüfung blockieren.

Nach der Übernahme schreibt der Profileditor nur in den Einstellungen-Ordner. Der Dateityp-Katalog wird atomar gespeichert. Bestehende lokale Einstellungen bleiben bei späteren Updates erhalten; neue Standardzuordnungen werden bewusst über **Standard laden** übernommen. Diesen Ordner gemeinsam mit Fallindex und Fallunterlagen sichern. Direkte Änderungen an `filetypes.json` werden bei ungültiger Prüfsumme abgelehnt.

### Automatische Regel-Migration

`crypto-rules.json` wird bei jedem Start mit dem mitgelieferten Standardkatalog abgeglichen:

- **Lokale Änderungen haben Vorrang:** Existiert eine Regel-ID bereits lokal, bleibt sie unverändert erhalten.
- **Neue Standardregeln werden ergänzt:** Noch nicht vorhandene App-, Datei- und Backup-Regeln der neuen Version werden hinzugefügt.
- **Eigene Regeln bleiben erhalten:** Vom Benutzer angelegte Regeln, die nicht zum Standard gehören, werden niemals entfernt.
- **Bewusst gelöschte Standardregeln bleiben entfernt:** Ab `v0.2.0-alpha.62` merkt sich `deleted_default_rule_ids` gelöschte Standardregeln. Sie werden bei künftigen Updates nicht wiederhergestellt. Regeln, die vor Alpha 62 gelöscht wurden, können einmalig wieder auftauchen, weil diese Information noch nicht existierte.

Diese Migration ist deterministisch: Sie verändert keine historischen Scan-Snapshots, klassifiziert alte Fälle nicht neu und verändert die Fallindex-`sqlite3` nicht.

Die CLI verwendet den gespeicherten Katalog, wenn `FORENSIC_TRIAGE_SETTINGS_ROOT` in ihrer Umgebung gesetzt ist; andernfalls verwendet sie den mitgelieferten Standard. Auch CLI-Scans speichern ihren Katalogstand.

## English summary

Settings has separate keyword-profile, file-type, detection-rule, and system-update sections outside the case dialog. Detection rules cover crypto apps, banking/finance apps, device-backup structures and file-name hints. Operators can edit or duplicate profiles, maintain an extension catalog and shared metadata rules, and deliberately open online or signed offline updates. Duplicate extensions and stale concurrent saves are rejected. Each new scan stores immutable catalog, crypto-rule and backup-hint snapshots; historical results are unchanged. Operator settings are kept outside release checkouts and should be included in backups. Neither extension categories nor rule hits confirm file contents or assets.
