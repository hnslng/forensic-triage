# Konfiguration / Configuration

## Grundsatz

Lokale Einstellungen gehören nicht in den Programmcode und nicht in Git. Das Installationsskript legt deshalb einmalig folgende Datei an:

```text
/etc/forensic-triage/triage.env
```

Sie gehört `root` und hat Dateimodus `0600`. Der Installer erhält eigene Einstellungen grundsätzlich, migriert aber passende alte Codepfade und ergänzt fehlende Updateparameter. Im Pi-Modus wird der Backend-Host ausdrücklich auf `127.0.0.1` gesetzt.

Der optionale Pi-Modus legt Netzwerkgeheimnisse bewusst getrennt vom Webdienst ab:

```text
/etc/forensic-triage/pi-network.env
```

Auch diese Datei gehört `root`, hat Modus `0600` und wird bei Aktualisierungen nicht überschrieben. Dadurch erhält der Webprozess das WLAN-Kennwort nicht als eigene Umgebungsvariable.

Bearbeiten, nachdem Fall und Scans beendet wurden:

```bash
sudoedit /etc/forensic-triage/triage.env
sudoedit /etc/forensic-triage/pi-network.env  # nur im Pi-Modus
sudo systemctl restart forensic-triage-web.service
```

## Einstellungen

| Name | Standard | Bedeutung |
|---|---|---|
| `FORENSIC_TRIAGE_WEB_HOST` | `127.0.0.1` | Netzwerkadresse des Webdienstes |
| `FORENSIC_TRIAGE_WEB_PORT` | `8787` | interner Python-Port; nginx veröffentlicht die Oberfläche auf Port 80 |
| `FORENSIC_TRIAGE_RESULTS_ROOT` | `<Projekt>/results` | technische Scannergebnisse |
| `FORENSIC_TRIAGE_CASEFILES_ROOT` | `<Projekt>/casefiles` | dauerhafte lokale Fallakten |
| `FORENSIC_TRIAGE_WEB_ROOT` | `<Projekt>/web` | statische Oberfläche; für Releasewechsel an den Laufzeitlink binden |
| `FORENSIC_TRIAGE_PROFILE` | `<Projekt>/profiles/default.yaml` | Start-/Kompatibilitätsprofil |
| `FORENSIC_TRIAGE_SETTINGS_ROOT` | `<Projekt>/settings` beim Installer; sonst `settings` neben dem Fallordner | dauerhafte Profile und Dateityp-Katalog außerhalb von Release-Checkouts |
| `FORENSIC_TRIAGE_SCAN_TIMEOUT_SECONDS` | `180` | Frist bis zum Scan-Abbruchversuch in Sekunden; Kernel-/Aufräumgrenzen siehe unten |
| `FORENSIC_TRIAGE_COMMAND_TIMEOUT_SECONDS` | `15` | Zeitlimit eines einzelnen Gerätebefehls in Sekunden |
| `FORENSIC_TRIAGE_DEVICE_DISCOVERY_TIMEOUT_SECONDS` | `2` | Zeitlimit für `lsblk` bei der Geräteerkennung; danach höchstens 0,5 Sekunden Abbruchnachlauf |
| `FORENSIC_TRIAGE_DEVICE_DISCOVERY_BACKOFF_SECONDS` | `10` | Pause vor einem erneuten Dashboard-Geräteabruf nach einem Fehler |
| `FORENSIC_TRIAGE_CONTAINER_INDEX_SECONDS` | `3` | gemeinsames Zusatzzeitbudget für ZIP-/ISO-/7Z-/RAR-Verzeichnisse je Medium; keine harte I/O-Garantie |
| `FORENSIC_TRIAGE_CONTAINER_MAX_FILES` | `50` | höchstens katalogisierte ZIP-/ISO-/7Z-/RAR-Dateien je Medium |
| `FORENSIC_TRIAGE_CONTAINER_MAX_ENTRIES` | `2000` | höchstens Einträge je Container |
| `FORENSIC_TRIAGE_CONTAINER_MAX_TOTAL_ENTRIES` | `10000` | höchstens interne Einträge insgesamt je Medium |
| `FORENSIC_TRIAGE_UPDATE_ENABLED` | `true` | aktiviert Update-Prüfung und bewusst angeforderte Installation; keine automatische Installation |
| `FORENSIC_TRIAGE_UPDATE_REMOTE` | `origin` | Git-Remote für die Release-Prüfung |
| `FORENSIC_TRIAGE_UPDATE_GIT_ROOT` | `<Projekt>` | dauerhafter Git-Checkout für spätere Online-Updates nach einem Offline-Release |
| `FORENSIC_TRIAGE_UPDATE_STATE_FILE` | `/var/lib/forensic-triage/update-status.env` | lokaler, root-geschützter Update-Status für das Dashboard |
| `FORENSIC_TRIAGE_OFFLINE_UPDATE_FILE` | `/var/lib/forensic-triage/offline-update.tbu` | kurzlebiger Übergabepfad eines vollständig empfangenen Offline-Pakets |
| `FORENSIC_TRIAGE_OFFLINE_UPDATE_MAX_BYTES` | `268435456` | maximale Uploadgröße; nginx begrenzt zusätzlich auf 256 MB |
| `FORENSIC_TRIAGE_OFFLINE_UPDATE_ALLOWED_SIGNERS` | `/etc/forensic-triage/offline-update-allowed-signers` | öffentlicher SSH-Prüfschlüssel, niemals der private Signaturschlüssel |
| `FORENSIC_TRIAGE_UPDATE_GUARD_FILE` | `/run/forensic-triage-update-requested` | flüchtige Sperre gegen neue Fall-/Scanstarts während einer Installation |
| `FORENSIC_TRIAGE_RUNTIME_LINK` | `<Projekt>-current` | Laufzeitlink zum aktiven Code, beim Bootstrap `/opt/triagebox-current` |
| `FORENSIC_TRIAGE_RELEASES_ROOT` | `<Projekt>-releases` | Ablage vorbereiteter Release-Checkouts |

Beispiel:

```ini
FORENSIC_TRIAGE_WEB_HOST=127.0.0.1
FORENSIC_TRIAGE_WEB_PORT=8787
FORENSIC_TRIAGE_RESULTS_ROOT=/srv/triage/results
FORENSIC_TRIAGE_CASEFILES_ROOT=/srv/triage/casefiles
FORENSIC_TRIAGE_WEB_ROOT=/opt/triagebox-current/web
FORENSIC_TRIAGE_PROFILE=/opt/triagebox-current/profiles/default.yaml
FORENSIC_TRIAGE_SETTINGS_ROOT=/opt/triagebox/settings
FORENSIC_TRIAGE_SCAN_TIMEOUT_SECONDS=180
FORENSIC_TRIAGE_COMMAND_TIMEOUT_SECONDS=15
FORENSIC_TRIAGE_CONTAINER_INDEX_SECONDS=3
FORENSIC_TRIAGE_CONTAINER_MAX_FILES=50
FORENSIC_TRIAGE_CONTAINER_MAX_ENTRIES=2000
FORENSIC_TRIAGE_CONTAINER_MAX_TOTAL_ENTRIES=10000
```

## Beschädigte oder sehr langsame Medien

Jede Grobsichtung läuft in einem eigenen Prozess und – unter Linux – in einem privaten Mount-Namensraum. Für vollständige Scans wird standardmäßig nach 180 Sekunden ein Abbruch ausgelöst; einzelne Gerätebefehle haben 15 Sekunden Zeitlimit. Aufräumen und nicht unterbrechbare Kernelzugriffe können über diese Zeiten hinausgehen. Damit wartet der Webdienst nicht unbegrenzt auf den Scanner. Ein blockierter Kernel, USB-Bus oder Systemdatenträger kann trotzdem den gesamten Rechner betreffen; siehe [forensische Sicherheitsgrenzen](forensic-safety.md#beschädigte-medien).

Auch die Geräteerkennung im Dashboard ist begrenzt: `lsblk` erhält standardmäßig zwei Sekunden, danach folgt höchstens eine halbe Sekunde Abbruchnachlauf. Bei einem Fehler pausieren automatische Statusabfragen und manuelles Aktualisieren die erneute Geräteerkennung für zehn Sekunden. Gleichzeitige Dashboard-Abfragen warten nicht hinter einem laufenden Geräteabruf. Fallstatus und Updateinformationen können weiter geliefert werden, solange deren Speicher erreichbar ist. Die Oberfläche zeigt den letzten bekannten Gerätebestand mit unbekanntem Verbindungsstatus; neue Scans und Auswerfen sind dort bis zur erfolgreichen Erkennung gesperrt. Ein fehlgeschlagener Abruf gilt ausdrücklich nicht als Nachweis, dass ein quarantänisiertes Medium abgezogen wurde.

Die beiden zusätzlichen Konfigurationswerte gelten durch Programmvorgaben auch bei bestehenden Installationen; die lokale `triage.env` muss dafür nicht überschrieben werden. Die automatische Sichtung geeigneter CD/DVD-Medien bleibt grundsätzlich vorgesehen. Für Tests mit einem auffällig instabilen Laufwerk Auto-Scan vorher ausschalten und eine eigene Stromversorgung verwenden.

Nach einer Zeitüberschreitung wird nur der betroffene Gerätepfad gesperrt und als `MEDIUM ANTWORTET NICHT` angezeigt. Im laufenden Webdienst wird die Sperre nach erfolgreich erkanntem Abziehen aufgehoben. Sie liegt bisher nur im Arbeitsspeicher und ist nach einem Dienst-/Pi-Neustart ebenfalls leer. Das begrenzt automatische Wiederholungen innerhalb derselben Dienstlaufzeit, ist aber keine neustartfeste Quarantäne. Die Zeitlimits sind bewusst konfigurierbar, dürfen aber erst nach praktischen Tests mit der Zielhardware erhöht werden.

Der ZIP-/ISO-/7Z-/RAR-Schnellindex hat zusätzlich ein gemeinsames Standardbudget von drei Sekunden je Medium. Dies ist ein Prüfbudget und noch keine auf allen Medien bestätigte harte Laufzeitobergrenze; insbesondere Bibliotheks-/Hardwarezugriffe können länger dauern. Mengenlimits begrenzen die katalogisierten Einträge; sie sind keine Garantie gegen beliebigen Ressourcenverbrauch eines Archivparsers. Nutzdateien werden nicht extrahiert oder dekomprimiert, angegebene entpackte Größen nur als Metadaten behandelt. Komprimierte Archivverzeichnisse können intern dekodiert werden. Ein erreichtes Limit erzeugt einen unvollständigen, sichtbar gekennzeichneten Index. Verschachtelte Container werden nicht geöffnet.

Für die Fallentfernung gibt es bewusst kein Passwort. Der Dialog verlangt zwei eindeutige Bedienhandlungen für den konkret genannten Fall. Entfernen erhält den Fallordner im internen Papierkorb; ein fertiger Rückimport in den Fallindex fehlt. Das ist eine Fehlbedienungssperre, aber keine Benutzer- oder Rechteverwaltung. Die Sperre für aktive Fälle besteht bisher nur im Dashboard; siehe [Fallakte](case-archive.md#entfernen-und-wiederherstellung).

## Pi-Netzwerk

Die lokale Datei `pi-network.env` enthält:

| Name | Alpha-Standard | Bedeutung |
|---|---|---|
| `TRIAGEBOX_WIFI_SSID` | `TRIAGEBOX` | sichtbarer WLAN-Name |
| `TRIAGEBOX_WIFI_PASSWORD` | `triagebox123` | ausschließlich einfaches Entwicklungskennwort |
| `TRIAGEBOX_WIFI_INTERFACE` | `wlan0` | integrierte WLAN-Schnittstelle |
| `TRIAGEBOX_WIFI_CONNECTION` | `TRIAGEBOX-HOTSPOT` | Name des NetworkManager-Profils |
| `TRIAGEBOX_WIFI_ADDRESS` | `10.42.0.1/24` | private Hotspot-Adresse und Netz |
| `TRIAGEBOX_HOSTNAME` | `triagebox` | mDNS-Hostname für `triagebox.local` |
| `TRIAGEBOX_WIFI_COUNTRY` | `AT` | WLAN-Regulierungsland |

Das Entwicklungskennwort ist absichtlich leicht zu merken, aber allgemein bekannt und daher **nicht für echten Einsatz geeignet**. Ein späteres starkes Kennwort kann in Anführungszeichen als shell-kompatibler `KEY=VALUE`-Eintrag hinterlegt werden. Anschließend über Ethernet oder Konsole die vorhandene Netzwerkkonfiguration anwenden (beim Bootstrap-Pfad):

```bash
sudo /opt/triagebox-current/scripts/configure_pi_network.sh
```

Bei anderer Installation den zugehörigen Laufzeitpfad verwenden. Der Befehl wendet die Netzwerkdatei auf NetworkManager an und kann die Verbindung kurz unterbrechen. Alternativ ist eine bewusste erneute Pi-Installation möglich; der bloße Webdienst-Neustart reicht für WLAN-Änderungen nicht.

## Port und Netzwerk

`127.0.0.1` ist die sichere Voreinstellung für Entwicklung oder Zugriff über SSH. Der Raspberry Pi 3B+ stellt im Pi-Modus den WLAN-Hotspot `TRIAGEBOX` bereit. Ethernet am gemeinsamen Router-LAN funktioniert ebenfalls; die direkte Laptop-Kabelverbindung ohne Router ist noch vorzubereiten. Eine andere Bindeadresse darf erst nach festgelegten privaten IP-Adressen und Firewallregeln aktiviert werden. `0.0.0.0` würde auf allen Netzwerkschnittstellen lauschen und soll nicht unüberlegt verwendet werden.

Nach einem internen Portwechsel muss neben `triage.env` auch `proxy_pass` in `/etc/nginx/sites-available/forensic-triage` angepasst werden. Danach `sudo nginx -t`, den Webdienst neu starten und nginx neu laden. Der direkte Backend-Zugriff wäre bei Port `8877` nur auf dem Scanner `http://127.0.0.1:8877/`; die normale Browseradresse `http://triagebox.local/` bleibt ohne Port unverändert.

Auf einem Pi wird dieser interne Port durch nginx als portfreie Adresse `http://triagebox.local/` veröffentlicht. Zugelassen sind ausschließlich Loopback sowie private IPv4-Netze (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`). Damit funktioniert dieselbe Adresse im TRIAGEBOX-Hotspot und über Ethernet im normalen privaten LAN; aus öffentlichen Netzen wird der Zugriff abgewiesen. Der Python-Dienst selbst bleibt auf `127.0.0.1`. HTTP ist eine Bedienvereinfachung, aber noch kein Ersatz für das in `security-concept.md` geplante HTTPS und die gemeinsame Geräteentsperrung.

## Updates

Beim Booten mit Verzögerung und anschließend täglich startet ein `systemd`-Timer ausschließlich die Prüfung auf einen neuen Git-Release-Tag. Das Update wird niemals selbstständig installiert. Das Dashboard zeigt den Status und kann die Installation bewusst anfordern. Serverseitig wird sie verweigert, solange ein Fall aktiv oder ein Scan aktiv ist.

Die Online-Installation erzeugt einen separaten Release-Checkout, erstellt die Python-Umgebung und führt die Tests aus. Alternativ übernimmt der Webdienst ein signiertes Offline-Paket. Der Code-Laufzeitlink wird anschließend atomar gewechselt; Deploymentvorlagen werden allerdings schon davor geschrieben. Es existiert ein begrenzter Rückwechselpfad, aber noch keine vollständige Wiederherstellung aller Komponenten bei Start-/Stromfehlern; siehe [Updategrenzen](installation.md#5-aktualisieren) und [Offline-Updates](offline-updates.md). Fallakten und Ergebnisse sollen außerhalb der Release-Ordner liegen. Ihre tatsächlichen konfigurierten Pfade sowie eigene Profile müssen vor Updates geprüft und gesichert werden.

## Speicherpfade

Der Fallpfad muss vor realem Einsatz auf verschlüsseltem und zugriffsgeschütztem Speicher liegen. Vor einer Änderung:

1. Fall beenden und Dienst stoppen.
2. Bestehende Daten vollständig und nachvollziehbar übertragen.
3. Eigentümer und Rechte für den als `root` laufenden Dienst prüfen.
4. Pfad in `triage.env` ändern.
5. Dienst starten und Export, Manifest sowie Wiederherstellung testen.

Das bloße Ändern des Pfades verschiebt keine bestehenden Daten.

## Stichwortprofile und Dateitypen

Seit Alpha 44 werden beide unter **Einstellungen** außerhalb des Fallfensters verwaltet. Der Webdienst übernimmt vorhandene Profile nach `FORENSIC_TRIAGE_SETTINGS_ROOT/profiles` und bearbeitet dort die lokalen Kopien. Der Dateityp-Katalog liegt daneben in `filetypes.json`. Die tatsächliche Stichwortauswahl sowie der Katalogstand werden mit jedem neuen Scan gespeichert.

Die lokale Ablage bleibt bei Releasewechseln erhalten. Neue Programmstandards ersetzen keine eigenen Einstellungen automatisch. Bedienung, Migrationsgrenzen beim ersten Wechsel von einem älteren Updater und das Verhalten der CLI stehen in [Einstellungen](settings.md). Vorhandene Sichtungen werden durch Änderungen nicht umklassifiziert.

## Priorität

Explizite Kommandozeilenargumente wie `--port` überschreiben die Werte aus der Umgebung. Der systemd-Dienst verwendet normalerweise nur `triage.env`; manuelle Teststarts können Argumente verwenden.

## English summary

Local web settings are stored in root-only `/etc/forensic-triage/triage.env`. Pi hotspot settings and the Wi-Fi secret are kept separately in root-only `/etc/forensic-triage/pi-network.env`, so the web service does not receive the Wi-Fi password. Existing settings are generally retained, with documented path/update migrations and a forced loopback backend binding in Pi mode. Secrets must never be committed.
