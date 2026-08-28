# Vorbereitung für eine mögliche spätere öffentliche Bereitstellung

Stand: 27. August 2026

## Geprüfter Umfang

- aktueller Arbeitsbaum und alle erreichbaren Git-Commits
- Dateinamen und Inhalte auf typische private Schlüssel, GitHub-Tokens, API-Schlüssel und lokale Konfigurationsdateien
- Git-Tracking von `casefiles/`, `results/`, Exporten und Umgebungsdateien
- Commit-Autorendaten

## Ergebnis

Es wurden keine privaten Schlüssel, Zugriffstokens, API-Schlüssel oder echten Fallakten im Repositoryverlauf gefunden. Die Commit-Autoradresse ist eine GitHub-`noreply`-Adresse.

Historisch enthalten sind eine private RFC-1918-Adresse der früheren Entwicklungs-VM und das ausdrücklich als Entwicklungsvorgabe dokumentierte Löschkennwort einer alten Alpha-Version. Die aktuelle Pi-Vorlage enthält `triagebox123` ausschließlich als öffentlich bekannten Entwicklungsplatzhalter. Dieser Wert ist kein betriebliches Geheimnis und ausdrücklich nicht für echten Einsatz vorgesehen. Echte lokale Kennwörter bleiben außerhalb von Git unter `/etc/forensic-triage/`.

Persönliche Starterdateien werden von Git ignoriert und es wird keine Mac-/VM-Startervorlage mehr ausgeliefert. Fallakten, Ergebnisse, Exporte, `.env`-Dateien sowie Schlüsseldateien sind ausgeschlossen.

## Veröffentlichungshinweis

Das Repository bleibt grundsätzlich privat, kann für den dokumentierten Bootstrap aber bewusst kurzzeitig öffentlich geschaltet werden. Vor jeder solchen Phase ist der aktuelle Stand erneut auf Geheimnisse und Falldaten zu prüfen. Sichtbarkeit ist keine fachliche, technische oder rechtliche Einsatzfreigabe. Die Nutzungsrechte richten sich nach `LICENSE.md`; Sicherheitsmeldungen nach `SECURITY.md`.
