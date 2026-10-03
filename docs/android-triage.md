# Android-/Mobilgerät-Triage

Stand: 3. Oktober 2026 · Anwendung `v0.2.0-alpha.63`

## Zweck

Der normale Mobilgerät-Lauf ist ein **Krypto-Schnellscan**. Er erfasst Geräteidentität, Betriebssystem, zugängliche Benutzer-/Arbeitsprofile und die gemeldeten Benutzer-Apps. Die App-Kennungen werden gegen dieselbe lokale Erkennungsregelbasis wie beim Apple-Mobilgerät geprüft. Er liest keine App-Inhalte, Nachrichten, Fotos, Dateien, Wallets, Schlüssel oder Seeds.

„Keine Krypto-Apps in der erfassten Benutzer-App-Liste erkannt“ ist deshalb kein Beleg, dass das Mobilgerät keine Krypto-Nutzung oder Vermögenswerte enthält. War ein Profil nicht zugänglich, steht es ausdrücklich auf **nicht vollständig prüfbar**. Banking-/Finanz-Apps werden separat als neutraler Finanzhinweis dokumentiert.

## Automatische Erkennung

1. Apple-Geräte werden über `idevice_id` erkannt und dem iPhone-Collector zugeordnet.
2. Android-Geräte werden zunächst ohne Inhaltszugriff anhand ihrer Linux-USB-Geräteinformationen erkannt. Bekannte Hersteller-IDs dienen nur der Zuordnung als Android-Kandidat.
3. Sobald das Android-Mobilgerät die Verbindung freigibt, meldet `adb devices -l` den Zustand `device`. Dann werden Hersteller, Modell, Android-Version und Build ergänzt und der Scan kann automatisch starten.
4. `unauthorized` bedeutet: Die Verbindungsabfrage wartet am Telefon. `offline` beziehungsweise fehlende Freigabe wird nicht als scanbares Gerät behandelt.

Die Box pollt den Zustand weiter. Bei aktivem Fall und Auto-Scan wechselt ein bestätigtes Gerät selbstständig vom Hilfebildschirm in den Scan.

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

1. Alpha 60 über den Online-Pfad installieren; `adb` ist eine neue Systemabhängigkeit und steckt deshalb nicht in einem reinen alten Offline-Paket.
2. Testfall starten, Auto-Scan aktiv lassen.
3. Samsung entsperrt per Datenkabel anschließen. Prüfen, ob zunächst Hersteller/Modell und die Samsung-Anleitung erscheinen.
4. USB-Debugging aktivieren. Zuerst **nicht** bestätigen: Oberfläche muss weiter „Verbindung am Telefon bestätigen“ zeigen und darf keine Sichtung anlegen.
5. Bestätigen: Scan muss automatisch starten.
6. Geräteangaben, alle sichtbaren Profile, App-Zahl, Krypto-Treffer, Regelgrund und Erfassungsstatus prüfen.
7. Mit Arbeitsprofil wiederholen. Secure Folder einmal gesperrt und einmal geöffnet testen; niemals darf aus Nichtzugänglichkeit ein Negativbefund werden.
8. Kabel während App-Erfassung abziehen: Webdienst und andere Scans müssen bedienbar bleiben; der Lauf muss nachvollziehbar fehlschlagen.
9. `summary.json.timings`, `scan.log`, PDF-Bericht und Audit kontrollieren.

## Noch nicht praktisch bestätigt

Die Android-Funktion ist automatisiert simuliert, aber in Alpha 60 noch nicht an einem realen Samsung/Pixel/Xiaomi-Gerät abgenommen. Herstellerpfade, Paketlisten je Profil, USB-Zugriffsregeln und Auto-Start müssen auf dem Pi praktisch verifiziert werden. Android-Oberflächen und Paketnamen können sich ändern; Regeln und Anleitung benötigen laufende Pflege.
