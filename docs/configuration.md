# Konfiguration / Configuration

## Grundsatz

Lokale Einstellungen gehören nicht in den Programmcode und nicht in Git. Das Installationsskript legt deshalb einmalig folgende Datei an:

```text
/etc/forensic-triage/triage.env
```

Sie gehört `root`, hat Dateimodus `0600` und wird bei einer erneuten Installation nicht überschrieben.

Der optionale Pi-Modus legt Netzwerkgeheimnisse bewusst getrennt vom Webdienst ab:

```text
/etc/forensic-triage/pi-network.env
```

Auch diese Datei gehört `root`, hat Modus `0600` und wird bei Aktualisierungen nicht überschrieben. Dadurch erhält der Webprozess das WLAN-Kennwort nicht als eigene Umgebungsvariable.

Bearbeiten:

```bash
sudoedit /etc/forensic-triage/triage.env
sudoedit /etc/forensic-triage/pi-network.env  # nur im Pi-Modus
sudo systemctl restart forensic-triage-web.service
```

## Einstellungen

| Name | Standard | Bedeutung |
|---|---|---|
| `FORENSIC_TRIAGE_WEB_HOST` | `127.0.0.1` | Netzwerkadresse des Webdienstes |
| `FORENSIC_TRIAGE_WEB_PORT` | `8787` | TCP-Port der Bedienoberfläche |
| `FORENSIC_TRIAGE_RESULTS_ROOT` | `<Projekt>/results` | technische Scannergebnisse |
| `FORENSIC_TRIAGE_CASEFILES_ROOT` | `<Projekt>/casefiles` | dauerhafte lokale Fallakten |
| `FORENSIC_TRIAGE_WEB_ROOT` | `<Projekt>/web` | statische Bedienoberfläche; normalerweise unverändert |
| `FORENSIC_TRIAGE_PROFILE` | `<Projekt>/profiles/default.yaml` | Start-/Kompatibilitätsprofil |
| `FORENSIC_TRIAGE_SCAN_TIMEOUT_SECONDS` | `180` | maximale Gesamtdauer einer Grobsichtung in Sekunden |
| `FORENSIC_TRIAGE_COMMAND_TIMEOUT_SECONDS` | `15` | maximale Dauer eines einzelnen Gerätebefehls in Sekunden |
| `FORENSIC_TRIAGE_DEVICE_DISCOVERY_TIMEOUT_SECONDS` | `2` | Zeitlimit für `lsblk` bei der Geräteerkennung; danach höchstens 0,5 Sekunden Abbruchnachlauf |
| `FORENSIC_TRIAGE_DEVICE_DISCOVERY_BACKOFF_SECONDS` | `10` | Pause vor einem erneuten Dashboard-Geräteabruf nach einem Fehler |
| `FORENSIC_TRIAGE_CONTAINER_INDEX_SECONDS` | `3` | gemeinsames maximales Zusatzzeitbudget für ZIP-/ISO-/7Z-/RAR-Verzeichnisse je Medium |
| `FORENSIC_TRIAGE_CONTAINER_MAX_FILES` | `50` | höchstens katalogisierte ZIP-/ISO-/7Z-/RAR-Dateien je Medium |
| `FORENSIC_TRIAGE_CONTAINER_MAX_ENTRIES` | `2000` | höchstens Einträge je Container |
| `FORENSIC_TRIAGE_CONTAINER_MAX_TOTAL_ENTRIES` | `10000` | höchstens interne Einträge insgesamt je Medium |
| `FORENSIC_TRIAGE_UPDATE_ENABLED` | `true` | aktiviert nur die tägliche Update-Prüfung, niemals eine automatische Installation |
| `FORENSIC_TRIAGE_UPDATE_REMOTE` | `origin` | Git-Remote für die Release-Prüfung |
| `FORENSIC_TRIAGE_UPDATE_STATE_FILE` | `/var/lib/forensic-triage/update-status.env` | lokaler, root-geschützter Update-Status für das Dashboard |

Beispiel:

```ini
FORENSIC_TRIAGE_WEB_HOST=127.0.0.1
FORENSIC_TRIAGE_WEB_PORT=8787
FORENSIC_TRIAGE_RESULTS_ROOT=/srv/triage/results
FORENSIC_TRIAGE_CASEFILES_ROOT=/srv/triage/casefiles
FORENSIC_TRIAGE_WEB_ROOT=/opt/triage-box/web
FORENSIC_TRIAGE_PROFILE=/opt/triage-box/profiles/default.yaml
FORENSIC_TRIAGE_SCAN_TIMEOUT_SECONDS=180
FORENSIC_TRIAGE_COMMAND_TIMEOUT_SECONDS=15
FORENSIC_TRIAGE_CONTAINER_INDEX_SECONDS=3
FORENSIC_TRIAGE_CONTAINER_MAX_FILES=50
FORENSIC_TRIAGE_CONTAINER_MAX_ENTRIES=2000
FORENSIC_TRIAGE_CONTAINER_MAX_TOTAL_ENTRIES=10000
```

## Beschädigte oder sehr langsame Medien

Jede Grobsichtung läuft in einem eigenen Prozess und – unter Linux – in einem privaten Mount-Namensraum. Ein vollständiger Scan wird standardmäßig nach 180 Sekunden beendet; einzelne Gerätebefehle bereits nach 15 Sekunden. Damit wartet der Webdienst nicht unbegrenzt auf den Scanner. Ein blockierter Kernel, USB-Bus oder Systemdatenträger kann trotzdem den gesamten Rechner betreffen; siehe [forensische Sicherheitsgrenzen](forensic-safety.md#beschädigte-medien).

Auch die Geräteerkennung im Dashboard ist begrenzt: `lsblk` erhält standardmäßig zwei Sekunden, danach folgt höchstens eine halbe Sekunde Abbruchnachlauf. Bei einem Fehler pausieren automatische Statusabfragen und manuelles Aktualisieren die erneute Geräteerkennung für zehn Sekunden. Gleichzeitige Dashboard-Abfragen warten nicht hinter einem laufenden Geräteabruf. Fallstatus und Updateinformationen können weiter geliefert werden, solange deren Speicher erreichbar ist. Die Oberfläche zeigt den letzten bekannten Gerätebestand mit unbekanntem Verbindungsstatus; neue Scans und Auswerfen sind dort bis zur erfolgreichen Erkennung gesperrt. Ein fehlgeschlagener Abruf gilt ausdrücklich nicht als Nachweis, dass ein quarantänisiertes Medium abgezogen wurde.

Die beiden zusätzlichen Konfigurationswerte gelten durch Programmvorgaben auch bei bestehenden Installationen; die lokale `triage.env` muss dafür nicht überschrieben werden. Die automatische Sichtung geeigneter CD/DVD-Medien bleibt grundsätzlich vorgesehen. Für Tests mit einem auffällig instabilen Laufwerk Auto-Scan vorher ausschalten und eine eigene Stromversorgung verwenden.

Nach einer Zeitüberschreitung wird nur der betroffene Gerätepfad gesperrt und als `MEDIUM ANTWORTET NICHT` angezeigt. Die Sperre verschwindet erst, nachdem das Medium physisch getrennt wurde und die Oberfläche den Offline-Zustand erkannt hat. Das verhindert automatische Endloswiederholungen. Die Zeitlimits sind bewusst konfigurierbar, dürfen aber erst nach praktischen Tests mit der Zielhardware erhöht werden.

Der ZIP-/ISO-/7Z-/RAR-Schnellindex hat zusätzlich ein gemeinsames Standardbudget von drei Sekunden je Medium. Mengenlimits schützen gegen übergroße Verzeichnisse und sogenannte Archivbomben; da niemals dekomprimiert oder extrahiert wird, werden angegebene entpackte Größen nur als Metadaten behandelt. Ein erreichtes Limit erzeugt einen unvollständigen, sichtbar gekennzeichneten Index und keinen endlosen Tiefenscan. Verschachtelte Container werden nicht geöffnet.

Für die Fallentfernung gibt es bewusst kein Passwort. Der Dialog verlangt zwei eindeutige Bedienhandlungen für den konkret genannten Fall. Entfernen verschiebt die Fallakte nur in den wiederherstellbaren internen Papierkorb. Das ist eine Fehlbedienungssperre, aber keine Benutzer- oder Rechteverwaltung.

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

Das Entwicklungskennwort ist absichtlich leicht zu merken, aber allgemein bekannt und daher **nicht für echten Einsatz geeignet**. Ein späteres starkes Kennwort kann in Anführungszeichen als shell-kompatibler `KEY=VALUE`-Eintrag hinterlegt werden. Anschließend aus dem Projektordner erneut `sudo ./scripts/install_debian.sh --pi` ausführen.

## Port und Netzwerk

`127.0.0.1` ist die sichere Voreinstellung für Entwicklung oder Zugriff über SSH. Der Raspberry Pi 3B+ soll später primär einen privaten WLAN-Hotspot `TRIAGEBOX` bereitstellen; Ethernet bleibt die Rückfallebene. Eine andere Bindeadresse darf erst nach festgelegten privaten IP-Adressen und Firewallregeln aktiviert werden. `0.0.0.0` würde auf allen Netzwerkschnittstellen lauschen und soll nicht unüberlegt verwendet werden.

Nach einem Portwechsel muss auch die aufrufende Adresse angepasst werden. Bei Port `8877` wäre das beispielsweise `http://127.0.0.1:8877/`.

Auf einem Pi wird dieser interne Port durch nginx als portfreie Adresse `http://triagebox.local/` veröffentlicht. Zugelassen sind ausschließlich Loopback sowie private IPv4-Netze (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`). Damit funktioniert dieselbe Adresse im TRIAGEBOX-Hotspot und über Ethernet im normalen privaten LAN; aus öffentlichen Netzen wird der Zugriff abgewiesen. Der Python-Dienst selbst bleibt auf `127.0.0.1`. HTTP ist eine Bedienvereinfachung, aber noch kein Ersatz für das in `security-concept.md` geplante HTTPS und die gemeinsame Geräteentsperrung.

## Updates

Beim Booten mit Verzögerung und anschließend täglich startet ein `systemd`-Timer ausschließlich die Prüfung auf einen neuen Git-Release-Tag. Das Update wird niemals selbstständig installiert. Das Dashboard zeigt den Status und kann die Installation bewusst anfordern. Serverseitig wird sie verweigert, solange ein Fall aktiv oder ein Scan aktiv ist.

Die Installation erzeugt einen separaten Release-Checkout, erstellt die Python-Umgebung und führt die Tests aus. Erst danach ersetzt ein atomarer Symlink die laufende Version. Falls der neue Dienst nicht startet, zeigt der Symlink wieder auf die vorherige Version. Fallakten, Ergebnisse und die lokale Konfiguration liegen außerhalb dieser Release-Ordner und bleiben unberührt.

## Speicherpfade

Der Fallpfad muss vor realem Einsatz auf verschlüsseltem und zugriffsgeschütztem Speicher liegen. Vor einer Änderung:

1. Fall beenden und Dienst stoppen.
2. Bestehende Daten vollständig und nachvollziehbar übertragen.
3. Eigentümer und Rechte für den als `root` laufenden Dienst prüfen.
4. Pfad in `triage.env` ändern.
5. Dienst starten und Export, Manifest sowie Wiederherstellung testen.

Das bloße Ändern des Pfades verschiebt keine bestehenden Daten.

## Stichwortprofile

Profile werden im Dashboard bearbeitet und als YAML-Dateien im Profilordner gespeichert. Sie sind keine geheimen Einstellungen und können versioniert werden, sofern sie keine echten Fallinformationen enthalten. Die lokale Auswahl für einen Scan wird mit dem Ergebnis protokolliert.

## Priorität

Explizite Kommandozeilenargumente wie `--port` überschreiben die Werte aus der Umgebung. Der systemd-Dienst verwendet normalerweise nur `triage.env`; manuelle Teststarts können Argumente verwenden.

## English summary

Local web settings are stored in root-only `/etc/forensic-triage/triage.env`. Pi hotspot settings and the Wi-Fi secret are kept separately in root-only `/etc/forensic-triage/pi-network.env`, so the web service does not receive the Wi-Fi password. Both files are preserved on reinstall and must never be committed.
