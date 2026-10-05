# Android-/Mobilgerät-Triage

Stand: 5. Oktober 2026 · Anwendung `v0.2.0-alpha.74`

## Zweck

Der normale Mobilgerät-Lauf ist ein **Krypto-Schnellscan**. Er erfasst Geräteidentität, Betriebssystem, zugängliche Benutzer-/Arbeitsprofile und die gemeldeten Benutzer-Apps. Die App-Kennungen werden gegen dieselbe lokale Erkennungsregelbasis wie beim Apple-Mobilgerät geprüft. Er liest keine App-Inhalte, Nachrichten, Fotos, Dateien, Wallets, Schlüssel oder Seeds.

„Keine Krypto-Apps in der erfassten Benutzer-App-Liste erkannt“ ist deshalb kein Beleg, dass das Mobilgerät keine Krypto-Nutzung oder Vermögenswerte enthält. War ein Profil nicht zugänglich, steht es ausdrücklich auf **nicht vollständig prüfbar**. Banking-/Finanz-Apps werden separat als neutraler Finanzhinweis dokumentiert.

## Automatische Erkennung

1. Apple-Geräte werden über `idevice_id` erkannt und dem iPhone-Collector zugeordnet.
2. Android-Geräte werden ohne Inhaltszugriff aus Linux-sysfs erkannt. Bekannte Android-Vendor-IDs sind starke Evidenz. Zusätzlich werden Geräteklasse, alle USB-Interfaceklassen/-protokolle sowie Hersteller- und Produkttexte bewertet.
3. MTP/PTP allein genügt ausdrücklich nicht: Kameras und sonstige Imaging-Geräte ohne Telefon-/Android-Indiz werden verworfen. Hersteller-/Produktmerkmale decken neben den bisherigen Marken nun auch TCL/Alcatel, Nokia/HMD, realme, ZTE, ASUS/ROG, Fairphone, Lenovo, Meizu, Tecno, Infinix, itel, Blackview, Ulefone, Doogee, Cubot, Oukitel und UMIDIGI ab. Eine unbekannte Vendor-ID wird nur mit kombinierter, nachvollziehbarer Telefonidentität plus passendem MTP/PTP-/Composite-Merkmal als Kandidat behandelt.
4. Physisch erkannt, aber noch ohne ADB: `debugging_required`, nicht scanbar, Anleitung sichtbar. ADB `unauthorized`: `authorization_required`, Bestätigung am Telefon erforderlich. ADB `device`: `authorized`, scanbar.
5. Die USB- und ADB-Ansichten werden über identische Seriennummer oder die von ADB gemeldete USB-Topologie korreliert. Ohne eindeutiges Signal wird nicht nur anhand eines Herstellernamens zusammengeführt.

Die Box pollt den Zustand weiter. Die Telefonkachel und Anleitung sind bereits ohne aktiven Fall sichtbar; ein Scan bleibt bis zum bewussten Fallstart und `authorized` gesperrt. Bei aktivem Fall und Auto-Scan wechselt ein bestätigtes Gerät selbstständig vom Hilfebildschirm in den Scan.

## Vorbereitung am Telefon

Die Oberfläche zeigt ohne technischen Jargon passende Schritte. Die genauen Menünamen können je Hersteller, Android-Version und Gerätesprache abweichen.

Referenz für Gerätepfade und USB-Debugging: [Android Developers – Configure on-device developer options](https://developer.android.com/studio/debug/dev-options). Samsung beschreibt das Freischalten der Entwickleroptionen zusätzlich in [Enable and access Developer options on your Samsung Galaxy phone](https://www.samsung.com/ca/support/mobile-devices/galaxy-phone-developer-options/).

### Samsung

1. **Einstellungen → Telefoninfo → Softwareinformationen** öffnen.
2. Siebenmal auf **Buildnummer** tippen und den Gerätecode bestätigen.
3. Zu **Einstellungen → Entwickleroptionen** zurückgehen.
4. **USB-Debugging** aktivieren.
5. Das Telefon entsperrt lassen und **„USB-Debugging zulassen?“** bestätigen.

### Google Pixel

1. **Einstellungen → Über das Telefon** öffnen.
2. Siebenmal auf **Build-Nummer** tippen und den Gerätecode bestätigen.
3. **System → Entwickleroptionen** öffnen.
4. **USB-Debugging** aktivieren und die Verbindungsabfrage bestätigen.

Für Xiaomi, Motorola und OnePlus enthält die Oberfläche eigene kurze Pfade; für andere Android-Hersteller einen allgemeinen Ablauf. Nach dem Einsatz sollte USB-Debugging nach der jeweiligen Verfahrensanweisung wieder deaktiviert und die Computerfreigabe gegebenenfalls widerrufen werden. Das Aktivieren ist eine Zustandsänderung am untersuchten Gerät und muss organisatorisch freigegeben sein.

## Profile und geschützte Bereiche

Der Collector liest `pm list users` und fragt die Benutzer-App-Pakete jedes gemeldeten Profils separat ab. Ergebnis und Vollständigkeit bleiben pro Profil erhalten. Typische Fälle:

- Hauptprofil: wird normalerweise als Benutzer `0` gemeldet.
- Arbeitsprofil oder weiterer Android-Benutzer: wird automatisch zusätzlich abgefragt, wenn sichtbar.
- Samsung Secure Folder/Knox oder herstellerspezifischer geschützter Bereich: kann getrennt, gesperrt oder gar nicht sichtbar sein. Fehlt ein zuverlässig zugängliches Profil, meldet TRIAGE//BOX **unbekannt/nicht vollständig prüfbar** und niemals „keine Apps vorhanden“.

## Gemeinsame Krypto-Regeln

Jede App-Regel kann enthalten:

- `ios_bundle_ids`: verifizierte iOS-Kennungen,
- `android_package_ids`: verifizierte Android-Paketnamen,
- `name`, `aliases` und vorsichtige `terms`,
- `category` und `relevance`.

Kategorien:

- `wallet`: Self-Custody-Wallet – hoch,
- `hardware_wallet`: Hardware-Wallet-Begleiter – hoch,
- `exchange`: Kryptobörse/Broker – hoch,
- `portfolio`: Krypto-Steuer/Portfolio – mittel,
- `payment`: spezifischer Krypto-Zahlungsdienst,
- `market`: Krypto-Kurse/Markt.

Die mit Alpha 60 gelieferten Android-IDs für MetaMask, Trust Wallet, Exodus, Ledger Live, Bitpanda, Coinbase, Kraken und Binance wurden anhand ihrer offiziellen Google-Play-Einträge verifiziert. Weitere Regeln dürfen erst nach Verifikation ergänzt werden. Lokale Änderungen liegen außerhalb von Git und werden pro Scan als unveränderlicher Regelstand gespeichert.

Verwendete Primärquellen: [MetaMask](https://play.google.com/store/apps/details?id=io.metamask), [Trust Wallet](https://play.google.com/store/apps/details?id=com.wallet.crypto.trustapp), [Exodus](https://play.google.com/store/apps/details?id=exodusmovement.exodus), [Ledger Live](https://play.google.com/store/apps/details?id=com.ledger.live), [Bitpanda](https://play.google.com/store/apps/details?id=com.bitpanda.bitpanda), [Coinbase](https://play.google.com/store/apps/details?id=com.coinbase.android), [Kraken](https://play.google.com/store/apps/details?id=com.kraken.invest.app) und [Binance](https://play.google.com/store/apps/details?id=com.binance.dev).

## Gespeicherte Ergebnisse

Ein Android-Lauf erzeugt die gemeinsame Fallstruktur mit `device.json`, `phone.json`, `android.json`, `apps.json`, `crypto-rules.json`, `crypto-hints.json`, `summary.json`, leerem `files.csv`, Audit und Bericht. `summary.json.timings` enthält Dauerwerte für Geräteinformationen, App-Erfassung sowie Klassifikation/Speicherung. Das leere Dateiverzeichnis ist beabsichtigt: Der Schnellscan ist keine Dateisichtung.

## Praktischer Samsung-Test

1. Alpha 72 installieren und Pi/Dienst frisch starten; `adb` muss als Systemabhängigkeit vorhanden sein.
2. Testfall starten, Auto-Scan aktiv lassen.
3. DIAGNOSE → DEBUG → ANDROID öffnen. Samsung **ohne USB-Debugging** entsperrt per Datenkabel anschließen und normale Datenfreigabe bestätigen. Telefonkachel, `debugging_required`, Anleitung, USB-Interfaces und Kandidatenbegründung prüfen.
4. USB-Debugging aktivieren. Zuerst **nicht** bestätigen: `authorization_required`; keine Sichtung darf beginnen.
5. Bestätigen: `authorized`; bei aktivem Fall darf der Scan starten.
6. Geräteangaben, alle sichtbaren Profile, App-Zahl, Krypto-Treffer, Regelgrund und Erfassungsstatus prüfen.
7. Mit Arbeitsprofil wiederholen. Secure Folder einmal gesperrt und einmal geöffnet testen; niemals darf aus Nichtzugänglichkeit ein Negativbefund werden.
8. Kabel während App-Erfassung abziehen: Webdienst und andere Scans müssen bedienbar bleiben; der Lauf muss nachvollziehbar fehlschlagen.
9. Telefon abziehen: genau ein sauberer Disconnect, keine zweite/flackernde Telefonkachel. `summary.json.timings`, `scan.log`, PDF-Bericht und Audit kontrollieren.

## Noch nicht praktisch bestätigt

Der reale Alpha-71-Pi-Test zeigte ein physisch erkanntes, aber abgelehntes TCL/A1-Alpha-21-Telefon (`1bbb:0168`, `06/01/01:MTP`). Ursache war fehlende TCL-Telefon-Evidenz, nicht USB/sysfs/MTP. Alpha 72 behebt genau diesen Fall; der exakte Datensatz und Provider-/White-Label-Varianten sind automatisiert regressionsgeprüft. Weitere reale USB-Deskriptoren, udev-/Zugriffsregeln, Paketlisten je Profil und Auto-Start müssen weiterhin praktisch verifiziert werden.
