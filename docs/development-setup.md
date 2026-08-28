# Generische Entwicklungsumgebung / Generic development setup

Dieses Dokument beschreibt ein neutrales Beispiel für die Entwicklung mit einem Verwaltungsrechner und einem getrennten Debian-Testsystem. Lokale Adressen, Benutzernamen und Schlüsselpfade gehören nicht in eine mögliche spätere Veröffentlichung.

## Beispielaufbau

- Quellcode und Git-Checkout: Verwaltungsrechner
- privates GitHub-Repository: `hnslng/forensic-triage`
- Testsystem: getrennte Debian-VM oder Raspberry Pi
- Webdienst in der VM: `127.0.0.1:8787`
- Zugriff vom Mac: SSH-Tunnel auf `http://127.0.0.1:8787/`

## Starter am Mac

`TRIAGE-BOX starten.command` ist ausschließlich eine private Hilfsdatei für den derzeitigen Mac-/VM-Testaufbau. Sie öffnet den lokalen SSH-Tunnel und anschließend die Weboberfläche. Die Datei enthält gerätespezifische Verbindungsangaben, wird von Git ignoriert und gehört nicht zur Raspberry-Pi-Produktinstallation. Eine öffentliche Beispielvorlage wird nicht mit dem Repository ausgeliefert.

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
