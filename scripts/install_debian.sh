#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CONFIG_DIR="/etc/forensic-triage"
CONFIG_FILE="$CONFIG_DIR/triage.env"
SERVICE_FILE="/etc/systemd/system/forensic-triage-web.service"
SERVICE_TEMPLATE="$PROJECT_ROOT/deploy/forensic-triage-web.service.in"
CONFIG_TEMPLATE="$PROJECT_ROOT/deploy/triage.env.example"
CHECK_ONLY=false

if [[ "${1:-}" == "--check" ]]; then
  CHECK_ONLY=true
elif [[ $# -gt 0 ]]; then
  echo "Verwendung: sudo $0 [--check]" >&2
  exit 2
fi

if [[ $EUID -ne 0 ]]; then
  echo "Bitte mit sudo ausführen: sudo $0" >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  echo "Nicht unterstütztes System: /etc/os-release fehlt." >&2
  exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID_LIKE:-} ${ID:-}" != *debian* ]]; then
  echo "Dieses Installationsskript unterstützt derzeit nur Debian-basierte Systeme." >&2
  exit 1
fi

if [[ ! "$PROJECT_ROOT" =~ ^/[A-Za-z0-9._/-]+$ ]]; then
  echo "Der Projektpfad enthält für die sichere Dienstinstallation ungeeignete Zeichen: $PROJECT_ROOT" >&2
  exit 1
fi

for required in "$PROJECT_ROOT/pyproject.toml" "$SERVICE_TEMPLATE" "$CONFIG_TEMPLATE"; do
  if [[ ! -f "$required" ]]; then
    echo "Projektdatei fehlt: $required" >&2
    exit 1
  fi
done

if $CHECK_ONLY; then
  echo "Installationsprüfung erfolgreich."
  echo "Projekt: $PROJECT_ROOT"
  echo "Konfiguration: $CONFIG_FILE"
  echo "Dienst: $SERVICE_FILE"
  exit 0
fi

INSTALL_OWNER="${SUDO_USER:-$(stat -c '%U' "$PROJECT_ROOT")}"
if ! id "$INSTALL_OWNER" >/dev/null 2>&1; then
  echo "Installationsbenutzer existiert nicht: $INSTALL_OWNER" >&2
  exit 1
fi

run_as_owner() {
  if [[ "$INSTALL_OWNER" == "root" ]]; then
    "$@"
  else
    runuser -u "$INSTALL_OWNER" -- "$@"
  fi
}

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git python3 python3-venv python3-pip sleuthkit util-linux udev eject

if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  run_as_owner python3 -m venv "$PROJECT_ROOT/.venv"
fi
run_as_owner "$PROJECT_ROOT/.venv/bin/python" -m pip install --upgrade pip
run_as_owner "$PROJECT_ROOT/.venv/bin/python" -m pip install -e "$PROJECT_ROOT[test]"
run_as_owner "$PROJECT_ROOT/.venv/bin/python" -m pytest "$PROJECT_ROOT/tests" -q

install -d -m 0750 "$CONFIG_DIR"
if [[ ! -f "$CONFIG_FILE" ]]; then
  TEMP_CONFIG="$(mktemp)"
  sed "s|@PROJECT_ROOT@|$PROJECT_ROOT|g" "$CONFIG_TEMPLATE" > "$TEMP_CONFIG"
  install -o root -g root -m 0600 "$TEMP_CONFIG" "$CONFIG_FILE"
  rm -f "$TEMP_CONFIG"
  echo "Neue Konfiguration angelegt: $CONFIG_FILE"
else
  echo "Vorhandene Konfiguration bleibt unverändert: $CONFIG_FILE"
fi

TEMP_SERVICE="$(mktemp)"
sed "s|@PROJECT_ROOT@|$PROJECT_ROOT|g" "$SERVICE_TEMPLATE" > "$TEMP_SERVICE"
install -o root -g root -m 0644 "$TEMP_SERVICE" "$SERVICE_FILE"
rm -f "$TEMP_SERVICE"

systemctl daemon-reload
systemctl enable --now forensic-triage-web.service
systemctl restart forensic-triage-web.service

echo
echo "TRIAGE//BOX wurde installiert."
echo "Version: $("$PROJECT_ROOT/.venv/bin/forensic-triage-web" --version)"
echo "Dienst: $(systemctl is-active forensic-triage-web.service)"
echo "Konfiguration: $CONFIG_FILE"
