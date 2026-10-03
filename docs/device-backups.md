# Gerätebackup-Erkennung

TRIAGE//BOX erkennt auf USB-/CD-Datenträgern charakteristische Strukturen lokaler Geräte-Backups, ohne deren Inhalt zu öffnen oder auszuwerten. Die Erkennung arbeitet ausschließlich auf Pfad-, Dateinamen- und Endungsmerkmalen.

## Erkannte Backup-Typen

| Backup-Typ | Plattform | Erkennungsmerkmale | Sicherheit |
|---|---|---|---|
| Apple Finder/iTunes Backup | iOS | `MobileSync/Backup`, `iTunes/Backup`, `Manifest.db`, `Info.plist` | hoch |
| Samsung Smart Switch | Android | `Smart Switch/Backup`, `Smart Switch/PC`, DB-Dateien | mittel |
| Android ADB Backup | Android | Dateien mit Endung `.ab` | hoch (Legacy) |
| Xiaomi lokales Backup | Android | `MIUI/backup`, `Xiaomi/backup`, `.bak`-Dateien | mittel |
| Huawei HiSuite Backup | Android | `HiSuite`, `Huawei/Backup` | mittel |
| OnePlus / Oppo / realme Backup | Android | `OnePlus/backup`, `OPPO/backup`, `realme/backup`, `ColorOS/backup` | niedrig |
| Windows-Image-Backup | Windows | `WindowsImageBackup`, `.vhd`/`.vhdx` | hoch |
| iCloud Drive lokaler Cache | iOS/macOS | `Mobile Documents`, `iCloud Drive` | niedrig |

## Bedeutung der Erkennungssicherheit

- **HOCH** – mehrere unabhängige Strukturmerkmale stimmen überein.
- **MITTEL** – mehrere Hinweise, aber ohne eindeutige charakteristische Dateien.
- **NIEDRIG** – einzelner Pfadindikator; manuelle Prüfung empfohlen.

Eine Erkennung beweist nicht, dass ein Backup vollständig oder wiederherstellbar ist, und sagt nichts über seinen Inhalt aus. Es wird nur festgestellt: „Diese Verzeichnisstruktur sieht wie ein bekannter Backup-Typ aus."

## Integration

Backup-Hinweise erscheinen:

- im Scan-Ergebnis unter **Geräte-Backups**
- in `backup-hints.json` im Ergebnisverzeichnis
- in `summary.json` unter `backup_hints`
- im Fallbericht und PDF
- im Fall-ZIP und dessen `manifest.sha256`

## Grenzen

- Backup-Inhalte werden nicht gelesen, entschlüsselt oder wiederhergestellt.
- Umbenannte oder stark veränderte Backup-Strukturen können übersehen werden.
- Einzelne allgemeine Dateinamen (z. B. `backup.bak`) führen nicht automatisch zu einer Erkennung.
