# Installation und Aktualisierung / Installation and upgrade

Das Ziel ist eine wiederholbare Installation auf dem Raspberry Pi sowie auf einem Debian-basierten Testsystem. Der Pi ist das vorgesehene Feldgerät, bleibt aber bis zur praktischen Hardwareabnahme unvalidiert.

## Kurzfassung

### Raspberry Pi mit kurzzeitig öffentlichem Repository

Repository kurzzeitig auf öffentlich stellen und auf dem per Ethernet verbundenen Raspberry Pi einmal ausführen:

```bash
curl -fsSLo /tmp/triagebox-install.sh https://raw.githubusercontent.com/hnslng/forensic-triage/main/scripts/bootstrap_pi.sh && sudo bash /tmp/triagebox-install.sh
```

Der Bootstrap prüft Raspberry Pi OS/Debian, installiert Git, lädt das Repository nach `/opt/triagebox` und startet anschließend automatisch `install_debian.sh --pi`. Sobald der Befehl vollständig abgeschlossen ist, kann das Repository wieder privat gestellt werden. Die installierte Anwendung funktioniert danach ohne GitHub-Verbindung weiter. Für ein späteres Update über denselben Befehl muss das Repository erneut erreichbar sein oder der Pi einen eigenen Deploy-Key erhalten.

Das Herunterladen und Ausführen eines Root-Skripts setzt Vertrauen in die angegebene Quelle voraus. Deshalb wird die Datei zuerst sichtbar unter `/tmp/triagebox-install.sh` gespeichert und nicht unmittelbar in eine Shell-Pipe geleitet.

### Bereits vorhandener Quellcode

Sobald der Quellcode auf dem Scanner liegt:

```bash
cd /pfad/zu/forensic-triage
sudo ./scripts/install_debian.sh
```

Das Skript:

1. prüft Debian und den Projektordner,
2. installiert die benötigten Systempakete einschließlich Debian-`7zip` für die reine 7Z-/RAR-Verzeichnisauflistung,
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

Für den späteren Raspberry Pi gibt es zusätzlich einen ausdrücklich gewählten Pi-Modus:

```bash
sudo ./scripts/install_debian.sh --pi
```

Dieser Modus ist für Raspberry Pi OS Bookworm vorgesehen, muss über Ethernet oder direkt an der Konsole gestartet werden und verweigert die Umschaltung, wenn die laufende SSH-Verbindung über `wlan0` kommt.

## 1. Quellcode bereitstellen

### Empfohlen: privates Git-Checkout auf dem Scanner

Der Scanner erhält dafür einen eigenen, möglichst nur lesenden GitHub-Deploy-Key. Persönliche Tokens oder private Schlüssel anderer Rechner gehören nicht auf den Pi.

```bash
cd /home/triage
git clone git@github.com:hnslng/forensic-triage.git
cd forensic-triage
```

Keine privaten Schlüssel oder Zugriffstokens im Projektordner speichern.

### Alternative: freigegebenes Releasepaket übertragen

Wenn der Scanner keinen GitHub-Zugang erhalten soll, kann ein versioniertes `git archive` von einem Verwaltungsrechner übertragen werden. Das konkrete Verfahren ist von der Betriebsumgebung abhängig. Interne Entwicklungs- und Validierungsaufbauten sind bewusst von dieser Produktinstallation getrennt dokumentiert.

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

Vor echtem Einsatz insbesondere den verschlüsselten Fallpfad prüfen:

```bash
sudoedit /etc/forensic-triage/triage.env
sudo systemctl restart forensic-triage-web.service
```

Alle Werte und Sicherheitsregeln stehen in [configuration.md](configuration.md). Die Standardadresse ist `127.0.0.1`, der Standardport `8787`.

## 4. Oberfläche erreichen

Bei `127.0.0.1` ist die Oberfläche nur auf dem Scanner selbst erreichbar. Das ist für lokale Anzeige oder einen abgesicherten SSH-Tunnel geeignet.

Für den Raspberry Pi 3B+ bereitet der Pi-Modus einen privaten WPA2-Hotspot `TRIAGEBOX` als Hauptzugang vor. Der Laptop verbindet sich direkt mit diesem WLAN und öffnet anschließend:

```text
http://triagebox.local/
```

Die derzeitige Alpha-Vorlage verwendet absichtlich das einfache Entwicklungskennwort `triagebox123`. Es ist öffentlich bekannt, kein echtes Geheimnis und muss vor einem realen Einsatz in `/etc/forensic-triage/pi-network.env` geändert werden. Danach den Pi-Modus erneut ausführen oder die NetworkManager-Verbindung aktualisieren.

Der Pi-Modus erledigt automatisch:

- Hostname `triagebox` und mDNS/Avahi,
- 2,4-GHz-Hotspot über `wlan0`,
- WPA2/RSN mit CCMP,
- private Adresse `10.42.0.1/24` und DHCP über NetworkManager,
- Bindung des Python-Webdienstes ausschließlich an `127.0.0.1` sowie portfreien Zugriff über den lokalen Reverse-Proxy,
- Firewall-Regel gegen Weiterleitung vom Hotspot ins Ethernet/Internet,
- automatischen Hotspot-Start beim Booten.

Eine direkte Ethernet-Verbindung mit fester privater Adresse bleibt die geplante Rückfallebene. USB-Gadget-Netzwerk ist für den 3B+ nicht vorgesehen.

Die portfreie HTTP-Adresse ist für den privaten WPA2-Hotspot vorbereitet. Portloses HTTPS, das gemeinsame Gerätepasswort und feste Ethernet-Rückfalladressen folgen getrennt. Hotspot, mDNS, Reverse-Proxy und Firewall gelten bis zum Test auf dem echten Pi weiterhin als unvalidiert.

## 5. Aktualisieren

Der Pi prüft fünf Minuten nach dem Start und danach täglich auf den neuesten Git-Release-Tag. Ohne erreichbares Repository wird nichts verändert. Das Prüfen lädt keinen Code in die laufende Anwendung und installiert nichts.

Eine gefundene Version erscheint im Dashboard. Die Installation wird bewusst dort gestartet und ist gesperrt, solange ein Fall aktiv ist oder ein Scan läuft. Sie läuft getrennt ab: neuer Release-Checkout, Python-Abhängigkeiten und Tests, atomarer Wechsel auf die neue Version, Neustart. Startet die neue Version nicht, stellt das Skript automatisch den vorherigen Release wieder her.

Für Wartung ohne Dashboard bleibt möglich:

Nur ohne laufenden Scan und nach beendetem Fall:

```bash
sudo systemctl start forensic-triage-update@check.service
sudo systemctl start forensic-triage-update@install.service
```

Die bewusste Installation benötigt ein erreichbares Git-Repository und einen freigegebenen Git-Tag. Bei einer Installation aus einem Releasepaket zuerst den neuen freigegebenen Code übertragen und anschließend dasselbe Installationsskript erneut ausführen.

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

Bis diese Punkte praktisch validiert sind, ist die Pi-Installation vorbereitet, aber noch keine freigegebene Einsatzinstallation.

## English quick install

For a temporarily public repository, download `scripts/bootstrap_pi.sh` from the documented raw GitHub URL and run the saved file with `sudo`; it clones into `/opt/triagebox` and starts the Pi installer. Alternatively clone with a read-only deploy key. Run Pi setup from Ethernet or the local console. The development Wi-Fi password must be replaced before real use.
