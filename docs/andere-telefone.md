# Andere Telefone und Betriebssysteme

Stand: 2. Oktober 2026 · Anwendung `v0.2.0-alpha.60`

TRIAGE//BOX besitzt zwei implementierte Telefonpfade:

- iPhone über reguläre Apple-USB-Dienste,
- Android über USB-Vorerkennung und eine ausdrücklich am Telefon autorisierte ADB-Verbindung.

Beide sind App-only-Krypto-Schnellscans. Sie lesen keine Telefondateien oder Medien. Der Android-Pfad ist herstellerübergreifend; Samsung, Pixel, Xiaomi, Motorola und OnePlus unterscheiden sich in der Oberfläche nur durch die Hilfeschritte. Technischer Ablauf, Profile und Grenzen stehen in [Android-Triage](android-triage.md).

Andere Telefonbetriebssysteme, proprietäre Synchronisationsprotokolle und Hersteller-Sonderwege sind nicht implementiert. Ein Gerät darf deshalb nicht allein wegen fehlender Erkennung als leer, irrelevant oder frei von Krypto-Apps bewertet werden. Vor einer Erweiterung sind reproduzierbare Geräteerkennung, rechtlich/organisatorisch zulässige Freigabe, stabile App-Metadaten und eine klare Kennzeichnung nicht zugänglicher Bereiche erforderlich. Es wird kein vorhandener iPhone- oder Android-Adapter nur aufgrund ähnlicher USB-Klassen wiederverwendet.
