# Installation und Aktualisierung / Installation and upgrade

Das Ziel ist eine wiederholbare Installation auf dem Raspberry Pi sowie auf einem Debian-basierten Testsystem. Der Pi 3B+ läuft bereits als Testgerät; vor Alpha 44 wurden Installation, Updates und mehrere USB-Sichtungen praktisch verwendet. Der Alpha-44-Praxistest, systematische Fehler-/Wiederherstellungstests und die Einsatzfreigabe stehen aus. Den Nachweisstand beschreibt [Projektstand](project-status.md).

## Kurzfassung

### Raspberry Pi mit kurzzeitig öffentlichem Repository

Repository kurzzeitig auf öffentlich stellen und auf dem per Ethernet verbundenen Raspberry Pi einmal ausführen:

```bash
curl -fsSLo /tmp/triagebox-install.sh https://raw.githubusercontent.com/hnslng/forensic-triage/main/scripts/bootstrap_pi.sh && sudo bash /tmp/triagebox-install.sh
```

Der Bootstrap prüft Raspberry Pi OS/Debian, installiert Git, lädt das Repository nach `/opt/triagebox` und startet anschließend automatisch `install_debian.sh --pi`. Sobald der Befehl vollständig abgeschlossen ist, kann das Repository wieder privat gestellt werden. Die installierte Anwendung funktioniert danach ohne GitHub-Verbindung weiter. Für spätere Updates muss das Repository für den als root laufenden Update-Dienst erreichbar sein oder der Pi einen eigenen Deploy-Key erhalten. Für reguläre Updates den Web-Updater verwenden; erneuter Bootstrap ist eine bewusste Neu-/Wartungsinstallation und kann das Git-Remote wieder auf die Bootstrap-Adresse setzen.

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
5. führt die Python-Tests aus (Browserprüfungen laufen separat auf dem Entwicklungsrechner),
6. legt die lokale Konfiguration nur beim ersten Lauf an,
7. installiert und startet Webdienst, nginx und Update-Prüftimer; der Pi-Modus richtet zusätzlich das Netzwerk ein.

Eine erneute Ausführung aktualisiert Programm und Dienste und erhält Fall-/Ergebnisordner. Die Konfiguration wird nicht pauschal ersetzt: passende alte Web-/Profilpfade werden migriert und fehlende Updateparameter ergänzt. `--pi` setzt den Backend-Host auf `127.0.0.1`. Vor einer Wartungsinstallation Fall und Scans beenden; sie ersetzt nicht den geprüften Updateablauf.

Nur Voraussetzungen prüfen, ohne etwas zu installieren:

```bash
sudo ./scripts/install_debian.sh --check
```

Für den Raspberry Pi gibt es zusätzlich einen ausdrücklich gewählten Pi-Modus:

```bash
sudo ./scripts/install_debian.sh --pi
```

Der Installer prüft die Debian-Familie, keine bestimmte OS-Releaseversion. Raspberry Pi OS Lite/Debian wird im Pi-Testbetrieb verwendet; eine vollständige Versionsmatrix und reproduzierbare Neuinstallation stehen aus. Den Pi-Modus über Ethernet oder direkt an der Konsole starten: Er verweigert die Umschaltung, wenn die erkannte SSH-Verbindung über `wlan0` kommt. Der Hotspot ersetzt die WLAN-Clientverbindung zum Router.

## 1. Quellcode bereitstellen

### Empfohlen: privates Git-Checkout auf dem Scanner

Der Scanner erhält dafür einen eigenen, möglichst nur lesenden GitHub-Deploy-Key. Persönliche Tokens oder private Schlüssel anderer Rechner gehören nicht auf den Pi.

```bash
cd /home/triage
git clone git@github.com:hnslng/forensic-triage.git
cd forensic-triage
```

Keine privaten Schlüssel oder Zugriffstokens im Projektordner speichern. Der per systemd gestartete Updater läuft als **root**. Ein erfolgreicher Git-Zugriff nur als Benutzer `triage` reicht deshalb nicht: Git-Remote, Hostschlüsselvertrauen und nur lesender Deploy-Key müssen auch im Kontext des Update-Dienstes passen. Der Installer richtet diese GitHub-Berechtigung nicht automatisch ein.

Nach entsprechender Einrichtung beim Bootstrap-Pfad rein lesend prüfen:

```bash
sudo -H git -C /opt/triagebox-current ls-remote origin HEAD
```

Bei einem anderen Installationspfad dessen konfigurierten Laufzeitlink verwenden. Meldet Git `could not read Username for 'https://github.com'`, benötigt der private HTTPS-Zugriff eine Authentifizierung; für den vorgesehenen Deploy-Key muss das Remote auf SSH zeigen. Das WLAN-Kennwort und der SSH-Zugang zum Pi sind unabhängig vom GitHub-Zugriff.

### Alternative: freigegebenes Releasepaket übertragen

Wenn der Scanner keinen GitHub-Zugang erhalten soll, kann ein versioniertes `git archive` von einem Verwaltungsrechner übertragen werden. Das konkrete Verfahren ist von der Betriebsumgebung abhängig. Ein solches Paket enthält kein `.git`; der tagbasierte Web-Updater funktioniert damit nicht. Aktualisierungen müssen dann als neue Pakete bereitgestellt werden. Interne Entwicklungs- und Validierungsaufbauten sind von dieser Produktinstallation getrennt dokumentiert.

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

Änderungen nur nach beendetem Fall und abgeschlossenen Scans vornehmen. Der Installer aktiviert keine Speicherverschlüsselung; vor echtem Einsatz muss diese separat eingerichtet werden. Konfiguration bearbeiten:

```bash
sudoedit /etc/forensic-triage/triage.env
sudo systemctl restart forensic-triage-web.service
```

Alle Werte stehen in [configuration.md](configuration.md). `127.0.0.1:8787` ist die interne Python-Adresse. nginx veröffentlicht die Oberfläche auf Port 80; nach Änderung des internen Ports muss auch sein Upstream angepasst werden.

Ab Alpha 44 verwaltet `FORENSIC_TRIAGE_SETTINGS_ROOT` die lokale Profil- und Dateityp-Ablage. Der Webdienst übernimmt vorhandene Profile beim Start; spätere Updater übernehmen Profile aus dem laufenden Release vor dem Umschalten. Vor dem ersten Wechsel von älteren Updatern eigene Profile separat sichern, insbesondere nur in bisherigen Release-Verzeichnissen vorhandene Dateien. Details und Grenzen: [Einstellungen](settings.md#lokale-ablage-und-updates).

## 4. Oberfläche erreichen

`127.0.0.1` bezeichnet immer den Rechner, auf dem der Browser läuft. Der Python-Dienst ist so nur lokal erreichbar; der Installer stellt zusätzlich nginx bereit, der die Oberfläche im privaten Netz veröffentlicht, auch ohne `--pi`.

Für den Raspberry Pi 3B+ richtet der Pi-Modus einen privaten WPA2-Hotspot `TRIAGEBOX` als Hauptzugang ein. Der Laptop verbindet sich direkt mit diesem WLAN und öffnet anschließend:

```text
http://triagebox.local/
```

Ist der Pi gleichzeitig per Ethernet mit demselben privaten LAN wie der Laptop verbunden, funktioniert dieselbe Adresse ohne Wechsel in den Hotspot. Falls mDNS nicht aufgelöst wird, kann ersatzweise die von Router beziehungsweise FRITZ!Box vergebene LAN-IP verwendet werden, ohne Portzusatz. Diese LAN-Adresse ist standortabhängig. Im TRIAGEBOX-Hotspot ist bei unveränderter Konfiguration auch `http://10.42.0.1/` erreichbar.

Die derzeitige Alpha-Vorlage verwendet absichtlich das einfache Entwicklungskennwort `triagebox123`. Es ist öffentlich bekannt, kein echtes Geheimnis und muss vor einem realen Einsatz in `/etc/forensic-triage/pi-network.env` geändert werden. Danach die Netzwerk-Konfiguration über Ethernet oder Konsole anwenden; siehe [Konfiguration](configuration.md#pi-netzwerk). Ein bloßer Neustart des Webdienstes ändert das NetworkManager-WLAN-Kennwort nicht.

Der Pi-Modus erledigt automatisch:

- Hostname `triagebox` und mDNS/Avahi,
- 2,4-GHz-Hotspot über `wlan0`,
- WPA2/RSN mit CCMP,
- private Adresse `10.42.0.1/24` und DHCP über NetworkManager,
- Bindung des Python-Webdienstes ausschließlich an `127.0.0.1` sowie portfreien Zugriff über den lokalen Reverse-Proxy,
- Firewall-Regel gegen Weiterleitung vom Hotspot ins Ethernet/Internet,
- automatischen Hotspot-Start beim Booten.

Eine direkte Ethernet-Verbindung mit fester privater Adresse bleibt die geplante Rückfallebene. USB-Gadget-Netzwerk ist für den 3B+ nicht vorgesehen.

Die portfreie HTTP-Adresse wurde auf dem Test-Pi bereits erfolgreich verwendet. Portloses HTTPS, das gemeinsame Gerätepasswort und eine feste Ethernet-Rückfalladresse folgen getrennt. Hotspot, mDNS, Reverse-Proxy und Firewall müssen vor einem echten Einsatz weiter validiert werden.

## 5. Aktualisieren

Der Pi prüft fünf Minuten nach dem Start und danach täglich auf den neuesten Git-Release-Tag. Ohne erreichbares Repository wird nichts verändert. Das Prüfen lädt keinen Code in die laufende Anwendung und installiert nichts.

Eine gefundene Version erscheint im Dashboard. Die Installation wird bewusst dort gestartet und ist gesperrt, solange ein Fall aktiv ist oder ein Scan läuft. Seit Alpha 43 kann der Fall direkt im Updatefenster beendet werden; Installation bleibt eine separate Aktion. Die Vorbereitung erstellt einen neuen Release-Checkout, installiert Python-Abhängigkeiten und führt Python-Tests aus. Anschließend wird der Code-Laufzeitlink atomar gewechselt und der Dienst neu gestartet.

**Der Rückwechsel ist noch begrenzt:** Dienst- und nginx-Vorlagen werden bereits vor dem Linkwechsel installiert. Nach dem Neustart prüft das Skript den Dienststatus und enthält einen Rückwechselpfad für den Code. Ein fehlgeschlagener Neustartbefehl kann das Skript aber schon davor beenden; Vorlagen, Pakete und andere Änderungen werden nicht vollständig zurückgesetzt. Das ist keine bestätigte Stromausfallsicherheit. Fehlerbehandlung, Wiederaufnahme und vollständige Wiederherstellung sind offene Tests und Entwicklungsaufgaben.

Für Wartung ohne Dashboard bleibt möglich:

Nur ohne laufenden Scan und nach beendetem Fall. Der direkte systemd-Aufruf durch den Administrator umgeht die Fall-/Scanprüfung des HTTP-Handlers; diese Voraussetzung muss hier selbst geprüft werden:

```bash
sudo systemctl start forensic-triage-update@check.service
sudo systemctl start forensic-triage-update@install.service
```

Die bewusste Installation benötigt ein erreichbares Git-Repository und einen freigegebenen Git-Tag. Bei einer Installation aus einem Releasepaket zuerst den neuen freigegebenen Code übertragen und anschließend dasselbe Installationsskript erneut ausführen.

Vor größeren Aktualisierungen ist eine verschlüsselte Sicherung der Fallakten vorzusehen. Das Installationsskript verschiebt keine bestehenden Speicherpfade und löscht keine Fallakten.

Installer und Updater aktivieren ein persistentes, komprimiertes Systemjournal. Es ist auf 64 MB und 14 Tage begrenzt, damit USB-, Kernel- und Dienstfehler auch nach einem unkontrollierten Neustart diagnostizierbar bleiben, ohne den Systemspeicher unbegrenzt zu belegen.

## 6. Manuelle Diagnose

```bash
sudo systemctl status forensic-triage-web.service --no-pager
sudo journalctl -u forensic-triage-web.service -n 100 --no-pager
sudo journalctl -b -1 -k --no-pager
sudo ./scripts/install_debian.sh --check
```

Versionen:

```bash
.venv/bin/forensic-triage --version
.venv/bin/forensic-triage-web --version
```

## 7. Raspberry Pi – vor Freigabe prüfen

- Betriebssystem und Paketverfügbarkeit
- ausreichende Stromversorgung; eigener Laufwerksstrom kann einen aktiven Hub für dieses Laufwerk ersetzen, weitere USB-Geräte gesondert betrachten
- Systemlaufwerk nicht am selben störanfälligen USB-Pfad wie Prüfmedien; beim Pi 3B+ bevorzugt hochwertige MicroSD für das System
- mehrere USB-Geräte gleichzeitig
- reales CD/DVD-Laufwerk
- direkter Ethernet-Zugriff und Firewall
- Touch-/Kleinbildschirm
- kontrolliertes Herunterfahren und Stromverlust
- Temperatur und Dauerlast

Der vorhandene Pi-Testbetrieb ersetzt diese Abnahme nicht; die Einsatzinstallation ist noch nicht freigegeben.

## English quick install

For a temporarily public repository, download `scripts/bootstrap_pi.sh` from the documented raw GitHub URL and run the saved file with `sudo`; it clones into `/opt/triagebox` and starts the Pi installer. Alternatively clone with a read-only deploy key. Run Pi setup from Ethernet or the local console. The development Wi-Fi password must be replaced before real use.
