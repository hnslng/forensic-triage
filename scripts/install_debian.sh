#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CONFIG_DIR="/etc/forensic-triage"
CONFIG_FILE="$CONFIG_DIR/triage.env"
PI_NETWORK_CONFIG="$CONFIG_DIR/pi-network.env"
SERVICE_FILE="/etc/systemd/system/forensic-triage-web.service"
PI_FIREWALL_SERVICE_FILE="/etc/systemd/system/forensic-triage-pi-firewall.service"
SERVICE_TEMPLATE="$PROJECT_ROOT/deploy/forensic-triage-web.service.in"
CONFIG_TEMPLATE="$PROJECT_ROOT/deploy/triage.env.example"
PI_NETWORK_TEMPLATE="$PROJECT_ROOT/deploy/pi-network.env.example"
PI_FIREWALL_SERVICE_TEMPLATE="$PROJECT_ROOT/deploy/forensic-triage-pi-firewall.service.in"
CHECK_ONLY=false
PI_MODE=false

for argument in "$@"; do
  case "$argument" in
    --check) CHECK_ONLY=true ;;
    --pi) PI_MODE=true ;;
    *)
      echo "Verwendung: sudo $0 [--check] [--pi]" >&2
      exit 2
      ;;
  esac
done

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

REQUIRED_FILES=("$PROJECT_ROOT/pyproject.toml" "$SERVICE_TEMPLATE" "$CONFIG_TEMPLATE")
if $PI_MODE; then
  REQUIRED_FILES+=(
    "$PI_NETWORK_TEMPLATE"
    "$PI_FIREWALL_SERVICE_TEMPLATE"
    "$PROJECT_ROOT/scripts/configure_pi_network.sh"
    "$PROJECT_ROOT/scripts/apply_pi_firewall.sh"
  )
fi
for required in "${REQUIRED_FILES[@]}"; do
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
  echo "Pi-Modus: $PI_MODE"
  exit 0
fi

INSTALL_OWNER="$(stat -c '%U' "$PROJECT_ROOT")"
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
PACKAGES=(git python3 python3-venv python3-pip sleuthkit util-linux udev eject)
if $PI_MODE; then
  PACKAGES+=(network-manager avahi-daemon libnss-mdns nftables)
fi
apt-get install -y "${PACKAGES[@]}"

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

if $PI_MODE; then
  if [[ ! -f "$PI_NETWORK_CONFIG" ]]; then
    install -o root -g root -m 0600 "$PI_NETWORK_TEMPLATE" "$PI_NETWORK_CONFIG"
    echo "Pi-Netzwerkkonfiguration angelegt: $PI_NETWORK_CONFIG"
  else
    echo "Vorhandene Pi-Netzwerkkonfiguration bleibt unverändert: $PI_NETWORK_CONFIG"
  fi
  "$PROJECT_ROOT/scripts/configure_pi_network.sh" "$PI_NETWORK_CONFIG" "$CONFIG_FILE"
fi

TEMP_SERVICE="$(mktemp)"
sed "s|@PROJECT_ROOT@|$PROJECT_ROOT|g" "$SERVICE_TEMPLATE" > "$TEMP_SERVICE"
install -o root -g root -m 0644 "$TEMP_SERVICE" "$SERVICE_FILE"
rm -f "$TEMP_SERVICE"

if $PI_MODE; then
  TEMP_PI_FIREWALL_SERVICE="$(mktemp)"
  sed "s|@PROJECT_ROOT@|$PROJECT_ROOT|g" "$PI_FIREWALL_SERVICE_TEMPLATE" > "$TEMP_PI_FIREWALL_SERVICE"
  install -o root -g root -m 0644 "$TEMP_PI_FIREWALL_SERVICE" "$PI_FIREWALL_SERVICE_FILE"
  rm -f "$TEMP_PI_FIREWALL_SERVICE"
fi

systemctl daemon-reload
systemctl enable --now forensic-triage-web.service
if $PI_MODE; then
  systemctl enable NetworkManager.service avahi-daemon.service forensic-triage-pi-firewall.service
  systemctl restart forensic-triage-pi-firewall.service
fi
systemctl restart forensic-triage-web.service

echo
echo "TRIAGE//BOX wurde installiert."
echo "Version: $("$PROJECT_ROOT/.venv/bin/forensic-triage-web" --version)"
echo "Dienst: $(systemctl is-active forensic-triage-web.service)"
echo "Konfiguration: $CONFIG_FILE"
if $PI_MODE; then
  # shellcheck disable=SC1090
  source "$PI_NETWORK_CONFIG"
  INSTALLED_WEB_PORT="$(sed -n 's/^FORENSIC_TRIAGE_WEB_PORT=//p' "$CONFIG_FILE" | tail -n 1)"
  echo "Hotspot vorbereitet: ${TRIAGEBOX_WIFI_SSID:-TRIAGEBOX}"
  echo "Adresse: http://${TRIAGEBOX_HOSTNAME:-triagebox}.local:${INSTALLED_WEB_PORT:-8787}/"
  echo "WLAN-Konfiguration: $PI_NETWORK_CONFIG"
  echo "Jetzt neu starten: sudo reboot"
fi
