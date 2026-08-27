# Temporäre Entwicklungsumgebung / Temporary development setup

Dieses Dokument beschreibt ausschließlich die derzeitige Mac- und VM-Testumgebung. Sie ist **kein Bestandteil der späteren TRIAGE//BOX-Installation** und keine Vorgabe für den Raspberry Pi.

## Aktueller Aufbau

- Quellcode und Git-Checkout: Mac
- privates GitHub-Repository: `hnslng/forensic-triage`
- Testsystem: Debian-VM unter `10.0.1.105`
- Webdienst in der VM: `127.0.0.1:8787`
- Zugriff vom Mac: SSH-Tunnel auf `http://127.0.0.1:8787/`

Die VM enthält derzeit eine bereitgestellte Kopie ohne eigenen `.git`-Ordner. Der maßgebliche Git-Stand liegt am Mac und auf GitHub.

## Starter am Mac

`TRIAGE-BOX starten.command` prüft den lokalen Port, öffnet bei Bedarf den SSH-Tunnel und startet den Browser. Die Datei enthält nur Entwicklungswerte für Host und Schlüsselpfad.

Diese Datei wird für den späteren Pi-Betrieb voraussichtlich nicht benötigt. Bei direkter Ethernet-Verbindung öffnet der Laptop lediglich die Adresse des Pi im Browser.

## Manuelle Verbindung

```bash
ssh -N -L 8787:127.0.0.1:8787 \
  -i "$HOME/.ssh/forensic_triage_agent" \
  triage@10.0.1.105
```

## Code auf die VM übertragen

Aus dem lokalen Git-Checkout:

```bash
git archive --format=tar HEAD | ssh \
  -i "$HOME/.ssh/forensic_triage_agent" \
  triage@10.0.1.105 \
  'mkdir -p /home/triage/forensic-triage && tar -xf - -C /home/triage/forensic-triage'
```

Danach den Installer auf der VM erneut ausführen. Vorhandene Konfiguration und Fallordner bleiben erhalten.

## English summary

The Mac and Debian VM are temporary development infrastructure, not product requirements. The Mac holds the authoritative Git checkout and reaches the VM through an SSH tunnel. A future Pi deployment should use its own validated network and installation procedure.
