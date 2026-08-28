# Geplantes Zugriffsschutzkonzept / Planned access protection

## Zielbild

TRIAGE//BOX soll am Einsatzort ohne Benutzerverwaltungsaufwand bedienbar bleiben:

```text
GERÄT EINSCHALTEN
→ MIT TRIAGEBOX-WLAN VERBINDEN
→ triagebox.local ÖFFNEN
→ GERÄT EINMAL ENTSPERREN
→ FALL UND BEARBEITERKÜRZEL EINGEBEN
→ SICHTEN UND BERICHT EXPORTIEREN
→ FALL BEENDEN
```

Das Bearbeiterkürzel bleibt Bestandteil des Fallprotokolls, ist aber ausdrücklich **keine Anmeldung und kein Berechtigungsnachweis**.

## Kleine, verbindliche Sicherheitslösung

Für die erste einsatzfähige Pi-Version ist keine zentrale Benutzer- oder Rollenverwaltung vorgesehen. Stattdessen sind folgende Schutzschichten geplant:

1. **Privater WLAN-Hotspot:** WPA3, soweit Raspberry Pi 3B+ und verwendeter Treiber dies zuverlässig unterstützen, andernfalls mindestens WPA2. Das gerätespezifische WLAN-Passwort soll zufällig, mindestens 20 Zeichen lang und nicht in Git gespeichert sein.
2. **Ein gemeinsames Gerätepasswort:** Die Weboberfläche wird einmal pro Arbeitssitzung entsperrt. Es gibt vorerst keine einzelnen Benutzerkonten; das getrennt erfasste Bearbeiterkürzel dient weiterhin der Protokollierung.
3. **Kurze serverseitige Sitzung:** Anmeldung nur über ein nicht dauerhaftes, `HttpOnly`- und `SameSite`-geschütztes Sitzungscookie. Automatische Sperre nach Inaktivität, Neustart oder ausdrücklichem Abmelden; „Fall beenden“ soll die Bedienoberfläche auf Wunsch ebenfalls sperren.
4. **Verschlüsselte Übertragung:** Zieladresse `https://triagebox.local/` über Port 443 ohne sichtbare Portnummer. Für die vorgesehenen verwalteten Laptops wird das lokale Zertifikat beziehungsweise die lokale Zertifizierungsstelle einmalig vertrauenswürdig eingerichtet.
5. **Begrenztes Netzwerk:** Kein Internet-Routing und keine unnötigen Dienste im Hotspot. Firewall erlaubt nur die benötigte Weboberfläche sowie einen ausdrücklich administrativ freigegebenen Wartungszugang. Ethernet verwendet dieselbe Web-Anmeldung.
6. **Verschlüsselter Fallspeicher:** `casefiles/`, `results/`, Berichte, Exporte und interner Papierkorb liegen vor realem Einsatz auf verschlüsseltem Speicher. Das Entsperrverfahren muss mit einem kopflosen Pi-Start vereinbar sein und darf den Schlüssel nicht ungeschützt auf derselben SD-Karte ablegen.
7. **Geheimnisse bleiben lokal:** WLAN- und Gerätepasswort, Zertifikatsschlüssel und Speicherentsperrung gehören in root-geschützte lokale Konfiguration beziehungsweise einen geeigneten Schlüsselspeicher, niemals in Git, Bericht oder Audit-Log.

## Bewusst nicht vorgesehen

- keine zentrale Benutzerverwaltung
- kein Active Directory oder Cloud-Zwang
- keine Rollenmatrix für den ersten Feldprototyp
- keine dauerhafte Anmeldung im Browser
- kein offener Hotspot und keine ungeschützte Weboberfläche

Einzelne Benutzerkonten werden erst neu bewertet, wenn mehrere Organisationen oder unterschiedliche Berechtigungsrollen das Gerät tatsächlich gemeinsam verwenden. Bis dahin ist ein gemeinsames Gerätepasswort die bewusst einfache Zugangssperre; es ersetzt keine personengebundene Identitätsprüfung.

## Noch zu entscheiden und zu testen

- [ ] tatsächliche WPA2-/WPA3-Fähigkeit des Raspberry Pi 3B+ im Access-Point-Betrieb validieren
- [ ] Verfahren für Ersteinrichtung, Wechsel und Wiederherstellung von WLAN- und Gerätepasswort festlegen
- [ ] sichere Sitzung, Zeitlimit, Abmeldung und Sperre nach Neustart implementieren und testen
- [ ] lokales HTTPS-Zertifikatsverfahren für die vorgesehenen Laptops festlegen
- [ ] Firewall, Ethernet-Fallback und Verhalten ohne Internetverbindung praktisch prüfen
- [ ] verschlüsselten Fall-/Ergebnisspeicher einschließlich Entsperren, Stromausfall und Wiederherstellung validieren
- [ ] festlegen, wann exportierte Berichte vom Bedienlaptop entfernt oder in die genehmigte Fallablage übernommen werden
- [ ] Sicherheitsreview und dokumentierte Freigabe vor echtem Einsatz durchführen

## Referenzen

- [Raspberry Pi: passwortgeschützten Hotspot mit NetworkManager erstellen](https://www.raspberrypi.com/tutorials/host-a-hotel-wifi-hotspot/)
- [BSI: WPA3 beziehungsweise WPA2 und starkes WLAN-Passwort](https://www.bsi.bund.de/DE/Themen/Verbraucherinnen-und-Verbraucher/Informationen-und-Empfehlungen/Cyber-Sicherheitsempfehlungen/cyber-sicherheitsempfehlungen.html)
- [OWASP: sichere serverseitige Sitzungen und Cookie-Eigenschaften](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [BSI: Verschlüsselung auf mobilen Geräten](https://www.bsi.bund.de/DE/Themen/Verbraucherinnen-und-Verbraucher/Informationen-und-Empfehlungen/Cyber-Sicherheitsempfehlungen/Daten-sichern-verschluesseln-und-loeschen/Datenverschluesselung/Verschluesselung-auf-mobilen-Geraeten/verschluesselung-auf-mobilen-Geraeten.html)

## English summary

The planned field appliance uses a password-protected private hotspot, one shared device unlock per work session, short server-side sessions, local HTTPS, a restricted network, and encrypted case storage. Operator initials remain audit metadata rather than authentication. Central user management is intentionally deferred unless a real multi-user requirement emerges.
