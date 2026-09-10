# Signierte Offline-Updates

Seit `v0.2.0-alpha.45` kann TRIAGE//BOX ein freigegebenes Anwendungspaket über den eigenen WLAN-Hotspot erhalten. Der Raspberry Pi benötigt dabei keinen Internetzugang. Das Verfahren ergänzt den Git-basierten Online-Updater; es installiert weiterhin niemals automatisch.

## Bedienablauf

1. Das freigegebene Paket `triagebox-v…tbu` auf einem vertrauenswürdigen Laptop bereithalten.
2. Laptop mit dem WLAN **TRIAGEBOX** verbinden und `http://triagebox.local/` öffnen.
3. Aktiven Fall beenden und laufende Scans vollständig abwarten.
4. **System & Updates** öffnen, unter **Offline über TRIAGEBOX-WLAN** das `.tbu`-Paket auswählen und die Installation bestätigen.
5. Upload, Signaturprüfung, Vorbereitung, Python-Tests und Dienstneustart abwarten. Die Oberfläche verbindet sich nach dem kurzen Neustart erneut.

Alpha 45 selbst muss auf einem vorhandenen Alpha-44-Gerät noch einmal über den bisherigen Online-Weg installiert werden. Ab der danach folgenden Version kann der Offline-Weg verwendet werden.

Der erste praktische Alpha-45→Alpha-46-Versuch zeigte, dass eine schlanke kopierte Python-Umgebung kein `setuptools` enthalten muss. Alpha 48 bringt deshalb ein signiertes, eng auf dieses Projekt begrenztes Build-Backend mit. Ein in Alpha 47 noch vom systemd-Arbeitsordner abhängiger Selbsttest wurde ebenfalls korrigiert. Damit benötigt die Offline-Installation kein nachzuladendes Python-Buildpaket.

Der anschließende Sprung Alpha 45 → Alpha 48 wurde am Raspberry Pi erfolgreich über die Weboberfläche abgeschlossen. Eine während des Neustarts stehen gebliebene alte Fehlermeldung wurde für Alpha 49 bereinigt.

## Was der Pi prüft

- festes Paketformat und eine maximale Uploadgröße von standardmäßig 256 MB
- kryptografische SSH-Signatur mit dem lokal hinterlegten öffentlichen Freigabeschlüssel
- gültige, gegenüber der installierten Version höhere Release-Version
- vollständige, signierte Dateiliste ohne absolute Pfade, `..`, Symlinks oder Zusatzdateien
- Dateigröße und SHA-256 jeder einzelnen Paketdatei vor der Freigabe
- unveränderte Python-, Build- und Testabhängigkeiten
- vollständigen Python-Testlauf im getrennten Release-Verzeichnis
- erfolgreichen Start des Webdienstes nach dem atomaren Laufzeitlink-Wechsel

Ein beschädigtes, manipuliertes, altes oder mit einem fremden Schlüssel signiertes Paket wird vor der Aktivierung abgelehnt. Während einer angeforderten Installation sperrt eine Datei unter `/run` zusätzlich neue Fall- und Scanstarts – auch aus einem zweiten Browserfenster.

## Bewusste Grenze

Offline-Updates übernehmen die bereits installierte Python-Umgebung. Ein Release, das Systempakete, Python-Abhängigkeiten oder Build-Abhängigkeiten verändert, wird deshalb abgelehnt und muss über den Online-Updater beziehungsweise eine Wartungsinstallation eingespielt werden. Das verhindert, dass ein Paket nur teilweise funktioniert.

Der Codewechsel ist atomar und ein fehlgeschlagener Dienststart wechselt auf den vorherigen Code zurück. Änderungen an systemd-/nginx-Vorlagen erfolgen wie beim Online-Updater schon vor dem Laufzeitwechsel. Stromausfall, vollständiger Rollback aller Systemdateien und Wiederaufnahme eines unterbrochenen Updates sind weiterhin praktisch zu prüfen.

## Freigabepaket erstellen

Das Paket wird ausschließlich aus dem angegebenen, bereits committed Git-Tag gebaut – niemals aus ungespeicherten Arbeitsdateien:

```bash
.venv/bin/python scripts/build_offline_update.py v0.2.0-alpha.51
```

Die Ausgabe liegt standardmäßig unter `dist/` und wird durch `.gitignore` ausgeschlossen. Das Skript erwartet den privaten Signaturschlüssel standardmäßig unter:

```text
~/.config/triagebox/offline-update-signing
```

Ein anderer Pfad kann mit `--key` oder `TRIAGEBOX_UPDATE_SIGNING_KEY` gesetzt werden. Der private Schlüssel darf niemals in Git, auf dem Pi oder in einem Updatepaket landen. Er muss gegen Verlust und unbefugtes Kopieren gesichert werden. Der zugehörige öffentliche Schlüssel liegt als `deploy/offline-update-allowed-signers` im freigegebenen Programmstand. Sein aktueller Fingerprint lautet:

```text
SHA256:1M3GBzFT/tmc1sd3GdA92C8puKApMTHuPd8cWfOcy/Y
```

Wird der private Schlüssel verloren oder kompromittiert, ist eine bewusst autorisierte Schlüsselrotation über einen bereits vertrauenswürdigen Online-/Wartungsstand erforderlich. Ein beliebiges neues Schlüsselpaar darf vorhandene Geräte nicht ohne diesen Vertrauensübergang übernehmen.

## English summary

Alpha 45 accepts signed `.tbu` application bundles uploaded through the private TRIAGEBOX hotspot, so the Pi does not need internet access. The device verifies the SSH signature, release version, complete file manifest, per-file SHA-256 values, dependency compatibility and its Python tests before switching the runtime symlink. Dependency-changing releases still require an online or maintenance installation. The private signing key stays on the release workstation and must never be committed or copied to the Pi.
