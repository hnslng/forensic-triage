# Konfiguration / Configuration

## Grundsatz

Lokale Einstellungen gehören nicht in den Programmcode und nicht in Git. Das Installationsskript legt deshalb einmalig folgende Datei an:

```text
/etc/forensic-triage/triage.env
```

Sie gehört `root`, hat Dateimodus `0600` und wird bei einer erneuten Installation nicht überschrieben.

Bearbeiten:

```bash
sudoedit /etc/forensic-triage/triage.env
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

Beispiel:

```ini
FORENSIC_TRIAGE_WEB_HOST=127.0.0.1
FORENSIC_TRIAGE_WEB_PORT=8787
FORENSIC_TRIAGE_RESULTS_ROOT=/srv/triage/results
FORENSIC_TRIAGE_CASEFILES_ROOT=/srv/triage/casefiles
FORENSIC_TRIAGE_WEB_ROOT=/opt/triage-box/web
FORENSIC_TRIAGE_PROFILE=/opt/triage-box/profiles/default.yaml
```

Für die Fallentfernung gibt es bewusst kein Passwort. Der Dialog verlangt zwei eindeutige Bedienhandlungen für den konkret genannten Fall. Entfernen verschiebt die Fallakte nur in den wiederherstellbaren internen Papierkorb. Das ist eine Fehlbedienungssperre, aber keine Benutzer- oder Rechteverwaltung.

## Port und Netzwerk

`127.0.0.1` ist die sichere Voreinstellung für Entwicklung oder Zugriff über SSH. Der Raspberry Pi 3B+ soll später primär einen privaten WLAN-Hotspot `TRIAGEBOX` bereitstellen; Ethernet bleibt die Rückfallebene. Eine andere Bindeadresse darf erst nach festgelegten privaten IP-Adressen und Firewallregeln aktiviert werden. `0.0.0.0` würde auf allen Netzwerkschnittstellen lauschen und soll nicht unüberlegt verwendet werden.

Nach einem Portwechsel muss auch die aufrufende Adresse angepasst werden. Bei Port `8877` wäre das beispielsweise `http://127.0.0.1:8877/`.

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

Local settings are stored in the root-only `/etc/forensic-triage/triage.env` file and are preserved on reinstall. It controls host, port, result and case roots, and the default profile. Keep localhost for SSH-based access, store real case data on encrypted storage, and never commit the configuration file.
