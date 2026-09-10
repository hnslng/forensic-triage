# Roadmap und nächste Schritte

Dokumentationsstand: 10. September 2026 · Anwendung: `v0.2.0-alpha.50`.

Der gemeinsame Einstellungen-Bereich außerhalb des Fallfensters, der erweiterte und bearbeitbare Dateityp-Katalog, Scan-Snapshots sowie die dauerhafte lokale Profilablage sind implementiert und isoliert geprüft. Der Pi-Praxistest nach Aktualisierung steht aus; siehe [Einstellungen](settings.md).

Das Ziel bleibt eine schnelle Grobsichtung vor Ort: Fall starten, Medien anschließen, Metadaten und Hinweise prüfen, Entscheidung begründen und Bericht exportieren. Die nächste Etappe ist ein nachvollziehbarer vollständiger Probeeinsatz. Zusätzliche Analysefunktionen werden vorerst zurückgestellt.

## Bereits vorhanden

Der [Projektstand](project-status.md) trennt implementierte Funktionen, bisherige Beobachtungen und noch ausstehende Abnahmen.

- Pi-Installation, WPA2-Hotspot, mDNS und portfreier HTTP-Zugang über Hotspot und privates Router-LAN.
- Fallstart und Fallende, parallele USB-Scans, neutrale Sichtungsnummern und Online-/Offline-Dashboard.
- Metadatenverzeichnis, Suchprofile, Kategorien, größte Dateien und begrenzte ZIP-/ISO-/7Z-/RAR-Verzeichnisse.
- Archivstatusfilter, zwei Entscheidungen, Geräteangaben, Audit, PDF-Bericht und ZIP-Export.
- Doppelbestätigung beim Entfernen, Dateierhalt im Papierkorb, Prozesszeitlimits und persistente Diagnoseprotokolle.
- Reine Updateprüfung und bewusste Installation; Fallende direkt im Updatefenster seit Alpha 43.
- Signierte Offline-Updates über den eigenen Hotspot, ohne Internetzugang des Pi; Abhängigkeitsänderungen bleiben bewusst online.

Diese Punkte sind implementiert; damit sind noch nicht alle Störfälle auf dem Pi abgenommen.

## 1. Vollständigen Probeeinsatz durchführen

- [ ] Vorab die Löschsperre für aktive Fälle und laufende Scans serverseitig ergänzen und isoliert testen. Der DELETE-Endpunkt prüft bislang nur die Fallbestätigung; die Dashboard-Sperre allein reicht nicht.
- [ ] Drei bekannte Teststicks in einem neuen Testfall parallel sichten; einzeln anschließen, gemeinsam angeschlossen starten und erneut anschließen.
- [ ] Gerät, Seriennummer, Partition, Sichtungsnummer und Verzeichnis gegen den Sollbestand vergleichen; gleiche oder fehlende Seriennummern gesondert prüfen.
- [ ] Kategorien, Stichworttreffer, Archivzustände und Dateizahlen gegen das zum Testmedium gehörende Manifest prüfen.
- [ ] Zwischen Sichtungen, Archivstatus und Explorer wechseln; keine fremden oder veralteten Ergebnisse zulassen.
- [ ] Beide Entscheidungen mit passenden Pflichtangaben speichern und PDF, ZIP, Medienregister und Audit vergleichen.
- [ ] Fall beenden, erneut öffnen und nach einem Dienst-/Pi-Neustart prüfen.
- [ ] Ergebnis nach [Testplan](test-plan.md#vollständiger-probeeinsatz) dokumentieren, Abweichungen mit reproduzierbaren Schritten festhalten.

Erledigt ist diese Etappe erst, wenn jede Sichtung in Oberfläche, Bericht und Ablage eindeutig demselben Medium zugeordnet bleibt.

## 2. Fehlverhalten und Wiederanlauf absichern

- [ ] Netzwerkverlust, Browser-Neuladen und mehrere Browserfenster testen. Der aktive Fall liegt derzeit im Webdienst; Browser-Neuladen beendet ihn nicht.
- [ ] Gewünschte Wiederfreigabe nach Verbindungs-/Browserverlust festlegen und gegebenenfalls implementieren; vor Standortwechsel bleibt ausdrückliches Fallende Pflicht.
- [ ] Langsamen/blockierten Worker, Zeitüberschreitung und Abziehen ausschließlich mit Testmedien prüfen; andere Scans und gespeicherte Akten müssen bedienbar bleiben.
- [ ] Umgang mit gesperrten Geräten nach Neustart absichern; die bisherige Quarantäne liegt nur im Arbeitsspeicher und ist danach leer.
- [x] Neue Fall- und Scanstarts während einer Updateinstallation zusätzlich serverseitig über eine gemeinsame Laufzeitsperre verhindern (Alpha 45).
- [ ] Große Verzeichnisbäume, viele kleine Dateien, weitere Dateisysteme und volle Ergebnisablage testen.
- [ ] Archivbudgets mit vielen, großen, defekten, verschlüsselten und mehrteiligen Archiven messen; Grenzen und unvollständige Ergebnisse prüfen.
- [ ] Pi-Systemmedium von Prüfmedien trennen; MicroSD statt USB-System-SSD für den Zielaufbau praktisch testen.
- [x] Pi-Unterspannung/Drosselung aktuell und seit Boot erfassen; nur bei einem Ereignis als kompakte farbige Warnung anzeigen und Zustandsänderungen im Systemjournal protokollieren (Alpha 50).
- [x] Neustart und Herunterfahren in einem getrennten Power-Menü zweistufig bestätigen und während Fall, Scan oder Update serverseitig sperren (Alpha 50).
- [ ] Kontrolliertes Herunterfahren und Neustart praktisch prüfen; Stromverlust, Temperatur und zuverlässige Offline-Zeit bleiben getrennte Tests.

## 3. Daten, Profile und Updates wiederherstellbar machen

- [ ] Konsistente Sicherung von Fallindex, Fallordnern, Papierkorb, Profilen und lokaler Konfiguration erstellen und auf einem getrennten Teststand zurückspielen.
- [ ] Wiederherstellung eines entfernten Falls in den SQLite-Index implementieren und testen. Der Papierkorb bewahrt Dateien auf; ein Restore-Knopf oder fertiger Import fehlt.
- [x] Bearbeitete Profile und Dateityp-Katalog dauerhaft außerhalb des Release-Verzeichnisses ablegen; Übernahme ohne Überschreiben lokal prüfen (Alpha 44).
- [ ] Erhalt der Einstellungen bei realem Pi-Update und Rückwechsel prüfen, einschließlich der automatischen Erstübernahme aus Alpha 43; Einzelheiten in `settings.md` beachten.
- [ ] Protokollumfang abschließen: Fallende ist derzeit kein eigenes Audit-Ereignis; Navigation und Filter erzeugen ebenfalls keines.
- [ ] PDF-Formulierungen und Grobinhalt fachlich prüfen; Aufbewahrung, Export und endgültige Entfernung festlegen.
- [ ] Privaten Git-Lesezugriff des Update-Dienstes reproduzierbar einrichten und nach Neustart testen.
- [ ] Updatefehler und Stromunterbrechung testen. Das vorhandene Umschalten des Code-Symlinks ist noch kein vollständiger Rollback von Dienstkonfiguration, Paketen und Daten.
- [ ] Offline-Update von Alpha 45 auf die folgende Version praktisch über den Pi-Hotspot testen; Signaturfehler und Verbindungsabbruch am Pi nachvollziehen.
- [ ] Startprüfung, Rollback und Wiederaufnahme eines fehlgeschlagenen Updates vervollständigen; unabhängige Sicherung beibehalten.

## 4. Einfachen Schutz vor echtem Einsatz fertigstellen

- [ ] Gerätespezifisches WLAN-Passwort und Verhalten ohne Internet abnehmen; der Alpha-Platzhalter ist kein Einsatzkennwort.
- [ ] Gemeinsames Gerätepasswort, Abmeldung und Inaktivitätssperre gemäß [Schutzkonzept](security-concept.md) umsetzen.
- [ ] Lokales HTTPS mit einem für die verwendeten Laptops geeigneten Zertifikatsverfahren umsetzen.
- [ ] Verschlüsselte Fallablage mit praktisch geprüftem Entsperr- und Wiederherstellungsablauf einrichten.
- [ ] Firewall und erlaubte Zugriffe über Hotspot/LAN prüfen; direkte Ethernet-Rückfallebene ohne Router konfigurieren.
- [ ] Hardware-Schreibblocker und tatsächlichen Schreibschutz mit den vorgesehenen Medien validieren.
- [ ] Sicherheitsreview, Betriebsablauf und dokumentierte Freigabe durchführen; Bearbeiterkürzel allein ist keine Anmeldung.

## CD/DVD und weiterer Hardwareausbau

- [ ] Laufwerk mit eigener Stromversorgung identifizieren und testen: zunächst leer mit Auto-Scan aus, dann intaktes Testmedium manuell, zuletzt Auto-Scan und Fehlerfälle.
- [ ] Bei ausreichender eigener Versorgung des Laufwerks ist für dieses allein kein zusätzlich versorgter Hub erforderlich. Hub-Bedarf für weitere Geräte nach Anzahl, Strombedarf und Lasttest entscheiden.
- [ ] Gehäuse, Kabel, Kühlung und System-/Fallspeicher des Pi 3B+ festlegen. Laptop-Browser bleibt der aktuelle Bedienweg; ein kleiner Bildschirm ist optional und mit tatsächlicher Auflösung zu testen.
- [ ] LEDs erst nach bestandenem Probeeinsatz bewerten.

## Zurückgestellte Erweiterungen

- PDF-/Office-Verschlüsselung: vor einer Entscheidung den zusätzlichen Aufwand mit etwa 1.000 Dokumenten messen; Öffnungsschutz und Bearbeitungsschutz unterscheiden. Noch keine Umsetzung oder verlässliche Laufzeitangabe.
- Dateisignaturen zur Erkennung umbenannter Dateien, verschlüsselte Volumes und TAR-Unterstützung erst nach Stabilitätsmessungen bewerten.
- Englische Vollübersetzung, weitere Rollen und digitale Signaturen nur bei belegtem Bedarf.
- Abhängigkeiten und unterstützte OS-Versionen nach reproduzierbarer Neuinstallation festlegen; Release- und Integrationsprüfungen erweitern.

Imaging, Carving, Recovery, Vollinhaltsanalyse, Passwortbrechen und automatische Sicherstellungsentscheidungen bleiben außerhalb des Umfangs.

## English summary

The Pi prototype is operational; installation, networking, USB triage and deliberate updates have been exercised. The next milestone is a documented end-to-end trial, followed by failure/recovery tests, durable profiles and backups, and the planned access/storage protection. Existing process deadlines and release switching are not a guarantee against hardware or power failures. Optical-drive testing can use a separately powered drive. Additional analysis features remain deferred.
