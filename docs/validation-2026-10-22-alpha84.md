# Lokaler Release-Prüfnachweis · Alpha 84

Prüfdatum: **22. Oktober 2026**. Anwendung: `0.2.0a84`, Tag: `v0.2.0-alpha.84`, Release-Commit: `c171badef3dfc2ffd242313f9c9f11c1406ccf37`. Prüfung lokal unter macOS; keine Installation oder Hardwareabnahme auf dem Raspberry Pi und kein Push im Rahmen dieser Freigabe.

## Anlass und belegte Ursache

Ein bereitgestelltes historisches Scanpaket zeigte nach 55,446 Sekunden einen als abgeschlossen dargestellten Lauf mit 0 Dateien. Das NTFS-Dateisystem war erkannt worden. Beim Lesen der Metadaten eines JPG-Eintrags trat `ENOENT` („Datei oder Verzeichnis nicht gefunden“) auf; anschließend wurde die gesamte Partition übersprungen und ein leeres Ergebnis gespeichert. Ein Gesamtzeitlimit war für diesen Lauf nicht der protokollierte Grund. Warum der Eintrag nicht lesbar war, bleibt ungeklärt; daraus folgt weder eine Kapazitätsgrenze noch ein Nachweis für einen leeren Stick.

Die Auswertung erfolgte lesend, ohne Änderung des bereitgestellten ZIP-Pakets. Fallnummer, Seriennummer, ursprünglicher Dateipfad und Falldaten werden hier bewusst nicht übernommen.

## Korrektur und Grenzen

- Einzelne Metadatenfehler werden pro Pfad dokumentiert; lesbare Dateien vor und nach dem Fehler bleiben erhalten. Nicht lesbare Verzeichnisse werden über die Fehlerbehandlung der Verzeichnisbegehung erfasst.
- Partitionsstatus: `ok`, `partial` oder `unsupported_or_error`. Zusammengefasster Sichtungsstatus: `complete`, `partial` oder `failed`. Keine auswertbare Partition gilt nicht als erfolgreicher Leerbefund.
- Fehlerangaben stehen in `raw/fast_mount_*.json` und `partitions.json`, Zusammenfassung und Warnungen in `summary.json`. Oberfläche, Diagnose und Text-/PDF-Berichte kennzeichnen unvollständige beziehungsweise fehlgeschlagene Erfassung.
- Ältere Ergebnisse werden beim Laden anhand vorhandener Partitionsangaben eingeordnet, ohne originale Scan-Dateien zu ändern. Bereits verworfene Dateilisten benötigen einen erneuten Scan.
- Schreibschutz und Zeitlimits unverändert: standardmäßig 180 Sekunden je Gesamtscan und 15 Sekunden je Gerätebefehl; konfigurierbare Werte. Kein Nachweis gegen Kernel-/Busstillstand.
- Alpha 83 ist enthalten: Verbindungskennung statt wiederverwendetem Gerätepfad; bei fehlender Kernelkennung und vollständig gleich gemeldeten, unbeobachteten Wechseln bleibt eine dokumentierte Zuordnungsgrenze.

## Erfolgreiche Prüfungen

| Prüfung | Ergebnis |
|---|---|
| Vollständiger Python-Testlauf | 319 bestanden, zuletzt nach Versionsanhebung auf Alpha 84 |
| Isolierte Chromium-Oberflächentests | 107 bestanden; Warntext, Statuswechsel und sichere Textdarstellung eingeschlossen |
| Lesefehler-Regressionen | Fehlender Dateieintrag, erhaltene vorherige/nachfolgende Einträge, Verzeichnisfehler, komplette und teilweise Partitionsausfälle |
| Historische Unterlagen und Berichte | Fehlerstatus aus gespeicherten Partitionsdaten; ursprüngliche Zusammenfassung unverändert |
| Historisches Fehlerpaket, lesend geprüft | Mit neuer Statusableitung `failed`, 0 Dateien, eine Partitionswarnung |
| Offline-Paket | Signatur, Manifest-Dateiprüfsummen und getrennte Vorbereitung erfolgreich |
| Abhängigkeiten | Fingerprint identisch zu Alpha 83 |
| Änderungsformatierung | `git diff --check` erfolgreich |

Reproduzierbare Entwicklungstests:

```bash
.venv/bin/python -m pytest -o addopts='' -q
NODE_PATH=/opt/homebrew/lib/node_modules node --test tests/test_web_ui.cjs
git diff --check
```

`NODE_PATH` bezeichnet die verwendete lokale Playwright-Installation; auf anderen Rechnern entsprechend anpassen. Browserprüfungen liefen mit synthetischen Daten ohne Pi-/USB-Zugriff. Der Browserlauf erfolgte bei identischem Oberflächencode vor der abschließenden Diagnose-Anpassung im Webdienst und der Versionsanhebung; der vollständige Python-Lauf prüfte anschließend auch diese Änderungen. Diese Befehle sind keine Hardwaretests.

## Ausgegebenes signiertes Paket

- Datei: `dist/triagebox-v0.2.0-alpha.84.tbu` (lokal, nicht versioniert)
- Größe: **446089 Bytes**
- SHA-256: **`51bde7045bc2d95178e44638d809dcfa49d4f7f380e1061bebe8f562d802c61b`**
- Gebaut aus dem oben genannten committed Tag; keine uncommitteten Arbeitsdateien.
- Mit `prepare_bundle` in einem temporären Release-Verzeichnis für den Ausgangsstand `0.2.0a83` geprüft: Signatur und Manifest akzeptiert, Dateien erfolgreich vorbereitet; neues Qualitätsmodul bytegleich mit dem Release-Quelltext. Keine Aktivierung auf einem Gerät.

Nachträgliche reine Dokumentationsänderungen werden separat committed. Sie verändern weder den Alpha-84-Tag noch dieses Paket; dessen Prüfsumme bleibt gültig. Der vorliegende nachträgliche Prüfnachweis gehört daher nicht zum Inhalt des bereits ausgegebenen Pakets.

## Noch offene Abnahme

- Alpha 84 tatsächlich auf dem Pi installieren und angezeigte Version bestätigen.
- Betroffenen NTFS-Teststick erneut sichten und gegen unabhängig bekannten Bestand vergleichen; neue Dateiliste ist noch nicht nachgewiesen.
- Schnellen Wechsel mehrerer realer Sticks einschließlich fehlender/gleicher Seriennummern prüfen.
- Fehlerdarstellung, Teilinventar, Export und Unmount auf dem Pi bestätigen, einschließlich Nur-Lesen-Prüfung.
- Allgemeine Hardware-, Stromausfall-, Wiederherstellungs- und Schutzkonzept-Abnahme bleibt offen; siehe [Projektstatus](project-status.md) und [Testplan](test-plan.md).

Ergebnis: **lokal geprüftes Alpha-Offline-Paket für den bewussten Nachtest**, keine formale Freigabe für ungeprüften produktiven Einsatz.
