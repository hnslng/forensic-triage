#!/usr/bin/env bash

set -euo pipefail

NETWORK_CONFIG="${1:-/etc/forensic-triage/pi-network.env}"
WEB_CONFIG="${2:-/etc/forensic-triage/triage.env}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "Die Pi-Netzwerkkonfiguration muss als root ausgeführt werden." >&2
  exit 1
fi

if [[ ! -r /proc/device-tree/model ]] || ! tr -d '\0' </proc/device-tree/model | grep -qi "Raspberry Pi"; then
  echo "--pi wurde verlangt, aber dieses System wurde nicht als Raspberry Pi erkannt." >&2
  exit 1
fi

if [[ ! -r "$NETWORK_CONFIG" || ! -f "$WEB_CONFIG" ]]; then
  echo "Konfigurationsdatei fehlt: $NETWORK_CONFIG oder $WEB_CONFIG" >&2
  exit 1
fi

# The file is root-owned (0600) and deliberately uses shell-compatible KEY=VALUE syntax.
# shellcheck disable=SC1090
source "$NETWORK_CONFIG"

: "${TRIAGEBOX_WIFI_SSID:?TRIAGEBOX_WIFI_SSID fehlt}"
: "${TRIAGEBOX_WIFI_PASSWORD:?TRIAGEBOX_WIFI_PASSWORD fehlt}"
: "${TRIAGEBOX_WIFI_INTERFACE:=wlan0}"
: "${TRIAGEBOX_WIFI_CONNECTION:=TRIAGEBOX-HOTSPOT}"
: "${TRIAGEBOX_WIFI_ADDRESS:=10.42.0.1/24}"
: "${TRIAGEBOX_HOSTNAME:=triagebox}"
: "${TRIAGEBOX_WIFI_COUNTRY:=AT}"

if (( ${#TRIAGEBOX_WIFI_PASSWORD} < 8 || ${#TRIAGEBOX_WIFI_PASSWORD} > 63 )); then
  echo "Das WLAN-Kennwort muss 8 bis 63 Zeichen lang sein." >&2
  exit 1
fi
if [[ ! "$TRIAGEBOX_WIFI_INTERFACE" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Ungültige WLAN-Schnittstelle." >&2
  exit 1
fi
if [[ ! "$TRIAGEBOX_HOSTNAME" =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$ ]]; then
  echo "Ungültiger Hostname: $TRIAGEBOX_HOSTNAME" >&2
  exit 1
fi
if [[ ! "$TRIAGEBOX_WIFI_ADDRESS" =~ ^[0-9.]+/[0-9]{1,2}$ ]]; then
  echo "Ungültige Hotspot-Adresse: $TRIAGEBOX_WIFI_ADDRESS" >&2
  exit 1
fi
if ! command -v nmcli >/dev/null 2>&1; then
  echo "NetworkManager/nmcli ist nicht installiert." >&2
  exit 1
fi
if ! nmcli -t -f DEVICE,TYPE device status | grep -Fqx "$TRIAGEBOX_WIFI_INTERFACE:wifi"; then
  echo "WLAN-Schnittstelle $TRIAGEBOX_WIFI_INTERFACE wurde nicht gefunden." >&2
  exit 1
fi

# Activating AP mode disconnects any existing Wi-Fi client connection. Refuse
# to cut off a remote installer; the documented Pi setup path uses Ethernet.
if [[ -n "${SSH_CONNECTION:-}" ]]; then
  SSH_CLIENT_IP="${SSH_CONNECTION%% *}"
  SSH_INTERFACE="$(ip route get "$SSH_CLIENT_IP" 2>/dev/null | sed -n 's/.* dev \([^ ]*\).*/\1/p' | head -n 1)"
  if [[ "$SSH_INTERFACE" == "$TRIAGEBOX_WIFI_INTERFACE" ]]; then
    echo "Die SSH-Sitzung läuft über $TRIAGEBOX_WIFI_INTERFACE. Bitte Pi per Ethernet verbinden und --pi erneut ausführen." >&2
    exit 1
  fi
fi

hostnamectl set-hostname "$TRIAGEBOX_HOSTNAME"
if command -v raspi-config >/dev/null 2>&1; then
  raspi-config nonint do_wifi_country "$TRIAGEBOX_WIFI_COUNTRY"
fi

if ! nmcli -t -f NAME connection show | grep -Fqx "$TRIAGEBOX_WIFI_CONNECTION"; then
  nmcli connection add \
    type wifi ifname "$TRIAGEBOX_WIFI_INTERFACE" \
    con-name "$TRIAGEBOX_WIFI_CONNECTION" ssid "$TRIAGEBOX_WIFI_SSID"
fi

nmcli connection modify "$TRIAGEBOX_WIFI_CONNECTION" \
  connection.interface-name "$TRIAGEBOX_WIFI_INTERFACE" \
  connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  802-11-wireless.mode ap \
  802-11-wireless.band bg \
  802-11-wireless.ssid "$TRIAGEBOX_WIFI_SSID" \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.proto rsn \
  802-11-wireless-security.pairwise ccmp \
  802-11-wireless-security.psk "$TRIAGEBOX_WIFI_PASSWORD" \
  ipv4.method shared \
  ipv4.addresses "$TRIAGEBOX_WIFI_ADDRESS" \
  ipv6.method disabled

nmcli radio wifi on
"$SCRIPT_DIR/apply_pi_firewall.sh" "$NETWORK_CONFIG"
nmcli connection up "$TRIAGEBOX_WIFI_CONNECTION"

HOTSPOT_IP="${TRIAGEBOX_WIFI_ADDRESS%/*}"
if grep -q '^FORENSIC_TRIAGE_WEB_HOST=' "$WEB_CONFIG"; then
  sed -i "s/^FORENSIC_TRIAGE_WEB_HOST=.*/FORENSIC_TRIAGE_WEB_HOST=$HOTSPOT_IP/" "$WEB_CONFIG"
else
  printf '\nFORENSIC_TRIAGE_WEB_HOST=%s\n' "$HOTSPOT_IP" >>"$WEB_CONFIG"
fi
WEB_PORT="$(sed -n 's/^FORENSIC_TRIAGE_WEB_PORT=//p' "$WEB_CONFIG" | tail -n 1)"
WEB_PORT="${WEB_PORT:-8787}"

echo "Pi-Netzwerk vorbereitet."
echo "Hostname: $TRIAGEBOX_HOSTNAME.local"
echo "Hotspot: $TRIAGEBOX_WIFI_SSID"
echo "Adresse: http://$TRIAGEBOX_HOSTNAME.local:$WEB_PORT/"
echo "Das WLAN-Kennwort steht nur in $NETWORK_CONFIG."
