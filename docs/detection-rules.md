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
- Metadaten: `status`, `verified`, `source`, `last_verified`, `regions`

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

Der mitgelieferte Katalog ist bewusst ein breiter, lokal gepflegter und erweiterbarer Katalog – keine mathematisch vollständige Liste aller Apps. Nicht verifizierte App-IDs bleiben leer und werden als „ID fehlt“ gekennzeichnet.

## Migration

Beim ersten Start werden bestehende lokale `crypto-rules.json` automatisch übernommen. Alte `iphone-triage.json`-Dateien werden weiterhin migriert. Scans speichern den jeweiligen Regelstand als Snapshot; historische Sichtungen werden nicht nachträglich neu klassifiziert.
