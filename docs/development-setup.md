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

Diese Datei wird für den späteren Pi-Betrieb voraussichtlich nicht benötigt. Bei direkter Ethernet-Verbindung öffnet der Laptop lediglich die Adresse des Pi im Browser.

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

Danach den Installer auf der VM erneut ausführen. Vorhandene Konfiguration und Fallordner bleiben erhalten.

## English summary

A workstation and Debian VM can be used as temporary development infrastructure. Local hostnames, addresses, usernames, and key paths must remain outside any later public release. A Pi deployment should use its own validated network and installation procedure.
