# iPhone-Grobsichtung über USB

Stand: 30. September 2026 · Anwendung `v0.2.0-alpha.54`

## Zweck und Grenze

TRIAGE//BOX kann ein regulär entsperrtes und vom Benutzer als vertrauenswürdig bestätigtes iPhone über die normalen Apple-USB-Dienste grob sichten. Die Funktion umgeht keine iOS-Sicherheitsmaßnahme, führt keinen Jailbreak durch und versucht weder Kennwörter noch Seed-Phrases, Private Keys oder andere Geheimnisse zu extrahieren.

Die Oberfläche zeigt ausschließlich Triage-Hinweise. Eine installierte Wallet- oder Börsen-App ist **kein Nachweis für vorhandene Vermögenswerte**. Ein auffälliger Dateiname ist **kein Nachweis für den Inhalt einer Datei**.

## Technischer Ablauf

1. `usbmuxd` stellt die USB-Verbindung zu den Apple-Diensten her.
2. `idevice_id` erkennt angeschlossene iPhones. `idevicepair` prüft beziehungsweise startet die reguläre Kopplung; erforderlichenfalls muss das iPhone entsperrt und „Diesem Computer vertrauen“ bestätigt werden.
3. `ideviceinfo` liest Gerätename, ProductType, iOS-/Build-Version und verfügbare Gerätekennung.
4. `ideviceinstaller` fragt die Metadaten der gemeldeten Benutzer-Apps ab. Name, Bundle-ID und Version werden anhand lokaler Regeln kategorisiert.
5. `ifuse` bindet den regulären AFC-Medienbereich und ausdrücklich per File Sharing freigegebene App-Dokumentbereiche jeweils nur lesend in den privaten Mount-Namensraum des Scan-Workers ein.
6. TRIAGE//BOX liest dort nur Dateisystem-Metadaten: Name, Pfad, Endung, Größe und verfügbaren Änderungszeitpunkt. Nutzdateien werden nicht geöffnet.
7. Ergebnis, unzugängliche Bereiche, Limits und Regelstand werden in derselben lokalen Fallakte wie USB-/CD-Sichtungen gespeichert.

Der allgemeine Bereich „Auf meinem iPhone“ ist nicht als vollständiger globaler Ordner verfügbar. Sichtbar sind nur Bereiche, die iOS über AFC beziehungsweise den jeweiligen File-Sharing-/House-Arrest-Dienst freigibt. App-Sandboxes, Schlüsselbund, private App-Daten und gesperrte Bereiche bleiben außerhalb des Umfangs.

## Erkennungsregeln

Die mitgelieferte Ausgangsliste liegt in `rules/iphone-triage.json`. Beim ersten Start wird eine dauerhafte lokale Kopie als `iphone-triage.json` im konfigurierten `FORENSIC_TRIAGE_SETTINGS_ROOT` angelegt. Updates überschreiben diese lokale Kopie nicht.

App-Regeln verwenden exakte Bundle-IDs, Bundle-Präfixe und neutrale Namensfragmente. Enthalten sind zunächst Wallet-/Krypto-, Kryptobörsen-, Messenger-, Cloud- und Banking-Hinweise, unter anderem Ledger Live, MetaMask, Trust Wallet, Coinbase, Binance, Kraken, Crypto.com, Phantom, Exodus, OKX, Bitpanda und BlueWallet. Dateiregeln kombinieren Pfadfragmente und Endungen, damit etwa `wallet-backup.json` als möglicher Hinweis markiert wird, nicht aber jede beliebige JSON-Datei.

## Zuverlässigkeit und Einschränkungen

- Gerätekennung und Basisinformationen sind bei erfolgreicher Kopplung typischerweise stabil verfügbar.
- App-Metadaten hängen von iOS-Version, Apple-Dienst und der von Apple tatsächlich herausgegebenen Liste ab. Die Oberfläche unterscheidet deshalb eine leere vollständige Liste von einer technisch unvollständigen Erfassung.
- AFC-/File-Sharing-Zugriff umfasst nur regulär freigegebene Bereiche. Ein unzugänglicher Bereich wird einzeln protokolliert.
- Der Zugriff wird mit `-o ro` angefordert und vor der Inventarisierung anhand der Linux-Mountinformationen als nur lesend verifiziert. TRIAGE//BOX führt keine Schreiboperation auf dem iPhone aus. Dies ist kein Hardware-Schreibblocker und iOS/Apple-Dienste bleiben Teil der Vertrauenskette.
- Zeit-, App-, Bereichs- und Dateilimits halten die Grobsichtung begrenzt. Erreichte Limits erscheinen als `unvollständig`, niemals als „keine Treffer“.
- Aktuelle iOS-Versionen können Verhalten und verfügbare Metadaten ändern. `pymobiledevice3` wurde als mögliche spätere Kompatibilitätsschicht bewertet, ist in der kleinsten robusten Erstfassung aber bewusst keine zusätzliche Pi-Abhängigkeit. Vor einer Ergänzung ist ein dokumentierter Realtest erforderlich.

## Installation und Update

Eine Neuinstallation über `scripts/install_debian.sh --pi` installiert zusätzlich `usbmuxd`, `libimobiledevice-utils`, `ideviceinstaller` und `ifuse`.

Ein reines Offline-`.tbu` enthält keine Debian-Pakete. Bei einem bereits installierten Alpha-System müssen diese Pakete daher einmal mit Internetzugang installiert oder der aktuelle Installer erneut ausgeführt werden. Fehlen Werkzeuge, bleibt die iPhone-Funktion deaktiviert; vorhandene USB-/CD-Funktionen bleiben erhalten.

## Erster Test mit einem echten iPhone

Nur mit einem eigenen beziehungsweise ausdrücklich freigegebenen Testgerät arbeiten:

1. TRIAGE//BOX aktualisieren und die vier Pakete installieren. Danach ohne iPhone prüfen, dass USB-Sichtungen weiterhin funktionieren.
2. Einen Testfall mit eindeutigem Kürzel starten. Keine echten Beweismitteldaten verwenden.
3. iPhone entsperren, per Datenkabel anschließen und Bildschirm eingeschaltet lassen.
4. Wenn iOS fragt, „Diesem Computer vertrauen“ bestätigen und den Gerätecode am iPhone eingeben. Der Code wird nicht in TRIAGE//BOX eingegeben.
5. Auf der iPhone-Kachel Gerätename/Modell, iOS-Version, UDID-Kürzung und Kopplungsstatus prüfen. Dann Scan starten beziehungsweise Auto-Scan abwarten.
6. Ergebnis prüfen: App-Erfassungsstatus, Kategorien, zugängliche Bereiche, Datei-Hinweise und sichtbare Unvollständigkeitswarnungen. Einen bekannten File-Sharing-Testordner verwenden, ohne sensible Inhalte.
7. Technische Details und `files.csv`, `apps.json`, `iphone.json`, `device.json` sowie `scan.log` in der Fallakte vergleichen. Sicherstellen, dass keine Nutzdatei kopiert wurde.
8. Kabel abziehen, offene Entscheidung dokumentieren und PDF-/ZIP-Export prüfen.
9. Negativtests wiederholen: gesperrtes iPhone; Vertrauen nicht bestätigt; Vertrauen widerrufen; File Sharing deaktiviert; Scanlimit bewusst klein setzen. Jeder Fall muss eine konkrete Erklärung statt „keine Treffer“ liefern.

Dieser Realtest ist noch keine forensische Freigabe. Ergebnisse, iPhone-/iOS-Modell, Kabel, Pi-Version und alle Abweichungen im Prüfprotokoll festhalten.
