# Interne generische Entwicklungsumgebung / Internal generic development setup

Dieses Dokument ist kein Bestandteil der Bedienung oder Pi-Installation. Es beschreibt ausschließlich ein neutrales Beispiel für reproduzierbare Entwicklung mit einem Verwaltungsrechner und einem getrennten Debian-Testsystem. Lokale Adressen, Benutzernamen und Schlüsselpfade gehören nicht in eine Veröffentlichung.

## Beispielaufbau

- Quellcode und Git-Checkout: Verwaltungsrechner
- privates oder kontrolliert veröffentlichtes Git-Repository
- Testsystem: getrennte Debian-VM oder Raspberry Pi
- Webdienst in der VM: `127.0.0.1:8787`
- Zugriff vom Verwaltungsrechner: SSH-Tunnel auf `http://127.0.0.1:8787/`

## Lokaler Entwicklungsstarter

`TRIAGE-BOX starten.command` ist ausschließlich eine private Hilfsdatei eines Entwicklungsrechners. Sie enthält gerätespezifische Verbindungsangaben, wird von Git ignoriert und gehört nicht zur Raspberry-Pi-Produktinstallation. Eine öffentliche Beispielvorlage wird nicht ausgeliefert.

Diese Datei wird für den aktuellen Pi-Betrieb nicht benötigt. Im Hotspot oder gemeinsamen Router-LAN öffnet der Laptop `http://triagebox.local/`. Eine direkte Ethernet-Verbindung ohne Router ist noch separat zu konfigurieren.

## Manuelle Verbindung

```bash
ssh -N -L 8787:127.0.0.1:8787 \
  -i "$HOME/.ssh/forensic_triage_agent" \
  triage@triagebox.local
```

## Code auf die VM übertragen

Aus dem lokalen Git-Checkout:

```bash
git archive --format=tar HEAD | ssh \
  -i "$HOME/.ssh/forensic_triage_agent" \
  triage@triagebox.local \
  'mkdir -p /home/triage/forensic-triage && tar -xf - -C /home/triage/forensic-triage'
```

Nur für einen bewusst getrennten Entwicklungsstand verwenden, nicht zum Überschreiben einer laufenden Pi-Releaseinstallation. Danach den Installer auf dem Testsystem erneut ausführen; seine Konfigurationsmigrationen sind in [Installation](installation.md) beschrieben. Ein gewöhnliches `git archive` enthält keine Git-Historie und unterstützt deshalb nicht den Git-basierten Web-Updater. Für freigegebene Offline-Updates gibt es stattdessen das signierte [`.tbu`-Verfahren](offline-updates.md).

## English summary

A workstation and Debian VM can be used as temporary development infrastructure. Local hostnames, addresses, usernames, and key paths must remain outside any later public release. A Pi deployment should use its own validated network and installation procedure.
