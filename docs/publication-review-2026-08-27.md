# Vorbereitung für eine mögliche spätere öffentliche Bereitstellung

Stand: 27. August 2026

## Geprüfter Umfang

- aktueller Arbeitsbaum und alle erreichbaren Git-Commits
- Dateinamen und Inhalte auf typische private Schlüssel, GitHub-Tokens, API-Schlüssel und lokale Konfigurationsdateien
- Git-Tracking von `casefiles/`, `results/`, Exporten und Umgebungsdateien
- Commit-Autorendaten

## Ergebnis

Es wurden keine privaten Schlüssel, Zugriffstokens, API-Schlüssel oder echten Fallakten im Repositoryverlauf gefunden. Die Commit-Autoradresse ist eine GitHub-`noreply`-Adresse.

Historisch enthalten sind eine private RFC-1918-Adresse der früheren Entwicklungs-VM und das ausdrücklich als Entwicklungsvorgabe dokumentierte Löschkennwort einer alten Alpha-Version. Die aktuelle Version enthält weder diese lokale Adresse in der aktiven Vorlage noch ein Standardpasswort. Alte Alpha-Stände bleiben ausdrücklich ohne Einsatzfreigabe.

Persönliche Starterdateien werden künftig von Git ignoriert. Das Repository enthält nur noch eine neutrale Vorlage. Fallakten, Ergebnisse, Exporte, `.env`-Dateien sowie Schlüsseldateien sind ausgeschlossen.

## Veröffentlichungshinweis

Das Repository bleibt vorerst privat. Falls es später öffentlich gestellt wird, ist die Sichtbarkeit keine fachliche, technische oder rechtliche Einsatzfreigabe. Die Nutzungsrechte richten sich nach `LICENSE.md`; Sicherheitsmeldungen nach `SECURITY.md`.
