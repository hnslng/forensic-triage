#!/bin/zsh

set -u

TRIAGE_URL="http://127.0.0.1:8787/"
TRIAGE_HOST="triage@10.0.1.105"
TRIAGE_KEY="${HOME}/.ssh/forensic_triage_agent"

if ! curl -fsS --max-time 2 "$TRIAGE_URL/api/status" >/dev/null 2>&1; then
  ssh -fN \
    -L 8787:127.0.0.1:8787 \
    -i "$TRIAGE_KEY" \
    -o BatchMode=yes \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    "$TRIAGE_HOST"
fi

if curl -fsS --max-time 5 "$TRIAGE_URL/api/status" >/dev/null 2>&1; then
  open "$TRIAGE_URL"
  echo "TRIAGE//BOX ist verbunden und wurde im Browser geöffnet."
else
  echo "Verbindung fehlgeschlagen. Bitte prüfen: VM eingeschaltet, Netzwerk verbunden."
  read -r "?Zum Schließen Eingabetaste drücken …"
  exit 1
fi
