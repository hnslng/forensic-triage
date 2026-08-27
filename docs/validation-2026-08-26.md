# Validierung mit physischem Medium – 26. August 2026

## Umgebung

- Debian 13 VM, Kernel `6.12.105+deb13-amd64`
- Python 3.13.5
- The Sleuth Kit 4.12.1
- SanDisk USB, 123.060.879.360 Bytes
- GPT mit einer exFAT-Partition `TRIAGE_TEST`

Der autorisierte Testdatenträger wurde nach wiederholter Prüfung von USB-Transport, Modell, Kapazität, Mountpoints und Abgrenzung zu `/dev/sda` neu partitioniert und schnellformatiert. Der synthetische Generator erzeugte 960 Dateien. Danach wurde das Medium unmountet sowie der Kernel-Read-only-Zustand gesetzt und vor der Analyse verifiziert.

## Ergebnis des mountfreien TSK-Laufs

- Validierung bestanden, keine Abweichungen
- Dateien: 960
- Ordner: 18
- logische Dateibytes: 553.421.052
- Stichworttreffer: 60
- Scanlaufzeit: 1.921,431 Sekunden (32:01,431)
- Read-only-Zustand nach Scan: `1`

Das Ergebnis liegt lokal im von Git ausgeschlossenen Verzeichnis `results/2026-08-26T093319Z_BM-001/`.

## Feststellung

Der erste Lauf enthielt ungefähr 149.000 gelöschte Einträge aus einer früheren Nutzung des schnellformatierten exFAT-Mediums. Dies lag außerhalb der Definition eines Inventars der aktuell vorhandenen Dateien. Der Scanner wurde deshalb auf `fls -u` umgestellt und filtert zusätzlich gelöschte, virtuelle TSK-, Orphan-, Volume-Label- und exFAT-Verwaltungseinträge. Sowohl die erneute Verarbeitung der gespeicherten Rohdaten als auch der abschließende End-to-End-Scan entsprachen dem Sollmanifest.

Auf diesem 114,6-GiB-exFAT-Medium liest der rekursive `fls`-Lauf annähernd das gesamte Volume, obwohl nur wenige aktive Dateien vorhanden sind. Kapazität und Datenträgerdurchsatz bestimmen deshalb die Laufzeit.

## Ergebnis des schnellen Modus

Dasselbe Medium wurde anschließend im Standardmodus `fast` gescannt. Das gesamte Blockgerät war bereits schreibgeschützt. Die Partition wurde vorübergehend mit `ro,nosuid,nodev,noexec` gemountet, die Optionen wurden programmatisch geprüft und der Mount vor Abschluss entfernt.

- Validierung bestanden, keine Abweichungen
- Dateien: 960
- Ordner: 18
- logische Dateibytes: 553.421.052
- Stichworttreffer: 60
- vom Scanner gemeldete Laufzeit: 0,732 Sekunden
- Read-only-Zustand nach Scan: `1`
- Mountpoint nach Scan: keiner

Das Ergebnis liegt lokal unter `results/2026-08-26T122801Z_BM-FAST-001/`.

## Aussagekraft und Grenzen

Dieser Test bestätigt den Sollbestand und den Read-only-Ablauf für genau diese Kombination aus Debian-VM, SanDisk, exFAT und synthetischen Dateien. Er validiert noch nicht mehrere reale Datenträger gleichzeitig, Raspberry Pi, CD/DVD, beschädigte Medien, andere Dateisysteme oder den Einsatz mit einem Hardware-Schreibblocker.

## English summary

A 960-file synthetic exFAT fixture on a physical SanDisk USB device matched the expected manifest with zero mismatches. The mount-free TSK scan took 32 minutes; the guarded fast read-only scan took 0.732 seconds and left no mountpoint. This validates only the documented VM/device/filesystem combination, not operational deployment.
