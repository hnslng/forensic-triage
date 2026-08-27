# Installation und Aktualisierung / Installation and upgrade

Das Ziel ist eine wiederholbare Installation auf einem Debian-basierten Scanner. Die aktuelle Debian-VM ist die Referenz; der Raspberry Pi wird erst auf der realen Hardware freigegeben.

## Kurzfassung

Sobald der Quellcode auf dem Scanner liegt:

```bash
cd /pfad/zu/forensic-triage
sudo ./scripts/install_debian.sh
```

Das Skript:

1. prüft Debian und den Projektordner,
2. installiert die benötigten Systempakete,
3. erstellt beziehungsweise aktualisiert `.venv`,
4. installiert TRIAGE//BOX,
5. führt alle automatisierten Tests aus,
6. legt die lokale Konfiguration nur beim ersten Lauf an,
7. installiert und startet den systemd-Dienst.

Es ist idempotent: Eine erneute Ausführung aktualisiert Programm und Dienst, überschreibt aber weder `/etc/forensic-triage/triage.env` noch `casefiles/` oder `results/`.

Nur Voraussetzungen prüfen, ohne etwas zu installieren:

```bash
sudo ./scripts/install_debian.sh --check
```

## 1. Quellcode bereitstellen

### Empfohlen: öffentliches Git-Checkout auf dem Scanner

Für das öffentliche Repository ist zum Lesen kein GitHub-Konto, Token oder Deploy-Key erforderlich.

```bash
cd /home/triage
git clone https://github.com/hnslng/forensic-triage.git
cd forensic-triage
```

Keine privaten Schlüssel oder Zugriffstokens im Projektordner speichern.

### Alternative: freigegebenes Releasepaket übertragen

Wenn der Scanner keinen GitHub-Zugang erhalten soll, kann ein versioniertes `git archive` von einem Verwaltungsrechner übertragen werden. Das konkrete Verfahren ist von der Betriebsumgebung abhängig. Die derzeitige Mac-/VM-Testvariante ist getrennt in [development-setup.md](development-setup.md) dokumentiert.

## 2. Installation ausführen

```bash
cd /home/triage/forensic-triage
sudo ./scripts/install_debian.sh
```

Danach prüfen:

```bash
systemctl is-active forensic-triage-web.service
/home/triage/forensic-triage/.venv/bin/forensic-triage-web --version
```

## 3. Konfiguration anpassen

Die Installation legt beim ersten Lauf an:

```text
/etc/forensic-triage/triage.env
```

Der Installer erzeugt beim ersten Lauf ein zufälliges Löschpasswort in der lokalen Konfiguration. Vor echtem Einsatz mindestens dieses Passwort und den verschlüsselten Fallpfad prüfen:

```bash
sudoedit /etc/forensic-triage/triage.env
sudo systemctl restart forensic-triage-web.service
```

Alle Werte und Sicherheitsregeln stehen in [configuration.md](configuration.md). Die Standardadresse ist `127.0.0.1`, der Standardport `8787`.

## 4. Oberfläche erreichen

Bei `127.0.0.1` ist die Oberfläche nur auf dem Scanner selbst erreichbar. Das ist für lokale Anzeige oder einen abgesicherten SSH-Tunnel geeignet.

Für den Raspberry Pi 3B+ ist ein privater, passwortgeschützter WLAN-Hotspot `TRIAGEBOX` als Hauptzugang vorgesehen. Der Laptop verbindet sich direkt mit diesem WLAN und öffnet anschließend `http://triagebox.local/`. Eine direkte Ethernet-Verbindung mit fester privater Adresse bleibt die robuste Rückfallebene. USB-Gadget-Netzwerk ist für den 3B+ nicht vorgesehen.

Hostname, mDNS/Avahi, Standardport 80, feste Rückfalladressen und Firewall werden erst auf der realen Hardware eingerichtet und gemeinsam validiert. Die Konfiguration darf die Oberfläche nicht versehentlich in anderen WLANs oder im Internet freigeben.

## 5. Aktualisieren

Nur ohne laufenden Scan und nach beendetem Fall:

```bash
cd /home/triage/forensic-triage
git pull --ff-only origin main
sudo ./scripts/install_debian.sh
```

Bei einer Installation aus einem Releasepaket zuerst den neuen freigegebenen Code übertragen und anschließend dasselbe Installationsskript erneut ausführen.

Vor größeren Aktualisierungen ist eine verschlüsselte Sicherung der Fallakten vorzusehen. Das Installationsskript verschiebt keine bestehenden Speicherpfade und löscht keine Fallakten.

## 6. Manuelle Diagnose

```bash
sudo systemctl status forensic-triage-web.service --no-pager
sudo journalctl -u forensic-triage-web.service -n 100 --no-pager
sudo ./scripts/install_debian.sh --check
```

Versionen:

```bash
.venv/bin/forensic-triage --version
.venv/bin/forensic-triage-web --version
```

## 7. Raspberry Pi – vor Freigabe prüfen

- Betriebssystem und Paketverfügbarkeit
- aktiver USB-Hub und ausreichende Stromversorgung
- mehrere USB-Geräte gleichzeitig
- reales CD/DVD-Laufwerk
- direkter Ethernet-Zugriff und Firewall
- Touch-/Kleinbildschirm
- kontrolliertes Herunterfahren und Stromverlust
- Temperatur und Dauerlast

Bis diese Punkte praktisch validiert sind, bleibt die Debian-VM die technische Referenz und nicht das spätere Einsatzgerät.

## English quick install

Clone the public repository over HTTPS or place a trusted release bundle on a Debian-based scanner, then run `sudo ./scripts/install_debian.sh`. The idempotent installer installs packages, creates the virtual environment, runs tests, installs the systemd service, and creates `/etc/forensic-triage/triage.env` with a random deletion password if it does not exist. Edit that root-only file to change host, port, storage roots, profile, and deletion password.
