# Apple-Mobilgerät-Grobsichtung über USB

Stand: 3. Oktober 2026 · Anwendung `v0.2.0-alpha.62`

## Zweck und Grenze

TRIAGE//BOX kann ein regulär entsperrtes und vom Benutzer als vertrauenswürdig bestätigtes iPhone oder iPad über die normalen Apple-USB-Dienste grob sichten. Die Funktion umgeht keine iOS-Sicherheitsmaßnahme, führt keinen Jailbreak durch und versucht weder Kennwörter noch Seed-Phrases, Private Keys oder andere Geheimnisse zu extrahieren.

Die Oberfläche zeigt ausschließlich Triage-Hinweise. Eine installierte Wallet- oder Börsen-App ist **kein Nachweis für vorhandene Vermögenswerte**. Der normale Lauf durchsucht seit Alpha 60 keine Dateien oder Medien mehr.

## Technischer Ablauf

1. `usbmuxd` stellt die USB-Verbindung zu den Apple-Diensten her.
2. `idevice_id` erkennt angeschlossene iPhones und iPads. `idevicepair` prüft beziehungsweise startet die reguläre Kopplung; erforderlichenfalls muss das Mobilgerät entsperrt und „Diesem Computer vertrauen" bestätigt werden.
3. `ideviceinfo` liest Gerätename, ProductType, iOS-/Build-Version, die gemeldete **Seriennummer** und getrennt davon die **UDID**. Wird eine Kennung nicht gemeldet, steht dort ausdrücklich „nicht gemeldet“; die UDID wird nicht als Seriennummer ausgegeben.
4. `ideviceinstaller` fragt die Metadaten der gemeldeten Benutzer-Apps ab. Name, Bundle-ID und Version werden anhand lokaler Regeln kategorisiert.
5. Die App-Liste wird gegen den unveränderlich in den Scan kopierten Regelstand klassifiziert.
6. Ergebnis, Vollständigkeit, Phasendauern und Regelstand werden in derselben lokalen Fallakte wie USB-/CD-Sichtungen gespeichert.

Der Schnellscan bindet weder den AFC-Medienbereich noch File-Sharing-/House-Arrest-Bereiche ein. App-Sandboxes, Schlüsselbund, private App-Daten, Fotos und gesperrte Bereiche bleiben außerhalb des Umfangs. Eine spätere „Erweiterte Sichtung“ ist nur eine Roadmap-Idee und derzeit nicht als Bedienfunktion vorhanden.

## Erkennungsregeln

Die gemeinsame Ausgangsliste für App- und Dateimetadaten liegt in `src/forensic_triage/data/crypto-rules.json`. Beim ersten Start wird sie als `crypto-rules.json` im konfigurierten `FORENSIC_TRIAGE_SETTINGS_ROOT` angelegt. Eine bereits vorhandene ältere `iphone-triage.json` wird einmalig als Ausgangspunkt übernommen; danach wird ausschließlich die neue gemeinsame Datei verwendet. Updates überschreiben lokale Anpassungen nicht. Die Oberfläche bietet unter **Einstellungen → Erkennungsregeln** Bearbeiten, JSON-Import und -Export. Jeder neue Scan speichert seine eigene `crypto-rules.json`-Kopie und `crypto-hints.json` mit konkreten Treffergründen.

App-Regeln unterstützen getrennte `ios_bundle_ids` und `android_package_ids`, danach exakte Namen, Aliase und frühere Namen und zuletzt ausdrücklich eingetragene, vorsichtige Begriffe. Wallets, Hardware-Wallet-Apps und Börsen sind hohe Hinweise, Portfolio-/Steuer- und Zahlungs-Apps mittlere Hinweise, vage Hinweise niedrig. Messenger, Cloud und Banking sind **neutral** und zählen nicht als Krypto-App-Hinweis. Dateiregeln bleiben für USB-/CD-Medien vorhanden, werden beim Mobilgerät-Schnellscan aber nicht ausgeführt.

Die Mobilgerät-Ansicht zeigt zuerst Gerätename, Seriennummer und Anzahl der erfassten Apps. Darunter folgt eine verständliche Krypto-Einschätzung. Bei Treffern empfiehlt sie eine Fachperson; selbst mehrere Treffer belegen weder Nutzung noch Vermögenswerte. Fehlt die App-Liste, wird ohne Treffer keine verlässliche Negativaussage getroffen. Messenger, Banking und andere neutrale Kategorien lösen keine Krypto-Warnung aus.

App-Namen in erkannten Gruppen sind direkt sichtbar; sonstige Apps bleiben aufklappbar und durchsuchbar. UDID, Modellkennung und vollständige technische App-Liste liegen im Detailbereich. Dateitypen, Größen, Stichwörter, Dateiverzeichnis und größte Dateien erscheinen beim Mobilgerät nicht, weil sie im Schnellscan nicht erhoben werden. Keine Angabe behauptet eine vollständige Mobilgerät-Auslesung.

## Zuverlässigkeit und Einschränkungen

- Gerätekennung und Basisinformationen sind bei erfolgreicher Kopplung typischerweise stabil verfügbar.
- App-Metadaten hängen von iOS-Version, Apple-Dienst und der von Apple tatsächlich herausgegebenen Liste ab. Die Oberfläche unterscheidet deshalb eine leere vollständige Liste von einer technisch unvollständigen Erfassung.
- TRIAGE//BOX führt im Schnellscan nur Abfragen gegen reguläre Apple-Dienste aus und keine Datei-Mounts. Dies ist kein Hardware-Schreibblocker; iOS/Apple-Dienste bleiben Teil der Vertrauenskette.
- Das App-Limit hält eine fehlerhafte oder unerwartet große Antwort begrenzt. Ein erreichtes Limit erscheint als `unvollständig`, niemals als „keine Treffer“.
- Aktuelle iOS-Versionen können Verhalten und verfügbare Metadaten ändern. `pymobiledevice3` wurde als mögliche spätere Kompatibilitätsschicht bewertet, ist in der kleinsten robusten Erstfassung aber bewusst keine zusätzliche Pi-Abhängigkeit. Vor einer Ergänzung ist ein dokumentierter Realtest erforderlich.

## Installation und Update

Eine Neuinstallation über `scripts/install_debian.sh --pi` installiert `usbmuxd`, `libimobiledevice-utils` und `ideviceinstaller`. `ifuse` bleibt für mögliche erweiterte Tests installiert, wird im normalen Schnellscan aber nicht verwendet.

Ein reines Offline-`.tbu` enthält keine Debian-Pakete. Bei einem bereits installierten Alpha-System müssen diese Pakete daher einmal mit Internetzugang installiert oder der aktuelle Installer erneut ausgeführt werden. Fehlen Werkzeuge, bleibt die iPhone-Funktion deaktiviert; vorhandene USB-/CD-Funktionen bleiben erhalten.

## Erster Test mit einem echten iPhone oder iPad

Nur mit einem eigenen beziehungsweise ausdrücklich freigegebenen Testgerät arbeiten:

1. TRIAGE//BOX aktualisieren und die vier Pakete installieren. Danach ohne Mobilgerät prüfen, dass USB-Sichtungen weiterhin funktionieren.
2. Einen Testfall mit eindeutigem Kürzel starten. Keine echten Beweismitteldaten verwenden.
3. iPhone oder iPad entsperren, per Datenkabel anschließen und Bildschirm eingeschaltet lassen.
4. Wenn iOS fragt, „Diesem Computer vertrauen" bestätigen und den Gerätecode am Mobilgerät eingeben. Der Code wird nicht in TRIAGE//BOX eingegeben.
5. Auf der Mobilgerät-Kachel Gerätename/Modell, iOS-Version, UDID-Kürzung und Kopplungsstatus prüfen. Dann Scan starten beziehungsweise Auto-Scan abwarten.
6. Ergebnis prüfen: App-Erfassungsstatus, Krypto-Kategorien, Erfassungsstatus und sichtbare Unvollständigkeitswarnungen.
7. Technische Details und `summary.json.timings`, leeres `files.csv`, `apps.json`, `phone.json`, `iphone.json`, `device.json` sowie `scan.log` vergleichen. Sicherstellen, dass keine Datei-/Medieninventarisierung stattgefunden hat.
8. Kabel abziehen, offene Entscheidung dokumentieren und PDF-/ZIP-Export prüfen.
9. Negativtests wiederholen: gesperrtes Mobilgerät; Vertrauen nicht bestätigt; Vertrauen widerrufen; App-Limit bewusst klein setzen. Jeder Fall muss eine konkrete Erklärung statt „keine Treffer" liefern.

Der zuletzt vor Alpha 60 beobachtete reale iPhone-Lauf dauerte ungefähr 16,35 Sekunden und enthielt noch den begrenzten Dateinamen-Zusatz. Alpha 61 protokolliert Phasen getrennt und lässt die gesamte Datei-/Mountphase weg. Eine belastbare prozentuale Verbesserung darf erst nach demselben Realgerät-Test mit Alpha 61 angegeben werden.

Dieser Realtest ist noch keine forensische Freigabe. Ergebnisse, iPhone-/iOS-Modell, Kabel, Pi-Version und alle Abweichungen im Prüfprotokoll festhalten.
