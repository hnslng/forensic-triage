# Dokumentation / Documentation

Die Projektdokumentation ist primär auf Deutsch verfasst. Die README enthält zusätzlich eine englische Zusammenfassung; zentrale Fachbegriffe und Grenzen sind in den einzelnen Dokumenten ebenfalls kurz auf Englisch zusammengefasst.

## Einstieg

1. [Installation und Aktualisierung](installation.md)
2. [So funktioniert TRIAGE//BOX](how-it-works.md)
3. [Konfiguration](configuration.md)
4. [Bedienung und Fallworkflow](operation.md)
5. [Forensische Sicherheitsgrenzen](forensic-safety.md)
6. [Geplantes Zugriffsschutzkonzept](security-concept.md)
7. [Roadmap und offene Aufgaben](roadmap.md)

## Technische Unterlagen

- [Architektur](architecture.md)
- [Lokale Fallakte und Protokollierung](case-archive.md)
- [Testplan](test-plan.md)
- [Vorbereitung einer möglichen öffentlichen Bereitstellung](publication-review-2026-08-27.md)
- [Sicherheitsrichtlinie](../SECURITY.md)
- [Nutzungsbedingungen](../LICENSE.md)
- [Änderungshistorie](../CHANGELOG.md)

## Interne Entwicklungsnachweise

Diese Unterlagen gehören nicht zum Bedien- oder Installationsablauf auf dem Raspberry Pi, bleiben aber für Reproduzierbarkeit und Werkzeugvalidierung erhalten:

- [Generische Entwicklungsumgebung](development-setup.md)
- [Validierung vom 26. August 2026](validation-2026-08-26.md)

## Maßgeblicher Stand

Die Paketversion steht in `pyproject.toml` und `src/forensic_triage/__init__.py`. Für Version 0.2.0-alpha.23 lautet die Python-Version gemäß PEP 440 `0.2.0a23`; der Git-Tag lautet `v0.2.0-alpha.23`.

Anleitungen im Repository sind Entwicklungs- und Betriebsunterlagen für den privaten Prototyp. Sie ersetzen keine behördlichen Vorgaben, Verfahrensanweisungen, Freigaben oder formale Werkzeugvalidierung.

## English

The documentation is maintained primarily in German. Start with the bilingual project [README](../README.md). Package and Git release identifiers are documented above. These documents describe a private alpha prototype and do not replace organizational procedures or formal forensic validation.
