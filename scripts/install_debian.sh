#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CONFIG_DIR="/etc/forensic-triage"
CONFIG_FILE="$CONFIG_DIR/triage.env"
PI_NETWORK_CONFIG="$CONFIG_DIR/pi-network.env"
SERVICE_FILE="/etc/systemd/system/forensic-triage-web.service"
UPDATE_SERVICE_FILE="/etc/systemd/system/forensic-triage-update@.service"
UPDATE_TIMER_FILE="/etc/systemd/system/forensic-triage-update-check.timer"
NGINX_SITE_FILE="/etc/nginx/sites-available/forensic-triage"
NGINX_ENABLED_FILE="/etc/nginx/sites-enabled/forensic-triage"
PI_FIREWALL_SERVICE_FILE="/etc/systemd/system/forensic-triage-pi-firewall.service"
SERVICE_TEMPLATE="$PROJECT_ROOT/deploy/forensic-triage-web.service.in"
UPDATE_SERVICE_TEMPLATE="$PROJECT_ROOT/deploy/forensic-triage-update@.service.in"
UPDATE_TIMER_TEMPLATE="$PROJECT_ROOT/deploy/forensic-triage-update-check.timer"
NGINX_TEMPLATE="$PROJECT_ROOT/deploy/forensic-triage-nginx.conf.in"
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
REQUIRED_FILES+=("$UPDATE_SERVICE_TEMPLATE" "$UPDATE_TIMER_TEMPLATE" "$NGINX_TEMPLATE" "$PROJECT_ROOT/scripts/update_triagebox.sh")
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
PACKAGES=(git python3 python3-venv python3-pip sleuthkit util-linux udev eject 7zip nginx)
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
RUNTIME_LINK="${PROJECT_ROOT}-current"
RELEASES_ROOT="${PROJECT_ROOT}-releases"
if [[ -e "$RUNTIME_LINK" && ! -L "$RUNTIME_LINK" ]]; then
  echo "Laufzeitpfad ist kein sicher austauschbarer Symlink: $RUNTIME_LINK" >&2
  exit 1
fi
# A deliberate manual installation means that this tested checkout becomes
# the live release. Otherwise a previous atomic updater release would remain
# active even though pip and the service templates were refreshed here.
ln -sfn "$PROJECT_ROOT" "$RUNTIME_LINK"
if [[ ! -f "$CONFIG_FILE" ]]; then
  TEMP_CONFIG="$(mktemp)"
  sed -e "s|@PROJECT_ROOT@|$PROJECT_ROOT|g" \
      -e "s|@RUNTIME_ROOT@|$RUNTIME_LINK|g" \
      -e "s|@RELEASES_ROOT@|$RELEASES_ROOT|g" "$CONFIG_TEMPLATE" > "$TEMP_CONFIG"
  install -o root -g root -m 0600 "$TEMP_CONFIG" "$CONFIG_FILE"
  rm -f "$TEMP_CONFIG"
  echo "Neue Konfiguration angelegt: $CONFIG_FILE"
else
  echo "Vorhandene Konfiguration bleibt unverändert: $CONFIG_FILE"
  # Older installations used an absolute code directory. Keep case data where
  # it is, but let static files and the profile follow an atomic release link.
  sed -i "s|^FORENSIC_TRIAGE_WEB_ROOT=$PROJECT_ROOT/web$|FORENSIC_TRIAGE_WEB_ROOT=$RUNTIME_LINK/web|" "$CONFIG_FILE"
  sed -i "s|^FORENSIC_TRIAGE_PROFILE=$PROJECT_ROOT/profiles/default.yaml$|FORENSIC_TRIAGE_PROFILE=$RUNTIME_LINK/profiles/default.yaml|" "$CONFIG_FILE"
  grep -q '^FORENSIC_TRIAGE_RUNTIME_LINK=' "$CONFIG_FILE" || printf '\nFORENSIC_TRIAGE_RUNTIME_LINK=%s\n' "$RUNTIME_LINK" >>"$CONFIG_FILE"
  grep -q '^FORENSIC_TRIAGE_RELEASES_ROOT=' "$CONFIG_FILE" || printf 'FORENSIC_TRIAGE_RELEASES_ROOT=%s\n' "$RELEASES_ROOT" >>"$CONFIG_FILE"
  grep -q '^FORENSIC_TRIAGE_UPDATE_ENABLED=' "$CONFIG_FILE" || printf 'FORENSIC_TRIAGE_UPDATE_ENABLED=true\n' >>"$CONFIG_FILE"
  grep -q '^FORENSIC_TRIAGE_UPDATE_REMOTE=' "$CONFIG_FILE" || printf 'FORENSIC_TRIAGE_UPDATE_REMOTE=origin\n' >>"$CONFIG_FILE"
  grep -q '^FORENSIC_TRIAGE_UPDATE_STATE_FILE=' "$CONFIG_FILE" || printf 'FORENSIC_TRIAGE_UPDATE_STATE_FILE=/var/lib/forensic-triage/update-status.env\n' >>"$CONFIG_FILE"
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
sed -e "s|@PROJECT_ROOT@|$PROJECT_ROOT|g" -e "s|@RUNTIME_ROOT@|$RUNTIME_LINK|g" "$SERVICE_TEMPLATE" > "$TEMP_SERVICE"
install -o root -g root -m 0644 "$TEMP_SERVICE" "$SERVICE_FILE"
rm -f "$TEMP_SERVICE"

TEMP_UPDATE_SERVICE="$(mktemp)"
sed "s|@RUNTIME_ROOT@|$RUNTIME_LINK|g" "$UPDATE_SERVICE_TEMPLATE" > "$TEMP_UPDATE_SERVICE"
install -o root -g root -m 0644 "$TEMP_UPDATE_SERVICE" "$UPDATE_SERVICE_FILE"
rm -f "$TEMP_UPDATE_SERVICE"
install -o root -g root -m 0644 "$UPDATE_TIMER_TEMPLATE" "$UPDATE_TIMER_FILE"

WEB_PORT="$(sed -n 's/^FORENSIC_TRIAGE_WEB_PORT=//p' "$CONFIG_FILE" | tail -n 1)"
WEB_PORT="${WEB_PORT:-8787}"
TEMP_NGINX="$(mktemp)"
sed "s|@WEB_PORT@|$WEB_PORT|g" "$NGINX_TEMPLATE" > "$TEMP_NGINX"
install -o root -g root -m 0644 "$TEMP_NGINX" "$NGINX_SITE_FILE"
rm -f "$TEMP_NGINX"
ln -sfn "$NGINX_SITE_FILE" "$NGINX_ENABLED_FILE"
rm -f /etc/nginx/sites-enabled/default
nginx -t

if $PI_MODE; then
  TEMP_PI_FIREWALL_SERVICE="$(mktemp)"
  sed "s|@PROJECT_ROOT@|$PROJECT_ROOT|g" "$PI_FIREWALL_SERVICE_TEMPLATE" > "$TEMP_PI_FIREWALL_SERVICE"
  install -o root -g root -m 0644 "$TEMP_PI_FIREWALL_SERVICE" "$PI_FIREWALL_SERVICE_FILE"
  rm -f "$TEMP_PI_FIREWALL_SERVICE"
fi

systemctl daemon-reload
systemctl enable --now forensic-triage-web.service
systemctl enable --now nginx.service
systemctl enable --now forensic-triage-update-check.timer
if $PI_MODE; then
  systemctl enable NetworkManager.service avahi-daemon.service forensic-triage-pi-firewall.service
  systemctl restart forensic-triage-pi-firewall.service
fi
systemctl restart forensic-triage-web.service
systemctl reload nginx.service

echo
echo "TRIAGE//BOX wurde installiert."
echo "Version: $("$PROJECT_ROOT/.venv/bin/forensic-triage-web" --version)"
echo "Dienst: $(systemctl is-active forensic-triage-web.service)"
echo "Lokaler Zugang: http://127.0.0.1/"
echo "Konfiguration: $CONFIG_FILE"
if $PI_MODE; then
  # shellcheck disable=SC1090
  source "$PI_NETWORK_CONFIG"
  echo "Hotspot vorbereitet: ${TRIAGEBOX_WIFI_SSID:-TRIAGEBOX}"
  echo "Adresse: http://${TRIAGEBOX_HOSTNAME:-triagebox}.local/"
  echo "WLAN-Konfiguration: $PI_NETWORK_CONFIG"
  echo "Jetzt neu starten: sudo reboot"
fi
