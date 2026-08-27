# Installation und Aktualisierung / Installation and upgrade

Diese Anleitung beschreibt die aktuelle Debian-VM. Sie ist zugleich die Grundlage für eine spätere Raspberry-Pi-Installation, die erst auf der realen Hardware validiert wird.

## 1. Voraussetzungen

Empfohlen:

- Debian 13 oder Raspberry Pi OS auf Debian-Basis
- Python 3.11 oder neuer
- The Sleuth Kit (`mmls`, `fsstat`, `fls`)
- `lsblk`, `blockdev`, `findmnt`, `mount`, `umount`, `udevadm` und `eject`
- lokaler Benutzer `triage`
- SSH-Zugang mit Schlüssel
- verschlüsselter, zugriffsgeschützter Speicher für reale Fallakten

Pakete installieren:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip sleuthkit util-linux udev eject
```

`exfatprogs` ist nur erforderlich, wenn autorisierte Testmedien mit exFAT erzeugt oder geprüft werden sollen:

```bash
sudo apt install -y exfatprogs
```

## 2. Quellcode bereitstellen

### Variante A: eigener Git-Checkout auf dem Scanner

Der öffentliche Git-Schlüssel des Scanner-Systems muss dafür als berechtigter, möglichst nur lesender Deploy-Key im privaten GitHub-Repository hinterlegt sein. Der SSH-Schlüssel für die Anmeldung **am** Scanner ist nicht automatisch ein GitHub-Schlüssel. Niemals einen privaten Schlüssel oder persönlichen Zugriffstoken in das Repository kopieren.

```bash
cd /home/triage
git clone git@github.com:hnslng/forensic-triage.git
cd forensic-triage
```

Für einen bereits vorhandenen Checkout:

```bash
cd /home/triage/forensic-triage
git pull --ff-only origin main
```

### Variante B: Bereitstellung vom Verwaltungs-Mac

Die aktuelle Referenz-VM verwendet diese Variante und enthält deshalb bewusst keinen `.git`-Ordner. Im lokalen Git-Checkout auf dem Mac ausführen:

```bash
git archive --format=tar HEAD | ssh \
  -i "$HOME/.ssh/forensic_triage_agent" \
  triage@10.0.1.105 \
  'mkdir -p /home/triage/forensic-triage && tar -xf - -C /home/triage/forensic-triage'
```

`git archive` überträgt nur versionierte Projektdateien. Die lokalen Verzeichnisse `.venv/`, `casefiles/` und `results/` werden dadurch weder übertragen noch gelöscht. Fallakten dürfen niemals mit einer pauschalen Lösch-/Synchronisationsoption überschrieben werden.

## 3. Python-Umgebung installieren

```bash
cd /home/triage/forensic-triage
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
```

Für Entwicklung und Tests:

```bash
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest
```

Version prüfen:

```bash
.venv/bin/forensic-triage --version
.venv/bin/forensic-triage-web --version
```

Für diesen Stand müssen beide Befehle `0.2.0a1` ausgeben.

## 4. Webdienst installieren

Die mitgelieferte Service-Datei erwartet den Checkout unter `/home/triage/forensic-triage` und startet den Scanner als `root`, weil Blockgeräte-Schreibschutz und Read-only-Mounts erhöhte Rechte erfordern.

```bash
sudo cp deploy/forensic-triage-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now forensic-triage-web.service
sudo systemctl status forensic-triage-web.service --no-pager
```

Der Dienst lauscht standardmäßig nur auf `127.0.0.1:8787`. Das ist für die VM beabsichtigt.

## 5. Löschpasswort ändern

Das Entwicklungskennwort `123` darf nicht im Einsatz bleiben. Lokale Service-Konfiguration anlegen:

```bash
sudo systemctl edit forensic-triage-web.service
```

Eintragen:

```ini
[Service]
Environment="FORENSIC_TRIAGE_DELETE_PASSWORD=HIER-EIN-LANGES-LOKALES-PASSWORT-EINTRAGEN"
```

Anschließend:

```bash
sudo systemctl daemon-reload
sudo systemctl restart forensic-triage-web.service
```

Die lokale Override-Datei und das Passwort dürfen nicht in Git gespeichert werden.

## 6. Verbindung vom Mac

Manuell:

```bash
ssh -N -L 8787:127.0.0.1:8787 \
  -i "$HOME/.ssh/forensic_triage_agent" \
  triage@10.0.1.105
```

Danach `http://127.0.0.1:8787/` öffnen. Alternativ kann auf dem eingerichteten Mac `TRIAGE-BOX starten.command` doppelt angeklickt werden. Bei geänderter VM-Adresse müssen dort `TRIAGE_HOST` und gegebenenfalls `TRIAGE_KEY` angepasst werden.

## 7. Aktualisierung

Nur bei beendetem Fall und ohne laufenden Scan aktualisieren:

Bei Variante A auf dem Scanner:

```bash
cd /home/triage/forensic-triage
git pull --ff-only origin main
.venv/bin/python -m pip install -e .
.venv/bin/python -m pytest
sudo systemctl restart forensic-triage-web.service
sudo systemctl is-active forensic-triage-web.service
```

Bei Variante B zuerst den oben beschriebenen `git archive`-Transfer vom Mac wiederholen und danach auf dem Scanner ausführen:

```bash
cd /home/triage/forensic-triage
.venv/bin/python -m pip install -e .
.venv/bin/python -m pytest
sudo systemctl restart forensic-triage-web.service
sudo systemctl is-active forensic-triage-web.service
```

Die Verzeichnisse `casefiles/` und `results/` nicht löschen, überschreiben oder in Git aufnehmen. Vor größeren Aktualisierungen ist eine lokale, verschlüsselte Sicherung der Fallakten vorzusehen.

## 8. Raspberry Pi

Die Software ist grundsätzlich ARM-kompatibel, wurde aber noch nicht auf dem vorgesehenen Raspberry Pi validiert. Vor Feldbetrieb sind mindestens zu prüfen:

- Betriebssystem und Paketnamen
- Stromversorgung mehrerer USB-Geräte beziehungsweise aktiver Hub
- Verhalten von USB-, CD- und DVD-Geräten
- Touch-/Kleinbildschirmdarstellung
- direkte Ethernet-Verbindung zum Laptop
- fester Link-Local-/Privat-IP-Bereich und Firewall
- Temperatur, Laufzeit und kontrolliertes Herunterfahren

Bis diese Prüfungen abgeschlossen und dokumentiert sind, ist die Debian-VM die maßgebliche Referenzumgebung.

## English quick install

Install Debian packages (`git`, Python, `sleuthkit`, `util-linux`, `udev`, `eject`), clone the private repository to `/home/triage/forensic-triage`, create `.venv`, install with `pip install -e .`, install the provided systemd unit, and replace the default deletion password through a local systemd override. Keep the service bound to localhost and access it through SSH. Do not deploy the Raspberry Pi build before hardware validation.
