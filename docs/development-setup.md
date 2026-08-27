# Generische Entwicklungsumgebung / Generic development setup

Dieses Dokument beschreibt ein neutrales Beispiel für die Entwicklung mit einem Verwaltungsrechner und einem getrennten Debian-Testsystem. Lokale Adressen, Benutzernamen und Schlüsselpfade gehören nicht in Git.

## Beispielaufbau

- Quellcode und Git-Checkout: Verwaltungsrechner
- öffentliches GitHub-Repository: `hnslng/forensic-triage`
- Testsystem: getrennte Debian-VM oder Raspberry Pi
- Webdienst in der VM: `127.0.0.1:8787`
- Zugriff vom Mac: SSH-Tunnel auf `http://127.0.0.1:8787/`

## Starter am Mac

`TRIAGE-BOX starten.command.example` ist eine neutrale Vorlage. Sie wird lokal als `TRIAGE-BOX starten.command` kopiert und dort mit Host und Schlüsselpfad ergänzt. Die persönliche Datei wird von Git ignoriert.

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

A workstation and Debian VM can be used as temporary development infrastructure. Local hostnames, addresses, usernames, and key paths must remain outside the public repository. A Pi deployment should use its own validated network and installation procedure.
