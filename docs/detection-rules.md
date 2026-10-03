# Erkennungsregeln

TRIAGE//BOX verwendet eine gemeinsame, lokal gepflegte Regelsammlung für die Erkennung von Krypto-Apps, Banking-/Finanz-Apps, Geräte-Backups und Dateihinweisen. Die Regeln liegen als JSON-Datei im Einstellungsordner (`crypto-rules.json`) und werden über **Einstellungen → Erkennungsregeln** bearbeitet.

## Regeltypen

### App-Regeln

App-Regeln gelten für iPhones, iPads und Android-Geräte im Krypto-Schnellscan sowie indirekt für die Interpretation von App-Metadaten. Sie enthalten:

- `ios_bundle_ids` – iOS-Bundle-IDs (z. B. `io.metamask.ios`)
- `android_package_ids` – Android-Package-IDs (z. B. `io.metamask`)
- `name` – exakter App-Name
- `aliases` / `former_names` – alternative oder frühere Namen
- `terms` – zusätzliche, vorsichtige Suchbegriffe im App-Namen
- `category` und `relevance`
- `ios_id_status` / `android_id_status` – Status der technischen ID: `verified`, `unverified` oder explizit `not_applicable`
- `ios_id_note` / `android_id_note` – optionale plattformspezifische Erläuterung
- Metadaten: `status`, `verified`, `source`, `last_verified`, `regions`

Das ältere allgemeine Feld `verified` bleibt für die Kompatibilität erhalten. In der Oberfläche wird die konkrete Aussage getrennt je Plattform dargestellt:

| Symbol | Status | Bedeutung |
|---|---|---|
| `✓` | `verified` | Mindestens eine technische ID dieser Plattform ist anhand einer nachvollziehbaren Quelle verifiziert. |
| `?` | `unverified` | Derzeit ist keine verlässlich geprüfte ID dieser Plattform hinterlegt. Das bedeutet **nicht**, dass dort keine App existiert. |
| `—` | `not_applicable` | Die Regel ist für diese Plattform nachweislich nicht anwendbar. Dieser Status wird nie aus einer leeren ID-Liste geraten. |

### Datei-Regeln

Datei-Regeln gelten für Datenträger-Scans und prüfen Dateinamen und -pfade:

- `filename_equals` – exakte Dateinamen
- `terms` – Begriffe in Name oder Pfad
- `context_terms` – zusätzlicher Kontext (ODER-Verknüpfung)
- `extensions` – eingeschränkte Endungen

### Backup-Regeln

Backup-Regeln erkennen lokale Geräte-Backup-Strukturen auf Datenträgern:

- `required_paths` – Pfadmerkmale, die vorkommen müssen
- `required_files` – charakteristische Dateinamen
- `required_extensions` – charakteristische Endungen
- `confidence` – `high`, `medium` oder `low`
- `platform` – Betriebssystem oder Hersteller

## Kategorien und Relevanz

| Kategorie | Bedeutung | Relevanz |
|---|---|---|
| `wallet` | Self-Custody-Wallet | `high` |
| `hardware_wallet` | Hardware-Wallet-Begleiter-App | `high` |
| `exchange` | Kryptobörse / Broker | `high` |
| `portfolio` | Steuer / Portfolio | `medium` |
| `payment` | Krypto-Zahlungsdienst | `medium` |
| `market` | Kurse / Markt | `medium` |
| `banking` | Banking / Finanzen | `neutral` |
| `messenger` | Messenger | `neutral` |
| `cloud` | Cloudspeicher | `neutral` |

Banking, Messenger und Cloud sind immer neutral und erzeugen keinen Krypto-Hinweis.

## Vollständigkeit

Der mitgelieferte Katalog ist bewusst ein breiter, lokal gepflegter und erweiterbarer Katalog – keine mathematisch vollständige Liste aller Apps. Nicht verifizierte App-IDs bleiben leer und werden mit `?` als noch nicht verifiziert gekennzeichnet. Die Erkennung kann, soweit die Regel dies vorsieht, weiterhin über exakten Namen, Alias, früheren Namen oder vorsichtigen Suchbegriff erfolgen.

## Migration

Beim Start wird `crypto-rules.json` automatisch mit dem mitgelieferten Standardkatalog abgeglichen:

- Vorhandene lokale Regeln bleiben unverändert erhalten.
- Neue Standardregeln werden ergänzt.
- Eigene Benutzerregeln bleiben erhalten.
- Ab `v0.2.0-alpha.62` werden bewusst gelöschte Standardregeln in `deleted_default_rule_ids` vermerkt und bei künftigen Updates nicht wiederhergestellt.
- Ab `v0.2.0-alpha.63` wurden die getrennten Plattformstatus ergänzt; Alpha 64 zeigt sie als vereinfachte Textzeichen `✓` / `?` / `—` ohne sichtbaren Badge. Eine vorhandene ID wird nur mit bisherigem `verified: true` als `verified` übernommen; fehlende IDs werden `unverified`. `not_applicable` entsteht ausschließlich durch eine explizite, belegte Angabe.

Das lokale Regelschema bleibt in Alpha 63 auf Version 3; die neuen Felder werden beim ersten Start deterministisch ergänzt und die lokale Regelversion fortgeschrieben. Lokale Änderungen, eigene Regeln und Tombstones bleiben erhalten. Scans speichern den jeweiligen Regelstand als Snapshot; historische Sichtungen werden weder umgeschrieben noch nachträglich neu klassifiziert. Alte `iphone-triage.json`-Dateien werden weiterhin einmalig migriert.
